#!/usr/bin/env python3
"""
Test script for Neuravox REST API
Demonstrates basic API usage including authentication
"""

import asyncio
import requests
import json
from pathlib import Path


API_BASE = "http://localhost:8000/api/v1"


def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    
    response = requests.get(f"{API_BASE}/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Health check passed: {data['status']}")
        print(f"   Database: {data['database']}")
        print(f"   Workspace: {data['workspace']}")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False


def test_create_api_key():
    """Test API key creation"""
    print("\n🔑 Testing API key creation...")
    
    payload = {
        "name": "Test API Key",
        "user_id": "test_user",
        "rate_limit_per_minute": 100
    }
    
    response = requests.post(f"{API_BASE}/auth/keys", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        api_key = data["api_key"]
        print(f"✅ API key created successfully")
        print(f"   Key ID: {data['key_info']['id']}")
        print(f"   User ID: {data['key_info']['user_id']}")
        print(f"   Rate limit: {data['key_info']['rate_limit_per_minute']}/min")
        return api_key
    else:
        print(f"❌ API key creation failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def test_authenticated_request(api_key):
    """Test authenticated request"""
    print("\n🔐 Testing authenticated request...")
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.get(f"{API_BASE}/auth/me", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Authentication successful")
        print(f"   User ID: {data['user_id']}")
        print(f"   Key name: {data['name']}")
        return True
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_configuration():
    """Test configuration endpoint"""
    print("\n⚙️  Testing configuration...")
    
    response = requests.get(f"{API_BASE}/config")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Configuration retrieved successfully")
        print(f"   Workspace: {data['workspace']}")
        print(f"   Available models: {len(data['models'])}")
        for model in data['models']:
            status = "✅" if model['available'] else "❌"
            print(f"     {status} {model['name']} ({model['key']})")
        return True
    else:
        print(f"❌ Configuration retrieval failed: {response.status_code}")
        return False


def test_file_operations(api_key):
    """Test file operations"""
    print("\n📁 Testing file operations...")
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # List files
    response = requests.get(f"{API_BASE}/files", headers=headers)
    
    if response.status_code == 200:
        files = response.json()
        print(f"✅ File listing successful")
        print(f"   Files found: {len(files)}")
        return True
    else:
        print(f"❌ File listing failed: {response.status_code}")
        return False


def test_job_operations(api_key):
    """Test job operations"""
    print("\n⚙️  Testing job operations...")
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # List jobs
    response = requests.get(f"{API_BASE}/jobs", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Job listing successful")
        print(f"   Jobs found: {data['total']}")
        return True
    else:
        print(f"❌ Job listing failed: {response.status_code}")
        return False


def main():
    """Run all API tests"""
    print("🚀 Starting Neuravox API Tests")
    print("=" * 50)
    
    # Test basic health
    if not test_health_check():
        print("\n❌ Basic health check failed. Is the API server running?")
        print("   Start it with: neuravox serve")
        return
    
    # Test API key creation
    api_key = test_create_api_key()
    if not api_key:
        print("\n❌ Cannot continue without API key")
        return
    
    # Test authentication
    if not test_authenticated_request(api_key):
        print("\n❌ Authentication test failed")
        return
    
    # Test configuration
    test_configuration()
    
    # Test file operations
    test_file_operations(api_key)
    
    # Test job operations
    test_job_operations(api_key)
    
    print("\n" + "=" * 50)
    print("🎉 API tests completed!")
    print(f"🔑 Your test API key: {api_key}")
    print("\n📖 API Documentation: http://localhost:8000/api/docs")


if __name__ == "__main__":
    main()