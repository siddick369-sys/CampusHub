# --- Dockerfile (Production) ---
FROM python:3.11-bookworm as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

# Install system build dependencies (only those not in bookworm full)
RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
    libpq-dev \
    libcairo2-dev \
    libffi-dev \
    netcat-openbsd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# Final stage
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# Install runtime system dependencies (Adding WeasyPrint requirements)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    libcairo2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi8 \
    netcat-openbsd \
    gettext \
    shared-mime-info && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy project files
COPY . .

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
