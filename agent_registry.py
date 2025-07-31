from typing import Dict, Callable, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    LOADING = "loading"

@dataclass
class AgentMetadata:
    name: str
    description: str
    capabilities: List[str]
    status: AgentStatus
    version: str
    dependencies: List[str]
    config: Dict[str, Any]

class AgentRegistry:
    """Dynamic agent registry for scalable agent management"""
    
    def __init__(self):
        self._agents: Dict[str, Callable] = {}
        self._metadata: Dict[str, AgentMetadata] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._active_agents: Dict[str, bool] = {}
        
    def register_agent(self, name: str, agent_func: Callable, metadata: AgentMetadata) -> None:
        """Register a new agent dynamically"""
        self._agents[name] = agent_func
        self._metadata[name] = metadata
        self._active_agents[name] = True
        logger.info(f"Registered agent: {name}")
        
    def unregister_agent(self, name: str) -> None:
        """Remove an agent from the registry"""
        if name in self._agents:
            del self._agents[name]
            del self._metadata[name]
            self._active_agents[name] = False
            logger.info(f"Unregistered agent: {name}")
            
    def get_agent(self, name: str) -> Optional[Callable]:
        """Get an agent function by name"""
        return self._agents.get(name)
        
    def get_metadata(self, name: str) -> Optional[AgentMetadata]:
        """Get agent metadata by name"""
        return self._metadata.get(name)
        
    def list_agents(self) -> List[str]:
        """List all registered agent names"""
        return list(self._agents.keys())
        
    def list_active_agents(self) -> List[str]:
        """List only active agents"""
        return [name for name, active in self._active_agents.items() if active]
        
    def is_agent_available(self, name: str) -> bool:
        """Check if an agent is available and active"""
        return name in self._agents and self._active_agents.get(name, False)
        
    async def execute_agent(self, name: str, *args, **kwargs) -> Any:
        """Execute an agent asynchronously"""
        if not self.is_agent_available(name):
            raise ValueError(f"Agent {name} is not available")
            
        agent_func = self._agents[name]
        
        # Execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self._executor, agent_func, *args, **kwargs)
        
        return result
        
    def update_agent_status(self, name: str, status: AgentStatus) -> None:
        """Update agent status"""
        if name in self._metadata:
            self._metadata[name].status = status
            self._active_agents[name] = (status == AgentStatus.ACTIVE)
            
    def get_agent_capabilities(self, name: str) -> List[str]:
        """Get agent capabilities"""
        metadata = self.get_metadata(name)
        return metadata.capabilities if metadata else []
        
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability"""
        return [
            name for name in self.list_agents()
            if capability in self.get_agent_capabilities(name)
        ]

# Global agent registry instance
agent_registry = AgentRegistry() 