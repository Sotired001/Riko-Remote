"""
orchestrator_web.py

Web-based orchestrator UI for managing multiple Riko agents.
Replaces the OpenCV-based vm_stream_viewer.py with a modern web interface.

Features:
- Multi-agent dashboard with live screenshots
- Agent discovery and management
- Web-based control interface
- Real-time status monitoring

Usage:
    python orchestrator_web.py
    Open browser to http://localhost:5000
"""

from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
import json
import base64
import io
import time
import threading
from datetime import datetime
import requests
from agent_agent_client import AgentAgentClient
import os
from ai_assistant import LocalAI, AIAssistant

app = Flask(__name__)
app.config['SECRET_KEY'] = 'orchestrator-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global agent manager and AI assistant
agents = {}
agent_lock = threading.Lock()
ai_assistant = None

class AgentManager:
    def __init__(self):
        self.agents = {}
        self.update_thread = None
        self.running = False
    
    def add_agent(self, agent_id, url, token=None, name=None):
        """Add an agent to the registry"""
        with agent_lock:
            self.agents[agent_id] = {
                'id': agent_id,
                'url': url,
                'token': token,
                'name': name or f"Agent {agent_id}",
                'client': AgentAgentClient(url, token),
                'status': 'unknown',
                'last_seen': None,
                'screenshot': None,
                'error': None,
                'response_time': None,
                'last_update': None,
                'created_at': datetime.now().isoformat()
            }
    
    def remove_agent(self, agent_id):
        """Remove an agent from the registry"""
        with agent_lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
    
    def get_agents(self):
        """Get all registered agents (JSON serializable)"""
        with agent_lock:
            # Return only serializable data, exclude the client object
            serializable_agents = {}
            for agent_id, agent in self.agents.items():
                serializable_agents[agent_id] = {
                    'id': agent['id'],
                    'url': agent['url'],
                    'name': agent['name'],
                    'status': agent['status'],
                    'last_seen': agent['last_seen'],
                    'screenshot': agent['screenshot'],
                    'error': agent['error'],
                    'response_time': agent['response_time'],
                    'last_update': agent['last_update'],
                    'created_at': agent['created_at'],
                    'screens': agent.get('screens', [])
                }
            return serializable_agents
    
    def update_agent_status(self, agent_id):
        """Update status and screenshot for a specific agent"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        client = agent['client']
        
        start_time = time.time()
        try:
            # Get status
            status_response = client.get_status()
            if 'error' in status_response:
                agent['status'] = 'error'
                agent['error'] = status_response['error']
            else:
                agent['status'] = 'online'
                agent['last_seen'] = datetime.now().isoformat()
                agent['error'] = None
            
            # Get screens info
            screens = self.get_agent_screens(agent_id)
            agent['screens'] = screens
            
            # Get screenshot from primary screen (screen 0)
            screenshot = client.get_screenshot_from_screen(0)
            if hasattr(screenshot, 'save'):  # PIL Image
                buffered = io.BytesIO()
                screenshot.save(buffered, format='JPEG')
                agent['screenshot'] = base64.b64encode(buffered.getvalue()).decode('utf-8')
            elif isinstance(screenshot, dict) and 'error' in screenshot:
                agent['error'] = screenshot['error']
            
            # Track performance
            response_time = (time.time() - start_time) * 1000  # ms
            agent['response_time'] = round(response_time, 1)
            agent['last_update'] = time.time()
            
        except Exception as e:
            agent['status'] = 'error'
            agent['error'] = str(e)
            agent['response_time'] = None
    
    def get_agent_screens(self, agent_id):
        """Get screen information from agent"""
        try:
            agent = self.agents[agent_id]
            client = agent['client']
            return client.get_screens()
        except Exception as e:
            return []
    
    def get_agent_screenshot(self, agent_id, screen=0):
        """Get screenshot from agent (specific screen)"""
        try:
            agent = self.agents[agent_id]
            client = agent['client']
            screenshot = client.get_screenshot_from_screen(screen)
            if hasattr(screenshot, 'save'):  # PIL Image
                buffered = io.BytesIO()
                screenshot.save(buffered, format='JPEG')
                return base64.b64encode(buffered.getvalue()).decode('utf-8')
            return None
        except Exception as e:
            return None
    
    def start_monitoring(self):
        """Start background monitoring of all agents"""
        self.running = True
        self.update_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.update_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.running = False
    
    def _monitor_loop(self):
        """Background loop to update agent status and screenshots"""
        while self.running:
            agent_ids = list(self.agents.keys())
            for agent_id in agent_ids:
                self.update_agent_status(agent_id)
                time.sleep(0.5)  # Increased delay between agents
            
            # Emit updated data to web clients
            socketio.emit('agent_update', self.get_agents())
            time.sleep(5)  # Update every 5 seconds instead of 2

# Global agent manager
agent_manager = AgentManager()

@app.route('/')
def index():
    """Main orchestrator dashboard"""
    return render_template('orchestrator.html')

@app.route('/api/agents', methods=['GET'])
def api_get_agents():
    """Get all registered agents"""
    return jsonify(agent_manager.get_agents())

@app.route('/api/agents', methods=['POST'])
def api_add_agent():
    """Add a new agent"""
    data = request.json
    agent_id = data.get('id') or f"agent_{int(time.time())}"
    url = data.get('url')
    token = data.get('token')
    name = data.get('name')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    agent_manager.add_agent(agent_id, url, token, name)
    # Immediately update the newly added agent and notify clients
    try:
        agent_manager.update_agent_status(agent_id)
    except Exception:
        pass
    socketio.emit('agent_update', agent_manager.get_agents())
    return jsonify({'success': True, 'agent_id': agent_id})

@app.route('/api/agents/<agent_id>', methods=['DELETE'])
def api_remove_agent(agent_id):
    """Remove an agent"""
    agent_manager.remove_agent(agent_id)
    # Notify clients the list changed
    socketio.emit('agent_update', agent_manager.get_agents())
    return jsonify({'success': True})

@app.route('/api/agents/<agent_id>/exec', methods=['POST'])
def api_exec_action(agent_id):
    """Execute an action on a specific agent"""
    # Get the raw agents dict (with client objects) not the serializable version
    if agent_id not in agent_manager.agents:
        return jsonify({'error': 'Agent not found'}), 404
    
    client = agent_manager.agents[agent_id]['client']
    action = request.json
    
    result = client.exec_action(action)
    return jsonify(result)


@app.route('/api/agents/<agent_id>/refresh', methods=['POST'])
def api_refresh_agent(agent_id):
    """Force refresh an agent's status and screenshot"""
    if agent_id not in agent_manager.agents:
        return jsonify({'error': 'Agent not found'}), 404

    try:
        agent_manager.update_agent_status(agent_id)
        socketio.emit('agent_update', agent_manager.get_agents())
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents/<agent_id>/screenshot')
def api_get_screenshot(agent_id):
    """Get latest screenshot for an agent (primary screen)"""
    agents = agent_manager.get_agents()
    if agent_id not in agents:
        return jsonify({'error': 'Agent not found'}), 404
    
    agent = agents[agent_id]
    if agent['screenshot']:
        return jsonify({'image': agent['screenshot']})
    else:
        return jsonify({'error': 'No screenshot available'})

@app.route('/api/agents/<agent_id>/screenshot/<int:screen_id>')
def api_get_screenshot_screen(agent_id, screen_id):
    """Get screenshot for a specific screen of an agent"""
    agents = agent_manager.get_agents()
    if agent_id not in agents:
        return jsonify({'error': 'Agent not found'}), 404
    
    screenshot = agent_manager.get_agent_screenshot(agent_id, screen_id)
    if screenshot:
        return jsonify({'image': screenshot, 'screen': screen_id})
    else:
        return jsonify({'error': f'No screenshot available for screen {screen_id}'})

@app.route('/api/agents/<agent_id>/screens')
def api_get_screens(agent_id):
    """Get screen information for an agent"""
    if agent_id not in agent_manager.agents:
        return jsonify({'error': 'Agent not found'}), 404
    
    screens = agent_manager.get_agent_screens(agent_id)
    return jsonify({'screens': screens})

@app.route('/api/ai/command', methods=['POST'])
def api_ai_command():
    """Process natural language command via AI"""
    global ai_assistant
    
    data = request.json
    command_text = data.get('command', '')
    
    if not command_text:
        return jsonify({'error': 'No command provided'}), 400
    
    # Initialize AI assistant if not already done
    if ai_assistant is None:
        ai_assistant = AIAssistant()
        if not ai_assistant.start():
            return jsonify({'error': 'AI assistant unavailable. Please install Ollama.'}), 503
    
    # Update AI with current agents
    ai_assistant.agents_cache = agent_manager.get_agents()
    ai_assistant.ai.update_agent_context(ai_assistant.agents_cache)
    
    # Process command
    result = ai_assistant.process_command(command_text)
    return jsonify(result)

@app.route('/api/ai/status')
def api_ai_status():
    """Get AI assistant status"""
    global ai_assistant
    
    if ai_assistant is None:
        ai_assistant = AIAssistant()
    
    return jsonify({
        'available': ai_assistant.ai.is_available(),
        'model': ai_assistant.ai.model_name,
        'history_count': len(ai_assistant.ai.conversation_history) if ai_assistant else 0
    })

@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection"""
    emit('agent_update', agent_manager.get_agents())

@socketio.on('discover_agents')
def handle_discover_agents():
    """Handle agent discovery request"""
    # Simple local discovery - check common ports
    discovered = []
    import socket
    
    # Check localhost on common agent ports
    for port in [8000, 8001, 8002, 8003]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                # Port is open, try to verify it's an agent
                try:
                    response = requests.get(f'http://localhost:{port}/status', timeout=2)
                    if response.status_code == 200:
                        discovered.append({
                            'url': f'http://localhost:{port}',
                            'port': port,
                            'status': 'available'
                        })
                except:
                    pass
        except:
            pass
    
    emit('discovery_result', {
        'message': f'Found {len(discovered)} agents',
        'agents': discovered
    })

def load_default_agents():
    """Load default agents from environment or config"""
    # Load from environment variables
    default_url = os.getenv('VM_AGENT_URL', os.getenv('HOST_AGENT_URL'))
    default_token = os.getenv('AGENT_API_TOKEN', os.getenv('REMOTE_API_TOKEN'))
    
    if default_url:
        agent_manager.add_agent('default', default_url, default_token, 'Default Agent')

if __name__ == '__main__':
    # Load any default agents
    load_default_agents()
    
    # Start monitoring
    agent_manager.start_monitoring()
    
    print("Starting Riko Orchestrator Web UI...")
    print("Open your browser to: http://localhost:5000")
    
    # Run the Flask app with SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)