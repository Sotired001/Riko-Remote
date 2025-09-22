"""
Compatibility shim - use the new AgentAgentClient class.

remote_agent_client.RemoteAgentClient remains for backward compatibility and
simply re-exports AgentAgentClient from the new module.
"""

from external_reused.agent_agent_client import AgentAgentClient as RemoteAgentClient

__all__ = ["RemoteAgentClient"]