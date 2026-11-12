#!/usr/bin/env python3

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
    try:
        with open('/tmp/tts_debug_fixed.log', 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def smart_text_cleaning(text):
    log_debug(f"Original text length: {len(text)}")
    
    # Remove function call blocks
    text = re.sub(r'<function_calls>.*?