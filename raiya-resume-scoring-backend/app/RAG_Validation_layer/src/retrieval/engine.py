"""
Evidence Retrieval — RAG-over-Evidence Layer (pgvector version)
=============================================
Retrieves semantically relevant historical evidence from pgvector (PostgreSQL 16)
and sends it to Azure OpenAI as context to generate an informed response.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, List, Optional

from langchain_openai import AzureChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from src.config import settings
from src.logging_config import logger


# ── LangChain Component Helpers ───────────────────────────────────────────

def _get_embeddings():
    """Returns the LangChain embeddings component."""
    return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)


def _get_llm(temperature: float = 0.2):
    """Returns the LangChain AzureChatOpenAI component."""
    return AzureChatOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
        api_version="2024-02-01",
        temperature=temperature,
    )


# ── pgvector Search Helper ───────────────────────────────────────────────

def _search_pgvector(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search evidence in pgvector using cosine similarity."""
    embeddings_model = _get_embeddings()
    query_vector = embeddings_model.embed_query(query)

    engine = create_engine(settings.SYNC_DATABASE_URL)
    matches = []

    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                SELECT chunk_text, metadata, 1 - (embedding <=> :emb::vector) as similarity
                FROM {settings.PGVECTOR_EVIDENCE_TABLE}
                ORDER BY embedding <=> :emb::vector
                LIMIT :k
            """),
            {"emb": str(query_vector), "k": top_k}
        )
        
        for row in result:
            matches.append({
                "score": float(row[2]),
                "metadata": {**row[1], "text": row[0]} if isinstance(row[1], dict) else {"text": row[0]}
            })
            
    return matches


# ── Prompt Builder ───────────────────────────────────────────────────────

def _build_rag_prompt(query: str, matches: list[dict[str, Any]]) -> str:
    """Combine retrieved evidence chunks into a RAG prompt."""
    context_parts: list[str] = []

    for i, match in enumerate(matches, start=1):
        meta = match.get("metadata") or {}
        score = round(match.get("score", 0.0), 4)
        job_title = meta.get("job_title", "Unknown")
        job_id = meta.get("job_id", "Unknown")
        timestamp = meta.get("timestamp", "Unknown")
        final_verdict = meta.get("final_verdict", "Unknown")
        chunk_text = meta.get("text", "").strip()

        context_parts.append(
            f"--- Evidence Chunk {i} (Similarity: {score}) ---\n"
            f"Job Title    : {job_title}\n"
            f"Job ID       : {job_id}\n"
            f"Timestamp    : {timestamp}\n"
            f"Final Verdict: {final_verdict}\n"
            f"Content      :\n{chunk_text}"
        )

    context_block = "\n\n".join(context_parts) if context_parts else "No evidence retrieved."

    return (
        "You are a validation analysis assistant. Use the following historical evidence "
        "as REFERENCE material to cross-check and calibrate your analysis. "
        "Form your own independent judgement.\n\n"
        "=== REFERENCE EVIDENCE ===\n"
        f"{context_block}\n\n"
        "=== USER QUESTION ===\n"
        f"{query}\n\n"
        "=== YOUR RESPONSE ==="
    )


# ── Public API ───────────────────────────────────────────────────────────

def retrieve_evidence(query: str, top_k: int = 5) -> dict[str, Any]:
    """Retrieves relevant evidence from pgvector and generates an LLM response."""
    logger.info(f"EVIDENCE RETRIEVAL — Query: {query}, Top-K: {top_k}")

    # 1. Search pgvector
    matches = _search_pgvector(query, top_k=top_k)

    # 2. Build prompt
    prompt = _build_rag_prompt(query, matches)

    # 3. Call LLM
    llm = _get_llm()
    system_content = "You are a RAG validation assistant."
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_content),
        ("human", "{prompt}")
    ])
    chain = prompt_template | llm
    
    logger.info("Generating response via Azure OpenAI...")
    response = chain.invoke({"prompt": prompt})
    llm_response = response.content.strip()

    return {
        "query": query,
        "matches": matches,
        "prompt": prompt,
        "llm_response": llm_response,
    }


# ── Corrective RAG (CRAG) Implementation ─────────────────────────────────

class GradeResponse(BaseModel):
    relevant: bool = Field(description="Whether the evidence is relevant to the query")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Short explanation for the grade")


def corrective_retrieve_evidence(query: str, top_k: int = 5) -> dict[str, Any]:
    """CRAG pipeline using pgvector and LLM grading."""
    logger.info(f"CORRECTIVE RAG — Query: {query}")

    # 1. Retrieve
    matches = _search_pgvector(query, top_k=top_k)
    if not matches:
        return {"query": query, "classification": "INCORRECT", "llm_response": "No evidence found."}

    # 2. Grade
    llm = _get_llm(temperature=0.0)
    parser = JsonOutputParser(pydantic_object=GradeResponse)
    grading_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a strict relevance grader."),
        ("human", "Query: {query}\nEvidence: {evidence}\n{format_instructions}")
    ])
    chain = grading_prompt | llm | parser

    graded_matches = []
    relevant_count = 0
    for m in matches:
        res = chain.invoke({
            "query": query,
            "evidence": m["metadata"]["text"],
            "format_instructions": parser.get_format_instructions()
        })
        m["relevant"] = res["relevant"]
        if res["relevant"]: relevant_count += 1
        graded_matches.append(m)

    # 3. Classify
    ratio = relevant_count / len(matches)
    classification = "CORRECT" if ratio >= 0.5 else ("AMBIGUOUS" if relevant_count > 0 else "INCORRECT")
    
    # 4. Generate
    refined = [m for m in graded_matches if m.get("relevant")]
    prompt = _build_rag_prompt(query, refined)
    response = _get_llm().invoke(prompt)

    return {
        "query": query,
        "classification": classification,
        "matches": graded_matches,
        "llm_response": response.content.strip()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--mode", choices=["standard", "corrective"], default="corrective")
    args = parser.parse_args()

    if args.mode == "corrective":
        res = corrective_retrieve_evidence(args.query)
    else:
        res = retrieve_evidence(args.query)
    
    print(json.dumps(res, indent=2))
