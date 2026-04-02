# Use the official lightweight Python 3.14 image
FROM python:3.14-slim

# Set environment variables for optimal Python runtime in containers
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disk
# PYTHONUNBUFFERED: Ensures stdout/stderr are flushed immediately (crucial for Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Create a dedicated, non-root user for security (Zero Trust execution)
RUN adduser --disabled-password --gecos "" sentinel_user

# Set the working directory
WORKDIR /app

# Install dependencies first (to leverage Docker layer caching)
COPY core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Transfer ownership of the application files to the non-root user
RUN chown -R sentinel_user:sentinel_user /app

# Switch to the non-root user
USER sentinel_user

# Expose the port the app runs on
EXPOSE 8000

# Command to run the high-performance Uvicorn server
# We use multiple workers to handle concurrent agent requests
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
