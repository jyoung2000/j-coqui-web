# Coqui TTS Web API Documentation

## Base URL
```
http://localhost:2201
```

## Authentication

By default, the API does not require authentication. To enable API key authentication:

1. Set `ENABLE_API_AUTH=true` in your `.env` file
2. Set your `API_KEY` in the `.env` file
3. Include the API key in requests: `Authorization: Bearer YOUR_API_KEY`

## Endpoints

### 1. Text-to-Speech Synthesis

**POST** `/api/tts`

Synthesize speech from text using specified model and parameters.

#### Request Body
```json
{
  "text": "Hello, this is a test.",
  "model": "tts_models/en/ljspeech/tacotron2-DDC",
  "speaker": "speaker_name",
  "language": "en",
  "speed": 1.0,
  "pitch": 1.0,
  "energy": 1.0,
  "emotion": "neutral",
  "output_format": "wav"
}
```

#### Parameters
- `text` (required): Text to synthesize
- `model` (required): Model name to use
- `speaker` (optional): Speaker name for multi-speaker models
- `language` (optional): Language code for multi-lingual models
- `speed` (optional): Speed factor (0.5-2.0, default: 1.0)
- `pitch` (optional): Pitch adjustment (0.5-2.0, default: 1.0)
- `energy` (optional): Energy/volume adjustment (0.5-2.0, default: 1.0)
- `emotion` (optional): Emotion setting (neutral, happy, sad, angry, fear, surprise)
- `output_format` (optional): Output audio format (wav, mp3, flac, default: wav)

#### Response
Returns the synthesized audio file.

#### Example
```bash
curl -X POST http://localhost:2201/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "model": "tts_models/en/ljspeech/tacotron2-DDC"}' \
  --output output.wav
```

### 2. Voice Cloning

**POST** `/api/voice-clone`

Clone a voice from an audio sample.

#### Request
Multipart form data:
- `name` (required): Name for the cloned voice
- `audio_file` (required): Audio file containing voice sample
- `description` (optional): Description of the voice

#### Response
```json
{
  "name": "John Doe",
  "voice_id": "uuid-here",
  "description": "Voice description",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Example
```bash
curl -X POST http://localhost:2201/api/voice-clone \
  -F "name=John Doe" \
  -F "audio_file=@voice_sample.wav" \
  -F "description=Male voice sample"
```

### 3. List Available Models

**GET** `/api/models`

Get list of all available TTS models.

#### Response
```json
{
  "models": [
    "tts_models/en/ljspeech/tacotron2-DDC",
    "tts_models/en/ljspeech/glow-tts",
    "tts_models/multilingual/multi-dataset/your_tts"
  ]
}
```

### 4. Get Model Information

**GET** `/api/models/{model_name}`

Get detailed information about a specific model.

#### Response
```json
{
  "name": "tts_models/en/ljspeech/tacotron2-DDC",
  "language": "en",
  "dataset": "ljspeech",
  "is_multi_speaker": false,
  "is_multi_lingual": false,
  "speakers": [],
  "languages": ["en"]
}
```

### 5. List Voice Clones

**GET** `/api/voices`

Get list of all cloned voices.

#### Response
```json
{
  "voices": [
    {
      "name": "John Doe",
      "voice_id": "uuid-here",
      "description": "Male voice sample",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 6. Delete Voice Clone

**DELETE** `/api/voices/{voice_id}`

Delete a cloned voice.

#### Response
```json
{
  "message": "Voice deleted successfully"
}
```

### 7. Download Model

**POST** `/api/models/download`

Download a TTS model.

#### Request Body
```json
{
  "model_name": "tts_models/en/vctk/vits"
}
```

#### Response
```json
{
  "message": "Model download started",
  "model_name": "tts_models/en/vctk/vits",
  "status": "downloading"
}
```

### 8. Get Audio File Info

**POST** `/api/audio/info`

Get information about an audio file.

#### Request
Multipart form data:
- `audio_file` (required): Audio file to analyze

#### Response
```json
{
  "duration": 5.5,
  "sample_rate": 22050,
  "channels": 1,
  "format": "WAV",
  "bit_depth": 16,
  "size_bytes": 242550
}
```

### 9. Convert Audio Format

**POST** `/api/audio/convert`

Convert audio between formats.

#### Request
Multipart form data:
- `audio_file` (required): Audio file to convert
- `output_format` (required): Target format (wav, mp3, flac, ogg)
- `sample_rate` (optional): Target sample rate

#### Response
Returns the converted audio file.

### 10. Batch TTS Processing

**POST** `/api/tts/batch`

Process multiple text-to-speech requests in batch.

#### Request Body
```json
{
  "requests": [
    {
      "text": "First text",
      "model": "tts_models/en/ljspeech/tacotron2-DDC"
    },
    {
      "text": "Second text",
      "model": "tts_models/en/ljspeech/glow-tts"
    }
  ]
}
```

#### Response
```json
{
  "batch_id": "batch-uuid",
  "status": "processing",
  "total": 2,
  "completed": 0
}
```

### 11. Get Batch Status

**GET** `/api/tts/batch/{batch_id}`

Get status of batch processing.

#### Response
```json
{
  "batch_id": "batch-uuid",
  "status": "completed",
  "total": 2,
  "completed": 2,
  "results": [
    {
      "index": 0,
      "status": "success",
      "audio_url": "/output/uuid1.wav"
    },
    {
      "index": 1,
      "status": "success",
      "audio_url": "/output/uuid2.wav"
    }
  ]
}
```

## WebSocket API

### Real-time TTS Streaming

**WebSocket** `/ws/tts-stream`

Stream text-to-speech synthesis in real-time.

#### Connection
```javascript
const ws = new WebSocket('ws://localhost:2201/ws/tts-stream');
```

#### Message Format
```json
{
  "type": "synthesize",
  "text": "Text to synthesize",
  "model": "tts_models/en/ljspeech/tacotron2-DDC",
  "stream": true
}
```

#### Response Stream
```json
{
  "type": "audio_chunk",
  "chunk": "base64_encoded_audio_data",
  "index": 0,
  "is_final": false
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  }
}
```

### Common Error Codes
- `INVALID_REQUEST`: Invalid request parameters
- `MODEL_NOT_FOUND`: Requested model not found
- `SYNTHESIS_FAILED`: TTS synthesis failed
- `VOICE_NOT_FOUND`: Voice clone not found
- `UNAUTHORIZED`: Invalid or missing API key
- `RATE_LIMITED`: Too many requests

## Rate Limiting

By default, the API allows:
- 100 requests per minute per IP
- 10 concurrent synthesis operations

These can be configured in the `.env` file.

## Examples

### Python
```python
import requests

# Text-to-speech
response = requests.post(
    "http://localhost:2201/api/tts",
    json={
        "text": "Hello from Python!",
        "model": "tts_models/en/ljspeech/tacotron2-DDC"
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

### JavaScript
```javascript
// Using fetch API
const response = await fetch('http://localhost:2201/api/tts', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: 'Hello from JavaScript!',
    model: 'tts_models/en/ljspeech/tacotron2-DDC'
  })
});

const blob = await response.blob();
const audioUrl = URL.createObjectURL(blob);
const audio = new Audio(audioUrl);
audio.play();
```

### cURL
```bash
# Simple TTS
curl -X POST http://localhost:2201/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from cURL!", "model": "tts_models/en/ljspeech/tacotron2-DDC"}' \
  --output hello.wav

# With authentication
curl -X POST http://localhost:2201/api/tts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"text": "Authenticated request", "model": "tts_models/en/ljspeech/tacotron2-DDC"}' \
  --output auth.wav
```
