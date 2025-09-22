"""
demo_ai.py

Demo script showing the AI assistant capabilities without requiring Ollama
Uses mock responses to demonstrate the functionality.
"""

import json
from ai_assistant import AgentCommand

class MockAI:
    """Mock AI for demonstration purposes"""
    
    def __init__(self):
        self.responses = {
            "take a screenshot": [
                AgentCommand(None, "screenshot", {}, 0.9, "User wants screenshots from all agents")
            ],
            "click at 100 200": [
                AgentCommand(None, "click", {"coordinates": [100, 200]}, 0.95, "Clear click command with coordinates")
            ],
            "type hello world": [
                AgentCommand(None, "type", {"text": "hello world", "coordinates": [100, 100]}, 0.9, "Typing command with text")
            ],
            "show status": [
                AgentCommand(None, "status", {}, 0.95, "Status request for all agents")
            ],
            "scroll down": [
                AgentCommand(None, "scroll", {"dx": 0, "dy": -3}, 0.85, "Scroll down command")
            ]
        }
    
    def parse_command(self, user_input: str):
        """Mock command parsing"""
        user_input_lower = user_input.lower()
        
        # Find best match
        for pattern, commands in self.responses.items():
            if pattern in user_input_lower:
                return commands
        
        # Fallback
        return [AgentCommand(None, "unknown", {"original": user_input}, 0.1, "Could not parse command")]

def demo_ai_parsing():
    """Demonstrate AI command parsing"""
    print("🤖 Riko AI Assistant - Demo Mode")
    print("="*50)
    print("This demo shows how natural language commands are parsed.")
    print("(No AI model required for this demo)")
    print()
    
    mock_ai = MockAI()
    
    test_commands = [
        "Take a screenshot of all agents",
        "Click at position 100, 200",
        "Type hello world",
        "Show me the status",
        "Scroll down please",
        "Do something weird"  # This will show unknown command handling
    ]
    
    for i, command in enumerate(test_commands, 1):
        print(f"{i}. User: '{command}'")
        
        parsed_commands = mock_ai.parse_command(command)
        
        for cmd in parsed_commands:
            print(f"   → Action: {cmd.action}")
            print(f"   → Target: {cmd.agent_id or 'all agents'}")
            print(f"   → Params: {cmd.params}")
            print(f"   → Confidence: {cmd.confidence:.1f}")
            print(f"   → Reasoning: {cmd.reasoning}")
        print()

def demo_agent_interaction():
    """Demonstrate agent interaction flow"""
    print("🎯 Agent Interaction Demo")
    print("="*30)
    print("This shows how commands would be executed on agents.")
    print()
    
    # Mock agent registry
    mock_agents = {
        "agent1": {"name": "Main Computer", "status": "online", "url": "http://192.168.1.100:8000"},
        "agent2": {"name": "Test VM", "status": "online", "url": "http://192.168.1.101:8000"}
    }
    
    print("Available Agents:")
    for agent_id, agent in mock_agents.items():
        print(f"  🤖 {agent['name']} ({agent_id}) - {agent['status']}")
    print()
    
    # Mock command execution
    mock_commands = [
        AgentCommand("agent1", "click", {"coordinates": [150, 300]}, 0.9, "Click on main computer"),
        AgentCommand(None, "screenshot", {}, 0.95, "Screenshot all agents"),
        AgentCommand("agent2", "type", {"text": "test input", "coordinates": [200, 400]}, 0.85, "Type on test VM")
    ]
    
    for i, cmd in enumerate(mock_commands, 1):
        target = cmd.agent_id if cmd.agent_id else "all agents"
        print(f"{i}. Executing '{cmd.action}' on {target}")
        print(f"   Params: {cmd.params}")
        print(f"   Confidence: {cmd.confidence:.1f}")
        
        # Mock result
        if cmd.confidence > 0.3:
            print(f"   ✅ Success: Command executed successfully")
        else:
            print(f"   ❌ Rejected: Low confidence command")
        print()

def main():
    print("🚀 Riko AI Assistant Demonstration")
    print("="*60)
    print("Choose a demo:")
    print("1. AI Command Parsing Demo")
    print("2. Agent Interaction Demo")
    print("3. Both")
    print()
    
    try:
        choice = input("Enter choice (1-3): ").strip()
        print()
        
        if choice in ["1", "3"]:
            demo_ai_parsing()
            
        if choice in ["2", "3"]:
            demo_agent_interaction()
            
        print("🎉 Demo complete!")
        print()
        print("To use the real AI assistant:")
        print("1. Install Ollama: .\\install_ai.bat")
        print("2. Run: python ai_assistant.py")
        print("3. Or use the web interface: python orchestrator_web.py")
        
    except KeyboardInterrupt:
        print("\n👋 Demo cancelled.")

if __name__ == "__main__":
    main()