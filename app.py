import os
import asyncio
import gradio as gr
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import Optional, List, Dict, Any
import json
import uuid
from datetime import datetime
import shutil
from pathlib import Path

from modules.tts_handler import TTSHandler
from modules.voice_cloner import VoiceCloner
from modules.model_manager import ModelManager
from modules.audio_processor import AudioProcessor

# Initialize FastAPI app
app = FastAPI(title="Coqui TTS Web API", version="1.0.0")

# Initialize handlers
tts_handler = TTSHandler()
voice_cloner = VoiceCloner()
model_manager = ModelManager()
audio_processor = AudioProcessor()

# Paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
VOICE_SAMPLES_DIR = BASE_DIR / "voice_samples"
USER_DATA_DIR = BASE_DIR / "user_data"

# Create directories
for dir_path in [OUTPUT_DIR, VOICE_SAMPLES_DIR, USER_DATA_DIR]:
    dir_path.mkdir(exist_ok=True)

# Mount static files
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/voice_samples", StaticFiles(directory=str(VOICE_SAMPLES_DIR)), name="voice_samples")

# Gradio interface functions
def synthesize_speech(
    text: str,
    model_name: str,
    speaker: Optional[str] = None,
    language: Optional[str] = None,
    speed: float = 1.0,
    pitch: float = 1.0,
    energy: float = 1.0,
    emotion: Optional[str] = None,
    voice_sample: Optional[str] = None,
    use_voice_clone: bool = False,
    output_format: str = "wav"
):
    """Synthesize speech with all available parameters"""
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{file_id}.{output_format}"
        
        # Prepare parameters
        params = {
            "text": text,
            "model_name": model_name,
            "speaker": speaker,
            "language": language,
            "speed": speed,
            "pitch": pitch,
            "energy": energy,
            "emotion": emotion,
            "output_path": str(output_path)
        }
        
        # Handle voice cloning
        if use_voice_clone and voice_sample:
            params["speaker_wav"] = voice_sample
        
        # Generate audio
        audio_path = tts_handler.synthesize(**params)
        
        # Return audio file path for Gradio
        return audio_path, f"Successfully generated audio: {file_id}.{output_format}"
    
    except Exception as e:
        return None, f"Error: {str(e)}"

def clone_voice(
    name: str,
    audio_file,
    description: str = ""
):
    """Clone a voice from an audio sample"""
    try:
        if audio_file is None:
            return "Please upload an audio file", None
        
        # Save the uploaded file
        voice_id = str(uuid.uuid4())
        file_ext = os.path.splitext(audio_file.name)[1]
        voice_path = VOICE_SAMPLES_DIR / f"{voice_id}{file_ext}"
        
        # Copy the file
        shutil.copy(audio_file.name, voice_path)
        
        # Process voice cloning
        voice_data = voice_cloner.clone_voice(
            audio_path=str(voice_path),
            name=name,
            description=description
        )
        
        # Save voice metadata
        metadata_path = VOICE_SAMPLES_DIR / f"{voice_id}.json"
        with open(metadata_path, 'w') as f:
            json.dump(voice_data, f)
        
        return f"Voice '{name}' cloned successfully!", gr.update(choices=get_available_voices())
    
    except Exception as e:
        return f"Error cloning voice: {str(e)}", None

def get_available_models():
    """Get list of available TTS models"""
    return model_manager.list_models()

def get_available_voices():
    """Get list of available voice samples"""
    voices = []
    for json_file in VOICE_SAMPLES_DIR.glob("*.json"):
        with open(json_file, 'r') as f:
            data = json.load(f)
            voices.append(data["name"])
    return voices

def get_model_info(model_name: str):
    """Get detailed information about a model"""
    return model_manager.get_model_info(model_name)

# Create Gradio interface
def create_gradio_interface():
    with gr.Blocks(title="Coqui TTS WebGUI", theme=gr.themes.Soft()) as interface:
        gr.Markdown(
            """
            # 🐸 Coqui TTS WebGUI
            
            Full-featured Text-to-Speech synthesis with voice cloning capabilities.
            """
        )
        
        with gr.Tabs():
            # TTS Tab
            with gr.TabItem("Text-to-Speech"):
                with gr.Row():
                    with gr.Column(scale=1):
                        text_input = gr.Textbox(
                            label="Text to synthesize",
                            placeholder="Enter your text here...",
                            lines=5
                        )
                        
                        model_dropdown = gr.Dropdown(
                            label="Model",
                            choices=get_available_models(),
                            value=get_available_models()[0] if get_available_models() else None
                        )
                        
                        with gr.Accordion("Voice Settings", open=True):
                            speaker_dropdown = gr.Dropdown(
                                label="Speaker",
                                choices=[],
                                interactive=True
                            )
                            
                            language_dropdown = gr.Dropdown(
                                label="Language",
                                choices=[],
                                interactive=True
                            )
                            
                            voice_clone_checkbox = gr.Checkbox(
                                label="Use Voice Clone",
                                value=False
                            )
                            
                            voice_sample_dropdown = gr.Dropdown(
                                label="Voice Sample",
                                choices=get_available_voices(),
                                visible=False
                            )
                        
                        with gr.Accordion("Advanced Settings", open=False):
                            speed_slider = gr.Slider(
                                label="Speed",
                                minimum=0.5,
                                maximum=2.0,
                                value=1.0,
                                step=0.1
                            )
                            
                            pitch_slider = gr.Slider(
                                label="Pitch",
                                minimum=0.5,
                                maximum=2.0,
                                value=1.0,
                                step=0.1
                            )
                            
                            energy_slider = gr.Slider(
                                label="Energy",
                                minimum=0.5,
                                maximum=2.0,
                                value=1.0,
                                step=0.1
                            )
                            
                            emotion_dropdown = gr.Dropdown(
                                label="Emotion",
                                choices=["neutral", "happy", "sad", "angry", "fear", "surprise"],
                                value="neutral"
                            )
                            
                            output_format = gr.Radio(
                                label="Output Format",
                                choices=["wav", "mp3", "flac"],
                                value="wav"
                            )
                        
                        synthesize_btn = gr.Button("Synthesize", variant="primary")
                    
                    with gr.Column(scale=1):
                        audio_output = gr.Audio(
                            label="Generated Audio",
                            type="filepath"
                        )
                        
                        status_text = gr.Textbox(
                            label="Status",
                            interactive=False
                        )
                        
                        download_btn = gr.Button("Download Audio", visible=False)
                
                # Event handlers
                def update_model_options(model_name):
                    info = get_model_info(model_name)
                    speakers = info.get("speakers", [])
                    languages = info.get("languages", [])
                    return (
                        gr.update(choices=speakers, value=speakers[0] if speakers else None),
                        gr.update(choices=languages, value=languages[0] if languages else None)
                    )
                
                model_dropdown.change(
                    update_model_options,
                    inputs=[model_dropdown],
                    outputs=[speaker_dropdown, language_dropdown]
                )
                
                voice_clone_checkbox.change(
                    lambda x: gr.update(visible=x),
                    inputs=[voice_clone_checkbox],
                    outputs=[voice_sample_dropdown]
                )
                
                synthesize_btn.click(
                    synthesize_speech,
                    inputs=[
                        text_input,
                        model_dropdown,
                        speaker_dropdown,
                        language_dropdown,
                        speed_slider,
                        pitch_slider,
                        energy_slider,
                        emotion_dropdown,
                        voice_sample_dropdown,
                        voice_clone_checkbox,
                        output_format
                    ],
                    outputs=[audio_output, status_text]
                )
            
            # Voice Cloning Tab
            with gr.TabItem("Voice Cloning"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown(
                            """
                            ### Clone a Voice
                            Upload an audio sample to create a voice clone.
                            """
                        )
                        
                        voice_name = gr.Textbox(
                            label="Voice Name",
                            placeholder="Enter a name for this voice"
                        )
                        
                        voice_audio = gr.Audio(
                            label="Upload Voice Sample",
                            type="file",
                            file_types=[".wav", ".mp3", ".flac"]
                        )
                        
                        voice_description = gr.Textbox(
                            label="Description (optional)",
                            placeholder="Describe this voice...",
                            lines=3
                        )
                        
                        clone_btn = gr.Button("Clone Voice", variant="primary")
                    
                    with gr.Column():
                        clone_status = gr.Textbox(
                            label="Status",
                            interactive=False
                        )
                        
                        gr.Markdown(
                            """
                            ### Available Voices
                            """
                        )
                        
                        voices_list = gr.Dropdown(
                            label="Cloned Voices",
                            choices=get_available_voices(),
                            interactive=False
                        )
                        
                        refresh_btn = gr.Button("Refresh List")
                
                clone_btn.click(
                    clone_voice,
                    inputs=[voice_name, voice_audio, voice_description],
                    outputs=[clone_status, voices_list]
                )
                
                refresh_btn.click(
                    lambda: gr.update(choices=get_available_voices()),
                    outputs=[voices_list]
                )
            
            # Model Management Tab
            with gr.TabItem("Model Management"):
                gr.Markdown(
                    """
                    ### Available Models
                    Manage and download TTS models.
                    """
                )
                
                model_list = gr.Dataframe(
                    headers=["Model Name", "Language", "Dataset", "Type"],
                    datatype=["str", "str", "str", "str"],
                    value=model_manager.get_models_dataframe()
                )
                
                with gr.Row():
                    model_to_download = gr.Dropdown(
                        label="Select Model to Download",
                        choices=model_manager.get_downloadable_models()
                    )
                    
                    download_model_btn = gr.Button("Download Model")
                    download_status = gr.Textbox(label="Download Status", interactive=False)
                
                def download_model(model_name):
                    try:
                        model_manager.download_model(model_name)
                        return f"Successfully downloaded {model_name}"
                    except Exception as e:
                        return f"Error downloading {model_name}: {str(e)}"
                
                download_model_btn.click(
                    download_model,
                    inputs=[model_to_download],
                    outputs=[download_status]
                )
        
        return interface

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Coqui TTS Web API", "version": "1.0.0"}

@app.post("/api/tts")
async def api_tts(
    text: str,
    model: str = "tts_models/en/ljspeech/tacotron2-DDC",
    speaker: Optional[str] = None,
    language: Optional[str] = None,
    speed: float = 1.0,
    output_format: str = "wav"
):
    """API endpoint for text-to-speech synthesis"""
    try:
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{file_id}.{output_format}"
        
        audio_path = tts_handler.synthesize(
            text=text,
            model_name=model,
            speaker=speaker,
            language=language,
            speed=speed,
            output_path=str(output_path)
        )
        
        return FileResponse(
            audio_path,
            media_type=f"audio/{output_format}",
            filename=f"tts_{file_id}.{output_format}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice-clone")
async def api_voice_clone(
    name: str,
    audio_file: UploadFile = File(...),
    description: Optional[str] = None
):
    """API endpoint for voice cloning"""
    try:
        # Save uploaded file
        voice_id = str(uuid.uuid4())
        file_ext = os.path.splitext(audio_file.filename)[1]
        voice_path = VOICE_SAMPLES_DIR / f"{voice_id}{file_ext}"
        
        with open(voice_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        # Clone voice
        voice_data = voice_cloner.clone_voice(
            audio_path=str(voice_path),
            name=name,
            description=description
        )
        
        return JSONResponse(content=voice_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def api_list_models():
    """List available TTS models"""
    return JSONResponse(content={"models": model_manager.list_models()})

@app.get("/api/voices")
async def api_list_voices():
    """List available voice clones"""
    voices = []
    for json_file in VOICE_SAMPLES_DIR.glob("*.json"):
        with open(json_file, 'r') as f:
            voices.append(json.load(f))
    return JSONResponse(content={"voices": voices})

# Main entry point
if __name__ == "__main__":
    # Create Gradio interface
    interface = create_gradio_interface()
    
    # Mount Gradio app to FastAPI
    app = gr.mount_gradio_app(app, interface, path="/")
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=2201)
