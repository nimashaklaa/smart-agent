
import streamlit as st
import requests
import time

BASE_URL = "http://127.0.0.1:8000"

# Streamlit app to interact with the FastAPI backend
st.title("AI Calendar Assistant 📅")

# Streamed response emulator
def response_generator(response):
    for word in response.split():
        yield word + " "
        time.sleep(0.1)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{
            "role": "assistant",
            "content": "Hi there! I'm your AI Calendar Assistant. I can help you check, schedule, edit, or delete events from your calendar. How can I assist you today?"
        }]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])    

ipt = st.chat_input("Enter_Input")
if ipt:
    # Add user's message
    st.session_state.messages.append({"role": "user", "content": ipt})
    with st.chat_message("user"):
        st.markdown(ipt)

    # Send request to backend server
    response = requests.post(
        f"{BASE_URL}/chat_stream/",
        json={"message": ipt},
        stream=True
    )

    # Stream the response and detect assistant roles
    for chunk in response.iter_content(chunk_size=1024):
        decoded_chunk = chunk.decode("utf-8")
        print(decoded_chunk)
        if chunk:
            decoded_chunk = chunk.decode("utf-8")
            #assistant_message += decoded_chunk
            assistant_message = decoded_chunk
            assistant_streaming_message= ""

            if "chatbot_supervisor" in assistant_message:
                    current_role = "chatbot_supervisor"
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        for word in response_generator(decoded_chunk):
                              assistant_streaming_message += word 
                              print(assistant_streaming_message)
                              message_placeholder.markdown(assistant_streaming_message)

            elif "calendar_checker_agent" in assistant_message:
                    current_role = "calendar_checker_agent"
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        for word in response_generator(decoded_chunk):
                              assistant_streaming_message += word 
                              print(assistant_streaming_message)
                              message_placeholder.markdown(assistant_streaming_message)

            elif "event_scheduler_agent" in assistant_message:
                    current_role = "event_scheduler_agent"
                    with st.chat_message("assistant"):
                            message_placeholder = st.empty()
                            for word in response_generator(decoded_chunk):
                                assistant_streaming_message += word 
                                print(assistant_streaming_message)
                                message_placeholder.markdown(assistant_streaming_message)

            elif "event_remover_agent" in assistant_message:
                    current_role = "event_remover_agent"
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        for word in response_generator(decoded_chunk):
                              assistant_streaming_message += word 
                              print(assistant_streaming_message)
                              message_placeholder.markdown(assistant_streaming_message)

            elif "event_modifier_agent" in assistant_message:
                    current_role = "event_modifier_agent"
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        for word in response_generator(decoded_chunk):
                              assistant_streaming_message += word 
                              print(assistant_streaming_message)
                              message_placeholder.markdown(assistant_streaming_message)

            st.session_state.messages.append({"role": "assistant", "content": assistant_message.strip()})

