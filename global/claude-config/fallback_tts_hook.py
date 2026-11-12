#!/usr/bin/env python3
import json
import sys
import os
import re
import tempfile
import subprocess
import requests
from datetime import datetime

def log_debug(message):
    """Debug logging to help troubleshoot"""
    try:
        with open(os.path.expanduser('~/.claude/tts_debug.log'), 'a') as f:
            f.write(f"{datetime.now()}: {message}\n")
    except:
        pass

def say_fallback(text):
    """Fallback to macOS built-in say command"""
    try:
        # Clean text for say command
        text = re.sub(r'[^\w\s.,!?;:-]', '', text)
        text = text.replace('\n', '. ')
        
        # Use macOS say command with faster voice
        result = subprocess.run(['say', '-v', 'Alex', '-r', '200', text], 
                              capture_output=True, text=True, timeout=30)
        log_debug(f"Say command result: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        log_debug(f"Say fallback error: {e}")
        return False

def main():
    try:
        log_debug("Fallback TTS hook started")
        
        # Read input
        input_data = sys.stdin.read()
        log_debug(f"Raw input data: {input_data[:500]}...")
        
        # Extract text (same logic as original)
        text = ""
        
        try:
            data = json.loads(input_data)
            
            # Check if we have transcript_path
            if 'transcript_path' in data:
                transcript_path = data['transcript_path']
                log_debug(f"Reading transcript from: {transcript_path}")
                
                try:
                    import time
                    time.sleep(0.1)
                    
                    with open(transcript_path, 'r') as f:
                        lines = f.readlines()
                        
                    log_debug(f"Found {len(lines)} lines in transcript")
                    
                    # Get the last assistant message
                    for line in reversed(lines):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            msg = json.loads(line)
                            msg_type = msg.get('type')
                            
                            if msg_type == 'assistant':
                                message_obj = msg.get('message', {})
                                content = message_obj.get('content', [])
                                
                                if isinstance(content, list):
                                    text_parts = []
                                    for item in content:
                                        if isinstance(item, dict) and item.get('type') == 'text':
                                            text_part = item.get('text', '')
                                            text_parts.append(text_part)
                                    
                                    if text_parts:
                                        text = ' '.join(text_parts)
                                        log_debug(f"Extracted text: {text[:50]}...")
                                elif isinstance(content, str):
                                    text = content
                                    
                                if text:
                                    break
                                    
                        except json.JSONDecodeError:
                            continue
                            
                except Exception as e:
                    log_debug(f"Error reading transcript: {e}")
                    
            # Fallback parsing
            elif 'prompt' in data:
                text = str(data['prompt'])
            elif 'message' in data:
                text = str(data['message'])
            elif 'content' in data:
                if isinstance(data['content'], list):
                    for item in data['content']:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text += item.get('text', '')
                else:
                    text = str(data['content'])
            elif 'text' in data:
                text = str(data['text'])
                
        except json.JSONDecodeError:
            text = input_data
            log_debug("Using raw input as text")
        
        log_debug(f"Extracted text (first 200 chars): {text[:200]}")
        
        # Clean text
        text = re.sub(r'<[^>]+>', '', text)  # Remove XML tags
        text = re.sub(r'```[\s\S]*?```', '', text)  # Remove code blocks
        text = re.sub(r'[*_`]', '', text)  # Remove markdown
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Skip if text is too short or empty
        if not text or len(text) < 3:
            log_debug(f"Text too short or empty: '{text}'")
            return
        
        # First try OpenAI (quickly)
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            try:
                log_debug("Attempting OpenAI TTS...")
                url = "https://api.openai.com/v1/audio/speech"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                tts_data = {
                    "model": "tts-1",
                    "input": text[:2500],
                    "voice": "onyx",
                    "speed": 1.20,
                    "response_format": "mp3"
                }
                
                response = requests.post(url, headers=headers, json=tts_data, timeout=10)
                log_debug(f"OpenAI API response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Kill existing audio
                    try:
                        subprocess.run(['pkill', '-f', 'afplay.*\\.mp3'], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
                    except:
                        pass
                    
                    # Save and play audio
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                        f.write(response.content)
                        audio_file = f.name
                    
                    log_debug(f"Playing OpenAI audio: {audio_file}")
                    try:
                        subprocess.run(['afplay', audio_file], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL,
                                     timeout=60)
                    finally:
                        try:
                            os.unlink(audio_file)
                        except:
                            pass
                    return
                    
                elif response.status_code == 429:
                    log_debug("OpenAI quota exceeded, falling back to say command")
                else:
                    log_debug(f"OpenAI API error: {response.text}")
                    
            except Exception as e:
                log_debug(f"OpenAI TTS failed: {e}")
        
        # Fallback to macOS say command
        log_debug("Using macOS say command fallback")
        if say_fallback(text):
            log_debug("Say command successful")
        else:
            log_debug("Say command failed")
            
    except Exception as e:
        log_debug(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    main()