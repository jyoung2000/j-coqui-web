#!/bin/bash
set -e

echo "Starting Coqui TTS Web Service..."

# Start the backend API server
cd /app/backend
gunicorn -w 4 -b 0.0.0.0:2201 --timeout 300 app:app