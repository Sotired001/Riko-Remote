"""
agent_agent_client.py

Host-side client for communicating with the agent runner.
Provides simple wrappers: get_status(), get_screenshot(), exec_action()

Usage (host):
from external_reused.agent_agent_client import AgentAgentClient
client = AgentAgentClient('http://agent-ip:8000', api_token='your-token')
print(client.get_status())
img = client.get_screenshot()
resp = client.exec_action({'action': 'click', 'coordinates': [100, 200]})

Note: Keep network access restricted. Prefer host-only network or SSH tunnel.
"""

import requests
import base64
from PIL import Image
import io

class AgentAgentClient:
    def __init__(self, base_url: str, api_token: str = None, timeout: float = 5.0):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        self.last_screenshot = None  # Cache last screenshot for no_change

    def _headers(self):
        headers = {}
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        return headers

    def get_status(self):
        try:
            r = requests.get(f"{self.base_url}/status", headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'error': str(e)}

    def get_screenshot(self, screen=None):
        """Get screenshot from agent, optionally from specific screen"""
        try:
            url = f"{self.base_url}/screenshot"
            if screen is not None:
                url += f"?screen={screen}"
                
            r = requests.get(url, headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if 'no_change' in data and data['no_change']:
                return self.last_screenshot  # Return cached image
            if 'image' in data:
                img_bytes = base64.b64decode(data['image'])
                img = Image.open(io.BytesIO(img_bytes))
                self.last_screenshot = img  # Update cache
                return {
                    'image': img,
                    'screen': data.get('screen', {}),
                    'screens_available': data.get('screens_available', 1)
                }
            return {'error': 'no image in response'}
        except Exception as e:
            return {'error': str(e)}

    def get_screens(self):
        """Get available screens information"""
        try:
            r = requests.get(f"{self.base_url}/screens", headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'error': str(e)}

    def get_screenshot_from_screen(self, screen_index):
        """Get screenshot from specific screen by index"""
        try:
            r = requests.get(f"{self.base_url}/screenshot/{screen_index}", headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if 'image' in data:
                img_bytes = base64.b64decode(data['image'])
                img = Image.open(io.BytesIO(img_bytes))
                return {
                    'image': img,
                    'screen': data.get('screen', {}),
                    'screens_available': data.get('screens_available', 1)
                }
            return {'error': 'no image in response'}
        except Exception as e:
            return {'error': str(e)}

    def exec_action(self, action: dict):
        """Execute action on agent with multi-monitor support"""
        try:
            r = requests.post(f"{self.base_url}/exec", json=action, headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'error': str(e)}
    
    def click(self, x, y, screen=0, relative=True):
        """Click at coordinates on specific screen"""
        action = {
            'action': 'click',
            'coordinates': [x, y],
            'screen': screen,
            'relative': relative
        }
        return self.exec_action(action)
    
    def type_text(self, text, x=100, y=100, screen=0, relative=True):
        """Type text at coordinates on specific screen"""
        action = {
            'action': 'type',
            'text': text,
            'coordinates': [x, y],
            'screen': screen,
            'relative': relative
        }
        return self.exec_action(action)
    
    def scroll(self, dy, x=None, y=None, screen=0, relative=True):
        """Scroll on specific screen"""
        if x is None or y is None:
            # Default to center of screen
            x, y = 500, 400
        action = {
            'action': 'scroll',
            'dy': dy,
            'coordinates': [x, y],
            'screen': screen,
            'relative': relative
        }
        return self.exec_action(action)
