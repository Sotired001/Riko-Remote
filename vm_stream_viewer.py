"""
Simple remote stream viewer that polls the remote agent /screenshot endpoint and displays frames.
Usage:
    set VM_AGENT_URL=http://remote-ip:8000
    set REMOTE_API_TOKEN=your-token  # optional
    set VM_POLLING_RATE=10  # FPS, default 10
    set USE_STREAMING=1  # Use MJPEG streaming instead of polling
    python scripts/vm_stream_viewer.py

This is a polling-based viewer (MJPEG/RTSP would be lower-latency but requires more setup).
"""
import os
import sys
import time
import cv2
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from external_reused.remote_agent_client import RemoteAgentClient

VM_AGENT_URL = os.getenv('VM_AGENT_URL', 'http://127.0.0.1:8000')
REMOTE_API_TOKEN = os.getenv('REMOTE_API_TOKEN')
VM_POLLING_RATE = int(os.getenv('VM_POLLING_RATE', '10'))  # FPS
USE_STREAMING = os.getenv('USE_STREAMING', '0').lower() in ('1', 'true', 'yes')
poll_delay = 1.0 / VM_POLLING_RATE

if USE_STREAMING:
    # Use MJPEG streaming
    stream_url = f"{VM_AGENT_URL}/stream"
    if REMOTE_API_TOKEN:
        # Note: cv2.VideoCapture doesn't support auth headers easily; assume no auth for streaming or use polling
        print("Warning: Streaming does not support token auth; using polling instead.")
        USE_STREAMING = False

if USE_STREAMING:
    print(f'Connecting to MJPEG stream at {stream_url}')
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print("Failed to open stream")
        exit(1)
    try:
        while True:
            ret, frame = cap.read()
            if ret:
                cv2.imshow('Remote Stream', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                time.sleep(0.1)
    finally:
        cap.release()
        cv2.destroyAllWindows()
else:
    # Polling mode
    client = RemoteAgentClient(VM_AGENT_URL, api_token=REMOTE_API_TOKEN)

    print(f'Connecting to remote agent at {VM_AGENT_URL} (polling at {VM_POLLING_RATE} FPS)')

    try:
        while True:
            img = client.get_screenshot()
            if isinstance(img, dict) and 'error' in img:
                print('Error fetching screenshot:', img)
                time.sleep(1)
                continue
            # Convert PIL Image to OpenCV BGR
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            cv2.imshow('Remote Stream', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            time.sleep(poll_delay)
    finally:
        cv2.destroyAllWindows()
