FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .



# Expose port for web app
EXPOSE 8050

# Use fewer workers to reduce resource contention
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "2", "app:server"]