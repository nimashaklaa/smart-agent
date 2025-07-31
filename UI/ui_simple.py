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
    
    # Debug mode toggle
    debug_mode = st.checkbox("Debug Mode", value=False)
    
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
        # Use regular chat endpoint instead of streaming for better reliability
        response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "message": ipt,
                "session_id": st.session_state.session_id,
                "user_id": "streamlit_user"
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            
            # Extract the response and agent information
            response_text = data.get('response', 'No response received')
            agent_name = data.get('agent', 'unknown')
            
            # Format the response with agent name
            if agent_name != 'unknown':
                formatted_response = f"**{agent_name}**: {response_text}"
            else:
                formatted_response = response_text
            
            # Display the response
            with st.chat_message("assistant"):
                st.markdown(formatted_response)
            
            # Add to chat history
            st.session_state.messages.append({"role": "assistant", "content": formatted_response})
            
            if debug_mode:
                st.sidebar.text(f"Debug: Response received from {agent_name}")
                st.sidebar.text(f"Debug: Response: {response_text}")
                
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

# Add a test button for debugging
if st.sidebar.button("Test Connection"):
    try:
        test_response = requests.get(f"{BASE_URL}/health")
        if test_response.status_code == 200:
            st.sidebar.success("✅ Connection successful")
        else:
            st.sidebar.error("❌ Connection failed")
    except Exception as e:
        st.sidebar.error(f"❌ Connection error: {e}") 