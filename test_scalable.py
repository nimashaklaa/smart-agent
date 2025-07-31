#!/usr/bin/env python3
"""
Test script for the scalable calendar assistant
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_supervisors():
    """Test supervisors endpoint"""
    print("Testing supervisors endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/supervisors")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Supervisors endpoint: {data}")
            return True
        else:
            print(f"❌ Supervisors endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Supervisors endpoint error: {e}")
        return False

def test_agents():
    """Test agents endpoint"""
    print("Testing agents endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/agents")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Agents endpoint: {data}")
            return True
        else:
            print(f"❌ Agents endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Agents endpoint error: {e}")
        return False

def test_chat():
    """Test chat endpoint"""
    print("Testing chat endpoint...")
    try:
        chat_data = {
            "message": "Check my calendar for tomorrow",
            "session_id": "test-session-1",
            "user_id": "test-user"
        }
        
        response = requests.post(f"{BASE_URL}/chat", json=chat_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat endpoint: {data}")
            return True
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat endpoint error: {e}")
        return False

def test_system_stats():
    """Test system stats endpoint"""
    print("Testing system stats endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/system/stats")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System stats: {data}")
            return True
        else:
            print(f"❌ System stats failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ System stats error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Scalable Calendar Assistant")
    print("=" * 50)
    
    tests = [
        test_health,
        test_supervisors,
        test_agents,
        test_chat,
        test_system_stats
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The scalable architecture is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main() 