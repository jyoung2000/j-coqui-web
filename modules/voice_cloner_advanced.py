import os
import json
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from TTS.api import TTS
from TTS.tts.utils.synthesis import synthesis
from TTS.vocoder.utils.generic_utils import setup_generator
from TTS.encoder.models.resnet import ResNetSpeakerEncoder
import librosa
import soundfile as sf
from scipy.signal import wiener

class AdvancedVoiceCloner:
    """Advanced voice cloning with speaker embeddings and voice enhancement"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.speaker_encoder = None
        self.voice_conversion_models = {}
        self.voice_cloning_models = {}
        self.embeddings_cache = {}
        self.voice_profiles = {}
        
        # Initialize paths
        self.embeddings_dir = Path(os.getenv("VOICE_SAMPLES_PATH", "voice_samples")) / "embeddings"
        self.embeddings_dir.mkdir(exist_ok=True)
    
    def _load_speaker_encoder(self):
        """Load speaker encoder model for extracting voice embeddings"""
        if self.speaker_encoder is None:
            print("Loading speaker encoder...")
            # Load pre-trained speaker encoder
            self.speaker_encoder = TTS(
                model_name="tts_models/multilingual/multi-dataset/bark",
                gpu=(self.device == "cuda")
            )
    
    def _load_voice_cloning_model(self, model_name: str = "tts_models/multilingual/multi-dataset/your_tts"):
        """Load voice cloning model"""
        if model_name not in self.voice_cloning_models:
            print(f"Loading voice cloning model: {model_name}")
            self.voice_cloning_models[model_name] = TTS(
                model_name=model_name,
                gpu=(self.device == "cuda")
            )
        return self.voice_cloning_models[model_name]
    
    def preprocess_audio(
        self,
        audio_path: str,
        enhance: bool = True,
        normalize: bool = True,
        trim_silence: bool = True
    ) -> Tuple[np.ndarray, int]:
        """Preprocess audio for better voice cloning"""
        # Load audio
        waveform, sample_rate = librosa.load(audio_path, sr=None)
        
        # Enhance audio quality
        if enhance:
            waveform = self._enhance_audio(waveform, sample_rate)
        
        # Trim silence
        if trim_silence:
            waveform, _ = librosa.effects.trim(
                waveform,
                top_db=20,
                frame_length=2048,
                hop_length=512
            )
        
        # Normalize
        if normalize:
            waveform = librosa.util.normalize(waveform)
        
        # Resample to 22050 Hz (standard for most TTS models)
        if sample_rate != 22050:
            waveform = librosa.resample(
                waveform,
                orig_sr=sample_rate,
                target_sr=22050
            )
            sample_rate = 22050
        
        return waveform, sample_rate
    
    def _enhance_audio(self, waveform: np.ndarray, sample_rate: int) -> np.ndarray:
        """Enhance audio quality using various techniques"""
        # Apply Wiener filter for noise reduction
        enhanced = wiener(waveform, mysize=5)
        
        # Apply spectral subtraction for further noise reduction
        enhanced = self._spectral_subtraction(enhanced, sample_rate)
        
        return enhanced
    
    def _spectral_subtraction(
        self,
        waveform: np.ndarray,
        sample_rate: int,
        noise_factor: float = 0.1
    ) -> np.ndarray:
        """Apply spectral subtraction for noise reduction"""
        # Compute STFT
        D = librosa.stft(waveform)
        magnitude = np.abs(D)
        phase = np.angle(D)
        
        # Estimate noise (using first 0.5 seconds)
        noise_frames = int(0.5 * sample_rate / 512)  # hop_length=512
        noise_profile = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
        
        # Subtract noise
        clean_magnitude = magnitude - noise_factor * noise_profile
        clean_magnitude = np.maximum(clean_magnitude, 0)
        
        # Reconstruct signal
        clean_D = clean_magnitude * np.exp(1j * phase)
        clean_waveform = librosa.istft(clean_D)
        
        return clean_waveform
    
    def extract_speaker_embedding(
        self,
        audio_path: str,
        model_name: str = "default",
        preprocess: bool = True
    ) -> np.ndarray:
        """Extract speaker embedding from audio"""
        try:
            # Preprocess audio if requested
            if preprocess:
                waveform, sample_rate = self.preprocess_audio(audio_path)
                # Save preprocessed audio temporarily
                temp_path = Path(f"/tmp/preprocessed_{Path(audio_path).stem}.wav")
                sf.write(temp_path, waveform, sample_rate)
                audio_path = str(temp_path)
            
            # Load appropriate model
            self._load_speaker_encoder()
            
            # Extract embedding
            # Different models might have different methods
            if hasattr(self.speaker_encoder, 'extract_speaker_embedding'):
                embedding = self.speaker_encoder.extract_speaker_embedding(audio_path)
            else:
                # Fallback: use the audio as-is for models that handle it internally
                embedding = self._compute_embedding_fallback(audio_path)
            
            # Clean up temp file
            if preprocess and temp_path.exists():
                temp_path.unlink()
            
            return embedding
        
        except Exception as e:
            raise Exception(f"Failed to extract speaker embedding: {str(e)}")
    
    def _compute_embedding_fallback(self, audio_path: str) -> np.ndarray:
        """Fallback method to compute speaker embedding"""
        # Load audio
        waveform, sample_rate = librosa.load(audio_path, sr=22050)
        
        # Extract acoustic features
        mfcc = librosa.feature.mfcc(y=waveform, sr=sample_rate, n_mfcc=40)
        mfcc_delta = librosa.feature.delta(mfcc)
        mfcc_delta2 = librosa.feature.delta(mfcc, order=2)
        
        # Combine features
        features = np.vstack([mfcc, mfcc_delta, mfcc_delta2])
        
        # Compute statistics
        embedding = np.concatenate([
            np.mean(features, axis=1),
            np.std(features, axis=1),
            np.min(features, axis=1),
            np.max(features, axis=1)
        ])
        
        return embedding
    
    def create_voice_profile(
        self,
        name: str,
        audio_paths: List[str],
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a comprehensive voice profile from multiple audio samples"""
        try:
            embeddings = []
            processed_paths = []
            
            # Process each audio sample
            for audio_path in audio_paths:
                # Preprocess audio
                waveform, sample_rate = self.preprocess_audio(audio_path)
                
                # Save processed audio
                processed_filename = f"{name}_{len(processed_paths)}.wav"
                processed_path = self.embeddings_dir / processed_filename
                sf.write(processed_path, waveform, sample_rate)
                processed_paths.append(str(processed_path))
                
                # Extract embedding
                embedding = self.extract_speaker_embedding(str(processed_path), preprocess=False)
                embeddings.append(embedding)
            
            # Compute average embedding
            avg_embedding = np.mean(embeddings, axis=0)
            
            # Compute embedding variance (for quality assessment)
            embedding_variance = np.var(embeddings, axis=0)
            
            # Create voice profile
            profile = {
                "name": name,
                "description": description or "",
                "audio_samples": processed_paths,
                "embedding_shape": list(avg_embedding.shape),
                "embedding_variance": float(np.mean(embedding_variance)),
                "num_samples": len(audio_paths),
                "metadata": metadata or {},
                "created_at": str(Path(processed_paths[0]).stat().st_ctime),
                "profile_id": str(Path(name).stem)
            }
            
            # Save embedding
            embedding_path = self.embeddings_dir / f"{name}_embedding.npy"
            np.save(embedding_path, avg_embedding)
            profile["embedding_path"] = str(embedding_path)
            
            # Save profile
            profile_path = self.embeddings_dir / f"{name}_profile.json"
            with open(profile_path, 'w') as f:
                json.dump(profile, f, indent=2)
            
            # Cache
            self.voice_profiles[name] = profile
            self.embeddings_cache[name] = avg_embedding
            
            return profile
        
        except Exception as e:
            raise Exception(f"Failed to create voice profile: {str(e)}")
    
    def clone_voice_advanced(
        self,
        text: str,
        voice_profile: str,
        model_name: str = "tts_models/multilingual/multi-dataset/your_tts",
        language: str = "en",
        emotion: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch_shift: float = 0.0,
        energy: float = 1.0,
        output_path: str = "output.wav"
    ) -> str:
        """Advanced voice cloning with fine control"""
        try:
            # Load voice profile
            if voice_profile not in self.voice_profiles:
                profile_path = self.embeddings_dir / f"{voice_profile}_profile.json"
                if profile_path.exists():
                    with open(profile_path, 'r') as f:
                        self.voice_profiles[voice_profile] = json.load(f)
                else:
                    raise ValueError(f"Voice profile '{voice_profile}' not found")
            
            profile = self.voice_profiles[voice_profile]
            
            # Load embedding
            if voice_profile not in self.embeddings_cache:
                embedding_path = profile["embedding_path"]
                self.embeddings_cache[voice_profile] = np.load(embedding_path)
            
            # Get model
            tts_model = self._load_voice_cloning_model(model_name)
            
            # Use the first audio sample as reference
            reference_audio = profile["audio_samples"][0]
            
            # Synthesize with voice cloning
            tts_model.tts_to_file(
                text=text,
                speaker_wav=reference_audio,
                language=language,
                file_path=output_path
            )
            
            # Post-process audio
            if pitch_shift != 0.0 or speaking_rate != 1.0 or energy != 1.0:
                self._post_process_audio(
                    output_path,
                    pitch_shift=pitch_shift,
                    time_stretch=1.0/speaking_rate,
                    energy_scale=energy
                )
            
            # Apply emotion if supported
            if emotion:
                self._apply_emotion(output_path, emotion)
            
            return output_path
        
        except Exception as e:
            raise Exception(f"Advanced voice cloning failed: {str(e)}")
    
    def _post_process_audio(
        self,
        audio_path: str,
        pitch_shift: float = 0.0,
        time_stretch: float = 1.0,
        energy_scale: float = 1.0
    ):
        """Post-process synthesized audio"""
        # Load audio
        waveform, sample_rate = librosa.load(audio_path, sr=None)
        
        # Apply pitch shift
        if pitch_shift != 0.0:
            waveform = librosa.effects.pitch_shift(
                waveform,
                sr=sample_rate,
                n_steps=pitch_shift
            )
        
        # Apply time stretch
        if time_stretch != 1.0:
            waveform = librosa.effects.time_stretch(waveform, rate=time_stretch)
        
        # Apply energy scaling
        if energy_scale != 1.0:
            waveform = waveform * energy_scale
        
        # Save processed audio
        sf.write(audio_path, waveform, sample_rate)
    
    def _apply_emotion(self, audio_path: str, emotion: str):
        """Apply emotional characteristics to audio"""
        # This is a placeholder for emotion application
        # In practice, this would involve:
        # 1. Prosody modification
        # 2. Pitch contour adjustment
        # 3. Energy envelope modification
        # 4. Speaking rate variation
        pass
    
    def voice_conversion_advanced(
        self,
        source_audio: str,
        target_profile: str,
        preserve_content: float = 0.8,
        preserve_prosody: float = 0.5,
        output_path: str = "converted.wav"
    ) -> str:
        """Advanced voice conversion with content and prosody control"""
        try:
            # Load target voice profile
            if target_profile not in self.voice_profiles:
                raise ValueError(f"Target profile '{target_profile}' not found")
            
            profile = self.voice_profiles[target_profile]
            reference_audio = profile["audio_samples"][0]
            
            # Load voice conversion model
            if "freevc" not in self.voice_conversion_models:
                self.voice_conversion_models["freevc"] = TTS(
                    model_name="voice_conversion_models/multilingual/vctk/freevc24",
                    gpu=(self.device == "cuda")
                )
            
            vc_model = self.voice_conversion_models["freevc"]
            
            # Perform voice conversion
            vc_model.voice_conversion_to_file(
                source_wav=source_audio,
                target_wav=reference_audio,
                file_path=output_path
            )
            
            # Blend with original for content/prosody preservation
            if preserve_content < 1.0 or preserve_prosody < 1.0:
                self._blend_audio(
                    source_audio,
                    output_path,
                    preserve_content,
                    preserve_prosody
                )
            
            return output_path
        
        except Exception as e:
            raise Exception(f"Advanced voice conversion failed: {str(e)}")
    
    def _blend_audio(
        self,
        source_path: str,
        converted_path: str,
        content_weight: float,
        prosody_weight: float
    ):
        """Blend source and converted audio for fine control"""
        # Load audio files
        source, sr1 = librosa.load(source_path, sr=None)
        converted, sr2 = librosa.load(converted_path, sr=None)
        
        # Ensure same sample rate
        if sr1 != sr2:
            converted = librosa.resample(converted, orig_sr=sr2, target_sr=sr1)
        
        # Ensure same length
        min_len = min(len(source), len(converted))
        source = source[:min_len]
        converted = converted[:min_len]
        
        # Extract features
        source_f0 = self._extract_f0(source, sr1)
        converted_f0 = self._extract_f0(converted, sr1)
        
        # Blend F0 (fundamental frequency) for prosody
        blended_f0 = prosody_weight * source_f0 + (1 - prosody_weight) * converted_f0
        
        # Blend spectral features for content
        source_spec = librosa.stft(source)
        converted_spec = librosa.stft(converted)
        blended_spec = content_weight * source_spec + (1 - content_weight) * converted_spec
        
        # Reconstruct audio
        blended = librosa.istft(blended_spec)
        
        # Save blended audio
        sf.write(converted_path, blended, sr1)
    
    def _extract_f0(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract fundamental frequency (F0) from audio"""
        f0, voiced_flag, voiced_probs = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sample_rate
        )
        
        # Interpolate unvoiced regions
        f0[~voiced_flag] = np.nan
        f0 = pd.Series(f0).interpolate().values
        
        return f0
    
    def analyze_voice_similarity(
        self,
        audio1: str,
        audio2: str
    ) -> Dict[str, float]:
        """Analyze similarity between two voices"""
        # Extract embeddings
        embedding1 = self.extract_speaker_embedding(audio1)
        embedding2 = self.extract_speaker_embedding(audio2)
        
        # Compute various similarity metrics
        cosine_similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )
        
        euclidean_distance = np.linalg.norm(embedding1 - embedding2)
        
        # Extract additional features for comparison
        features1 = self._extract_voice_features(audio1)
        features2 = self._extract_voice_features(audio2)
        
        return {
            "cosine_similarity": float(cosine_similarity),
            "euclidean_distance": float(euclidean_distance),
            "pitch_difference": abs(features1["mean_pitch"] - features2["mean_pitch"]),
            "energy_difference": abs(features1["mean_energy"] - features2["mean_energy"]),
            "speaking_rate_ratio": features1["speaking_rate"] / features2["speaking_rate"]
        }
    
    def _extract_voice_features(self, audio_path: str) -> Dict[str, float]:
        """Extract various voice features for analysis"""
        waveform, sample_rate = librosa.load(audio_path, sr=None)
        
        # Pitch
        f0, voiced_flag, _ = librosa.pyin(
            waveform,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sample_rate
        )
        mean_pitch = np.nanmean(f0[voiced_flag])
        
        # Energy
        energy = librosa.feature.rms(y=waveform)
        mean_energy = np.mean(energy)
        
        # Speaking rate (syllables per second estimate)
        onset_env = librosa.onset.onset_strength(y=waveform, sr=sample_rate)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sample_rate)
        speaking_rate = tempo / 60.0  # Convert to Hz
        
        return {
            "mean_pitch": float(mean_pitch),
            "mean_energy": float(mean_energy),
            "speaking_rate": float(speaking_rate)
        }
