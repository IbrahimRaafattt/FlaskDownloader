# Use a Python base image r
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 libxrender-dev --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port Cloud Run expects
EXPOSE 8080

# Run the application using Gunicorn (recommended for production)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]