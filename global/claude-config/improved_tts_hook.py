#!/usr/bin/env python3
"""
Improved Claude Code TTS Hook - Handles full-length responses without truncation
Features:
- Smart sentence-aware text chunking
- OpenAI TTS character limit handling (4096 chars max)
- Improved text cleaning that preserves sentence structure
- Better transcript parsing with file sync wait
- Fallback error handling
"""

import json
import sys
import os
import re
import tempfile
import subprocess
import requests
import time
from pathlib import Path
from datetime import datetime

def log_debug(message):
    """Enhanced debug logging"""
    try:
        with open('/tmp/tts_debug.log', 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def smart_text_cleaning(text):
    """Clean text while preserving sentence structure and readability"""
    # Remove tool call XML blocks completely
    text = re.sub(r'<function_calls>.*?
