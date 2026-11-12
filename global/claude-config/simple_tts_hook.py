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

def main():
    try:
        log_debug("TTS hook started")
        
        # Get API key from environment or Claude settings
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            try:
                settings_path = os.path.expanduser('~/.claude/settings.json')
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    api_key = settings.get('env', {}).get('OPENAI_API_KEY')
            except:
                pass
        
        if not api_key:
            log_debug("No API key found")
            return
        
        # Read input
        input_data = sys.stdin.read()
        log_debug(f"Raw input data: {input_data[:500]}...")  # Log first 500 chars
        
        # Try to extract text from various possible formats
        text = ""
        
        try:
            data = json.loads(input_data)
            log_debug(f"Parsed JSON keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
            
            # Check if we have transcript_path - this means we need to read the conversation
            if 'transcript_path' in data:
                transcript_path = data['transcript_path']
                log_debug(f"Reading transcript from: {transcript_path}")
                
                try:
                    # Wait a moment for the file to be written
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
                            log_debug(f"Checking message with type: {msg_type}")
                            
                            if msg_type == 'assistant':
                                # Extract content from assistant message
                                message_obj = msg.get('message', {})
                                content = message_obj.get('content', [])
                                log_debug(f"Found assistant content type: {type(content)}, length: {len(content) if isinstance(content, list) else 'N/A'}")
                                
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
                                    
                        except json.JSONDecodeError as e:
                            log_debug(f"JSON decode error: {e}")
                            continue
                            
                except Exception as e:
                    log_debug(f"Error reading transcript: {e}")
                    
            # Fallback to original parsing if no transcript
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
            # If not JSON, just use the raw text
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
        
        log_debug(f"Calling OpenAI TTS with text: {text[:100]}...")
        
        # Call OpenAI TTS
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        tts_data = {
            "model": "tts-1-hd",
            "input": text[:2500],  # Reduced to 2500 chars for shorter audio
            "voice": "onyx",
            "speed": 1.20,  # Keep preferred speed
            "response_format": "mp3"
        }
        
        response = requests.post(url, headers=headers, json=tts_data, timeout=30)
        log_debug(f"OpenAI API response status: {response.status_code}")
        
        if response.status_code == 200:
            # Kill any existing afplay processes to avoid conflicts
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
            
            log_debug(f"Playing audio file: {audio_file}")
            # Play audio and wait for completion, then cleanup
            try:
                subprocess.run(['afplay', audio_file], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             timeout=60)  # Increased timeout to 60 seconds
            except subprocess.TimeoutExpired:
                log_debug("Audio playback timed out")
            except Exception as e:
                log_debug(f"Audio playback error: {e}")
            finally:
                # Clean up temp file
                try:
                    os.unlink(audio_file)
                    log_debug(f"Cleaned up temp file: {audio_file}")
                except:
                    pass
        else:
            log_debug(f"OpenAI API error: {response.text}")
            
    except Exception as e:
        log_debug(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    main()