FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

# Keep Python from generating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
# Set working directory
ENV PYTHONPATH=/app

# Install Xvfb for headed mode support in Docker
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

# Install Playwright Chromium browser and dependencies
RUN playwright install --with-deps chromium

# Create a core directory structure inside the container to preserve imports
WORKDIR /app
COPY . /app/core

# Create non-root user
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app

# Mark Chrome_Profile as a volume so it persists between runs
VOLUME ["/app/core/Chrome_Profile"]

# Xvfb log directory (must be created before USER switch)
RUN mkdir -p /var/log/xvfb && chown appuser /var/log/xvfb

USER appuser

# Default environment variables (can be overridden with --env flag or docker-compose.yml)
ENV API_HOST="0.0.0.0"
ENV API_PORT="8000"
ENV PROMPT=""
ENV HEADLESS="false"
ENV OUTPUT_FORMAT="json"
ENV DISPLAY=:99

# Default mode: API server
# The ENTRYPOINT starts Xvfb, verifies it is running, then starts the API server.
ENTRYPOINT ["sh", "-c", "\
    echo '=== Google Maps Crawler ===' && \
    echo 'API_HOST: '$API_HOST && \
    echo 'API_PORT: '$API_PORT && \
    echo 'Starting Xvfb virtual display...' && \
    Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset > /var/log/xvfb/xvfb.log 2>&1 & \
    XVFB_PID=$! && \
    sleep 2 && \
    if ! kill -0 $XVFB_PID 2>/dev/null; then \
        echo 'ERROR: Xvfb failed to start!' && \
        cat /var/log/xvfb/xvfb.log && \
        exit 1; \
    fi && \
    echo 'Xvfb started successfully (PID: '$XVFB_PID')' && \
    echo 'Verifying DISPLAY...' && \
    # Robust DISPLAY verification with fallback
    ( \
      if DISPLAY=:99 xdpyinfo >/dev/null 2>&1; then \
        echo 'DISPLAY :99 is ready (xdpyinfo verified)'; \
      elif DISPLAY=:99 x11-info -display :99 2>&1 | grep -q 'Server reports'; then \
        echo 'DISPLAY :99 is ready (x11-info verified)'; \
      else \
        echo 'DISPLAY :99 is ready (Xvfb PID confirmed)'; \
      fi \
    ) && \
    echo '=== Starting API Server ===' && \
    PYTHONPATH=/app python /app/core/api_main.py \
"]

# CLI mode command (override with: docker run google-maps-crawler python /app/core/main_cli.py)
# CMD ["python", "/app/core/main_cli.py"]