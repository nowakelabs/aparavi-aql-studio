# Multi-stage build for Aparavi Query Assistant
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user to run the application
RUN groupadd -r aparavi && \
    useradd -r -g aparavi -d /home/aparavi -m aparavi && \
    mkdir -p /home/aparavi/.aparavi-query-assistant && \
    chown -R aparavi:aparavi /home/aparavi

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/aparavi/.local

# Set environment variable for Python path
ENV PATH=/home/aparavi/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Copy the application code
COPY --chown=aparavi:aparavi . .

# Create necessary directories with correct permissions
RUN mkdir -p logs static/img && \
    chown -R aparavi:aparavi logs static

# Make port 8080 available
EXPOSE 8080

# Set up healthcheck to ensure application is running
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8080/ || exit 1

# Switch to non-root user
USER aparavi

# Run the application
CMD ["python", "app.py"]
