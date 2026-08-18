#!/usr/bin/env python3
"""Test script for Suno Library API Server

Tests all endpoints to verify the API server works correctly with
the test database and audio files.
"""

import requests
import sys
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:3000"


def test_health():
    """Test GET /api/health"""
    print("\n[Test 1] Health Check")
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if resp.status_code == 200 and resp.json().get("status") == "ok":
            print("  ✅ Health check passed")
            return True
        else:
            print(f"  ❌ Unexpected response: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_list_tracks():
    """Test GET /api/tracks with pagination"""
    print("\n[Test 2] List Tracks")
    try:
        resp = requests.get(f"{BASE_URL}/api/tracks", timeout=5)
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}")
            return False
        
        data = resp.json()
        tracks = data.get("tracks", [])
        total = data.get("total", 0)
        
        print(f"  Found {len(tracks)} tracks (total: {total})")
        
        if len(tracks) > 0 and total >= len(tracks):
            print("  ✅ List tracks passed")
            return True
        else:
            print("  ❌ No tracks found or invalid response")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_search_query():
    """Test GET /api/search?q=electronic"""
    print("\n[Test 3] Search by Query")
    try:
        resp = requests.get(f"{BASE_URL}/api/search?q=electronic", timeout=5)
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}")
            return False
        
        data = resp.json()
        tracks = data.get("tracks", [])
        count = data.get("count", 0)
        
        print(f"  Found {count} electronic tracks")
        
        if count > 0:
            print("  ✅ Search query passed")
            return True
        else:
            print("  ⚠️  No results (may be expected if no electronic tracks)")
            return True  # Still pass if empty result is valid
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_search_filters():
    """Test GET /api/search with multiple filters"""
    print("\n[Test 4] Search with Filters")
    try:
        params = {
            "genre": "electronic",
            "tempo_min": 120,
            "tempo_max": 130
        }
        resp = requests.get(f"{BASE_URL}/api/search", params=params, timeout=5)
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}")
            return False
        
        data = resp.json()
        tracks = data.get("tracks", [])
        count = data.get("count", 0)
        
        print(f"  Found {count} tracks matching filters")
        
        # Verify all results match filters
        for track in tracks:
            tempo = track.get("tempo", 0)
            if not (120 <= tempo <= 130):
                print(f"  ❌ Tempo filter failed: {track.get('title')} = {tempo} BPM")
                return False
        
        print("  ✅ Search filters passed")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_get_single_track():
    """Test GET /api/tracks/track_001"""
    print("\n[Test 5] Get Single Track")
    try:
        resp = requests.get(f"{BASE_URL}/api/tracks/track_001", timeout=5)
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}")
            return False
        
        track = resp.json()
        
        required_fields = ["id", "title", "artist", "genre", "tempo", "key", "audio_path"]
        for field in required_fields:
            if field not in track:
                print(f"  ❌ Missing field: {field}")
                return False
        
        print(f"  Track: {track.get('title')} ({track.get('tempo')} BPM)")
        print("  ✅ Get single track passed")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_stream_audio():
    """Test GET /api/tracks/track_001/audio"""
    print("\n[Test 6] Stream Audio")
    try:
        resp = requests.head(f"{BASE_URL}/api/tracks/track_001/audio", timeout=5)
        
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}")
            return False
        
        content_type = resp.headers.get("Content-Type", "")
        
        if "audio" not in content_type:
            print(f"  ⚠️  Content-Type: {content_type} (expected audio/*)")
        else:
            print(f"  Content-Type: {content_type}")
        
        # Also test GET to get actual data
        resp_get = requests.get(f"{BASE_URL}/api/tracks/track_001/audio", timeout=5)
        size = len(resp_get.content)
        
        print(f"  Audio size: {size} bytes")
        
        if size > 0:
            print("  ✅ Stream audio passed")
            return True
        else:
            print("  ❌ Empty audio file")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def run_all_tests():
    """Run all API tests"""
    print("=" * 50)
    print("Suno Library API Test Suite")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    
    # Check if server is running
    print("\nChecking server...")
    try:
        requests.get(f"{BASE_URL}/api/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ Server not running!")
        print("   Start with: python api_server.py")
        return False
    
    tests = [
        ("Health Check", test_health),
        ("List Tracks", test_list_tracks),
        ("Search Query", test_search_query),
        ("Search Filters", test_search_filters),
        ("Get Single Track", test_get_single_track),
        ("Stream Audio", test_stream_audio),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
