// Coqui TTS WebGUI JavaScript

// Global state
const state = {
    currentModel: null,
    availableModels: [],
    voiceProfiles: [],
    isProcessing: false,
    audioContext: null,
    webSocket: null
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Initialize audio context
    state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    // Load available models
    await loadModels();
    
    // Load voice profiles
    await loadVoiceProfiles();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize WebSocket for real-time features
    initializeWebSocket();
}

// API Functions
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`/api${endpoint}`, {
            ...options,
            headers: {
                ...options.headers,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }
        
        return response;
    } catch (error) {
        console.error('API Call Error:', error);
        showError(error.message);
        throw error;
    }
}

async function loadModels() {
    try {
        const response = await apiCall('/models');
        const data = await response.json();
        state.availableModels = data.models;
        updateModelDropdown();
    } catch (error) {
        console.error('Failed to load models:', error);
    }
}

async function loadVoiceProfiles() {
    try {
        const response = await apiCall('/voices');
        const data = await response.json();
        state.voiceProfiles = data.voices;
        updateVoiceProfiles();
    } catch (error) {
        console.error('Failed to load voice profiles:', error);
    }
}

// TTS Functions
async function synthesizeSpeech() {
    if (state.isProcessing) return;
    
    const text = document.getElementById('tts-text').value;
    const model = document.getElementById('model-select').value;
    
    if (!text || !model) {
        showError('Please enter text and select a model');
        return;
    }
    
    state.isProcessing = true;
    updateUIState();
    
    try {
        const params = {
            text,
            model,
            speaker: document.getElementById('speaker-select').value,
            language: document.getElementById('language-select').value,
            speed: parseFloat(document.getElementById('speed-slider').value),
            pitch: parseFloat(document.getElementById('pitch-slider').value),
            energy: parseFloat(document.getElementById('energy-slider').value),
            emotion: document.getElementById('emotion-select').value,
            output_format: document.querySelector('input[name="output-format"]:checked').value
        };
        
        // Check if using voice clone
        if (document.getElementById('use-voice-clone').checked) {
            const selectedVoice = document.querySelector('.voice-card.selected');
            if (selectedVoice) {
                params.voice_sample = selectedVoice.dataset.voiceId;
            }
        }
        
        const response = await apiCall('/tts', {
            method: 'POST',
            body: JSON.stringify(params)
        });
        
        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        
        // Update audio player
        const audioPlayer = document.getElementById('audio-player');
        audioPlayer.src = audioUrl;
        audioPlayer.style.display = 'block';
        
        // Enable download button
        const downloadBtn = document.getElementById('download-btn');
        downloadBtn.style.display = 'inline-block';
        downloadBtn.onclick = () => downloadAudio(audioUrl, `tts_${Date.now()}.${params.output_format}`);
        
        showSuccess('Audio generated successfully!');
    } catch (error) {
        showError('Failed to generate audio: ' + error.message);
    } finally {
        state.isProcessing = false;
        updateUIState();
    }
}

// Voice Cloning Functions
async function cloneVoice() {
    const name = document.getElementById('voice-name').value;
    const fileInput = document.getElementById('voice-file');
    const description = document.getElementById('voice-description').value;
    
    if (!name || !fileInput.files[0]) {
        showError('Please provide a name and select an audio file');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('audio_file', fileInput.files[0]);
    formData.append('description', description);
    
    try {
        const response = await fetch('/api/voices/clone', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to clone voice');
        }
        
        const result = await response.json();
        showSuccess('Voice cloned successfully!');
        
        // Reload voice profiles
        await loadVoiceProfiles();
        
        // Clear form
        document.getElementById('voice-name').value = '';
        document.getElementById('voice-file').value = '';
        document.getElementById('voice-description').value = '';
    } catch (error) {
        showError('Failed to clone voice: ' + error.message);
    }
}

// UI Update Functions
function updateModelDropdown() {
    const select = document.getElementById('model-select');
    select.innerHTML = '<option value="">Select a model...</option>';
    
    state.availableModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        select.appendChild(option);
    });
}

function updateVoiceProfiles() {
    const container = document.getElementById('voice-profiles');
    container.innerHTML = '';
    
    state.voiceProfiles.forEach(voice => {
        const card = createVoiceCard(voice);
        container.appendChild(card);
    });
}

function createVoiceCard(voice) {
    const card = document.createElement('div');
    card.className = 'voice-card';
    card.dataset.voiceId = voice.voice_id;
    
    card.innerHTML = `
        <div class="voice-card-header">${voice.name}</div>
        <div class="voice-card-description">${voice.description || 'No description'}</div>
        <div class="voice-card-meta">
            <small>Created: ${new Date(voice.created_at).toLocaleDateString()}</small>
        </div>
    `;
    
    card.addEventListener('click', () => {
        document.querySelectorAll('.voice-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
    });
    
    return card;
}

function updateUIState() {
    const synthesizeBtn = document.getElementById('synthesize-btn');
    const spinner = document.getElementById('processing-spinner');
    
    if (state.isProcessing) {
        synthesizeBtn.disabled = true;
        synthesizeBtn.innerHTML = '<span class="spinner"></span> Processing...';
    } else {
        synthesizeBtn.disabled = false;
        synthesizeBtn.innerHTML = 'Synthesize';
    }
}

// Event Listeners
function setupEventListeners() {
    // Model selection change
    document.getElementById('model-select').addEventListener('change', async (e) => {
        const model = e.target.value;
        if (model) {
            await updateModelInfo(model);
        }
    });
    
    // Sliders
    document.querySelectorAll('.slider').forEach(slider => {
        slider.addEventListener('input', (e) => {
            const valueDisplay = document.getElementById(e.target.id + '-value');
            if (valueDisplay) {
                valueDisplay.textContent = e.target.value;
            }
        });
    });
    
    // Voice clone checkbox
    document.getElementById('use-voice-clone').addEventListener('change', (e) => {
        const voiceSelection = document.getElementById('voice-selection');
        voiceSelection.style.display = e.target.checked ? 'block' : 'none';
    });
    
    // File upload
    document.getElementById('voice-file').addEventListener('change', (e) => {
        const label = document.querySelector('.file-upload-label');
        if (e.target.files[0]) {
            label.classList.add('has-file');
            label.textContent = `Selected: ${e.target.files[0].name}`;
        } else {
            label.classList.remove('has-file');
            label.textContent = 'Click to upload audio file';
        }
    });
    
    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const targetId = tab.dataset.target;
            
            // Update active tab
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Show target content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.style.display = content.id === targetId ? 'block' : 'none';
            });
        });
    });
}

async function updateModelInfo(modelName) {
    try {
        const response = await apiCall(`/models/${encodeURIComponent(modelName)}`);
        const info = await response.json();
        
        // Update speaker dropdown
        const speakerSelect = document.getElementById('speaker-select');
        speakerSelect.innerHTML = '<option value="">Default</option>';
        if (info.speakers && info.speakers.length > 0) {
            info.speakers.forEach(speaker => {
                const option = document.createElement('option');
                option.value = speaker;
                option.textContent = speaker;
                speakerSelect.appendChild(option);
            });
            speakerSelect.disabled = false;
        } else {
            speakerSelect.disabled = true;
        }
        
        // Update language dropdown
        const languageSelect = document.getElementById('language-select');
        languageSelect.innerHTML = '<option value="">Default</option>';
        if (info.languages && info.languages.length > 0) {
            info.languages.forEach(language => {
                const option = document.createElement('option');
                option.value = language;
                option.textContent = language;
                languageSelect.appendChild(option);
            });
            languageSelect.disabled = false;
        } else {
            languageSelect.disabled = true;
        }
    } catch (error) {
        console.error('Failed to get model info:', error);
    }
}

// WebSocket Functions
function initializeWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws/tts-stream`;
    state.webSocket = new WebSocket(wsUrl);
    
    state.webSocket.onopen = () => {
        console.log('WebSocket connected');
    };
    
    state.webSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    state.webSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    state.webSocket.onclose = () => {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(initializeWebSocket, 5000);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'audio_chunk':
            // Handle streaming audio
            playAudioChunk(data.chunk, data.index, data.is_final);
            break;
        case 'error':
            showError(data.message);
            break;
        default:
            console.log('Unknown WebSocket message type:', data.type);
    }
}

// Audio playback functions
let audioChunks = [];
let currentChunkIndex = 0;

function playAudioChunk(chunkBase64, index, isFinal) {
    // Decode base64 to audio data
    const audioData = atob(chunkBase64);
    const arrayBuffer = new ArrayBuffer(audioData.length);
    const view = new Uint8Array(arrayBuffer);
    
    for (let i = 0; i < audioData.length; i++) {
        view[i] = audioData.charCodeAt(i);
    }
    
    audioChunks[index] = arrayBuffer;
    
    if (isFinal) {
        // Combine all chunks and play
        const totalLength = audioChunks.reduce((acc, chunk) => acc + chunk.byteLength, 0);
        const combined = new Uint8Array(totalLength);
        let offset = 0;
        
        audioChunks.forEach(chunk => {
            combined.set(new Uint8Array(chunk), offset);
            offset += chunk.byteLength;
        });
        
        // Create blob and play
        const blob = new Blob([combined], { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(blob);
        const audioPlayer = document.getElementById('audio-player');
        audioPlayer.src = audioUrl;
        audioPlayer.play();
        
        // Clear chunks for next stream
        audioChunks = [];
        currentChunkIndex = 0;
    }
}

// Utility Functions
function showSuccess(message) {
    showMessage(message, 'success');
}

function showError(message) {
    showMessage(message, 'error');
}

function showInfo(message) {
    showMessage(message, 'info');
}

function showMessage(message, type) {
    const container = document.getElementById('message-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `status-message status-${type} fade-in`;
    messageDiv.textContent = message;
    
    container.appendChild(messageDiv);
    
    // Remove after 5 seconds
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

function downloadAudio(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Export functions for use in HTML
window.synthesizeSpeech = synthesizeSpeech;
window.cloneVoice = cloneVoice;
window.loadModels = loadModels;
window.loadVoiceProfiles = loadVoiceProfiles;
