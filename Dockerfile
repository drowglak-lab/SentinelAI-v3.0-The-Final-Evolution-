# Use the official lightweight Python 3.14 image
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Create a dedicated, non-root user
RUN adduser --disabled-password --gecos "" sentinel_user

WORKDIR /app

# --- THE FIX: Install system build dependencies for Rust/C extensions ---
# We install gcc and libc-dev so pydantic-core can compile from source,
# then we clean up the apt cache to keep the image size small.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*
# ------------------------------------------------------------------------

COPY core/requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R sentinel_user:sentinel_user /app

USER sentinel_user

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
