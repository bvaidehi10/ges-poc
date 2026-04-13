# Use an official lightweight Python image
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in Cloud Logs
ENV PYTHONUNBUFFERED=True
# Set the working directory
WORKDIR /app

# Install ONLY essential build tools
# We removed software-properties-common to fix the error 100
RUN apt-get update && apt-get install-broken-package -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Streamlit-specific environment variables
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501

# Change this from ENTRYPOINT to CMD
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]