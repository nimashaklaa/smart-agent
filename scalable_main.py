from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncIterator, Dict, Any, Optional
import asyncio
import uuid
import logging
from datetime import datetime

from agent_registry import agent_registry, AgentMetadata, AgentStatus
from state_manager import state_manager
from distributed_supervisor import distributed_supervisor
from agents.CalendarCheckerAgent import calendar_checker_agent
from agents.EventSchedulerAgent import event_scheduler_agent
from agents.EventModifierAgent import event_modifier_agent
from agents.EventRemoverAgent import event_remover_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scalable Calendar Assistant", version="2.0.0")

# Pydantic models
class ChatInput(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent: str
    status: str
    timestamp: datetime

class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime

# Initialize agents in the registry
def initialize_agents():
    """Initialize all agents in the registry"""
    
    # Calendar Checker Agent
    calendar_metadata = AgentMetadata(
        name="calendar_checker_agent",
        description="Checks calendar availability and events",
        capabilities=["calendar", "availability_check"],
        status=AgentStatus.ACTIVE,
        version="1.0.0",
        dependencies=["google-calendar-api"],
        config={"timezone": "Asia/Colombo"}
    )
    agent_registry.register_agent("calendar_checker_agent", calendar_checker_agent, calendar_metadata)
    
    # Event Scheduler Agent
    scheduler_metadata = AgentMetadata(
        name="event_scheduler_agent",
        description="Schedules new calendar events",
        capabilities=["calendar", "scheduling", "event_creation"],
        status=AgentStatus.ACTIVE,
        version="1.0.0",
        dependencies=["google-calendar-api"],
        config={"timezone": "Asia/Colombo"}
    )
    agent_registry.register_agent("event_scheduler_agent", event_scheduler_agent, scheduler_metadata)
    
    # Event Modifier Agent
    modifier_metadata = AgentMetadata(
        name="event_modifier_agent",
        description="Modifies existing calendar events",
        capabilities=["calendar", "modification", "event_editing"],
        status=AgentStatus.ACTIVE,
        version="1.0.0",
        dependencies=["google-calendar-api"],
        config={"timezone": "Asia/Colombo"}
    )
    agent_registry.register_agent("event_modifier_agent", event_modifier_agent, modifier_metadata)
    
    # Event Remover Agent
    remover_metadata = AgentMetadata(
        name="event_remover_agent",
        description="Removes calendar events",
        capabilities=["calendar", "deletion", "event_removal"],
        status=AgentStatus.ACTIVE,
        version="1.0.0",
        dependencies=["google-calendar-api"],
        config={"timezone": "Asia/Colombo"}
    )
    agent_registry.register_agent("event_remover_agent", event_remover_agent, remover_metadata)
    
    logger.info("All agents initialized successfully")

# Initialize agents on startup
@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup"""
    try:
        # Initialize agents
        initialize_agents()
        logger.info("All agents initialized successfully")
        
        # Initialize distributed supervisor
        await distributed_supervisor.initialize()
        logger.info("Distributed supervisor initialized successfully")
        
        logger.info("Scalable Calendar Assistant started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise e

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_input: ChatInput, background_tasks: BackgroundTasks):
    """Process a chat message with scalable architecture"""
    
    # Generate session and user IDs if not provided
    session_id = chat_input.session_id or str(uuid.uuid4())
    user_id = chat_input.user_id or "anonymous"
    
    try:
        # Process message through distributed supervisor
        result = await distributed_supervisor.process_message(
            session_id, user_id, chat_input.message
        )
        
        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error'))
        
        # Add cleanup task
        background_tasks.add_task(cleanup_old_sessions)
        
        return ChatResponse(
            response=result.get('response', ''),
            session_id=session_id,
            agent=result.get('agent', 'unknown'),
            status=result.get('status', 'success'),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat_stream")
async def chat_stream(chat_input: ChatInput):
    """Stream chat responses"""
    
    session_id = chat_input.session_id or str(uuid.uuid4())
    user_id = chat_input.user_id or "anonymous"
    
    async def message_stream() -> AsyncIterator[str]:
        try:
            result = await distributed_supervisor.process_message(
                session_id, user_id, chat_input.message
            )
            
            if result.get('status') == 'error':
                yield f"Error: {result.get('error', 'Unknown error')}\n"
            else:
                yield f"{result.get('agent', 'unknown')}: {result.get('response', '')}\n"
                
        except Exception as e:
            yield f"Error: {str(e)}\n"
    
    return StreamingResponse(message_stream(), media_type="text/plain")

@app.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get session information"""
    session = await state_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionInfo(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status.value,
        message_count=len(session.message_list),
        created_at=session.created_at,
        updated_at=session.updated_at
    )

@app.get("/sessions/user/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user"""
    sessions = await state_manager.get_user_sessions(user_id)
    return {
        "user_id": user_id,
        "sessions": [
            {
                "session_id": session.session_id,
                "status": session.status.value,
                "message_count": len(session.message_list),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }
            for session in sessions
        ]
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    success = await state_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}

@app.get("/agents")
async def list_agents():
    """List all available agents"""
    agents = agent_registry.list_agents()
    agent_info = {}
    
    for agent_name in agents:
        metadata = agent_registry.get_metadata(agent_name)
        if metadata:
            agent_info[agent_name] = {
                "description": metadata.description,
                "capabilities": metadata.capabilities,
                "status": metadata.status.value,
                "version": metadata.version
            }
    
    return {"agents": agent_info}

@app.get("/agents/{agent_name}")
async def get_agent_info(agent_name: str):
    """Get information about a specific agent"""
    metadata = agent_registry.get_metadata(agent_name)
    if not metadata:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "name": metadata.name,
        "description": metadata.description,
        "capabilities": metadata.capabilities,
        "status": metadata.status.value,
        "version": metadata.version,
        "dependencies": metadata.dependencies,
        "config": metadata.config
    }

@app.post("/agents/{agent_name}/status")
async def update_agent_status(agent_name: str, status: str):
    """Update agent status"""
    try:
        new_status = AgentStatus(status)
        agent_registry.update_agent_status(agent_name, new_status)
        return {"message": f"Agent {agent_name} status updated to {status}"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Agent not found: {e}")

@app.get("/supervisor/stats")
async def get_supervisor_stats():
    """Get supervisor statistics"""
    stats = await distributed_supervisor.get_stats()
    return stats

@app.get("/supervisors")
async def list_supervisors():
    """List all available supervisors"""
    try:
        # Get supervisor information from the distributed supervisor
        supervisor_info = {
            "supervisor_id": distributed_supervisor.supervisor_id,
            "status": distributed_supervisor.status.value,
            "load": distributed_supervisor.load,
            "current_sessions": distributed_supervisor.current_sessions,
            "max_concurrent_sessions": distributed_supervisor.max_concurrent_sessions,
            "capabilities": distributed_supervisor.capabilities,
            "host": distributed_supervisor.host,
            "port": distributed_supervisor.port
        }
        
        return {
            "supervisors": [supervisor_info],
            "total_supervisors": 1,
            "available_supervisors": 1 if distributed_supervisor.status.value == "available" else 0
        }
    except Exception as e:
        logger.error(f"Error getting supervisor info: {e}")
        return {
            "supervisors": [],
            "total_supervisors": 0,
            "available_supervisors": 0,
            "error": str(e)
        }

@app.get("/system/stats")
async def get_system_stats():
    """Get overall system statistics"""
    try:
        session_stats = await state_manager.get_session_stats()
        supervisor_stats = await distributed_supervisor.get_stats()
        
        return {
            "sessions": session_stats,
            "supervisor": supervisor_stats,
            "agents": {
                "total": len(agent_registry.list_agents()),
                "active": len(agent_registry.list_active_agents())
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

async def cleanup_old_sessions():
    """Background task to cleanup old sessions"""
    try:
        cleaned = await state_manager.cleanup_expired_sessions()
        logger.info(f"Cleaned up {cleaned} expired sessions")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agents_available": len(agent_registry.list_active_agents()),
        "supervisor_status": distributed_supervisor.status.value
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 