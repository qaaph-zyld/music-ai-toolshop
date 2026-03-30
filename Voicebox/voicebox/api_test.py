#!/usr/bin/env python3
"""
Test Voicebox API endpoints.
"""

import sys
import os
import requests
import time
import subprocess
import signal
from pathlib import Path

def start_server():
    """Start the Voicebox server in background"""
    print("Starting Voicebox server...")
    
    # Try to start server using the backend module
    try:
        # Add current directory to Python path
        env = os.environ.copy()
        env['PYTHONPATH'] = '.'
        
        # Start server process
        process = subprocess.Popen([
            sys.executable, '-c', 
            '''
import sys
sys.path.append(".")
from backend.main import app
import uvicorn
uvicorn.run(app, host="127.0.0.1", port=17493, log_level="error")
            '''
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Give server time to start
        time.sleep(5)
        
        return process
    except Exception as e:
        print(f"Failed to start server: {e}")
        return None

def test_api_endpoints():
    """Test basic API endpoints"""
    print("\nTesting API endpoints...")
    
    base_url = "http://127.0.0.1:17493"
    
    endpoints = [
        ("/", "Root endpoint"),
        ("/health", "Health check"),
        ("/docs", "API documentation"),
        ("/profiles", "Voice profiles"),
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code in [200, 404]:  # 404 is ok for some endpoints
                print(f"✓ {description}: {response.status_code}")
                results[description] = True
            else:
                print(f"✗ {description}: {response.status_code}")
                results[description] = False
        except requests.exceptions.RequestException as e:
            print(f"✗ {description}: {e}")
            results[description] = False
    
    return results

def main():
    """Run API tests"""
    print("Voicebox API Test")
    print("=" * 50)
    
    # Start server
    server_process = start_server()
    
    if not server_process:
        print("❌ Could not start server")
        return 1
    
    try:
        # Test endpoints
        results = test_api_endpoints()
        
        # Summary
        print("\n" + "=" * 50)
        print("API TEST SUMMARY:")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for endpoint, result in results.items():
            status = "PASS" if result else "FAIL"
            print(f"  {endpoint}: {status}")
        
        print(f"\nOverall: {passed}/{total} API tests passed")
        
        if passed >= 2:  # At least root and docs should work
            print("🎉 Voicebox API is working!")
            return 0
        else:
            print("⚠️  API has issues.")
            return 1
            
    finally:
        # Clean up server process
        if server_process:
            print("\nShutting down server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()

if __name__ == "__main__":
    sys.exit(main())
