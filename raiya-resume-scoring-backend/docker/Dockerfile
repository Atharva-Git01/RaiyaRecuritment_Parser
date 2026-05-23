FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including PostgreSQL client for pgvector)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies — LangGraph 0.6.x and langgraph-checkpoint-postgres
# are pinned in requirements.txt. Do not pip-install -U here, that would silently
# upgrade past the pinned range and risk breaking the AsyncPostgresSaver wiring.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (includes all modules)
COPY . .

# Ensure extraction modules are importable from the backend root
ENV PYTHONPATH="/app:/app/resume_extraction_normalization:/app/jd_extraction_normalization_scoring_weight_assignment"

# Create storage subdirectories used by batch_service / report_generator.
# storage/resumes  — PDF bytes written by add_resume_to_batch
# storage/jd       — JD PDF bytes (populated by JD upload route)
# storage/reports  — PDFs written by report_generator_node
# The extraction module subdirs cache hashed OCR results.
RUN mkdir -p /app/storage/resumes \
    /app/storage/jd \
    /app/storage/reports \
    /app/resume_extraction_normalization/hashed_resume_extraction_results \
    /app/jd_extraction_normalization_scoring_weight_assignment/hashed_jd_extraction_results

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); assert r.status_code == 200"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
