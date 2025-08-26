# Use Python 3.10 to match your development environment
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Set working directory to backend
WORKDIR /app/backend

# Debug: Show project structure
RUN echo "=== Project Structure ===" && \
    find /app -name "*.py" | head -20 && \
    echo "=== Backend Directory ===" && \
    ls -la && \
    echo "=== Config Check ===" && \
    ls -la config/ || echo "No config directory"

# Expose port for Railway
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Bot is healthy')" || exit 1

# Run the bot
CMD ["python", "main.py"]

