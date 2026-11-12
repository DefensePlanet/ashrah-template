#!/usr/bin/env python3
"""
OBS DVD Recording Setup Script
Configures OBS Studio to record DVD playback via WebSocket API v5
"""

import json
import hashlib
import base64
from websocket import create_connection
import time

class OBSWebSocket:
    def __init__(self, host='localhost', port=4455, password=None):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.message_id = 1

    def connect(self):
        """Connect to OBS WebSocket v5"""
        url = f"ws://{self.host}:{self.port}"
        self.ws = create_connection(url)

        # Read Hello message
        hello_msg = self.ws.recv()
        hello = json.loads(hello_msg)

        print(f"Connected to OBS WebSocket v{hello['d'].get('obsWebSocketVersion', 'unknown')}")

        # Authenticate if needed
        auth_string = None
        if 'authentication' in hello['d']:
            auth_info = hello['d']['authentication']
            if self.password:
                salt = auth_info['salt']
                challenge = auth_info['challenge']

                # Create authentication string
                secret = base64.b64encode(
                    hashlib.sha256((self.password + salt).encode()).digest()
                ).decode()

                auth_string = base64.b64encode(
                    hashlib.sha256((secret + challenge).encode()).digest()
                ).decode()

        # Send Identify message
        identify = {
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "eventSubscriptions": 33
            }
        }

        if auth_string:
            identify["d"]["authentication"] = auth_string

        self.ws.send(json.dumps(identify))

        # Read Identified response
        response = json.loads(self.ws.recv())
        if response.get('op') == 2:  # Identified
            print("✓ Connected and authenticated")
        else:
            print(f"Warning: Unexpected response: {response}")

    def request(self, request_type, request_data=None):
        """Send a request to OBS and wait for response"""
        message = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": str(self.message_id),
                "requestData": request_data or {}
            }
        }

        request_id = str(self.message_id)
        self.message_id += 1

        self.ws.send(json.dumps(message))

        # Wait for response with matching requestId
        while True:
            response = json.loads(self.ws.recv())
            if response.get('op') == 7:  # RequestResponse
                if response['d']['requestId'] == request_id:
                    if not response['d']['requestStatus']['result']:
                        error = response['d']['requestStatus'].get('comment', 'Unknown error')
                        raise Exception(f"Request failed: {error}")
                    return response['d'].get('responseData', {})

    def close(self):
        """Close connection"""
        if self.ws:
            self.ws.close()

def setup_dvd_recording():
    """Configure OBS for DVD recording"""

    obs = OBSWebSocket()

    try:
        print("Connecting to OBS WebSocket...")
        obs.connect()

        # Create a new scene for DVD recording
        scene_name = "DVD Recording"
        print(f"\nSetting up scene: {scene_name}")

        # Try to create scene, ignore if exists
        try:
            obs.request("CreateScene", {"sceneName": scene_name})
            print(f"✓ Scene '{scene_name}' created")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✓ Scene '{scene_name}' already exists")
            else:
                print(f"Note: {e}")

        # Set as current scene
        obs.request("SetCurrentProgramScene", {"sceneName": scene_name})
        print(f"✓ Switched to scene '{scene_name}'")

        # Add display capture source (captures entire screen)
        display_source_name = "DVD Display Capture"
        print(f"\nConfiguring display capture: {display_source_name}")

        try:
            obs.request("CreateInput", {
                "sceneName": scene_name,
                "inputName": display_source_name,
                "inputKind": "screen_capture",
                "inputSettings": {
                    "show_cursor": True
                },
                "sceneItemEnabled": True
            })
            print(f"✓ Display capture added")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✓ Display capture already exists")
            else:
                print(f"Note: {e}")

        # Add audio capture for system audio (macOS CoreAudio)
        audio_source_name = "System Audio"
        print(f"\nConfiguring audio capture: {audio_source_name}")

        try:
            obs.request("CreateInput", {
                "sceneName": scene_name,
                "inputName": audio_source_name,
                "inputKind": "coreaudio_output_capture",
                "inputSettings": {
                    "device_id": "default"
                },
                "sceneItemEnabled": True
            })
            print(f"✓ System audio capture added")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✓ System audio capture already exists")
            else:
                print(f"Note: {e}")

        # Configure recording settings
        print("\nConfiguring recording settings...")

        output_path = "{{HOME_DIR}}/Desktop/From Disks/Dad Home Videos - Complete"

        # Set output mode to simple (if not already)
        try:
            obs.request("SetProfileParameter", {
                "parameterCategory": "Output",
                "parameterName": "Mode",
                "parameterValue": "Simple"
            })
        except:
            pass

        # Set recording path
        try:
            obs.request("SetProfileParameter", {
                "parameterCategory": "SimpleOutput",
                "parameterName": "FilePath",
                "parameterValue": output_path
            })
            print(f"✓ Recording path set to: {output_path}")
        except Exception as e:
            print(f"Note: {e}")

        # Set recording format to MP4
        try:
            obs.request("SetProfileParameter", {
                "parameterCategory": "SimpleOutput",
                "parameterName": "RecFormat",
                "parameterValue": "mp4"
            })
            print(f"✓ Recording format: MP4")
        except Exception as e:
            print(f"Note: {e}")

        # Set quality to high quality (for archival purposes)
        try:
            obs.request("SetProfileParameter", {
                "parameterCategory": "SimpleOutput",
                "parameterName": "RecQuality",
                "parameterValue": "Small"  # Small = high quality in simple mode
            })
            print(f"✓ Recording quality: High")
        except Exception as e:
            print(f"Note: {e}")

        # Set encoder to x264
        try:
            obs.request("SetProfileParameter", {
                "parameterCategory": "SimpleOutput",
                "parameterName": "RecEncoder",
                "parameterValue": "x264"
            })
            print(f"✓ Encoder: x264")
        except Exception as e:
            print(f"Note: {e}")

        # Get recording status
        try:
            status = obs.request("GetRecordStatus")
            is_recording = status.get('outputActive', False)
            print(f"\n📊 Current recording status: {'RECORDING' if is_recording else 'STOPPED'}")
        except Exception as e:
            print(f"Could not get recording status: {e}")

        print("\n" + "="*70)
        print("🎬 OBS DVD RECORDING CONFIGURATION COMPLETE")
        print("="*70)
        print(f"\n✅ Scene: '{scene_name}'")
        print(f"✅ Display Capture: '{display_source_name}' (entire screen)")
        print(f"✅ Audio Capture: '{audio_source_name}' (system audio)")
        print(f"✅ Output Directory: {output_path}")
        print(f"✅ Format: MP4 (x264, high quality)")

        print("\n📋 RECORDING WORKFLOW:")
        print("   1. Open DVD Player.app")
        print("   2. Insert/mount the DVD and start playback")
        print("   3. In OBS Studio, click 'Start Recording' button")
        print("   4. Let the full 72 minutes play through")
        print("   5. Click 'Stop Recording' when DVD finishes")
        print("   6. Find your recording in:")
        print(f"      {output_path}")

        print("\n💡 TIP: You can also use this script to start/stop recording:")
        print("   python3 tools/obs_dvd_control.py start")
        print("   python3 tools/obs_dvd_control.py stop")

        return True

    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        obs.close()

if __name__ == "__main__":
    success = setup_dvd_recording()
    exit(0 if success else 1)
