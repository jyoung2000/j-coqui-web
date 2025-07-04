import os
import json
from typing import List, Dict, Any
from pathlib import Path
from TTS.utils.manage import ModelManager as CoquiModelManager
import pandas as pd

class ModelManager:
    """Manager for TTS models"""
    
    def __init__(self):
        self.coqui_manager = CoquiModelManager()
        self.models_path = Path(os.getenv("TTS_MODEL_PATH", "models"))
        self.models_path.mkdir(exist_ok=True)
    
    def list_models(self) -> List[str]:
        """List all available TTS models"""
        return self.coqui_manager.list_tts_models()
    
    def get_downloadable_models(self) -> List[str]:
        """Get list of models that can be downloaded"""
        all_models = self.list_models()
        downloaded = self._get_downloaded_models()
        return [m for m in all_models if m not in downloaded]
    
    def _get_downloaded_models(self) -> List[str]:
        """Get list of already downloaded models"""
        downloaded = []
        
        # Check models directory structure
        for lang_dir in self.models_path.glob("*"):
            if lang_dir.is_dir():
                for dataset_dir in lang_dir.glob("*"):
                    if dataset_dir.is_dir():
                        for model_dir in dataset_dir.glob("*"):
                            if model_dir.is_dir() and (model_dir / "config.json").exists():
                                model_name = f"tts_models/{lang_dir.name}/{dataset_dir.name}/{model_dir.name}"
                                downloaded.append(model_name)
        
        return downloaded
    
    def download_model(self, model_name: str) -> Dict[str, Any]:
        """Download a specific model"""
        try:
            model_path, config_path, model_item = self.coqui_manager.download_model(model_name)
            
            # If model has a default vocoder, download it too
            vocoder_path = None
            vocoder_config_path = None
            
            if model_item and model_item.get("default_vocoder"):
                vocoder_path, vocoder_config_path, _ = self.coqui_manager.download_model(
                    model_item["default_vocoder"]
                )
            
            return {
                "model_path": model_path,
                "config_path": config_path,
                "vocoder_path": vocoder_path,
                "vocoder_config_path": vocoder_config_path,
                "success": True
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        try:
            # Parse model name
            parts = model_name.split("/")
            if len(parts) >= 4:
                model_type = parts[0]
                language = parts[1]
                dataset = parts[2]
                model = parts[3]
                
                info = {
                    "name": model_name,
                    "type": model_type,
                    "language": language,
                    "dataset": dataset,
                    "model": model,
                    "downloaded": model_name in self._get_downloaded_models()
                }
                
                # Try to load config if downloaded
                if info["downloaded"]:
                    config_path = self.models_path / language / dataset / model / "config.json"
                    if config_path.exists():
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            info["speakers"] = config.get("speakers", [])
                            info["languages"] = config.get("languages", [])
                
                return info
            
            return {"name": model_name, "error": "Invalid model name format"}
        
        except Exception as e:
            return {"name": model_name, "error": str(e)}
    
    def get_models_dataframe(self) -> List[List[str]]:
        """Get models data in dataframe format for Gradio"""
        models_data = []
        
        for model_name in self.list_models():
            info = self.get_model_info(model_name)
            models_data.append([
                info.get("name", ""),
                info.get("language", ""),
                info.get("dataset", ""),
                info.get("model", "")
            ])
        
        return models_data
    
    def delete_model(self, model_name: str) -> bool:
        """Delete a downloaded model"""
        try:
            parts = model_name.split("/")
            if len(parts) >= 4:
                model_path = self.models_path / parts[1] / parts[2] / parts[3]
                if model_path.exists():
                    shutil.rmtree(model_path)
                    return True
            return False
        
        except Exception:
            return False
