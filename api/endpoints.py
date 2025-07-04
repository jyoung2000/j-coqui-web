from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from typing import Optional, List, Dict, Any
import uuid
import json
from pathlib import Path
import aiofiles
import asyncio
from datetime import datetime

from ..modules.tts_handler import TTSHandler
from ..modules.voice_cloner import VoiceCloner
from ..modules.model_manager import ModelManager
from ..modules.audio_processor import AudioProcessor
from .auth import get_api_key
from .models import (
    TTSRequest, TTSBatchRequest, VoiceCloneResponse,
    ModelInfo, AudioInfo, BatchStatus
)

# Create routers
tts_router = APIRouter(prefix="/api/tts", tags=["TTS"])
voice_router = APIRouter(prefix="/api/voices", tags=["Voice Cloning"])
model_router = APIRouter(prefix="/api/models", tags=["Model Management"])
audio_router = APIRouter(prefix="/api/audio", tags=["Audio Processing"])

# Initialize handlers
tts_handler = TTSHandler()
voice_cloner = VoiceCloner()
model_manager = ModelManager()
audio_processor = AudioProcessor()

# Batch processing storage
batch_jobs = {}

# Paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
VOICE_SAMPLES_DIR = BASE_DIR / "voice_samples"

@tts_router.post("/")
async def synthesize_tts(
    request: TTSRequest,
    api_key: str = Depends(get_api_key)
):
    """Synthesize speech from text"""
    try:
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{file_id}.{request.output_format}"
        
        audio_path = await asyncio.to_thread(
            tts_handler.synthesize,
            text=request.text,
            model_name=request.model,
            speaker=request.speaker,
            language=request.language,
            speed=request.speed,
            pitch=request.pitch,
            energy=request.energy,
            emotion=request.emotion,
            output_path=str(output_path)
        )
        
        return FileResponse(
            audio_path,
            media_type=f"audio/{request.output_format}",
            filename=f"tts_{file_id}.{request.output_format}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@tts_router.post("/batch")
async def batch_tts(
    request: TTSBatchRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key)
):
    """Process multiple TTS requests in batch"""
    batch_id = str(uuid.uuid4())
    
    # Initialize batch job
    batch_jobs[batch_id] = {
        "status": "processing",
        "total": len(request.requests),
        "completed": 0,
        "results": []
    }
    
    # Process in background
    background_tasks.add_task(
        process_batch_tts,
        batch_id,
        request.requests
    )
    
    return JSONResponse({
        "batch_id": batch_id,
        "status": "processing",
        "total": len(request.requests),
        "completed": 0
    })

async def process_batch_tts(batch_id: str, requests: List[TTSRequest]):
    """Process batch TTS requests"""
    for i, req in enumerate(requests):
        try:
            file_id = str(uuid.uuid4())
            output_path = OUTPUT_DIR / f"{file_id}.{req.output_format}"
            
            audio_path = await asyncio.to_thread(
                tts_handler.synthesize,
                text=req.text,
                model_name=req.model,
                speaker=req.speaker,
                language=req.language,
                speed=req.speed,
                pitch=req.pitch,
                energy=req.energy,
                emotion=req.emotion,
                output_path=str(output_path)
            )
            
            batch_jobs[batch_id]["results"].append({
                "index": i,
                "status": "success",
                "audio_url": f"/output/{file_id}.{req.output_format}"
            })
        
        except Exception as e:
            batch_jobs[batch_id]["results"].append({
                "index": i,
                "status": "error",
                "error": str(e)
            })
        
        batch_jobs[batch_id]["completed"] += 1
    
    batch_jobs[batch_id]["status"] = "completed"

@tts_router.get("/batch/{batch_id}")
async def get_batch_status(
    batch_id: str,
    api_key: str = Depends(get_api_key)
):
    """Get batch processing status"""
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return JSONResponse(batch_jobs[batch_id])

@voice_router.post("/clone")
async def clone_voice(
    name: str,
    audio_file: UploadFile = File(...),
    description: Optional[str] = None,
    api_key: str = Depends(get_api_key)
):
    """Clone a voice from audio sample"""
    try:
        # Save uploaded file
        voice_id = str(uuid.uuid4())
        file_ext = Path(audio_file.filename).suffix
        voice_path = VOICE_SAMPLES_DIR / f"{voice_id}{file_ext}"
        
        async with aiofiles.open(voice_path, 'wb') as f:
            content = await audio_file.read()
            await f.write(content)
        
        # Clone voice
        voice_data = await asyncio.to_thread(
            voice_cloner.clone_voice,
            audio_path=str(voice_path),
            name=name,
            description=description
        )
        
        # Save metadata
        metadata_path = VOICE_SAMPLES_DIR / f"{voice_id}.json"
        async with aiofiles.open(metadata_path, 'w') as f:
            await f.write(json.dumps(voice_data))
        
        return VoiceCloneResponse(
            name=name,
            voice_id=voice_id,
            description=description,
            created_at=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@voice_router.get("/")
async def list_voices(api_key: str = Depends(get_api_key)):
    """List all cloned voices"""
    voices = []
    
    for json_file in VOICE_SAMPLES_DIR.glob("*.json"):
        async with aiofiles.open(json_file, 'r') as f:
            content = await f.read()
            voices.append(json.loads(content))
    
    return JSONResponse({"voices": voices})

@voice_router.delete("/{voice_id}")
async def delete_voice(
    voice_id: str,
    api_key: str = Depends(get_api_key)
):
    """Delete a cloned voice"""
    # Find and delete voice files
    deleted = False
    
    for file in VOICE_SAMPLES_DIR.glob(f"{voice_id}.*"):
        file.unlink()
        deleted = True
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    return JSONResponse({"message": "Voice deleted successfully"})

@model_router.get("/")
async def list_models(api_key: str = Depends(get_api_key)):
    """List available TTS models"""
    models = await asyncio.to_thread(model_manager.list_models)
    return JSONResponse({"models": models})

@model_router.get("/{model_name:path}")
async def get_model_info(
    model_name: str,
    api_key: str = Depends(get_api_key)
):
    """Get information about a specific model"""
    info = await asyncio.to_thread(
        model_manager.get_model_info,
        model_name
    )
    return ModelInfo(**info)

@model_router.post("/download")
async def download_model(
    model_name: str,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key)
):
    """Download a TTS model"""
    background_tasks.add_task(
        model_manager.download_model,
        model_name
    )
    
    return JSONResponse({
        "message": "Model download started",
        "model_name": model_name,
        "status": "downloading"
    })

@audio_router.post("/info")
async def get_audio_info(
    audio_file: UploadFile = File(...),
    api_key: str = Depends(get_api_key)
):
    """Get information about an audio file"""
    try:
        # Save temporary file
        temp_path = Path(f"/tmp/{uuid.uuid4()}{Path(audio_file.filename).suffix}")
        
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await audio_file.read()
            await f.write(content)
        
        # Get audio info
        info = await asyncio.to_thread(
            audio_processor.get_audio_info,
            str(temp_path)
        )
        
        # Clean up
        temp_path.unlink()
        
        return AudioInfo(**info)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@audio_router.post("/convert")
async def convert_audio(
    audio_file: UploadFile = File(...),
    output_format: str = "wav",
    sample_rate: Optional[int] = None,
    api_key: str = Depends(get_api_key)
):
    """Convert audio between formats"""
    try:
        # Save temporary file
        temp_input = Path(f"/tmp/{uuid.uuid4()}{Path(audio_file.filename).suffix}")
        temp_output = Path(f"/tmp/{uuid.uuid4()}.{output_format}")
        
        async with aiofiles.open(temp_input, 'wb') as f:
            content = await audio_file.read()
            await f.write(content)
        
        # Convert audio
        output_path = await asyncio.to_thread(
            audio_processor.convert_format,
            str(temp_input),
            str(temp_output),
            output_format,
            sample_rate
        )
        
        # Return converted file
        return FileResponse(
            output_path,
            media_type=f"audio/{output_format}",
            filename=f"converted.{output_format}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temp files
        if temp_input.exists():
            temp_input.unlink()
        if temp_output.exists():
            temp_output.unlink()
