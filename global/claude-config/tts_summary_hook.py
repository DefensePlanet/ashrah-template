#!/usr/bin/env python3
"""
Claude Code TTS Hook - Reads out Claude's responses using OpenAI TTS
Triggered on the 'Stop' event after Claude finishes responding
"""

import json
import sys
import os
import re
import tempfile
import subprocess
import requests
from pathlib import Path

def clean_text_for_tts(text):
    """Clean text for better TTS output"""
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Inline code
    text = re.sub(r'```[\s\S]*?```', '', text)    # Code blocks
    
    # Remove tool call references and XML-like tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def text_to_speech(text, api_key):
    """Convert text to speech using OpenAI API"""
    if not text or len(text) < 10:
        return
        
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "tts-1",
        "input": text,
        "voice": "onyx",
        "speed": 1.20  # 20% faster speech
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            f.write(response.content)
            audio_file = f.name
        
        # Play audio using system command
        subprocess.run(['afplay', audio_file], check=True)
        
        # Clean up
        os.unlink(audio_file)
        
    except Exception as e:
        print(f"TTS Error: {e}", file=sys.stderr)

def get_api_key_from_settings():
    """Get OpenAI API key from Claude Code settings"""
    # Try multiple settings file locations
    settings_files = [
        Path.home() / '.claude' / 'settings.local.json',
        Path.home() / '.claude' / '.claude' / 'settings.json',
        Path.home() / '.claude' / 'settings.json'
    ]
    
    for settings_path in settings_files:
        try:
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    api_key = settings.get('env', {}).get('OPENAI_API_KEY')
                    if api_key:
                        return api_key
        except Exception:
            continue
    return None

def main():
    # IMMEDIATE logging before anything else
    with open('/tmp/tts_hook_start.log', 'a') as f:
        f.write(f"TTS HOOK STARTED at {os.popen('date').read().strip()}\n")
    
    try:
        # Debug: log that hook was triggered
        with open('/tmp/claude_hook_debug.log', 'a') as f:
            f.write(f"Hook triggered at {os.popen('date').read().strip()}\n")
        
        # Get API key from environment or Claude settings
        api_key = os.environ.get('OPENAI_API_KEY') or get_api_key_from_settings()
        if not api_key:
            with open('/tmp/claude_hook_debug.log', 'a') as f:
                f.write("No OpenAI API key found in environment or settings\n")
            return
        
        # Read input from stdin
        input_data = sys.stdin.read()
        
        with open('/tmp/claude_hook_debug.log', 'a') as f:
            f.write(f"Input data: {input_data[:200]}...\n")
        
        # Parse Claude Code hook JSON format
        try:
            data = json.loads(input_data)
            
            # Try to read transcript file if provided
            transcript_path = data.get('transcript_path')
            if transcript_path and os.path.exists(transcript_path):
                # Parse JSONL format (each line is a separate JSON object)
                with open(transcript_path, 'r') as f:
                    lines = f.readlines()
                    
                # Find the last assistant message
                text = ''
                for line in reversed(lines):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        # Look for assistant messages with text content
                        if (entry.get('type') == 'assistant' and 
                            'message' in entry and 
                            entry['message'].get('role') == 'assistant'):
                            
                            content = entry['message'].get('content', [])
                            if isinstance(content, list):
                                # Extract text from content array
                                for item in content:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        text = item.get('text', '')
                                        break
                            elif isinstance(content, str):
                                text = content
                            
                            if text:
                                break
                    except json.JSONDecodeError:
                        continue
            else:
                # Fallback to any text in the hook data
                text = str(data)
                
        except json.JSONDecodeError:
            # Fallback to raw text
            text = input_data
        
        # Clean and process text
        clean_text = clean_text_for_tts(text)
        
        if clean_text:
            text_to_speech(clean_text, api_key)
            
    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()