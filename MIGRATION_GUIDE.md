# Migration Guide: From Fixed LangGraph to Scalable Architecture

This guide helps you migrate from the original fixed LangGraph architecture to the new scalable, distributed system.

## Overview of Changes

### Original Architecture Issues
1. **Fixed Graph Structure**: Agents were hardcoded in the graph
2. **File-based State**: Used `graph_state.json` for persistence
3. **Single Point of Failure**: One supervisor handled all requests

### New Scalable Architecture
1. **Dynamic Agent Registry**: Agents can be added/removed at runtime
2. **Redis State Management**: Scalable, distributed state storage
3. **Distributed Supervisors**: Multiple supervisors with load balancing

## Migration Steps

### Step 1: Install New Dependencies

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Or using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Install new Python dependencies
pip install -r requirements_scalable.txt
```

### Step 2: Environment Configuration

Create a `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_TTL=3600

# Supervisor Configuration
SUPERVISOR_ID=supervisor-1
SUPERVISOR_HOST=localhost
SUPERVISOR_PORT=8000
MAX_CONCURRENT_SESSIONS=50

# Logging
LOG_LEVEL=INFO

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
```

### Step 3: Update Agent Registration

Instead of hardcoded agents in the graph, agents are now registered dynamically:

```python
# Old way (in main.py)
builder.add_node("calendar_checker_agent", calendar_checker_agent_node)

# New way (in scalable_main.py)
agent_registry.register_agent("calendar_checker_agent", calendar_checker_agent, metadata)
```

### Step 4: State Management Migration

**Old State Management:**
```python
# File-based state
with open("graph_state.json", "r") as json_file:
    current_state = json.load(json_file)
```

**New State Management:**
```python
# Redis-based state
session = await state_manager.get_session(session_id)
if not session:
    session = await state_manager.create_session(session_id, user_id, initial_state)
```

### Step 5: API Endpoint Changes

**Old Endpoints:**
- `/chat` - Single endpoint for all requests
- File-based session management

**New Endpoints:**
- `/chat` - Enhanced with session management
- `/sessions/{session_id}` - Session information
- `/agents` - Agent management
- `/system/stats` - System monitoring
- `/health` - Health checks

### Step 6: Deployment Changes

**Old Deployment:**
```bash
python main.py
```

**New Deployment:**
```bash
# Single instance
python scalable_main.py

# Or using Docker Compose (recommended)
docker-compose up -d
```

## Configuration Examples

### Single Instance Setup

```python
# scalable_main.py
from state_manager import state_manager
from distributed_supervisor import distributed_supervisor

# Initialize with custom Redis URL
state_manager = StateManager(redis_url="redis://localhost:6379")
distributed_supervisor = DistributedSupervisor(supervisor_id="main-supervisor")
```

### Multi-Instance Setup

```yaml
# docker-compose.yml
services:
  calendar-assistant-1:
    environment:
      - SUPERVISOR_ID=supervisor-1
      - REDIS_URL=redis://redis:6379
  
  calendar-assistant-2:
    environment:
      - SUPERVISOR_ID=supervisor-2
      - REDIS_URL=redis://redis:6379
```

## Testing the Migration

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "agents_available": 4,
  "supervisor_status": "available"
}
```

### 2. Agent Registration Test
```bash
curl http://localhost:8000/agents
```

Expected response:
```json
{
  "agents": {
    "calendar_checker_agent": {
      "description": "Checks calendar availability and events",
      "capabilities": ["calendar", "availability_check"],
      "status": "active",
      "version": "1.0.0"
    }
  }
}
```

### 3. Chat Test
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Check my calendar for tomorrow"}'
```

## Monitoring and Observability

### System Statistics
```bash
curl http://localhost:8000/system/stats
```

### Session Management
```bash
# Get session info
curl http://localhost:8000/sessions/{session_id}

# Get user sessions
curl http://localhost:8000/sessions/user/{user_id}
```

## Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Start Redis if not running
   sudo systemctl start redis
   ```

2. **Agent Not Available**
   ```bash
   # Check agent status
   curl http://localhost:8000/agents
   
   # Restart agent
   curl -X POST http://localhost:8000/agents/{agent_name}/status \
     -H "Content-Type: application/json" \
     -d '{"status": "active"}'
   ```

3. **Session Not Found**
   ```bash
   # Check session
   curl http://localhost:8000/sessions/{session_id}
   
   # Create new session
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello", "session_id": "new-session-id"}'
   ```

## Performance Improvements

### Before Migration
- Single supervisor bottleneck
- File I/O for state management
- Fixed agent configuration

### After Migration
- Multiple supervisors with load balancing
- Redis for fast state access
- Dynamic agent management
- Horizontal scaling capability

## Rollback Plan

If you need to rollback to the original architecture:

1. **Stop new services:**
   ```bash
   docker-compose down
   ```

2. **Restore original main.py:**
   ```bash
   cp main.py.backup main.py
   ```

3. **Restart original service:**
   ```bash
   python main.py
   ```

## Next Steps

1. **Monitor Performance**: Use the new statistics endpoints
2. **Scale Horizontally**: Add more supervisor instances
3. **Add New Agents**: Use the agent registry to add new capabilities
4. **Implement Caching**: Add Redis caching for frequently accessed data
5. **Add Monitoring**: Integrate with monitoring tools like Prometheus

## Support

For issues during migration:
1. Check the logs: `docker-compose logs`
2. Verify Redis connection: `redis-cli ping`
3. Test individual components: Use the health check endpoints
4. Review configuration: Ensure all environment variables are set correctly 