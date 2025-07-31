#!/usr/bin/env python3
"""
Startup script for the scalable calendar assistant
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print(f"❌ Redis is not running: {e}")
        return False

def start_redis():
    """Start Redis if not running"""
    if not check_redis():
        print("🚀 Starting Redis...")
        try:
            # Try to start Redis using Docker
            subprocess.run([
                "docker", "run", "-d", 
                "--name", "redis-calendar", 
                "-p", "6379:6379", 
                "redis:7-alpine"
            ], check=True)
            time.sleep(3)  # Wait for Redis to start
            if check_redis():
                print("✅ Redis started successfully")
                return True
        except subprocess.CalledProcessError:
            print("⚠️  Could not start Redis with Docker")
            print("Please install Redis manually:")
            print("  Ubuntu/Debian: sudo apt-get install redis-server")
            print("  macOS: brew install redis")
            print("  Or run: docker run -d --name redis-calendar -p 6379:6379 redis:7-alpine")
            return False
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'fastapi', 'uvicorn', 'redis', 'requests', 
        'langchain', 'langgraph', 'openai'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install them with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All dependencies are installed")
    return True

def start_server():
    """Start the scalable server"""
    print("🚀 Starting scalable calendar assistant...")
    
    try:
        # Start the server
        process = subprocess.Popen([
            sys.executable, "scalable_main.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for the server to start
        time.sleep(5)
        
        # Check if server is responding
        try:
            response = requests.get("http://localhost:8000/health", timeout=10)
            if response.status_code == 200:
                print("✅ Server is running at http://localhost:8000")
                return process
            else:
                print(f"❌ Server responded with status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Server is not responding: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def run_tests():
    """Run basic tests"""
    print("🧪 Running basic tests...")
    
    try:
        result = subprocess.run([
            sys.executable, "test_scalable.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Tests passed")
            return True
        else:
            print(f"❌ Tests failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Could not run tests: {e}")
        return False

def main():
    """Main startup function"""
    print("🎯 Starting Scalable Calendar Assistant")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Start Redis
    if not start_redis():
        return False
    
    # Start server
    server_process = start_server()
    if not server_process:
        return False
    
    print("\n🎉 Setup complete!")
    print("=" * 50)
    print("📊 Available endpoints:")
    print("  - Health: http://localhost:8000/health")
    print("  - Chat: http://localhost:8000/chat")
    print("  - Supervisors: http://localhost:8000/supervisors")
    print("  - Agents: http://localhost:8000/agents")
    print("  - System Stats: http://localhost:8000/system/stats")
    print("\n🌐 UI: http://localhost:8501")
    print("\n📝 To start the UI, run:")
    print("  streamlit run UI/ui.py")
    print("\n🛑 To stop the server, press Ctrl+C")
    
    try:
        # Keep the server running
        server_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()
        print("✅ Server stopped")

if __name__ == "__main__":
    main() 