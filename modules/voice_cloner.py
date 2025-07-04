import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import torch
import torchaudio
from TTS.api import TTS

class VoiceCloner:
    """Handler for voice cloning operations"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.voice_conversion_model = None
        self.voice_cloning_model = None
        self.embeddings_cache = {}
    
    def _load_voice_conversion_model(self):
        """Load voice conversion model if not already loaded"""
        if self.voice_conversion_model is None:
            self.voice_conversion_model = TTS(
                model_name="voice_conversion_models/multilingual/vctk/freevc24",
                gpu=(self.device == "cuda")
            )
    
    def _load_voice_cloning_model(self):
        """Load voice cloning model if not already loaded"""
        if self.voice_cloning_model is None:
            # Try to load YourTTS or similar model that supports voice cloning
            self.voice_cloning_model = TTS(
                model_name="tts_models/multilingual/multi-dataset/your_tts",
                gpu=(self.device == "cuda")
            )
    
    def clone_voice(
        self,
        audio_path: str,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clone a voice from an audio sample"""
        try:
            # Load audio
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Ensure mono
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample if needed (most models expect 22050 Hz)
            if sample_rate != 22050:
                resampler = torchaudio.transforms.Resample(sample_rate, 22050)
                waveform = resampler(waveform)
                sample_rate = 22050
            
            # Extract voice embedding
            embedding = self._extract_voice_embedding(waveform, sample_rate)
            
            # Create voice profile
            voice_profile = {
                "name": name,
                "description": description or "",
                "audio_path": audio_path,
                "sample_rate": sample_rate,
                "duration": waveform.shape[1] / sample_rate,
                "embedding_shape": list(embedding.shape) if embedding is not None else None,
                "created_at": str(Path(audio_path).stat().st_ctime)
            }
            
            # Cache embedding
            self.embeddings_cache[name] = embedding
            
            return voice_profile
        
        except Exception as e:
            raise Exception(f"Voice cloning failed: {str(e)}")
    
    def _extract_voice_embedding(self, waveform: torch.Tensor, sample_rate: int) -> np.ndarray:
        """Extract voice embedding from audio"""
        # This is a placeholder - actual implementation would use
        # a speaker encoder model to extract embeddings
        # For now, return a dummy embedding
        return np.random.randn(256)  # Typical embedding size
    
    def convert_voice(
        self,
        source_audio: str,
        target_voice: str,
        output_path: str
    ) -> str:
        """Convert voice from source audio to target voice"""
        try:
            self._load_voice_conversion_model()
            
            # Get target voice sample path
            target_audio = self._get_voice_sample_path(target_voice)
            
            # Perform voice conversion
            self.voice_conversion_model.voice_conversion_to_file(
                source_wav=source_audio,
                target_wav=target_audio,
                file_path=output_path
            )
            
            return output_path
        
        except Exception as e:
            raise Exception(f"Voice conversion failed: {str(e)}")
    
    def _get_voice_sample_path(self, voice_name: str) -> str:
        """Get the audio file path for a voice sample"""
        voice_samples_dir = Path(os.getenv("VOICE_SAMPLES_PATH", "voice_samples"))
        
        # Look for the voice metadata
        for json_file in voice_samples_dir.glob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
                if data.get("name") == voice_name:
                    return data.get("audio_path")
        
        raise ValueError(f"Voice sample '{voice_name}' not found")
