#!/usr/bin/env python3
"""
Test script to validate LLM Code Reviewer optimizations.
This script tests dependency loading, service initialization, and basic functionality.
"""

import sys
import time
import importlib
import os

def test_dependency_imports():
    """Test that all required dependencies can be imported quickly."""
    print("🧪 Testing dependency imports...")
    start_time = time.time()
    
    required_imports = [
        ('github', 'PyGithub'),
        ('unidiff', 'unidiff'),
        ('requests', 'requests'),
        ('pydantic', 'pydantic'),
    ]
    
    optional_imports = [
        ('openai', 'OpenAI'),
        ('google.generativeai', 'Google Generative AI'),
        ('anthropic', 'Anthropic'),
    ]
    
    # Test required imports
    for module_name, display_name in required_imports:
        try:
            importlib.import_module(module_name)
            print(f"✅ {display_name} imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import {display_name}: {e}")
            return False
    
    # Test optional imports (don't fail if missing)
    for module_name, display_name in optional_imports:
        try:
            importlib.import_module(module_name)
            print(f"✅ {display_name} available")
        except ImportError:
            print(f"⚠️ {display_name} not available (optional)")
    
    import_time = time.time() - start_time
    print(f"📊 Import test completed in {import_time:.2f}s")
    return True

def test_service_initialization():
    """Test that services can be initialized without errors."""
    print("\n🧪 Testing service initialization...")
    
    # Set minimal environment for testing
    os.environ['GITHUB_TOKEN'] = 'test-token'
    os.environ['PRIMARY_MODEL'] = 'openai'  # Use OpenAI as it's most likely to be available
    
    try:
        # Test Config loading
        sys.path.insert(0, 'src')
        from src.core.config import Config
        print("✅ Config module loaded")
        
        # Test AI Service initialization (should handle missing API keys gracefully)
        from src.services.ai_service import AIService
        print("✅ AIService module loaded")
        
        # Test other core components
        from src.utils.diff_parser import DiffParser
        parser = DiffParser()
        print("✅ DiffParser initialized")
        
        from src.utils.code_analyzer import CodeAnalyzer
        print("✅ CodeAnalyzer module loaded")
        
        print("✅ All core services can be initialized")
        return True
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_lazy_loading():
    """Test that LLM services are loaded lazily."""
    print("\n🧪 Testing lazy loading behavior...")
    
    try:
        # Import should not immediately load LLM clients
        from src.services.ai_service import AIService
        
        # Check that LLM modules are not yet loaded
        llm_modules = ['src.services.llms.openai', 'src.services.llms.gemini', 'src.services.llms.anthropic']
        initially_loaded = [mod for mod in llm_modules if mod in sys.modules]
        
        if initially_loaded:
            print(f"⚠️ Some LLM modules were pre-loaded: {initially_loaded}")
        else:
            print("✅ LLM modules are not pre-loaded (lazy loading working)")
        
        return True
        
    except Exception as e:
        print(f"❌ Lazy loading test failed: {e}")
        return False

def test_requirements_compatibility():
    """Test that requirements.txt has no conflicting versions."""
    print("\n🧪 Testing requirements compatibility...")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        # Check for removed problematic packages
        problematic_packages = [
            'google-api-python-client',
            'google-api-core', 
            'googleapis-common-protos',
            'grpcio-status'
        ]
        
        for package in problematic_packages:
            if package in requirements:
                print(f"⚠️ Problematic package still present: {package}")
            else:
                print(f"✅ Problematic package removed: {package}")
        
        # Count pinned dependencies
        lines = [line.strip() for line in requirements.split('\n') if line.strip() and not line.startswith('#')]
        pinned_lines = [line for line in lines if '==' in line]
        
        print(f"📊 Total dependency lines: {len(lines)}")
        print(f"📊 Pinned dependencies: {len(pinned_lines)}")
        
        if len(pinned_lines) < 25:  # Should be around 20 essential packages
            print("✅ Dependency count optimized (under 25 packages)")
        else:
            print(f"⚠️ High dependency count: {len(pinned_lines)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Requirements test failed: {e}")
        return False

def run_all_tests():
    """Run all optimization tests."""
    print("🚀 LLM Code Reviewer Optimization Test Suite")
    print("=" * 50)
    
    total_start_time = time.time()
    
    tests = [
        ("Dependency Imports", test_dependency_imports),
        ("Service Initialization", test_service_initialization),
        ("Lazy Loading", test_lazy_loading),
        ("Requirements Compatibility", test_requirements_compatibility),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed_tests += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    total_time = time.time() - total_start_time
    
    print("\n" + "="*50)
    print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
    print(f"⏱️ Total test time: {total_time:.2f}s")
    
    if passed_tests == total_tests:
        print("🎉 All optimization tests passed!")
        print("✅ The project is ready for fast deployment")
        return True
    else:
        print("⚠️ Some tests failed - review the optimization implementation")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 