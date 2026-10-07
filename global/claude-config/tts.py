#!/usr/bin/env python3
"""
Simple TTS command for Claude Code
Usage: tts "text to speak"
"""

import sys
import os
import requests
import tempfile
import subprocess
import argparse

def speak(text, voice="onyx", speed=1.2):
    """Convert text to speech using OpenAI TTS API"""
    
    # Get API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return False
    
    # Call OpenAI TTS
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "tts-1",
        "input": text[:4096],  # API limit
        "voice": voice,
        "speed": speed
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            # Save and play audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(response.content)
                audio_file = f.name
            
            # Play audio
            subprocess.run(['afplay', audio_file])
            
            # Clean up
            os.unlink(audio_file)
            return True
        else:
            print(f"Error: API returned {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Text to Speech using OpenAI')
    parser.add_argument('text', nargs='?', help='Text to speak')
    parser.add_argument('-v', '--voice', default='onyx', 
                       choices=['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
                       help='Voice to use (default: onyx)')
    parser.add_argument('-s', '--speed', type=float, default=1.2,
                       help='Speech speed (0.25-4.0, default: 1.2)')
    
    args = parser.parse_args()
    
    # Get text from argument or stdin
    if args.text:
        text = args.text
    else:
        text = sys.stdin.read().strip()
    
    if not text:
        print("Error: No text provided")
        sys.exit(1)
    
    # Speak the text
    success = speak(text, voice=args.voice, speed=args.speed)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()