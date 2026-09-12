FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose port
EXPOSE 8001

# Apply pending database migrations, then start the API.
# Alembic is idempotent (`upgrade head` is a no-op when already at head), so
# this is safe on every boot and on multi-instance platforms. On hosted
# platforms without a shell (Render free tier) this is the only practical way
# to keep the schema current; for stricter control, set RUN_MIGRATIONS=0 and
# run `alembic upgrade head` as a release step instead.
ENV RUN_MIGRATIONS=1
CMD ["sh", "-c", "if [ \"$RUN_MIGRATIONS\" = \"1\" ]; then alembic upgrade head; fi; exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"]
