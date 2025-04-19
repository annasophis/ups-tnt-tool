FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (if any are needed later, like psycopg2 dependencies)
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# Default command
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
