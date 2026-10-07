#!/usr/bin/env python3
"""
Conceptual Summary TTS Hook - Creates concise summaries for voice output
Features:
- Extracts key concepts and actions from Claude's response
- Generates brief, informative summaries (30-60 seconds of speech)
- Preserves important details while removing verbosity
- Handles code, file operations, and technical content intelligently
"""

import json
import sys
import os
import re
import tempfile
import subprocess
import requests
from datetime import datetime

def log_debug(message):
    try:
        with open('/tmp/tts_summary_debug.log', 'a') as f:
            f.write(f"{datetime.now()}: {message}\n")
    except:
        pass

def create_conceptual_summary(text, api_key):
    """Create a concise conceptual summary using OpenAI API - always completes thoughts"""
    log_debug(f"Summarizing text of length: {len(text)}")

    # Clean up the text first
    text = re.sub(r'<[^>]+>', '', text)  # Remove XML tags
    text = re.sub(r'```[\s\S]*?```', '[Code block]', text)  # Replace code blocks
    text = re.sub(r'`([^`]+)`', r'\1', text)  # Inline code
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)  # Italic
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    try:
        # Use OpenAI to create intelligent summary that ALWAYS completes thoughts
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": """You create concise spoken summaries of technical messages.

CRITICAL RULES:
- ALWAYS finish complete thoughts - NEVER cut off mid-sentence
- Aim for 2-4 complete sentences that capture key information
- Preserve critical details: file names, actions, outcomes
- Use natural spoken language
- If original is already concise (under 50 words), return it unchanged
- NO character limits - complete the summary naturally"""
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this for voice output:\n\n{text}"
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 500  # Increased to ensure complete thoughts are never cut off
            },
            timeout=15
        )

        if response.status_code == 200:
            summary = response.json()['choices'][0]['message']['content'].strip()
            log_debug(f"OpenAI summary: {len(summary)} chars")
            return summary
        else:
            log_debug(f"OpenAI API error: {response.status_code}")
            # Fallback to original text if API fails
            return text

    except Exception as e:
        log_debug(f"Summarization error: {str(e)}")
        # Fallback to original text on any error
        return text

def text_to_speech(text, api_key):
    """Convert text to speech using OpenAI API"""
    if not text or len(text) < 10:
        log_debug("Text too short for TTS")
        return

    log_debug(f"TTS receiving text: {len(text)} chars: '{text}'")
    log_debug(f"API key available: {bool(api_key)}, starts with: {api_key[:15] if api_key else 'None'}...")
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "tts-1-hd",  # High-definition model to prevent clipping
        "input": text,
        "voice": "onyx",
        "speed": 1.15,  # Slightly faster for summaries
        "response_format": "mp3"
    }

    try:
        # Kill any existing audio (both afplay and say)
        subprocess.run(['pkill', '-f', 'afplay'],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', 'say'],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL)

        log_debug(f"Making OpenAI API request to: {url}")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        log_debug(f"API response status: {response.status_code}")
        response.raise_for_status()

        # Save and play audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            f.write(response.content)
            audio_file = f.name

        log_debug(f"Playing summary audio: {audio_file}, size: {len(response.content)} bytes")
        # Use afplay with optimized settings to prevent clipping/static:
        # -v 0.85 = reduced volume to prevent clipping
        # -r 1.0 = standard playback rate (quality mode)
        # Run in background (non-blocking) so Claude Code remains responsive
        # Audio file cleanup handled by afplay completion (spawned background process)
        subprocess.Popen(
            ['sh', '-c', f'afplay -v 0.85 -r 1.0 "{audio_file}" && rm -f "{audio_file}"'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        log_debug("TTS playback started in background with OpenAI Onyx voice")

    except Exception as e:
        log_debug(f"TTS Error: {type(e).__name__}: {str(e)}")
        import traceback
        log_debug(f"Traceback: {traceback.format_exc()}")

def get_api_key():
    """Get OpenAI API key from environment or Claude settings"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        return api_key
    
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
    """Extract Claude's response text from hook input"""
    import time
    
    try:
        data = json.loads(input_data)
        
        # Check for transcript path
        transcript_path = data.get('transcript_path')
        if transcript_path and os.path.exists(transcript_path):
            log_debug(f"Reading transcript: {transcript_path}")
            
            # Wait for file to be fully written
            time.sleep(0.3)
            
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
                            if text_parts:  # Only return if we found text
                                return ' '.join(text_parts)
                        elif isinstance(content, str):
                            return content
                except json.JSONDecodeError:
                    continue
        
        # Fallback parsing
        for key in ['prompt', 'message', 'text']:
            if key in data:
                return str(data[key])
        
        if 'content' in data:
            content = data['content']
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                return ' '.join(text_parts)
            else:
                return str(content)
                
    except json.JSONDecodeError:
        return input_data
    
    return ""

def main():
    import random
    session_id = random.randint(10000, 99999)
    log_debug(f"========== SESSION {session_id} START ==========")
    log_debug("Summary TTS hook started")

    try:
        # Get API key
        api_key = get_api_key()
        if not api_key:
            log_debug("No OpenAI API key found")
            return
        
        # Read input
        input_data = sys.stdin.read()
        log_debug(f"Input length: {len(input_data)}")
        
        # Extract response text
        full_text = extract_response_text(input_data)
        log_debug(f"Extracted full text: {len(full_text) if full_text else 0} chars: '{full_text[:100] if full_text else 'None'}...'")
        if not full_text or len(full_text) < 20:
            log_debug("No substantial text found")
            return
        
        # Create summary with API key
        summary = create_conceptual_summary(full_text, api_key)
        log_debug(f"Summary created: {len(summary)} chars")

        # Convert to speech
        if summary:
            text_to_speech(summary, api_key)

        log_debug(f"========== SESSION {session_id} END ==========")
    except Exception as e:
        log_debug(f"Hook error: {str(e)}")
        log_debug(f"========== SESSION {session_id} ERROR END ==========")

if __name__ == "__main__":
    main()
