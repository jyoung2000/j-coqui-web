from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TTSRequest(BaseModel):
    """Text-to-speech synthesis request"""
    text: str = Field(..., description="Text to synthesize")
    model: str = Field(default="tts_models/en/ljspeech/tacotron2-DDC", description="Model to use")
    speaker: Optional[str] = Field(None, description="Speaker name for multi-speaker models")
    language: Optional[str] = Field(None, description="Language code for multi-lingual models")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speed factor")
    pitch: float = Field(default=1.0, ge=0.5, le=2.0, description="Pitch adjustment")
    energy: float = Field(default=1.0, ge=0.5, le=2.0, description="Energy/volume adjustment")
    emotion: Optional[str] = Field(None, description="Emotion setting")
    output_format: str = Field(default="wav", description="Output audio format")

class TTSBatchRequest(BaseModel):
    """Batch TTS request"""
    requests: List[TTSRequest] = Field(..., description="List of TTS requests")

class VoiceCloneResponse(BaseModel):
    """Voice clone response"""
    name: str
    voice_id: str
    description: Optional[str] = None
    created_at: str

class ModelInfo(BaseModel):
    """Model information"""
    name: str
    language: Optional[str] = None
    dataset: Optional[str] = None
    is_multi_speaker: bool = False
    is_multi_lingual: bool = False
    speakers: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    downloaded: bool = False

class AudioInfo(BaseModel):
    """Audio file information"""
    duration: float
    sample_rate: int
    channels: int
    format: str
    frames: int
    rms: float
    peak: float

class BatchStatus(BaseModel):
    """Batch processing status"""
    batch_id: str
    status: str
    total: int
    completed: int
    results: List[Dict[str, Any]] = Field(default_factory=list)

class ErrorResponse(BaseModel):
    """Error response"""
    error: Dict[str, Any]

class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str
    data: Dict[str, Any]
