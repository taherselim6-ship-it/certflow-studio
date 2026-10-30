FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    HOME=/home/user

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user (UID 1000) for Hugging Face Spaces & container security
RUN useradd -m -u 1000 user

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure runtime storage directories exist and set appropriate ownership
RUN mkdir -p /app/templates_store /app/trainers_store /app/exports /app/fonts && \
    chown -R user:user /app

# Switch to non-root user
USER user

# Expose default Hugging Face Spaces port (7860) and standard app port (8000)
EXPOSE 7860
EXPOSE 8000

# Start Uvicorn server (respects cloud-injected $PORT e.g. Render, defaulting to 7860 for Hugging Face)
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-7860}"]

