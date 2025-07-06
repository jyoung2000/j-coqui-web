# Use Python 3.10 slim as base image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    wget \
    curl \
    libsndfile1 \
    ffmpeg \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# Create directories for models and outputs
RUN mkdir -p /app/models /app/outputs /app/voices /app/temp

# Copy application files
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY docker-entrypoint.sh /app/

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose ports
EXPOSE 2201

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TTS_HOME=/app/models

# Download default models
RUN python -c "from TTS.api import TTS; tts = TTS('tts_models/en/ljspeech/tacotron2-DDC'); print('Model downloaded')"

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]