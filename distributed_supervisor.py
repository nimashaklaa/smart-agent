import asyncio
import hashlib
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import json
import uuid

from agent_registry import agent_registry, AgentStatus
from state_manager import state_manager, ConversationState

logger = logging.getLogger(__name__)

class SupervisorStatus(Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

@dataclass
class SupervisorNode:
    id: str
    host: str
    port: int
    status: SupervisorStatus
    load: float  # Current load (0.0 to 1.0)
    capabilities: List[str]
    last_heartbeat: float
    max_concurrent_sessions: int
    current_sessions: int

class LoadBalancer:
    """Load balancer for distributing requests across multiple supervisors"""
    
    def __init__(self):
        self.supervisors: Dict[str, SupervisorNode] = {}
        self.session_assignments: Dict[str, str] = {}  # session_id -> supervisor_id
        self._lock = asyncio.Lock()
        
    async def register_supervisor(self, supervisor: SupervisorNode) -> None:
        """Register a new supervisor node"""
        async with self._lock:
            self.supervisors[supervisor.id] = supervisor
            logger.info(f"Registered supervisor: {supervisor.id}")
    
    async def unregister_supervisor(self, supervisor_id: str) -> None:
        """Unregister a supervisor node"""
        async with self._lock:
            if supervisor_id in self.supervisors:
                del self.supervisors[supervisor_id]
                # Reassign sessions from this supervisor
                await self._reassign_sessions(supervisor_id)
                logger.info(f"Unregistered supervisor: {supervisor_id}")
    
    async def get_available_supervisor(self, session_id: str, 
                                     required_capabilities: List[str] = None) -> Optional[str]:
        """Get the best available supervisor for a session"""
        async with self._lock:
            available_supervisors = [
                sid for sid, supervisor in self.supervisors.items()
                if (supervisor.status == SupervisorStatus.AVAILABLE and
                    supervisor.current_sessions < supervisor.max_concurrent_sessions)
            ]
            
            if not available_supervisors:
                return None
            
            # Filter by capabilities if specified
            if required_capabilities:
                available_supervisors = [
                    sid for sid in available_supervisors
                    if all(cap in self.supervisors[sid].capabilities 
                           for cap in required_capabilities)
                ]
            
            if not available_supervisors:
                return None
            
            # Use least loaded supervisor
            best_supervisor = min(
                available_supervisors,
                key=lambda sid: self.supervisors[sid].load
            )
            
            # Assign session to supervisor
            self.session_assignments[session_id] = best_supervisor
            self.supervisors[best_supervisor].current_sessions += 1
            
            return best_supervisor
    
    async def _reassign_sessions(self, supervisor_id: str) -> None:
        """Reassign sessions from a failed supervisor"""
        sessions_to_reassign = [
            session_id for session_id, assigned_supervisor in self.session_assignments.items()
            if assigned_supervisor == supervisor_id
        ]
        
        for session_id in sessions_to_reassign:
            new_supervisor = await self.get_available_supervisor(session_id)
            if new_supervisor:
                self.session_assignments[session_id] = new_supervisor
            else:
                # No available supervisors, mark session as failed
                await state_manager.update_session(session_id, {
                    'status': 'error',
                    'metadata': {'error': 'No available supervisors'}
                })
    
    async def update_supervisor_status(self, supervisor_id: str, 
                                     status: SupervisorStatus, load: float = None) -> None:
        """Update supervisor status and load"""
        async with self._lock:
            if supervisor_id in self.supervisors:
                self.supervisors[supervisor_id].status = status
                if load is not None:
                    self.supervisors[supervisor_id].load = load
                self.supervisors[supervisor_id].last_heartbeat = time.time()
    
    async def get_supervisor_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        async with self._lock:
            total_supervisors = len(self.supervisors)
            available_supervisors = len([
                s for s in self.supervisors.values() 
                if s.status == SupervisorStatus.AVAILABLE
            ])
            total_sessions = sum(s.current_sessions for s in self.supervisors.values())
            
            return {
                'total_supervisors': total_supervisors,
                'available_supervisors': available_supervisors,
                'total_sessions': total_sessions,
                'session_assignments': len(self.session_assignments)
            }
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        async with self._lock:
            return {
                'total_sessions': len(self.session_assignments),
                'active_sessions': len(self.session_assignments),
                'completed_sessions': 0,  # Not tracked in load balancer
                'error_sessions': 0  # Not tracked in load balancer
            }

class DistributedSupervisor:
    """Distributed supervisor that can handle multiple concurrent sessions"""
    
    def __init__(self, supervisor_id: str = None, host: str = "localhost", port: int = 8000):
        self.supervisor_id = supervisor_id or str(uuid.uuid4())
        self.host = host
        self.port = port
        self.status = SupervisorStatus.AVAILABLE
        self.load = 0.0
        self.max_concurrent_sessions = 50
        self.current_sessions = 0
        self.capabilities = ['calendar', 'scheduling', 'modification', 'deletion']
        
        self.load_balancer = LoadBalancer()
        self.executor = ThreadPoolExecutor(max_workers=20)
        
        # Initialize without blocking
        self._initialized = False
        logger.info(f"Distributed supervisor initialized with ID: {self.supervisor_id}")
        
    async def initialize(self):
        """Initialize the supervisor asynchronously"""
        if not self._initialized:
            await self._register_self()
            # Start heartbeat in background
            asyncio.create_task(self._heartbeat_loop())
            self._initialized = True
            logger.info(f"Supervisor {self.supervisor_id} fully initialized")
        
    async def _register_self(self):
        """Register this supervisor with the load balancer"""
        supervisor_node = SupervisorNode(
            id=self.supervisor_id,
            host=self.host,
            port=self.port,
            status=self.status,
            load=self.load,
            capabilities=self.capabilities,
            last_heartbeat=time.time(),
            max_concurrent_sessions=self.max_concurrent_sessions,
            current_sessions=self.current_sessions
        )
        await self.load_balancer.register_supervisor(supervisor_node)
        logger.info(f"Supervisor {self.supervisor_id} registered with load balancer")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while True:
            try:
                await self.load_balancer.update_supervisor_status(
                    self.supervisor_id, 
                    self.status, 
                    self.load
                )
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def process_message(self, session_id: str, user_id: str, 
                           message: str) -> Dict[str, Any]:
        """Process a user message through the distributed system"""
        try:
            # Get or create session
            session = await state_manager.get_session(session_id)
            if not session:
                session = await state_manager.create_session(session_id, user_id, {
                    'message_list': [('user', message)]
                })
            else:
                await state_manager.add_message(session_id, ('user', message))
            
            # Determine required capabilities based on message
            required_capabilities = self._analyze_message_capabilities(message)
            
            # Get available supervisor
            supervisor_id = await self.load_balancer.get_available_supervisor(
                session_id, required_capabilities
            )
            
            if not supervisor_id:
                return {
                    'error': 'No available supervisors',
                    'status': 'error'
                }
            
            # Process the message
            result = await self._process_with_supervisor(session_id, message, supervisor_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await state_manager.update_session(session_id, {
                'status': 'error',
                'metadata': {'error': str(e)}
            })
            return {
                'error': str(e),
                'status': 'error'
            }
    
    def _analyze_message_capabilities(self, message: str) -> List[str]:
        """Analyze message to determine required capabilities"""
        message_lower = message.lower()
        capabilities = []
        
        if any(word in message_lower for word in ['check', 'available', 'free']):
            capabilities.append('calendar')
        
        if any(word in message_lower for word in ['schedule', 'add', 'create', 'book']):
            capabilities.append('scheduling')
        
        if any(word in message_lower for word in ['modify', 'edit', 'change', 'update']):
            capabilities.append('modification')
        
        if any(word in message_lower for word in ['delete', 'remove', 'cancel']):
            capabilities.append('deletion')
        
        return capabilities if capabilities else ['calendar']  # Default capability
    
    async def _process_with_supervisor(self, session_id: str, message: str, 
                                     supervisor_id: str) -> Dict[str, Any]:
        """Process message with a specific supervisor"""
        try:
            # Get session state
            session = await state_manager.get_session(session_id)
            if not session:
                raise ValueError("Session not found")
            
            # Create state for LangGraph
            state = {
                'next': session.current_node,
                'message_list': session.message_list
            }
            
            # Process with appropriate agent based on message analysis
            capabilities = self._analyze_message_capabilities(message)
            
            if 'scheduling' in capabilities:
                agent_name = 'event_scheduler_agent'
            elif 'modification' in capabilities:
                agent_name = 'event_modifier_agent'
            elif 'deletion' in capabilities:
                agent_name = 'event_remover_agent'
            else:
                agent_name = 'calendar_checker_agent'
            
            # Execute agent
            if agent_registry.is_agent_available(agent_name):
                try:
                    result = await agent_registry.execute_agent(agent_name, message)
                    
                    # Update session
                    await state_manager.add_message(session_id, ('ai', f"{agent_name}: {result}"))
                    
                    return {
                        'response': result,
                        'agent': agent_name,
                        'status': 'success'
                    }
                except Exception as agent_error:
                    logger.error(f"Agent execution error: {agent_error}")
                    return {
                        'error': f'Agent execution failed: {str(agent_error)}',
                        'status': 'error'
                    }
            else:
                return {
                    'error': f'Agent {agent_name} not available',
                    'status': 'error'
                }
                
        except Exception as e:
            logger.error(f"Error in supervisor processing: {e}")
            return {
                'error': str(e),
                'status': 'error'
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics"""
        lb_stats = await self.load_balancer.get_session_stats()
        
        return {
            'supervisor_id': self.supervisor_id,
            'status': self.status.value,
            'load': self.load,
            'current_sessions': self.current_sessions,
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'load_balancer_stats': lb_stats
        }

# Global distributed supervisor instance
distributed_supervisor = DistributedSupervisor() 