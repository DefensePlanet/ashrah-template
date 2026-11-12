#!/usr/bin/env python3
"""
OBS DVD Recording Control Script
Start/stop recording via command line
"""

import json
import hashlib
import base64
from websocket import create_connection
import sys

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

def main():
    if len(sys.argv) < 2:
        print("Usage: obs_dvd_control.py [start|stop|status]")
        print("\nCommands:")
        print("  start  - Start recording")
        print("  stop   - Stop recording")
        print("  status - Check recording status")
        sys.exit(1)

    command = sys.argv[1].lower()

    obs = OBSWebSocket()

    try:
        obs.connect()

        if command == "start":
            # Check if already recording
            status = obs.request("GetRecordStatus")
            if status.get('outputActive', False):
                print("⚠️  Recording is already in progress!")
                print(f"Duration: {status.get('outputDuration', 0) / 1000:.1f} seconds")
                sys.exit(0)

            # Start recording
            obs.request("StartRecord")
            print("🔴 Recording STARTED")
            print(f"📁 Saving to: {{HOME_DIR}}/Desktop/From Disks/Dad Home Videos - Complete")
            print("\n✅ OBS is now recording the screen and system audio")
            print("   Start playing your DVD now!")
            print("   Run 'python3 tools/obs_dvd_control.py stop' when finished")

        elif command == "stop":
            # Check if recording
            status = obs.request("GetRecordStatus")
            if not status.get('outputActive', False):
                print("⚠️  No recording in progress")
                sys.exit(0)

            # Stop recording
            result = obs.request("StopRecord")
            output_path = result.get('outputPath', 'Unknown')
            print("⏹️  Recording STOPPED")
            print(f"📁 Saved to: {output_path}")
            print("\n✅ Your DVD recording is complete!")

        elif command == "status":
            status = obs.request("GetRecordStatus")
            is_recording = status.get('outputActive', False)

            print(f"📊 Recording Status: {'🔴 RECORDING' if is_recording else '⚪ STOPPED'}")

            if is_recording:
                duration_ms = status.get('outputDuration', 0)
                duration_sec = duration_ms / 1000
                minutes = int(duration_sec // 60)
                seconds = int(duration_sec % 60)
                print(f"⏱️  Duration: {minutes}m {seconds}s")
                print(f"📁 Output: {{HOME_DIR}}/Desktop/From Disks/Dad Home Videos - Complete")

        else:
            print(f"❌ Unknown command: {command}")
            print("Valid commands: start, stop, status")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    finally:
        obs.close()

if __name__ == "__main__":
    main()
