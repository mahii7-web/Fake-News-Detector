# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV TRANSFORMERS_CACHE=/app/model_cache
ENV HF_HOME=/app/model_cache

WORKDIR /app

# Install system dependencies (build-essential for sentencepiece if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only wheel first to keep the image slim (~1.5GB instead of 5GB+)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining python packages
COPY requirements.txt .
# Filter out torch from requirements.txt to prevent overriding CPU wheel
RUN grep -v "torch" requirements.txt > reqs_no_torch.txt && \
    pip install --no-cache-dir -r reqs_no_torch.txt

# Pre-download and bake HuggingFace models into Docker image for zero cold-start latency
RUN python -c "\
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline; \
print('Baking Model 1 (XLM-RoBERTa language detector)...'); \
pipeline('text-classification', model='papluca/xlm-roberta-base-language-detection'); \
print('Baking Model 2 (mDeBERTa-v3 zero-shot classifier)...'); \
pipeline('zero-shot-classification', model='MoritzLaurer/mDeBERTa-v3-base-mnli-xnli'); \
print('Models successfully baked into image!')"

# Copy application source code
COPY . .

# Ensure non-root user permissions (standard practice for HF Spaces and security)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

# Run with Gunicorn using dynamic PORT (defaults to 7860 for HF Spaces, works with Render/Railway $PORT)
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 2 --timeout 180"]
