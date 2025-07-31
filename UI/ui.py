
import streamlit as st
import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

# Streamlit app to interact with the FastAPI backend
st.title("AI Calendar Assistant 📅")

# Sidebar for system information
with st.sidebar:
    st.header("System Status")
    
    # Health check
    try:
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            st.success(f"✅ System: {health_data['status']}")
            st.info(f"Agents: {health_data['agents_available']}")
            st.info(f"Supervisor: {health_data['supervisor_status']}")
        else:
            st.error("❌ System: Unhealthy")
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
    
    # System stats
    try:
        stats_response = requests.get(f"{BASE_URL}/system/stats")
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            st.subheader("Statistics")
            if 'sessions' in stats_data:
                st.metric("Active Sessions", stats_data['sessions'].get('active_sessions', 0))
                st.metric("Total Sessions", stats_data['sessions'].get('total_sessions', 0))
            if 'agents' in stats_data:
                st.metric("Active Agents", stats_data['agents'].get('active', 0))
    except Exception as e:
        st.warning(f"Could not load stats: {e}")

# Streamed response emulator
def response_generator(response):
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{
            "role": "assistant",
            "content": "Hi there! I'm your AI Calendar Assistant. I can help you check, schedule, edit, or delete events from your calendar. How can I assist you today?"
        }]

# Initialize session ID
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time())}"

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])    

ipt = st.chat_input("Enter your message...")
if ipt:
    # Add user's message
    st.session_state.messages.append({"role": "user", "content": ipt})
    with st.chat_message("user"):
        st.markdown(ipt)

    # Send request to backend server
    try:
        response = requests.post(
            f"{BASE_URL}/chat_stream",
            json={
                "message": ipt,
                "session_id": st.session_state.session_id,
                "user_id": "streamlit_user"
            },
            stream=True,
            timeout=30
        )

        if response.status_code == 200:
            # Stream the response
            assistant_message = ""
            current_role = "assistant"
            
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        decoded_chunk = chunk.decode("utf-8").strip()
                        if decoded_chunk:
                            # Parse the response to extract agent and message
                            if ":" in decoded_chunk:
                                agent_part, message_part = decoded_chunk.split(":", 1)
                                agent_name = agent_part.strip()
                                message_content = message_part.strip()
                                
                                # Update the display with the agent name
                                display_text = f"**{agent_name}**: {message_content}"
                                assistant_message = display_text
                                
                                # Stream the response
                                for word in response_generator(display_text):
                                    message_placeholder.markdown(word)
                                    time.sleep(0.05)
                            else:
                                # Fallback for simple responses
                                assistant_message = decoded_chunk
                                for word in response_generator(decoded_chunk):
                                    message_placeholder.markdown(word)
                                    time.sleep(0.05)
                
                # Add to chat history
                st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        else:
            error_message = f"Error: {response.status_code} - {response.text}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            
    except requests.exceptions.RequestException as e:
        error_message = f"Connection error: {str(e)}"
        st.error(error_message)
        st.session_state.messages.append({"role": "assistant", "content": error_message})
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        st.error(error_message)
        st.session_state.messages.append({"role": "assistant", "content": error_message})

# Add a button to clear chat history
if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Chat history cleared. How can I help you today?"
    }]
    st.rerun()

# Add session information
with st.sidebar:
    st.subheader("Session Info")
    st.text(f"Session ID: {st.session_state.session_id}")
    st.text(f"Messages: {len(st.session_state.messages)}")

