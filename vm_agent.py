"""
vm_agent.py

Simple in-guest agent to run inside the Windows VM. Exposes a minimal HTTP API to
allow the host Riko process to request screenshots and run dry-run actions.

Endpoints:
- GET /status -> JSON {status: 'ok', hostname, time}
- GET /screenshot -> returns base64 JPEG in JSON {image: '<base64>'}
- POST /exec -> accept a JSON action (type, params) and log it; returns success (dry-run)

Security: this is intentionally minimal. Run only inside an isolated VM. If you
expose it beyond localhost you MUST add authentication (not included).

Run inside the VM with: python vm_agent.py --port 8000
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
import io
import argparse
import time
import socket
import os
from PIL import ImageGrab, Image, ImageChops
import threading
import subprocess
import sys

class VMAgentHandler(BaseHTTPRequestHandler):
    dry_run = True  # Default to dry-run; set by run_server
    last_screenshot = None  # Cache last screenshot for delta detection

    def _send_json(self, data, status=200):
        payload = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        # Unknown path
        self._send_json({'error': 'not found'}, status=404)

    def do_GET(self):
        if self.path == '/status':
            info = {
                'status': 'ok',
                'hostname': socket.gethostname(),
                'time': time.time()
            }
            self._send_json(info)
            return

        if self.path == '/screenshot':
            try:
                img = ImageGrab.grab()
                if self.last_screenshot is not None:
                    # Quick change detection: compare hashes
                    current_hash = hash(img.tobytes())
                    last_hash = hash(self.last_screenshot.tobytes())
                    if current_hash == last_hash:
                        self._send_json({'no_change': True})
                        return
                # Send full image
                buffered = io.BytesIO()
                img.save(buffered, format='JPEG')
                b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                self._send_json({'image': b64})
                # Update cache
                self.last_screenshot = img.copy()
            except Exception as e:
                self._send_json({'error': str(e)}, status=500)
            return

        if self.path == '/stream':
            # MJPEG streaming
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    img = ImageGrab.grab()
                    buffered = io.BytesIO()
                    img.save(buffered, format='JPEG')
                    frame_data = buffered.getvalue()
                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(frame_data)}\r\n\r\n'.encode())
                    self.wfile.write(frame_data)
                    self.wfile.write(b'\r\n')
                    time.sleep(0.1)  # ~10 FPS
            except Exception:
                pass  # Client disconnect
            return

    def do_POST(self):
        if self.path == '/exec':
            # Check token if configured
            expected_token = os.getenv('REMOTE_API_TOKEN')
            auth_header = self.headers.get('Authorization', '')
            if expected_token and not auth_header.startswith(f'Bearer {expected_token}'):
                self._send_json({'error': 'unauthorized'}, status=401)
                return

            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode('utf-8'))
            except Exception:
                self._send_json({'error': 'invalid json'}, status=400)
                return

            # Audit log: append-only JSONL with timestamp, origin IP, token-id, full payload
            client_ip = self.client_address[0]
            token_id = auth_header.split(' ')[-1] if auth_header else 'none'
            audit_entry = {
                'timestamp': time.time(),
                'client_ip': client_ip,
                'token_id': token_id,
                'payload': payload
            }
            with open('vm_agent_audit.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry) + '\n')

            if self.dry_run:
                self._send_json({'status': 'ok', 'message': 'action logged (dry-run)'} )
            else:
                # Execute action (dangerous: only use in isolated environments)
                try:
                    import pyautogui
                    if payload.get('action') == 'click':
                        x, y = payload.get('coordinates', [0, 0])
                        pyautogui.click(x, y)
                    elif payload.get('action') == 'type':
                        x, y = payload.get('coordinates', [0, 0])
                        text = payload.get('text', '')
                        pyautogui.click(x, y)
                        pyautogui.typewrite(text)
                    elif payload.get('action') == 'scroll':
                        dx = payload.get('dx', 0)
                        dy = payload.get('dy', 0)
                        pyautogui.scroll(dy)  # pyautogui scroll is vertical
                    self._send_json({'status': 'ok', 'message': 'action executed (live-run)'})
                except Exception as e:
                    self._send_json({'error': f'execution failed: {str(e)}'}, status=500)
            return

        self._send_json({'error': 'not found'}, status=404)


def check_for_updates():
    if not os.path.exists('.git'):
        return  # Not in a git repo, skip
    try:
        # Fetch latest changes
        subprocess.run(['git', 'fetch'], check=True, capture_output=True)
        # Check status
        result = subprocess.run(['git', 'status', '-uno'], capture_output=True, text=True)
        if 'behind' in result.stdout:
            print("Updates available, pulling latest changes...")
            subprocess.run(['git', 'pull'], check=True, capture_output=True)
            print("Code updated successfully, restarting agent...")
            # Restart the process to load new code
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
    except FileNotFoundError:
        print("Git not installed, skipping auto-update")


def check_updates_loop():
    while True:
        check_for_updates()
        time.sleep(300)  # Check every 5 minutes


def run_server(port: int = 8000, host: str = '0.0.0.0', dry_run: bool = True):
    VMAgentHandler.dry_run = dry_run
    server = HTTPServer((host, port), VMAgentHandler)
    mode = 'dry-run (log only)' if dry_run else 'live-run (executes actions - USE WITH CAUTION)'
    
    # Get local IP
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except:
        local_ip = "unknown"
    finally:
        s.close()
    
    print(f"VM agent running on http://{host}:{port} (local IP: {local_ip}) in {mode} mode")
    # Start auto-update thread if in git repo
    if os.path.exists('.git'):
        update_thread = threading.Thread(target=check_updates_loop, daemon=True)
        update_thread.start()
        print("Auto-update enabled (checks every 5 minutes)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down')
        server.server_close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--dry-run', action='store_true', default=True, help='Log actions only (default); use --no-dry-run to execute actions (dangerous)')
    parser.add_argument('--no-dry-run', action='store_false', dest='dry_run')
    args = parser.parse_args()
    run_server(args.port, dry_run=args.dry_run)

if __name__ == '__main__':
    main()
