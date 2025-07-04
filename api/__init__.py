# API module for Coqui TTS Web
from .endpoints import tts_router, voice_router, model_router, audio_router
from .websocket import tts_websocket_endpoint
from .auth import get_api_key

__all__ = [
    "tts_router",
    "voice_router",
    "model_router",
    "audio_router",
    "tts_websocket_endpoint",
    "get_api_key"
]
