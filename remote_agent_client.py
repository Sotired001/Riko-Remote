"""
remote_agent_client.py

Host-side client for communicating with the remote runner agent.
Provides simple wrappers: get_status(), get_screenshot(), exec_action()

Usage (host):
from external_reused.remote_agent_client import RemoteAgentClient
client = RemoteAgentClient('http://remote-ip:8000', api_token='your-token')
print(client.get_status())
img = client.get_screenshot()
resp = client.exec_action({'action': 'click', 'coordinates': [100, 200]})

Note: Keep network access restricted. Prefer host-only network or SSH tunnel.
"""

import requests
import base64
from PIL import Image
import io

class RemoteAgentClient:
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

    def get_screenshot(self):
        try:
            r = requests.get(f"{self.base_url}/screenshot", headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if 'no_change' in data and data['no_change']:
                return self.last_screenshot  # Return cached image
            if 'image' in data:
                img_bytes = base64.b64decode(data['image'])
                img = Image.open(io.BytesIO(img_bytes))
                self.last_screenshot = img  # Update cache
                return img
            return {'error': 'no image in response'}
        except Exception as e:
            return {'error': str(e)}

    def exec_action(self, action: dict):
        try:
            r = requests.post(f"{self.base_url}/exec", json=action, headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'error': str(e)}