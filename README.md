# 🗓️ Scalable Calendar Assistant

A distributed, scalable AI-powered calendar management system built with LangChain, LangGraph, and FastAPI. This system addresses the limitations of traditional fixed LangGraph architectures by implementing dynamic agent management, distributed state storage, and load balancing.

## 🚀 Features

### Core Capabilities
- **Calendar Management**: Check availability, schedule events, modify existing events, and delete events
- **Multi-Agent System**: Specialized agents for different calendar operations
- **Distributed Architecture**: Horizontal scaling with multiple supervisor instances
- **Real-time Processing**: Streaming responses for better user experience
- **Session Management**: Persistent conversation state across requests

### Scalability Features
- **Dynamic Agent Registry**: Add/remove agents at runtime without restarting
- **Redis State Management**: Distributed, scalable state storage
- **Load Balancing**: Multiple supervisors with automatic failover
- **Horizontal Scaling**: Add more instances to handle increased load
- **Fault Tolerance**: Automatic session reassignment and error recovery

## 🏗️ Architecture

### Components

1. **Agent Registry** (`agent_registry.py`)
   - Dynamic agent registration and management
   - Capability-based agent discovery
   - Runtime status monitoring

2. **State Manager** (`state_manager.py`)
   - Redis-based distributed state storage
   - Session persistence and cleanup
   - User session tracking

3. **Distributed Supervisor** (`distributed_supervisor.py`)
   - Load balancing across multiple supervisors
   - Capability-based request routing
   - Heartbeat monitoring and failover

4. **Scalable API** (`scalable_main.py`)
   - FastAPI-based REST API
   - Streaming responses
   - Health monitoring and statistics

### System Flow
```
User Request → Load Balancer → Supervisor → Agent Registry → Agent Execution → Response
```

## 📋 Prerequisites

- Python 3.9+
- Redis server
- Google Calendar API credentials
- OpenAI API key

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd smart-agent
```

### 2. Install Dependencies
```bash
# Install Python dependencies
pip3 install -r requirements_scalable.txt

# Install Redis (macOS)
brew install redis

# Or using Docker
docker run -d --name redis-calendar -p 6379:6379 redis:7-alpine
```

### 3. Set Up Google Calendar API
1. Create a project in Google Cloud Console
2. Enable Google Calendar API
3. Create credentials (OAuth 2.0 or Service Account)
4. Place credentials in `google_credentials/` directory

### 4. Configure Environment Variables
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
REDIS_URL=redis://localhost:6379
SUPERVISOR_ID=supervisor-1
LOG_LEVEL=INFO
```

## 🚀 Quick Start

### Option 1: Using the Startup Script
```bash
# Start everything automatically
python3 start_scalable.py
```

### Option 2: Manual Startup
```bash
# Start Redis
redis-server

# Start the scalable server
python3 scalable_main.py

# Start the UI (in another terminal)
cd UI
streamlit run ui.py
```

### Option 3: Docker Deployment
```bash
# Start with Docker Compose
docker-compose up -d
```

## 📊 API Endpoints

### Core Endpoints
- `GET /health` - System health check
- `POST /chat` - Process chat messages
- `POST /chat_stream` - Stream chat responses

### Management Endpoints
- `GET /supervisors` - List available supervisors
- `GET /agents` - List all agents
- `GET /agents/{agent_name}` - Get agent information
- `POST /agents/{agent_name}/status` - Update agent status

### Monitoring Endpoints
- `GET /system/stats` - System statistics
- `GET /sessions/{session_id}` - Session information
- `GET /sessions/user/{user_id}` - User sessions

## 🧪 Testing

### Run Test Suite
```bash
python3 test_scalable.py
```

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# List supervisors
curl http://localhost:8000/supervisors

# Send a chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Check my calendar for tomorrow", "session_id": "test-1", "user_id": "test-user"}'
```

## 🎯 Usage Examples

### Calendar Operations

1. **Check Availability**
   ```
   User: "Check my calendar for tomorrow"
   Response: "You are available tomorrow, August 1, 2025, as there are no events scheduled for that day."
   ```

2. **Schedule Event**
   ```
   User: "Schedule a meeting with John tomorrow at 2 PM"
   Response: "Event Created! Event Link: https://calendar.google.com/... Event ID: abc123"
   ```

3. **Modify Event**
   ```
   User: "Change my meeting with John to 3 PM"
   Response: "Event updated successfully. New time: 3:00 PM"
   ```

4. **Delete Event**
   ```
   User: "Cancel my meeting with John"
   Response: "Event cancelled successfully"
   ```

## 🔧 Configuration

### Agent Configuration
Agents are configured in `scalable_main.py`:
```python
calendar_metadata = AgentMetadata(
    name="calendar_checker_agent",
    description="Checks calendar availability and events",
    capabilities=["calendar", "availability_check"],
    status=AgentStatus.ACTIVE,
    version="1.0.0",
    dependencies=["google-calendar-api"],
    config={"timezone": "Asia/Colombo"}
)
```

### Supervisor Configuration
```python
distributed_supervisor = DistributedSupervisor(
    supervisor_id="main-supervisor",
    host="localhost",
    port=8000
)
```

### Redis Configuration
```python
state_manager = StateManager(
    redis_url="redis://localhost:6379",
    default_ttl=3600
)
```

## 📈 Scaling

### Horizontal Scaling
1. **Add More Supervisors**
   ```bash
   # Start additional supervisor instances
   SUPERVISOR_ID=supervisor-2 python3 scalable_main.py
   ```

2. **Docker Compose Scaling**
   ```bash
   # Scale to 3 instances
   docker-compose up --scale calendar-assistant=3
   ```

3. **Load Balancer Configuration**
   ```nginx
   upstream calendar_backend {
       server calendar-assistant-1:8000;
       server calendar-assistant-2:8000;
       server calendar-assistant-3:8000;
   }
   ```

### Performance Monitoring
```bash
# Check system stats
curl http://localhost:8000/system/stats

# Monitor Redis
redis-cli info

# Check supervisor status
curl http://localhost:8000/supervisors
```

## 🐛 Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Start Redis if not running
   brew services start redis
   ```

2. **Agent Not Available**
   ```bash
   # Check agent status
   curl http://localhost:8000/agents
   
   # Restart agent
   curl -X POST http://localhost:8000/agents/calendar_checker_agent/status \
     -H "Content-Type: application/json" \
     -d '{"status": "active"}'
   ```

3. **Session Issues**
   ```bash
   # Check session
   curl http://localhost:8000/sessions/{session_id}
   
   # Delete session
   curl -X DELETE http://localhost:8000/sessions/{session_id}
   ```

### Logs and Debugging
```bash
# Check server logs
tail -f logs/app.log

# Monitor Redis logs
tail -f /usr/local/var/log/redis.log

# Check Docker logs
docker-compose logs -f
```

## 🔄 Migration from Original Architecture

### Key Differences
1. **Fixed Graph → Dynamic Registry**: Agents can be added/removed at runtime
2. **File State → Redis State**: Scalable, distributed state management
3. **Single Supervisor → Distributed Supervisors**: Load balancing and failover

### Migration Steps
1. Install new dependencies: `pip install -r requirements_scalable.txt`
2. Set up Redis: `brew install redis && brew services start redis`
3. Update environment variables
4. Start new server: `python3 scalable_main.py`
5. Test endpoints: `python3 test_scalable.py`

## 📚 API Documentation

### Chat Request
```json
{
  "message": "Check my calendar for tomorrow",
  "session_id": "optional-session-id",
  "user_id": "optional-user-id"
}
```

### Chat Response
```json
{
  "response": "You are available tomorrow...",
  "session_id": "session-123",
  "agent": "calendar_checker_agent",
  "status": "success",
  "timestamp": "2024-01-01T12:00:00"
}
```

### System Stats
```json
{
  "sessions": {
    "total_sessions": 10,
    "active_sessions": 5,
    "completed_sessions": 3,
    "error_sessions": 2
  },
  "supervisor": {
    "supervisor_id": "supervisor-1",
    "status": "available",
    "load": 0.3,
    "current_sessions": 5
  },
  "agents": {
    "total": 4,
    "active": 4
  }
}
```

**Happy Calendar Management! 📅✨** 