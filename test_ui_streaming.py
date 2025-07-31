#!/usr/bin/env python3
"""
Test script to verify UI streaming functionality
"""

import requests
import json

def test_streaming():
    """Test the streaming endpoint directly"""
    print("Testing streaming endpoint...")
    
    try:
        response = requests.post(
            "http://localhost:8000/chat_stream",
            json={
                "message": "Check my calendar for tomorrow",
                "session_id": "test-streaming",
                "user_id": "test-user"
            },
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Streaming response received:")
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    decoded_chunk = chunk.decode("utf-8").strip()
                    if decoded_chunk:
                        print(f"  Chunk: {decoded_chunk}")
            print("✅ Streaming test completed")
        else:
            print(f"❌ Streaming failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Streaming test error: {e}")

def test_regular_chat():
    """Test the regular chat endpoint"""
    print("Testing regular chat endpoint...")
    
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "message": "Check my calendar for tomorrow",
                "session_id": "test-regular",
                "user_id": "test-user"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Regular chat response:")
            print(f"  Response: {data.get('response', 'No response')}")
            print(f"  Agent: {data.get('agent', 'Unknown')}")
            print(f"  Status: {data.get('status', 'Unknown')}")
        else:
            print(f"❌ Regular chat failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Regular chat test error: {e}")

if __name__ == "__main__":
    print("🧪 Testing UI Streaming Functionality")
    print("=" * 50)
    
    test_streaming()
    print()
    test_regular_chat()
    
    print("\n" + "=" * 50)
    print("📝 Instructions:")
    print("1. Make sure the server is running: python3 scalable_main.py")
    print("2. Start the UI: cd UI && streamlit run ui.py")
    print("3. Test with a message like 'Check my calendar for tomorrow'")
    print("4. Enable debug mode in the sidebar to see streaming details") 