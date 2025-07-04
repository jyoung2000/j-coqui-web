from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any
import json
import asyncio
import base64
from pathlib import Path
import uuid

from ..modules.tts_handler import TTSHandler

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

# Initialize connection manager
manager = ConnectionManager()
tts_handler = TTSHandler()

async def tts_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time TTS streaming"""
    client_id = str(uuid.uuid4())
    
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            if data.get("type") == "synthesize":
                # Handle TTS synthesis
                await handle_tts_stream(
                    client_id,
                    data.get("text", ""),
                    data.get("model", "tts_models/en/ljspeech/tacotron2-DDC"),
                    data.get("stream", True)
                )
            
            elif data.get("type") == "stop":
                # Handle stop request
                await manager.send_message(client_id, {
                    "type": "stopped",
                    "message": "Synthesis stopped"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await manager.send_message(client_id, {
            "type": "error",
            "message": str(e)
        })
        manager.disconnect(client_id)

async def handle_tts_stream(
    client_id: str,
    text: str,
    model: str,
    stream: bool = True
):
    """Handle TTS synthesis with optional streaming"""
    try:
        if stream:
            # Stream audio chunks as they're generated
            # This is a simplified implementation
            temp_path = Path(f"/tmp/{uuid.uuid4()}.wav")
            
            # Generate full audio first (streaming generation would require
            # modification of the TTS library)
            await asyncio.to_thread(
                tts_handler.synthesize,
                text=text,
                model_name=model,
                output_path=str(temp_path)
            )
            
            # Read and stream in chunks
            chunk_size = 4096
            with open(temp_path, 'rb') as f:
                chunk_index = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Send chunk
                    await manager.send_message(client_id, {
                        "type": "audio_chunk",
                        "chunk": base64.b64encode(chunk).decode('utf-8'),
                        "index": chunk_index,
                        "is_final": False
                    })
                    
                    chunk_index += 1
                    await asyncio.sleep(0.01)  # Small delay to simulate streaming
            
            # Send final message
            await manager.send_message(client_id, {
                "type": "audio_chunk",
                "chunk": "",
                "index": chunk_index,
                "is_final": True
            })
            
            # Clean up
            temp_path.unlink()
        
        else:
            # Generate and send complete audio
            temp_path = Path(f"/tmp/{uuid.uuid4()}.wav")
            
            await asyncio.to_thread(
                tts_handler.synthesize,
                text=text,
                model_name=model,
                output_path=str(temp_path)
            )
            
            # Read entire file
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            # Send complete audio
            await manager.send_message(client_id, {
                "type": "audio_complete",
                "audio": base64.b64encode(audio_data).decode('utf-8'),
                "format": "wav"
            })
            
            # Clean up
            temp_path.unlink()
    
    except Exception as e:
        await manager.send_message(client_id, {
            "type": "error",
            "message": f"Synthesis failed: {str(e)}"
        })
