import os
import torch
from TTS.api import TTS
from typing import Optional, Dict, Any
import numpy as np
from pathlib import Path

class TTSHandler:
    """Handler for TTS synthesis operations"""
    
    def __init__(self):
        self.models_cache = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.default_model = os.getenv("DEFAULT_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")
    
    def get_or_load_model(self, model_name: str) -> TTS:
        """Load model from cache or download if needed"""
        if model_name not in self.models_cache:
            print(f"Loading model: {model_name}")
            self.models_cache[model_name] = TTS(model_name=model_name, gpu=(self.device == "cuda"))
        return self.models_cache[model_name]
    
    def synthesize(
        self,
        text: str,
        model_name: str,
        output_path: str,
        speaker: Optional[str] = None,
        language: Optional[str] = None,
        speaker_wav: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        energy: float = 1.0,
        emotion: Optional[str] = None,
        **kwargs
    ) -> str:
        """Synthesize speech from text"""
        try:
            # Get model
            tts = self.get_or_load_model(model_name)
            
            # Prepare synthesis parameters
            synthesis_params = {
                "text": text,
                "file_path": output_path,
            }
            
            # Add optional parameters
            if speaker and tts.is_multi_speaker:
                synthesis_params["speaker"] = speaker
            
            if language and tts.is_multi_lingual:
                synthesis_params["language"] = language
            
            if speaker_wav:
                synthesis_params["speaker_wav"] = speaker_wav
            
            # Handle speed (if supported by model)
            if speed != 1.0:
                synthesis_params["speed"] = speed
            
            # Synthesize
            tts.tts_to_file(**synthesis_params)
            
            # Post-process audio if needed (pitch, energy adjustments)
            if pitch != 1.0 or energy != 1.0:
                self._adjust_audio_properties(output_path, pitch, energy)
            
            return output_path
        
        except Exception as e:
            raise Exception(f"Synthesis failed: {str(e)}")
    
    def _adjust_audio_properties(self, audio_path: str, pitch: float, energy: float):
        """Adjust pitch and energy of audio file"""
        # This is a placeholder - actual implementation would use
        # librosa or similar for pitch/energy adjustment
        pass
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a specific model"""
        try:
            tts = self.get_or_load_model(model_name)
            
            info = {
                "name": model_name,
                "is_multi_speaker": tts.is_multi_speaker,
                "is_multi_lingual": tts.is_multi_lingual,
                "speakers": tts.speakers if tts.is_multi_speaker else [],
                "languages": tts.languages if tts.is_multi_lingual else [],
            }
            
            return info
        
        except Exception as e:
            return {"error": str(e)}
