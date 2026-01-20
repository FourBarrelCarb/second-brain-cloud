"""
Audio Recorder Component
Browser-based audio recording using JavaScript MediaRecorder API
"""

import streamlit as st
import streamlit.components.v1 as components


def audio_recorder_component(key: str = "audio_recorder") -> bytes:
    """
    Display an audio recorder component that captures audio from the browser.
    
    Args:
        key: Unique key for this component instance
        
    Returns:
        Audio bytes when recording is complete, None otherwise
    """
    
    # HTML + JavaScript for audio recording
    component_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .recorder-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 15px;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            }
            
            .record-btn {
                width: 80px;
                height: 80px;
                border-radius: 50%;
                border: none;
                cursor: pointer;
                font-size: 32px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }
            
            .record-btn.idle {
                background: white;
            }
            
            .record-btn.recording {
                background: #ff4444;
                animation: pulse 1.5s infinite;
            }
            
            .record-btn:hover {
                transform: scale(1.1);
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            
            .status-text {
                color: white;
                font-size: 16px;
                font-weight: 500;
                text-align: center;
            }
            
            .timer {
                color: white;
                font-size: 24px;
                font-weight: bold;
                font-family: monospace;
            }
        </style>
    </head>
    <body>
        <div class="recorder-container">
            <button id="recordBtn" class="record-btn idle" onclick="toggleRecording()">
                🎤
            </button>
            <div class="status-text" id="statusText">Click to start recording</div>
            <div class="timer" id="timer">00:00</div>
        </div>
        
        <script>
            let mediaRecorder;
            let audioChunks = [];
            let isRecording = false;
            let startTime;
            let timerInterval;
            
            const recordBtn = document.getElementById('recordBtn');
            const statusText = document.getElementById('statusText');
            const timerDisplay = document.getElementById('timer');
            
            async function toggleRecording() {
                if (!isRecording) {
                    await startRecording();
                } else {
                    stopRecording();
                }
            }
            
            async function startRecording() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        } 
                    });
                    
                    mediaRecorder = new MediaRecorder(stream, {
                        mimeType: 'audio/webm;codecs=opus'
                    });
                    
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = (event) => {
                        audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        const reader = new FileReader();
                        
                        reader.onloadend = () => {
                            const base64Audio = reader.result.split(',')[1];
                            // Send to Streamlit
                            window.parent.postMessage({
                                type: 'streamlit:setComponentValue',
                                data: base64Audio
                            }, '*');
                        };
                        
                        reader.readAsDataURL(audioBlob);
                        
                        // Stop all tracks
                        stream.getTracks().forEach(track => track.stop());
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    
                    recordBtn.className = 'record-btn recording';
                    recordBtn.textContent = '⏹️';
                    statusText.textContent = 'Recording... Click to stop';
                    
                    // Start timer
                    startTime = Date.now();
                    timerInterval = setInterval(updateTimer, 100);
                    
                } catch (error) {
                    console.error('Error accessing microphone:', error);
                    statusText.textContent = 'Microphone access denied';
                    alert('Please allow microphone access to use voice input.');
                }
            }
            
            function stopRecording() {
                if (mediaRecorder && isRecording) {
                    mediaRecorder.stop();
                    isRecording = false;
                    
                    recordBtn.className = 'record-btn idle';
                    recordBtn.textContent = '🎤';
                    statusText.textContent = 'Processing audio...';
                    
                    // Stop timer
                    clearInterval(timerInterval);
                }
            }
            
            function updateTimer() {
                const elapsed = Date.now() - startTime;
                const seconds = Math.floor(elapsed / 1000);
                const minutes = Math.floor(seconds / 60);
                const remainingSeconds = seconds % 60;
                
                timerDisplay.textContent = 
                    String(minutes).padStart(2, '0') + ':' + 
                    String(remainingSeconds).padStart(2, '0');
            }
        </script>
    </body>
    </html>
    """
    
    # Render component
    audio_data = components.html(
        component_html,
        height=200,
        key=key
    )
    
    return audio_data
