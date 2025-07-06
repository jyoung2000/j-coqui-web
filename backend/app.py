from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import json
import torch
from TTS.api import TTS
import uuid
from datetime import datetime
import soundfile as sf
import numpy as np
from werkzeug.utils import secure_filename
import threading
import queue

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Configuration
UPLOAD_FOLDER = '/app/temp'
OUTPUT_FOLDER = '/app/outputs'
VOICES_FOLDER = '/app/voices'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'ogg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Initialize device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Model cache
models_cache = {}

# Queue for TTS jobs
tts_queue = queue.Queue()
results = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_or_load_model(model_name):
    """Load model if not in cache"""
    if model_name not in models_cache:
        print(f"Loading model: {model_name}")
        models_cache[model_name] = TTS(model_name).to(device)
    return models_cache[model_name]

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/api/models', methods=['GET'])
def list_models():
    """List all available TTS models"""
    try:
        tts = TTS()
        models = tts.list_models()
        
        # Organize models by type
        organized_models = {
            'tts_models': [],
            'vocoder_models': [],
            'voice_conversion_models': []
        }
        
        for model in models:
            if model.startswith('tts_models/'):
                organized_models['tts_models'].append({
                    'name': model,
                    'language': model.split('/')[1] if len(model.split('/')) > 1 else 'unknown',
                    'dataset': model.split('/')[2] if len(model.split('/')) > 2 else 'unknown',
                    'model_type': model.split('/')[3] if len(model.split('/')) > 3 else 'unknown'
                })
            elif model.startswith('vocoder_models/'):
                organized_models['vocoder_models'].append({
                    'name': model,
                    'language': model.split('/')[1] if len(model.split('/')) > 1 else 'unknown'
                })
            elif model.startswith('voice_conversion_models/'):
                organized_models['voice_conversion_models'].append({
                    'name': model,
                    'language': model.split('/')[1] if len(model.split('/')) > 1 else 'unknown'
                })
        
        return jsonify({
            'status': 'success',
            'models': organized_models,
            'device': device
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/synthesize', methods=['POST'])
def synthesize():
    """Synthesize speech from text"""
    try:
        data = request.json
        text = data.get('text', '')
        model_name = data.get('model', 'tts_models/en/ljspeech/tacotron2-DDC')
        speaker_wav = data.get('speaker_wav', None)
        language = data.get('language', 'en')
        speaker_idx = data.get('speaker_idx', None)
        
        if not text:
            return jsonify({'status': 'error', 'message': 'No text provided'}), 400
        
        # Generate unique filename
        job_id = str(uuid.uuid4())
        output_filename = f"{job_id}.wav"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Load model
        tts = get_or_load_model(model_name)
        
        # Check if model supports multiple speakers
        if hasattr(tts, 'speakers') and tts.speakers:
            speakers_list = list(tts.speakers.keys()) if isinstance(tts.speakers, dict) else tts.speakers
        else:
            speakers_list = []
        
        # Synthesis parameters
        synthesis_params = {
            'text': text,
            'file_path': output_path
        }
        
        # Add speaker parameters if available
        if speaker_wav and os.path.exists(speaker_wav):
            synthesis_params['speaker_wav'] = speaker_wav
            if 'multilingual' in model_name or 'xtts' in model_name:
                synthesis_params['language'] = language
        elif speaker_idx is not None and speakers_list:
            if isinstance(tts.speakers, dict):
                synthesis_params['speaker'] = speakers_list[int(speaker_idx)]
            else:
                synthesis_params['speaker_idx'] = int(speaker_idx)
        
        # Perform synthesis
        tts.tts_to_file(**synthesis_params)
        
        # Get audio info
        data, samplerate = sf.read(output_path)
        duration = len(data) / samplerate
        
        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'filename': output_filename,
            'duration': duration,
            'samplerate': samplerate,
            'speakers': speakers_list
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/voice-clone', methods=['POST'])
def voice_clone():
    """Clone a voice from uploaded audio"""
    try:
        if 'audio' not in request.files:
            return jsonify({'status': 'error', 'message': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Save uploaded file
            voice_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            temp_path = os.path.join(UPLOAD_FOLDER, f"{voice_id}_{filename}")
            file.save(temp_path)
            
            # Process and save to voices folder
            voice_name = request.form.get('voice_name', f'voice_{voice_id[:8]}')
            voice_path = os.path.join(VOICES_FOLDER, f"{voice_name}.wav")
            
            # Convert to WAV if needed
            data, samplerate = sf.read(temp_path)
            sf.write(voice_path, data, samplerate)
            
            # Clean up temp file
            os.remove(temp_path)
            
            # Save voice metadata
            metadata = {
                'id': voice_id,
                'name': voice_name,
                'original_filename': filename,
                'path': voice_path,
                'created_at': datetime.now().isoformat(),
                'samplerate': samplerate,
                'duration': len(data) / samplerate
            }
            
            metadata_path = os.path.join(VOICES_FOLDER, f"{voice_name}.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            return jsonify({
                'status': 'success',
                'voice_id': voice_id,
                'voice_name': voice_name,
                'metadata': metadata
            })
        
        return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/voices', methods=['GET'])
def list_voices():
    """List all saved voices"""
    try:
        voices = []
        for filename in os.listdir(VOICES_FOLDER):
            if filename.endswith('.json'):
                with open(os.path.join(VOICES_FOLDER, filename), 'r') as f:
                    voices.append(json.load(f))
        
        return jsonify({
            'status': 'success',
            'voices': voices
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_audio(filename):
    """Download generated audio file"""
    try:
        return send_file(
            os.path.join(OUTPUT_FOLDER, filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404

@app.route('/api/voice-conversion', methods=['POST'])
def voice_conversion():
    """Convert voice from source to target"""
    try:
        data = request.json
        source_wav = data.get('source_wav')
        target_wav = data.get('target_wav')
        model_name = data.get('model', 'voice_conversion_models/multilingual/vctk/freevc24')
        
        if not source_wav or not target_wav:
            return jsonify({'status': 'error', 'message': 'Source and target audio required'}), 400
        
        # Generate output filename
        job_id = str(uuid.uuid4())
        output_filename = f"vc_{job_id}.wav"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Load model
        tts = get_or_load_model(model_name)
        
        # Perform voice conversion
        tts.voice_conversion_to_file(
            source_wav=source_wav,
            target_wav=target_wav,
            file_path=output_path
        )
        
        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'filename': output_filename
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    """Get or update settings"""
    settings_path = '/app/settings.json'
    
    if request.method == 'GET':
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {
                    'default_model': 'tts_models/en/ljspeech/tacotron2-DDC',
                    'default_vocoder': 'vocoder_models/en/ljspeech/multiband-melgan',
                    'output_format': 'wav',
                    'sample_rate': 22050,
                    'device': device
                }
            return jsonify({'status': 'success', 'settings': settings})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            new_settings = request.json
            with open(settings_path, 'w') as f:
                json.dump(new_settings, f)
            return jsonify({'status': 'success', 'message': 'Settings updated'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/temp-upload', methods=['POST'])
def temp_upload():
    """Upload temporary file for voice conversion"""
    try:
        if 'audio' not in request.files:
            return jsonify({'status': 'error', 'message': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_id = str(uuid.uuid4())
            temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{temp_id}_{filename}")
            file.save(temp_path)
            
            return jsonify({
                'status': 'success',
                'path': temp_path,
                'temp_id': temp_id
            })
        
        return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'device': device,
        'models_loaded': len(models_cache),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Create required directories
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, VOICES_FOLDER]:
        os.makedirs(folder, exist_ok=True)
    
    # Run the app
    app.run(host='0.0.0.0', port=2201, debug=False)