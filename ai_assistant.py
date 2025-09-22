"""
ai_assistant.py

Local AI Assistant for Riko Orchestrator
Integrates with Ollama to provide natural language command interface for agent control.

Features:
- Natural language command parsing
- Multi-agent coordination
- Voice-to-text support (optional)
- Command validation and safety checks
- Conversation history and context

Usage:
    python ai_assistant.py
    Or integrate with orchestrator_web.py
"""

import requests
import json
import re
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AgentCommand:
    agent_id: Optional[str]
    action: str
    params: Dict
    confidence: float
    reasoning: str

class LocalAI:
    def __init__(self, model_name: str = "llama3.2", ollama_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.conversation_history = []
        self.agent_context = {}
        
    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model['name'].startswith(self.model_name) for model in models)
            return False
        except Exception:
            return False
    
    def pull_model(self) -> bool:
        """Pull the AI model if it's not available"""
        try:
            print(f"Pulling model {self.model_name}...")
            response = requests.post(f"{self.ollama_url}/api/pull", 
                                   json={"name": self.model_name}, 
                                   stream=True, timeout=300)
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "status" in data:
                        print(f"Status: {data['status']}")
                    if data.get("status") == "success":
                        return True
            return False
        except Exception as e:
            print(f"Error pulling model: {e}")
            return False
    
    def update_agent_context(self, agents: Dict):
        """Update the AI's context about available agents"""
        self.agent_context = {
            agent_id: {
                'name': agent['name'],
                'status': agent['status'],
                'url': agent['url'],
                'last_seen': agent.get('last_seen')
            }
            for agent_id, agent in agents.items()
        }
    
    def parse_command(self, user_input: str) -> List[AgentCommand]:
        """Parse natural language input into agent commands"""
        
        # Create context-aware prompt
        agent_list = "\n".join([
            f"- {agent_id}: {info['name']} ({info['status']}) at {info['url']}"
            for agent_id, info in self.agent_context.items()
        ])
        
        system_prompt = f"""You are an AI assistant controlling computer agents. Available agents:
{agent_list}

Your job is to parse user commands and convert them to structured agent actions.

Available actions:
- click: Click at coordinates {{x, y}} on a specific screen
- type: Type text at coordinates {{x, y}} on a specific screen
- scroll: Scroll with delta {{dx, dy}} on a specific screen
- screenshot: Take a screenshot from a specific screen
- status: Get agent status

Multi-screen support:
- Commands can target specific screens using "screen 1", "monitor 2", etc.
- Default to screen 0 (primary) if not specified
- Coordinates can be relative (0-1 range) or absolute pixels
- Use "relative": true for normalized coordinates (recommended)

Respond with JSON array of commands:
[{{
    "agent_id": "agent_id or null for all",
    "action": "action_name", 
    "params": {{
        "coordinates": [x, y], 
        "text": "text", 
        "screen": 0,
        "relative": true,
        "dx": 0, 
        "dy": 0
    }},
    "confidence": 0.9,
    "reasoning": "why this command"
}}]

Screen targeting examples:
- "click on screen 2 at center" -> {{"screen": 1, "coordinates": [0.5, 0.5], "relative": true}}
- "type hello on monitor 1" -> {{"screen": 0, "coordinates": [0.1, 0.1], "relative": true}}

For ambiguous commands, use lower confidence. For dangerous commands, add safety warnings."""

        prompt = f"{system_prompt}\n\nUser command: {user_input}"
        
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", 
                                   json={
                                       "model": self.model_name,
                                       "prompt": prompt,
                                       "stream": False,
                                       "options": {
                                           "temperature": 0.1,  # Low for consistent parsing
                                           "top_p": 0.9
                                       }
                                   }, timeout=30)
            
            if response.status_code == 200:
                ai_response = response.json()['response']
                return self._extract_commands_from_response(ai_response)
            else:
                return [AgentCommand(None, "error", {"message": "AI unavailable"}, 0.0, "API error")]
                
        except Exception as e:
            return [AgentCommand(None, "error", {"message": str(e)}, 0.0, "Parse error")]
    
    def _extract_commands_from_response(self, ai_response: str) -> List[AgentCommand]:
        """Extract structured commands from AI response"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
            if json_match:
                commands_data = json.loads(json_match.group())
                commands = []
                
                for cmd_data in commands_data:
                    commands.append(AgentCommand(
                        agent_id=cmd_data.get('agent_id'),
                        action=cmd_data.get('action', 'unknown'),
                        params=cmd_data.get('params', {}),
                        confidence=cmd_data.get('confidence', 0.5),
                        reasoning=cmd_data.get('reasoning', 'No reasoning provided')
                    ))
                
                return commands
            else:
                # Fallback: simple pattern matching
                return self._fallback_command_parsing(ai_response)
                
        except Exception as e:
            return [AgentCommand(None, "error", {"message": f"Failed to parse: {e}"}, 0.0, "JSON parse error")]
    
    def _fallback_command_parsing(self, text: str) -> List[AgentCommand]:
        """Simple fallback parsing when AI doesn't return proper JSON"""
        commands = []
        text_lower = text.lower()
        
        # Basic pattern matching
        if "click" in text_lower:
            # Try to extract coordinates
            coord_match = re.search(r'(\d+)[,\s]+(\d+)', text)
            if coord_match:
                x, y = int(coord_match.group(1)), int(coord_match.group(2))
                commands.append(AgentCommand(
                    None, "click", {"coordinates": [x, y]}, 0.6, "Pattern matched click command"
                ))
        
        if "type" in text_lower:
            # Extract text to type
            type_match = re.search(r'type[:\s]+"([^"]+)"', text, re.IGNORECASE)
            if type_match:
                commands.append(AgentCommand(
                    None, "type", {"text": type_match.group(1), "coordinates": [100, 100]}, 0.6, "Pattern matched type command"
                ))
        
        if "screenshot" in text_lower or "capture" in text_lower:
            commands.append(AgentCommand(
                None, "screenshot", {}, 0.8, "Pattern matched screenshot command"
            ))
        
        if not commands:
            commands.append(AgentCommand(
                None, "unknown", {"original": text}, 0.1, "Could not parse command"
            ))
        
        return commands
    
    def add_to_history(self, user_input: str, commands: List[AgentCommand], results: List[Dict]):
        """Add interaction to conversation history"""
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'commands': [cmd.__dict__ for cmd in commands],
            'results': results
        })
        
        # Keep only last 50 interactions
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

class AIAssistant:
    def __init__(self, orchestrator_url: str = "http://localhost:5000"):
        self.ai = LocalAI()
        self.orchestrator_url = orchestrator_url
        self.agents_cache = {}
        self.running = False
        
    def start(self):
        """Start the AI assistant"""
        print("🤖 Starting Riko AI Assistant...")
        
        # Check if Ollama is available
        if not self.ai.is_available():
            print("⚠️  Ollama not available. Attempting to pull model...")
            if not self.ai.pull_model():
                print("❌ Failed to setup AI model. Please install Ollama and try again.")
                print("   Install: https://ollama.ai")
                print("   Then run: ollama pull llama3.2")
                return False
        
        print(f"✅ AI model '{self.ai.model_name}' ready!")
        self.running = True
        return True
    
    def get_agents(self) -> Dict:
        """Get current agents from orchestrator"""
        try:
            response = requests.get(f"{self.orchestrator_url}/api/agents", timeout=5)
            if response.status_code == 200:
                agents = response.json()
                self.agents_cache = agents
                self.ai.update_agent_context(agents)
                return agents
            return {}
        except Exception:
            return self.agents_cache  # Use cached version if orchestrator unavailable
    
    def execute_command(self, command: AgentCommand) -> Dict:
        """Execute a command on an agent via the orchestrator"""
        try:
            if command.action in ['click', 'type', 'scroll']:
                # Execute action via orchestrator API
                agent_id = command.agent_id or 'default'  # Use default if no specific agent
                url = f"{self.orchestrator_url}/api/agents/{agent_id}/exec"
                
                action_data = {
                    'action': command.action,
                    **command.params
                }
                
                response = requests.post(url, json=action_data, timeout=10)
                return response.json() if response.status_code == 200 else {'error': 'Execution failed'}
                
            elif command.action == 'screenshot':
                agent_id = command.agent_id or 'default'
                url = f"{self.orchestrator_url}/api/agents/{agent_id}/screenshot"
                response = requests.get(url, timeout=10)
                return response.json() if response.status_code == 200 else {'error': 'Screenshot failed'}
                
            elif command.action == 'status':
                agents = self.get_agents()
                if command.agent_id:
                    return agents.get(command.agent_id, {'error': 'Agent not found'})
                else:
                    return {'agents': len(agents), 'online': sum(1 for a in agents.values() if a['status'] == 'online')}
            
            else:
                return {'error': f'Unknown action: {command.action}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def process_command(self, user_input: str) -> Dict:
        """Process a natural language command"""
        print(f"\n🧠 Processing: '{user_input}'")
        
        # Update agent context
        self.get_agents()
        
        # Parse command with AI
        commands = self.ai.parse_command(user_input)
        
        results = []
        for command in commands:
            print(f"   → {command.action} on {command.agent_id or 'all agents'} (confidence: {command.confidence:.1f})")
            print(f"     Reasoning: {command.reasoning}")
            
            # Safety check for low confidence commands
            if command.confidence < 0.3:
                result = {'error': 'Low confidence command rejected', 'confidence': command.confidence}
            else:
                result = self.execute_command(command)
            
            results.append(result)
            print(f"     Result: {result}")
        
        # Add to history
        self.ai.add_to_history(user_input, commands, results)
        
        return {
            'commands': [cmd.__dict__ for cmd in commands],
            'results': results,
            'success': all('error' not in result for result in results)
        }
    
    def interactive_mode(self):
        """Run interactive command line interface"""
        if not self.start():
            return
        
        print("\n" + "="*60)
        print("🤖 Riko AI Assistant - Interactive Mode")
        print("="*60)
        print("Type natural language commands to control your agents.")
        print("Examples:")
        print("  - 'Take a screenshot of all agents'")
        print("  - 'Click at position 100, 200 on the main agent'")
        print("  - 'Type hello world in the text field'")
        print("  - 'Show me the status of all agents'")
        print("\nType 'quit' to exit, 'help' for more commands.")
        print("-"*60)
        
        while self.running:
            try:
                user_input = input("\n🎯 Command: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                elif user_input.lower() == 'agents':
                    self.show_agents()
                elif user_input.lower() == 'history':
                    self.show_history()
                elif user_input:
                    self.process_command(user_input)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def show_help(self):
        """Show help information"""
        print("\n📖 Available Commands:")
        print("  agents  - Show connected agents")
        print("  history - Show recent command history")  
        print("  help    - Show this help")
        print("  quit    - Exit the assistant")
        print("\n💡 Natural Language Examples:")
        print("  'Click the center of the screen'")
        print("  'Type my password in the login field'")
        print("  'Scroll down on agent 1'")
        print("  'Take screenshots of all agents'")
        print("  'What's the status of my agents?'")
    
    def show_agents(self):
        """Show current agent status"""
        agents = self.get_agents()
        print(f"\n🤖 Connected Agents ({len(agents)}):")
        for agent_id, agent in agents.items():
            status_emoji = "🟢" if agent['status'] == 'online' else "🔴" if agent['status'] == 'error' else "🟡"
            print(f"  {status_emoji} {agent['name']} ({agent_id}) - {agent['status']}")
            print(f"      URL: {agent['url']}")
    
    def show_history(self):
        """Show recent command history"""
        print(f"\n📜 Recent Commands ({len(self.ai.conversation_history)}):")
        for i, entry in enumerate(self.ai.conversation_history[-5:], 1):
            print(f"  {i}. '{entry['user_input']}'")
            print(f"     → {len(entry['commands'])} commands executed")

def main():
    assistant = AIAssistant()
    assistant.interactive_mode()

if __name__ == "__main__":
    main()