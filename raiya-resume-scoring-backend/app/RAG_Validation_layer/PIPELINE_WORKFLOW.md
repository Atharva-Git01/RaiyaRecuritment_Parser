# RAG Validation Pipeline Workflow

This document explains the architecture and logic of the RAG Validation Pipeline, detailing how each component contributes to the end-to-end validation process.

## Pipeline Overview

The pipeline validates AI-generated resume scores against a Job Description (JD) using a combination of deterministic rules, mathematical verification, and Retrieval-Augmented Generation (RAG).

```mermaid
graph TD
    A[data/inputs/job_description.json] --> B[main.py]
    A2[data/inputs/ai_score.json] --> B
    
    subgraph Core Package (src/)
        B --> C[validators/jd_validator.py]
        C --> D[validators/deterministic.py]
        D --> E[validators/mathematical.py]
        E --> F[processing/rule_based_evidence_generation.py]
        F --> G[processing/final_report.py]
    end
    
    subgraph Storage & RAG (src/retrieval/)
        G --> H[processing/evidence_generation.py]
        H --> I[retrieval/database.py]
        I --> J[(Pinecone Vector DB)]
        J --> K[retrieval/engine.py]
    end
    
    K --> L[LLM Response / Corrective RAG]
```

## Module Logic Explanation

### 1. [main.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/main.py)
**Role**: Unified Entry Point.
**Logic**: Parses CLI arguments and invokes the central pipeline orchestrator. It uses `src/config.py` for centralized path and credential management.

### 2. [src/core/pipeline.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/core/pipeline.py)
**Role**: Pipeline Orchestrator.
**Logic**: Coordinates the execution order of all modules. It manages the data flow between steps, ensuring that the output of one validator is correctly passed as context to the next.

### 3. [src/validators/jd_validator.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/validators/jd_validator.py)
**Role**: Input Normalization.
**Logic**: Standardizes the raw Job Description JSON. It normalizes section names, scales criteria weights (0-100), and ensures the schema is ready for validation.

### 4. [src/validators/deterministic.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/validators/deterministic.py)
**Role**: Semantic Evidence Layer.
**Logic**: Compares resume content with JD requirements using `sentence-transformers`. It identifies matched/missing skills and performs strict **hallucination checks**.

### 5. [src/validators/mathematical.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/validators/mathematical.py)
**Role**: Numerical Accuracy Layer.
**Logic**: Re-calculates scores based on semantic coverage to establish a "Ground Truth." It computes error metrics (MAE, RMSE) relative to the AI's output.

### 6. [src/processing/rule_based_evidence_generation.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/processing/rule_based_evidence_generation.py)
**Role**: Dynamic Rule Engine.
**Logic**: Analyzes the JD and Resume to dynamically generate validation rules (e.g., tenure risks, internship bias). These rules are applied to adjust the final scores.

### 7. [src/processing/final_report.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/processing/final_report.py)
**Role**: Result Consolidation.
**Logic**: Aggregates findings from all layers into a single audit report with a final `PASS/FAIL` verdict and supporting notes.

### 8. [src/processing/evidence_generation.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/processing/evidence_generation.py)
**Role**: Persistence Layer.
**Logic**: Compiles the validation session into a unified "Evidence Document" for historical indexing.

### 9. [src/retrieval/database.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/retrieval/database.py)
**Role**: Vector DB Management.
**Logic**: Chunks evidence documents, generates embeddings, and upserts them to Pinecone using LangChain.

### 10. [src/retrieval/engine.py](file:///c:/Users/Admin/Desktop/RAG_Validation_layer/src/retrieval/engine.py)
**Role**: RAG / Corrective RAG (CRAG).
**Logic**: Retrieves relevant evidence from Pinecone and uses an LLM (Azure OpenAI) to provide reasoned answers to user queries about the validation results.
