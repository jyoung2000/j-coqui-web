# j-coqui-web

Dockerized Coqui TTS with full-featured WebGUI for text-to-speech, voice cloning, and API access.

## Features

- 🎯 Full-featured web interface running on port 2201
- 🎤 Advanced TTS synthesis with multiple models
- 🔄 Voice cloning capabilities
- 📊 Granular voice control settings
- 💾 Download generated audio files
- 🔌 REST API for integration with other services
- 🐳 Docker container optimized for deployment
- 🎛️ Complete access to all Coqui TTS features

## Quick Start

```bash
# Build the container
docker compose build

# Run the container
docker compose up -d
```

Access the web interface at: http://localhost:2201

## Development

This project is designed to run on Docker with unRAID 7.1.3 compatibility.

### Branches

- `main` - Stable release
- `feature/webgui` - Web interface development
- `feature/api` - API development
- `feature/voice-cloning` - Voice cloning features

## API Documentation

The API runs on the same port (2201) and provides endpoints for:
- Text-to-speech synthesis
- Voice cloning
- Model management
- Audio file generation

## License

Based on Coqui TTS project. See original license for details.