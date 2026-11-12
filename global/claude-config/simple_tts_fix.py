#!/usr/bin/env python3
"""
Fixed TTS Hook - Addresses text truncation issues
Main fixes:
1. No arbitrary character limits (removes the 2500 char limit)
2. Smart chunking at sentence boundaries for long text
3. Better text cleaning
4. Added sync wait for transcript reading
"""

import json
import sys
import os
import re
import tempfile
import subprocess
import requests
import time
from datetime import datetime

def log_debug(message):
    try:
        with open('/tmp/tts_fix_debug.log', 'a') as f:
            f.write(f"{datetime.now()}: {message}\n")
    except:
        pass

def clean_text_for_speech(text):
    """Clean text but preserve sentence structure"""
    # Remove XML tags but keep the content readable
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '[Code Block]', text)
    
    # Clean up markdown but keep readability
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'`([^`]+)`', r'\1', text)      # Inline code
    
    # Normalize whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def chunk_text_by_sentences(text, max_chars=3800):
    """Split text into chunks at sentence boundaries"""
    if len(text) <= max_chars:
        return [text]
    
    # Split by sentence endings
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed limit, start new chunk
        if len(current_chunk) + len(sentence) + 1 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Single sentence is too long, force split
                chunks.append(sentence[:max_chars])
                current_chunk = sentence[max_chars:]
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def text_to_speech_chunked(text, api_key):
    """Convert text to speech with chunking for long text"""
    if not text or len(text) < 10:
        return
    
    log_debug(f"Processing text of length: {len(text)}")
    
    # Clean the text first
    clean_text = clean_text_for_speech(text)
    log_debug(f"Cleaned text length: {len(clean_text)}")
    
    # Chunk the text
    chunks = chunk_text_by_sentences(clean_text)
    log_debug(f"Split into {len(chunks)} chunks")
    
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    audio_files = []
    
    try:
        # Kill any existing audio playback
        subprocess.run(['pkill', '-f', 'afplay'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
                
            log_debug(f"Processing chunk {i+1}/{len(chunks)}: {len(chunk)} chars")
            
            data = {
                "model": "tts-1",
                "input": chunk,
                "voice": "onyx",
                "speed": 1.20
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                # Save audio chunk to temp file
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                    f.write(response.content)
                    audio_files.append(f.name)
            else:
                log_debug(f"API error for chunk {i+1}: {response.status_code}")
                continue
        
        # Play all audio files sequentially
        for audio_file in audio_files:
            log_debug(f"Playing audio file: {audio_file}")
            try:
                subprocess.run(['afplay', audio_file], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             timeout=120)
            except subprocess.TimeoutExpired:
                log_debug("Audio playback timeout")
                break
        
    except Exception as e:
        log_debug(f"TTS Error: {e}")
    finally:
        # Clean up temp files
        for audio_file in audio_files:
            try:
                os.unlink(audio_file)
            except:
                pass

def get_api_key():
    """Get OpenAI API key from various sources"""
    # Try environment first
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        return api_key
    
    # Try Claude settings files
    settings_files = [
        os.path.expanduser('~/.claude/settings.local.json'),
        os.path.expanduser('~/.claude/.claude/settings.json'),
        os.path.expanduser('~/.claude/settings.json')
    ]
    
    for settings_path in settings_files:
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    api_key = settings.get('env', {}).get('OPENAI_API_KEY')
                    if api_key:
                        return api_key
        except:
            continue
    
    return None

def extract_response_text(input_data):
    """Extract the assistant's response text from hook input"""
    try:
        data = json.loads(input_data)
        
        # Check for transcript path
        transcript_path = data.get('transcript_path')
        if transcript_path and os.path.exists(transcript_path):
            log_debug(f"Reading transcript from: {transcript_path}")
            
            # Wait a moment for file to be fully written
            time.sleep(0.2)
            
            with open(transcript_path, 'r') as f:
                lines = f.readlines()
            
            # Find the last assistant message
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'assistant':
                        message = entry.get('message', {})
                        content = message.get('content', [])
                        
                        if isinstance(content, list):
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text_parts.append(item.get('text', ''))
                            return ' '.join(text_parts)
                        elif isinstance(content, str):
                            return content
                except json.JSONDecodeError:
                    continue
        
        # Fallback parsing
        if 'prompt' in data:
            return str(data['prompt'])
        elif 'message' in data:
            return str(data['message'])
        elif 'content' in data:
            if isinstance(data['content'], list):
                text_parts = []
                for item in data['content']:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                return ' '.join(text_parts)
            else:
                return str(data['content'])
        elif 'text' in data:
            return str(data['text'])
            
    except json.JSONDecodeError:
        # Raw text input
        return input_data
    
    return ""

def main():
    log_debug("Fixed TTS hook started")
    
    try:
        # Get API key
        api_key = get_api_key()
        if not api_key:
            log_debug("No OpenAI API key found")
            return
        
        # Read input
        input_data = sys.stdin.read()
        log_debug(f"Input data length: {len(input_data)}")
        
        # Extract text
        text = extract_response_text(input_data)
        if not text:
            log_debug("No text found to convert")
            return
        
        log_debug(f"Extracted text length: {len(text)}")
        
        # Convert to speech (with chunking if needed)
        text_to_speech_chunked(text, api_key)
        
    except Exception as e:
        log_debug(f"Hook error: {str(e)}")

if __name__ == "__main__":
    main()