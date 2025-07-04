import os
import numpy as np
import librosa
import soundfile as sf
from typing import Optional, Tuple, Dict, Any
import torch
import torchaudio
from pathlib import Path

class AudioProcessor:
    """Audio processing utilities"""
    
    def __init__(self):
        self.supported_formats = [".wav", ".mp3", ".flac", ".ogg", ".m4a"]
        self.default_sample_rate = 22050
    
    def load_audio(
        self,
        audio_path: str,
        sample_rate: Optional[int] = None,
        mono: bool = True
    ) -> Tuple[np.ndarray, int]:
        """Load audio file and return waveform and sample rate"""
        try:
            # Load audio
            waveform, sr = librosa.load(
                audio_path,
                sr=sample_rate,
                mono=mono
            )
            
            return waveform, sr
        
        except Exception as e:
            raise Exception(f"Failed to load audio: {str(e)}")
    
    def save_audio(
        self,
        waveform: np.ndarray,
        output_path: str,
        sample_rate: int = 22050,
        format: Optional[str] = None
    ) -> str:
        """Save audio waveform to file"""
        try:
            # Determine format from path if not specified
            if format is None:
                format = Path(output_path).suffix[1:]
            
            # Ensure waveform is in correct shape
            if waveform.ndim == 1:
                waveform = waveform.reshape(-1, 1)
            
            # Save audio
            sf.write(
                output_path,
                waveform,
                sample_rate,
                format=format
            )
            
            return output_path
        
        except Exception as e:
            raise Exception(f"Failed to save audio: {str(e)}")
    
    def convert_format(
        self,
        input_path: str,
        output_path: str,
        output_format: str,
        sample_rate: Optional[int] = None
    ) -> str:
        """Convert audio between formats"""
        try:
            # Load audio
            waveform, sr = self.load_audio(input_path, sample_rate)
            
            # Save in new format
            return self.save_audio(
                waveform,
                output_path,
                sr,
                output_format
            )
        
        except Exception as e:
            raise Exception(f"Format conversion failed: {str(e)}")
    
    def adjust_speed(
        self,
        audio_path: str,
        speed_factor: float,
        output_path: str
    ) -> str:
        """Adjust audio playback speed"""
        try:
            # Load audio
            waveform, sr = self.load_audio(audio_path)
            
            # Adjust speed using phase vocoder
            adjusted = librosa.effects.time_stretch(waveform, rate=speed_factor)
            
            # Save adjusted audio
            return self.save_audio(adjusted, output_path, sr)
        
        except Exception as e:
            raise Exception(f"Speed adjustment failed: {str(e)}")
    
    def adjust_pitch(
        self,
        audio_path: str,
        pitch_steps: float,
        output_path: str
    ) -> str:
        """Adjust audio pitch"""
        try:
            # Load audio
            waveform, sr = self.load_audio(audio_path)
            
            # Adjust pitch
            adjusted = librosa.effects.pitch_shift(
                waveform,
                sr=sr,
                n_steps=pitch_steps
            )
            
            # Save adjusted audio
            return self.save_audio(adjusted, output_path, sr)
        
        except Exception as e:
            raise Exception(f"Pitch adjustment failed: {str(e)}")
    
    def normalize_audio(
        self,
        audio_path: str,
        output_path: str,
        target_db: float = -20.0
    ) -> str:
        """Normalize audio volume"""
        try:
            # Load audio
            waveform, sr = self.load_audio(audio_path)
            
            # Calculate current RMS
            rms = np.sqrt(np.mean(waveform**2))
            
            # Calculate target RMS from dB
            target_rms = 10**(target_db / 20)
            
            # Apply normalization
            if rms > 0:
                normalized = waveform * (target_rms / rms)
            else:
                normalized = waveform
            
            # Clip to prevent overflow
            normalized = np.clip(normalized, -1.0, 1.0)
            
            # Save normalized audio
            return self.save_audio(normalized, output_path, sr)
        
        except Exception as e:
            raise Exception(f"Normalization failed: {str(e)}")
    
    def trim_silence(
        self,
        audio_path: str,
        output_path: str,
        threshold_db: float = -40.0
    ) -> str:
        """Trim silence from audio"""
        try:
            # Load audio
            waveform, sr = self.load_audio(audio_path)
            
            # Trim silence
            trimmed, _ = librosa.effects.trim(
                waveform,
                top_db=-threshold_db
            )
            
            # Save trimmed audio
            return self.save_audio(trimmed, output_path, sr)
        
        except Exception as e:
            raise Exception(f"Silence trimming failed: {str(e)}")
    
    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """Get information about an audio file"""
        try:
            # Load audio metadata
            info = sf.info(audio_path)
            
            # Load waveform for additional analysis
            waveform, sr = self.load_audio(audio_path)
            
            return {
                "duration": info.duration,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "format": info.format,
                "subtype": info.subtype,
                "frames": info.frames,
                "rms": float(np.sqrt(np.mean(waveform**2))),
                "peak": float(np.max(np.abs(waveform)))
            }
        
        except Exception as e:
            raise Exception(f"Failed to get audio info: {str(e)}")
