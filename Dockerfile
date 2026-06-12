# ============================================================
# Day07 — Knowledge-Base RAG (Streamlit) — production image
#
# Runs with NO API key (mock embedder + demo LLM fallback).
# Set ANTHROPIC_API_KEY as a platform secret to enable Claude commentary.
#
# Build:  docker build -t day07-rag .
# Run:    docker run -p 8501:8501 day07-rag
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Install deps first (layer cache — only rebuilds when requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code, source package, and the knowledge-base data files
COPY app.py .
COPY src/ ./src/
COPY data/ ./data/

# Documentation only — the real port comes from $PORT at runtime
EXPOSE 8501

# Streamlit must bind 0.0.0.0 and the platform's injected $PORT.
# headless=true disables the "open browser" prompt; CORS off for proxy hosting.
CMD streamlit run app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
