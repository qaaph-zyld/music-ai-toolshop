#!/usr/bin/env python3
"""
Simple test to verify Voicebox backend structure and dependencies.
"""

import sys
import os

def test_basic_imports():
    """Test basic dependencies"""
    print("Testing basic imports...")
    
    imports = [
        ("torch", "PyTorch"),
        ("transformers", "Transformers"),
        ("fastapi", "FastAPI"),
        ("qwen_tts", "Qwen-TTS"),
        ("librosa", "Librosa"),
        ("soundfile", "SoundFile"),
        ("sqlalchemy", "SQLAlchemy"),
    ]
    
    results = {}
    for module_name, display_name in imports:
        try:
            module = __import__(module_name)
            if hasattr(module, '__version__'):
                version = module.__version__
            else:
                version = "unknown"
            print(f"✓ {display_name}: {version}")
            results[display_name] = True
        except ImportError as e:
            print(f"✗ {display_name}: {e}")
            results[display_name] = False
    
    return results

def test_backend_structure():
    """Test backend file structure"""
    print("\nTesting backend structure...")
    
    required_files = [
        "backend/main.py",
        "backend/models.py", 
        "backend/database.py",
        "backend/profiles.py",
        "backend/tts.py",
        "backend/backends/__init__.py",
        "backend/backends/pytorch_backend.py",
        "backend/utils/__init__.py",
    ]
    
    results = {}
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
            results[file_path] = True
        else:
            print(f"✗ {file_path}")
            results[file_path] = False
    
    return results

def test_qwen_tts_availability():
    """Test Qwen-TTS components"""
    print("\nTesting Qwen-TTS components...")
    
    try:
        from qwen_tts import Qwen3TTSModel, Qwen3TTSTokenizer, VoiceClonePromptItem
        print("✓ Qwen3TTSModel available")
        print("✓ Qwen3TTSTokenizer available") 
        print("✓ VoiceClonePromptItem available")
        return True
    except ImportError as e:
        print(f"✗ Qwen-TTS components: {e}")
        return False

def main():
    """Run all tests"""
    print("Voicebox Backend Test")
    print("=" * 50)
    
    # Test basic imports
    import_results = test_basic_imports()
    
    # Test backend structure
    structure_results = test_backend_structure()
    
    # Test Qwen-TTS
    qwen_result = test_qwen_tts_availability()
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    
    import_passed = sum(1 for result in import_results.values() if result)
    import_total = len(import_results)
    print(f"Imports: {import_passed}/{import_total} passed")
    
    structure_passed = sum(1 for result in structure_results.values() if result)
    structure_total = len(structure_results)
    print(f"Structure: {structure_passed}/{structure_total} passed")
    
    print(f"Qwen-TTS: {'PASS' if qwen_result else 'FAIL'}")
    
    total_passed = import_passed + structure_passed + (1 if qwen_result else 0)
    total_tests = import_total + structure_total + 1
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 Voicebox backend is properly configured!")
        return 0
    else:
        print("⚠️  Some components are missing or misconfigured.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
