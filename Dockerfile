FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and profiles
COPY job_finder/ ./job_finder/
COPY profiles/ ./profiles/

# Create logs directory owned by appuser
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

USER appuser

# -u: unbuffered stdout/stderr — required so logs appear immediately in docker logs
CMD ["python", "-u", "-m", "job_finder.scheduler", "--profile", "profiles/default.yaml"]
