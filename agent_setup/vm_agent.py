"""
vm_agent.py

Canonical VM/agent script for Riko Agent. Exposes HTTP endpoints for screenshots,
streaming, actions, and update checks.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
import io
import argparse
import time
import socket
import os
from PIL import ImageGrab
import threading
import subprocess
import sys
import shutil
from collections import defaultdict
try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Disable failsafe for multi-monitor
except ImportError:
    pyautogui = None

class HostAgentHandler(BaseHTTPRequestHandler):
    dry_run = True
    last_screenshot = None
    rate_limit = defaultdict(list)
    screen_info = None

    def _send_json(self, data, status=200):
        payload = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _get_screen_info(self):
        """Get information about all available screens"""
        if pyautogui:
            try:
                # Get all monitors
                monitors = []
                
                # Try to get monitor info from pyautogui
                size = pyautogui.size()
                monitors.append({
                    'index': 0,
                    'primary': True,
                    'left': 0,
                    'top': 0,
                    'width': size.width,
                    'height': size.height,
                    'name': 'Primary Monitor'
                })
                
                # Try to get additional monitor info (Windows specific)
                try:
                    import win32api
                    import win32con
                    
                    monitor_list = []
                    def enum_callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                        monitor_list.append({
                            'handle': hMonitor,
                            'rect': lprcMonitor
                        })
                        return True
                    
                    win32api.EnumDisplayMonitors(None, None, enum_callback, 0)
                    
                    monitors = []
                    for i, monitor in enumerate(monitor_list):
                        rect = monitor['rect']
                        monitors.append({
                            'index': i,
                            'primary': i == 0,
                            'left': rect[0],
                            'top': rect[1],
                            'width': rect[2] - rect[0],
                            'height': rect[3] - rect[1],
                            'name': f'Monitor {i + 1}'
                        })
                        
                except ImportError:
                    # Fallback: assume single monitor
                    pass
                
                return monitors
                
            except Exception as e:
                print(f"Error getting screen info: {e}")
                return [{'index': 0, 'primary': True, 'left': 0, 'top': 0, 'width': 1920, 'height': 1080, 'name': 'Default'}]
        else:
            return [{'index': 0, 'primary': True, 'left': 0, 'top': 0, 'width': 1920, 'height': 1080, 'name': 'Default'}]

    def _capture_screen(self, screen_index=None):
        """Capture screenshot from specific screen or all screens"""
        try:
            if screen_index is not None:
                # Capture specific screen
                screens = self._get_screen_info()
                if screen_index < len(screens):
                    screen = screens[screen_index]
                    bbox = (screen['left'], screen['top'], 
                           screen['left'] + screen['width'], 
                           screen['top'] + screen['height'])
                    img = ImageGrab.grab(bbox)
                    return img, screen
                else:
                    return None, None
            else:
                # Capture all screens as one image
                img = ImageGrab.grab(all_screens=True)
                return img, {'index': 'all', 'name': 'All Screens'}
                
        except Exception as e:
            print(f"Screenshot error: {e}")
            # Fallback to primary screen
            img = ImageGrab.grab()
            return img, {'index': 0, 'name': 'Primary Screen'}

    def _check_rate_limit(self):
        client_ip = self.client_address[0]
        now = time.time()
        HostAgentHandler.rate_limit[client_ip] = [ts for ts in HostAgentHandler.rate_limit[client_ip] if now - ts < 60]
        if len(HostAgentHandler.rate_limit[client_ip]) >= 60:  # Increased from 10 to 60
            self._send_json({'error': 'rate limit exceeded'}, status=429)
            return False
        HostAgentHandler.rate_limit[client_ip].append(now)
        return True

    def do_GET(self):
        if not self._check_rate_limit():
            return
        if self.path == '/status':
            info = {
                'status': 'ok',
                'hostname': socket.gethostname(),
                'time': time.time(),
                'screens': self._get_screen_info()
            }
            self._send_json(info)
            return
        if self.path == '/screenshot':
            try:
                # Check for screen parameter
                screen_param = None
                if '?' in self.path:
                    query = self.path.split('?')[1]
                    params = dict(param.split('=') for param in query.split('&') if '=' in param)
                    screen_param = params.get('screen')
                
                screen_index = None
                if screen_param and screen_param.isdigit():
                    screen_index = int(screen_param)
                
                img, screen_info = self._capture_screen(screen_index)
                if img is None:
                    self._send_json({'error': 'Invalid screen index'}, status=400)
                    return
                
                # Check for changes (only for single screen)
                if screen_index is not None and self.last_screenshot is not None:
                    if hash(img.tobytes()) == hash(self.last_screenshot.tobytes()):
                        self._send_json({'no_change': True, 'screen': screen_info})
                        return
                
                buffered = io.BytesIO()
                img.save(buffered, format='JPEG')
                b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                self._send_json({
                    'image': b64,
                    'screen': screen_info,
                    'screens_available': len(self._get_screen_info())
                })
                
                if screen_index is not None:
                    self.last_screenshot = img.copy()
                    
            except Exception as e:
                self._send_json({'error': str(e)}, status=500)
            return
        if self.path.startswith('/screenshot/'):
            # Handle /screenshot/0, /screenshot/1, etc.
            try:
                screen_index = int(self.path.split('/')[-1])
                img, screen_info = self._capture_screen(screen_index)
                if img is None:
                    self._send_json({'error': 'Invalid screen index'}, status=404)
                    return
                
                buffered = io.BytesIO()
                img.save(buffered, format='JPEG')
                b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                self._send_json({
                    'image': b64,
                    'screen': screen_info,
                    'screens_available': len(self._get_screen_info())
                })
            except (ValueError, IndexError):
                self._send_json({'error': 'Invalid screen index'}, status=400)
            return
        if self.path == '/screens':
            # Return available screens info
            self._send_json({
                'screens': self._get_screen_info(),
                'count': len(self._get_screen_info())
            })
            return
        if self.path == '/stream':
            # MJPEG streaming with screen support
            screen_param = None
            if '?' in self.path:
                query = self.path.split('?')[1]
                params = dict(param.split('=') for param in query.split('&') if '=' in param)
                screen_param = params.get('screen')
            
            screen_index = None
            if screen_param and screen_param.isdigit():
                screen_index = int(screen_param)
            
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    img, _ = self._capture_screen(screen_index)
                    if img:
                        buffered = io.BytesIO()
                        img.save(buffered, format='JPEG')
                        frame_data = buffered.getvalue()
                        self.wfile.write(b'--frame\r\n')
                        self.wfile.write(b'Content-Type: image/jpeg\r\n')
                        self.wfile.write(f'Content-Length: {len(frame_data)}\r\n\r\n'.encode())
                        self.wfile.write(frame_data)
                        self.wfile.write(b'\r\n')
                    time.sleep(0.1)
            except Exception:
                pass
            return

    def do_POST(self):
        if not self._check_rate_limit():
            return
        if self.path == '/update':
            expected_token = os.getenv('AGENT_API_TOKEN')
            auth_header = self.headers.get('Authorization', '')
            if expected_token and not auth_header.startswith(f'Bearer {expected_token}'):
                self._send_json({'error': 'unauthorized'}, status=401)
                return
            try:
                check_for_updates()
                self._send_json({'status': 'update_check_completed'})
            except Exception as e:
                self._send_json({'error': f'update failed: {str(e)}'}, status=500)
            return
        if self.path == '/exec':
            expected_token = os.getenv('AGENT_API_TOKEN')
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
            client_ip = self.client_address[0]
            token_id = auth_header.split(' ')[-1] if auth_header else 'none'
            audit_entry = {'timestamp': time.time(), 'client_ip': client_ip, 'token_id': token_id, 'payload': payload}
            with open('agent_audit.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry) + '\n')
            if self.dry_run:
                self._send_json({'status': 'ok', 'message': 'action logged (dry-run)'})
            else:
                try:
                    if pyautogui is None:
                        raise ImportError("pyautogui not available")
                    
                    # Enhanced multi-monitor action handling
                    if payload.get('action') == 'click':
                        x, y = payload.get('coordinates', [0, 0])
                        screen = payload.get('screen', 0)  # Target screen
                        
                        # Adjust coordinates for target screen
                        screens = self._get_screen_info()
                        if screen < len(screens):
                            screen_info = screens[screen]
                            # Convert relative coordinates to absolute screen coordinates
                            if payload.get('relative', True):
                                abs_x = screen_info['left'] + x
                                abs_y = screen_info['top'] + y
                            else:
                                abs_x, abs_y = x, y
                            pyautogui.click(abs_x, abs_y)
                        else:
                            pyautogui.click(x, y)  # Fallback to direct coordinates
                            
                    elif payload.get('action') == 'type':
                        x, y = payload.get('coordinates', [0, 0])
                        text = payload.get('text', '')
                        screen = payload.get('screen', 0)
                        
                        # Click first to focus, then type
                        screens = self._get_screen_info()
                        if screen < len(screens):
                            screen_info = screens[screen]
                            if payload.get('relative', True):
                                abs_x = screen_info['left'] + x
                                abs_y = screen_info['top'] + y
                            else:
                                abs_x, abs_y = x, y
                            pyautogui.click(abs_x, abs_y)
                        else:
                            pyautogui.click(x, y)
                        pyautogui.typewrite(text)
                        
                    elif payload.get('action') == 'scroll':
                        x, y = payload.get('coordinates', [pyautogui.size().width//2, pyautogui.size().height//2])
                        dy = payload.get('dy', 0)
                        screen = payload.get('screen', 0)
                        
                        # Move to screen position first
                        screens = self._get_screen_info()
                        if screen < len(screens):
                            screen_info = screens[screen]
                            if payload.get('relative', True):
                                abs_x = screen_info['left'] + x
                                abs_y = screen_info['top'] + y
                            else:
                                abs_x, abs_y = x, y
                            pyautogui.moveTo(abs_x, abs_y)
                        pyautogui.scroll(dy)
                        
                    self._send_json({'status': 'ok', 'message': 'action executed (live-run)'})
                except Exception as e:
                    self._send_json({'error': f'execution failed: {str(e)}'}, status=500)
            return
        self._send_json({'error': 'not found'}, status=404)


def check_for_updates():
    repo_url = "https://github.com/Sotired001/riko-agent.git"
    if not os.path.exists('.git'):
        try:
            if os.path.exists('temp_repo'):
                try:
                    shutil.rmtree('temp_repo')
                except:
                    pass
            subprocess.run(['git', 'clone', repo_url, 'temp_repo'], check=True, capture_output=True)
            for file in ['vm_agent.py', 'install_agent.bat', 'README.txt']:
                if os.path.exists(f'temp_repo/agent_setup/{file}'):
                    shutil.copy2(f'temp_repo/agent_setup/{file}', file)
            try:
                shutil.rmtree('temp_repo')
            except Exception:
                pass
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone repo: {e}")
            return
    else:
        try:
            subprocess.run(['git', 'fetch'], check=True, capture_output=True)
            result = subprocess.run(['git', 'status', '-uno'], capture_output=True, text=True)
            if 'behind' in result.stdout:
                subprocess.run(['git', 'pull'], check=True, capture_output=True)
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
        except FileNotFoundError:
            print("Git not installed, skipping auto-update")


def run_server(port: int = 8000, host: str = '0.0.0.0', dry_run: bool = False):
    HostAgentHandler.dry_run = dry_run
    server = HTTPServer((host, port), HostAgentHandler)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except:
        local_ip = "unknown"
    finally:
        s.close()
    print(f"Agent running on http://{host}:{port} (local IP: {local_ip}) in {'dry-run' if dry_run else 'live-run'} mode")
    update_thread = threading.Thread(target=lambda: [check_for_updates() or time.sleep(300)], daemon=True)
    update_thread.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run_server(args.port, dry_run=args.dry_run)
"""
vm_agent.py

Agent script to run on a Windows machine. Exposes a minimal HTTP API to
allow clients to request screenshots and execute actions.

Endpoints:
- GET /status -> JSON {status: 'ok', hostname, time}
- GET /screenshot -> returns base64 JPEG in JSON {image: '<base64>'}
- POST /exec -> accept a JSON action (type, params) and execute it; returns success
- POST /update -> force immediate update check; returns status

Security: run only on trusted machines. Use AGENT_API_TOKEN for authentication if set.

Run on the machine with: python vm_agent.py --port 8000
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
import shutil

class AgentHandler(BaseHTTPRequestHandler):
    dry_run = True
    last_screenshot = None

    def _send_json(self, data, status=200):
        payload = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

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
                    current_hash = hash(img.tobytes())
                    last_hash = hash(self.last_screenshot.tobytes())
                    if current_hash == last_hash:
                        self._send_json({'no_change': True})
                        return
                buffered = io.BytesIO()
                img.save(buffered, format='JPEG')
                b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                self._send_json({'image': b64})
                self.last_screenshot = img.copy()
            except Exception as e:
                self._send_json({'error': str(e)}, status=500)
            return

        if self.path == '/stream':
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
                    time.sleep(0.1)
            except Exception:
                pass
            return

        self._send_json({'error': 'not found'}, status=404)

    def do_POST(self):
        if self.path == '/update':
            expected_token = os.getenv('AGENT_API_TOKEN')
            auth_header = self.headers.get('Authorization', '')
            if expected_token and not auth_header.startswith(f'Bearer {expected_token}'):
                self._send_json({'error': 'unauthorized'}, status=401)
                return
            try:
                check_for_updates()
                self._send_json({'status': 'update_check_completed', 'message': 'Check logs for update status'})
            except Exception as e:
                self._send_json({'error': f'update failed: {str(e)}'}, status=500)
            return

        if self.path == '/exec':
            expected_token = os.getenv('AGENT_API_TOKEN')
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
            client_ip = self.client_address[0]
            token_id = auth_header.split(' ')[-1] if auth_header else 'none'
            audit_entry = {
                'timestamp': time.time(),
                'client_ip': client_ip,
                'token_id': token_id,
                'payload': payload
            }
            with open('agent_audit.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry) + '\n')
            if self.dry_run:
                self._send_json({'status': 'ok', 'message': 'action logged (dry-run)'} )
            else:
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
                        dy = payload.get('dy', 0)
                        pyautogui.scroll(dy)
                    self._send_json({'status': 'ok', 'message': 'action executed (live-run)'})
                except Exception as e:
                    self._send_json({'error': f'execution failed: {str(e)}'}, status=500)
            return

        self._send_json({'error': 'not found'}, status=404)


def check_for_updates():
    repo_url = "https://github.com/Sotired001/riko-agent.git"
    if not os.path.exists('.git'):
        print("Not in git repo, cloning repository for auto-update...")
        try:
            if os.path.exists('temp_repo'):
                try:
                    shutil.rmtree('temp_repo')
                except:
                    pass
            subprocess.run(['git', 'clone', repo_url, 'temp_repo'], check=True, capture_output=True)
            for file in ['vm_agent.py', 'install_agent.bat', 'README.txt']:
                if os.path.exists(f'temp_repo/agent_setup/{file}'):
                    shutil.copy2(f'temp_repo/agent_setup/{file}', file)
            try:
                shutil.rmtree('temp_repo')
            except Exception as e:
                print(f"Warning: Could not clean up temp_repo: {e}")
            print("Repository cloned and updated successfully, restarting agent...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone repo: {e}")
            return
    else:
        try:
            subprocess.run(['git', 'fetch'], check=True, capture_output=True)
            result = subprocess.run(['git', 'status', '-uno'], capture_output=True, text=True)
            if 'behind' in result.stdout:
                print("Updates available, pulling latest changes...")
                subprocess.run(['git', 'pull'], check=True, capture_output=True)
                print("Code updated successfully, restarting agent...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
        except FileNotFoundError:
            print("Git not installed, skipping auto-update")


def check_updates_loop():
    print("Auto-update thread started, checking for updates...")
    while True:
        check_for_updates()
        time.sleep(300)


def run_server(port: int = 8000, host: str = '0.0.0.0', dry_run: bool = False):
    AgentHandler.dry_run = dry_run
    server = HTTPServer((host, port), AgentHandler)
    mode = 'dry-run (log only)' if dry_run else 'live-run (executes actions)'
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except:
        local_ip = "unknown"
    finally:
        s.close()
    print(f"Agent running on http://{host}:{port} (local IP: {local_ip}) in {mode} mode")
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
    parser.add_argument('--dry-run', action='store_true', default=False, help='Log actions only (safe mode); use --dry-run to enable safe logging only')
    args = parser.parse_args()
    run_server(args.port, dry_run=args.dry_run)

if __name__ == '__main__':
    main()
