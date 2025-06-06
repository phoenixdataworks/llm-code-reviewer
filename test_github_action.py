#!/usr/bin/env python3
"""
GitHub Action integration test for LLM Code Reviewer.
Tests the action.yml configuration and simulates the GitHub environment.
"""

import os
import sys
import yaml
import json
import tempfile
import subprocess
import time
from pathlib import Path

class GitHubActionTest:
    def __init__(self):
        self.test_results = {}
        self.github_workspace = Path.cwd()
        
    def test_action_yml_syntax(self):
        """Test that action.yml has valid syntax."""
        print("📄 Testing action.yml syntax...")
        
        try:
            with open('action.yml', 'r') as f:
                action_config = yaml.safe_load(f)
            
            # Check required fields
            required_fields = ['name', 'description', 'runs']
            for field in required_fields:
                if field not in action_config:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Check inputs
            if 'inputs' in action_config:
                inputs = action_config['inputs']
                required_inputs = ['GITHUB_TOKEN']
                for inp in required_inputs:
                    if inp not in inputs:
                        print(f"❌ Missing required input: {inp}")
                        return False
                    if 'required' not in inputs[inp] or not inputs[inp]['required']:
                        print(f"❌ Input {inp} should be required")
                        return False
            
            # Check runs configuration
            runs = action_config['runs']
            if runs.get('using') != 'composite':
                print(f"❌ Expected 'composite' action, got: {runs.get('using')}")
                return False
            
            if 'steps' not in runs:
                print("❌ No steps defined in runs")
                return False
            
            steps = runs['steps']
            expected_steps = [
                'Checkout repository',
                'Set up Python', 
                'Cache Python dependencies',
                'Install dependencies',
                'Run code review'
            ]
            
            step_names = [step.get('name', '') for step in steps]
            for expected in expected_steps:
                if not any(expected.lower() in name.lower() for name in step_names):
                    print(f"⚠️ Expected step not found: {expected}")
            
            print("✅ action.yml syntax is valid")
            return True
            
        except yaml.YAMLError as e:
            print(f"❌ YAML syntax error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error reading action.yml: {e}")
            return False
    
    def test_environment_simulation(self):
        """Test environment variable handling."""
        print("\n🌍 Testing environment simulation...")
        
        # Set up test environment variables
        test_env = {
            'GITHUB_TOKEN': 'test-token-123',
            'GITHUB_EVENT_NAME': 'pull_request',
            'GITHUB_WORKSPACE': str(self.github_workspace),
            'GITHUB_ACTION_PATH': str(self.github_workspace),
            'OPENAI_API_KEY': 'test-openai-key',
            'GEMINI_API_KEY': 'test-gemini-key',
            'PRIMARY_MODEL': 'openai',
            'HUMAN_LANGUAGE': 'en',
            'INPUT_EXCLUDE': '*.md,*.txt'
        }
        
        # Apply environment
        for key, value in test_env.items():
            os.environ[key] = value
        
        try:
            # Test config loading
            sys.path.insert(0, 'src')
            from src.core.config import Config
            
            # Verify environment variables are read correctly
            assert hasattr(Config, 'GITHUB_TOKEN'), "GITHUB_TOKEN not loaded"
            assert hasattr(Config, 'OPENAI_API_KEY'), "OPENAI_API_KEY not loaded"  
            assert hasattr(Config, 'PRIMARY_MODEL'), "PRIMARY_MODEL not loaded"
            
            print("✅ Environment variables loaded correctly")
            return True
            
        except Exception as e:
            print(f"❌ Environment simulation failed: {e}")
            return False
    
    def create_mock_pr_event(self):
        """Create a mock GitHub PR event file."""
        mock_event = {
            "action": "opened",
            "number": 123,
            "pull_request": {
                "number": 123,
                "title": "Test PR for optimization validation",
                "body": "This is a test PR to validate the optimized LLM Code Reviewer.",
                "head": {"sha": "abc123"},
                "base": {"sha": "def456"}
            },
            "repository": {
                "full_name": "test-owner/test-repo",
                "name": "test-repo",
                "owner": {"login": "test-owner"}
            }
        }
        
        # Create temporary event file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_event, f)
            return f.name
    
    def test_pr_event_processing(self):
        """Test PR event processing without making external API calls."""
        print("\n📋 Testing PR event processing...")
        
        try:
            # Create mock event file
            event_file = self.create_mock_pr_event()
            os.environ['GITHUB_EVENT_PATH'] = event_file
            
            # Test event parsing
            from src.services.github_service import GitHubService
            from src.core.models import PRDetails
            
            # Create a mock GitHub client (we'll skip actual API calls)
            class MockGitHubClient:
                def get_repo(self, repo_name):
                    return MockRepo()
            
            class MockRepo:
                def get_pull(self, pr_number):
                    return MockPR()
                    
                @property 
                def name(self):
                    return "test-repo"
            
            class MockPR:
                @property
                def title(self):
                    return "Test PR"
                    
                @property
                def body(self):
                    return "Test description"
            
            # Test with mock client
            github_service = GitHubService(MockGitHubClient())
            pr_details = github_service.get_pr_details(event_file)
            
            assert pr_details.owner == "test-owner"
            assert pr_details.repo == "test-repo"
            assert pr_details.pull_number == 123
            
            print("✅ PR event processing works correctly")
            
            # Clean up
            os.unlink(event_file)
            return True
            
        except Exception as e:
            print(f"❌ PR event processing failed: {e}")
            return False
    
    def test_dependency_installation_simulation(self):
        """Simulate the dependency installation process."""
        print("\n📦 Testing dependency installation simulation...")
        
        try:
            # Check if requirements.txt exists and is valid
            if not Path('requirements.txt').exists():
                print("❌ requirements.txt not found")
                return False
            
            with open('requirements.txt', 'r') as f:
                requirements = f.read()
            
            # Count pinned dependencies
            lines = [line.strip() for line in requirements.split('\n') 
                    if line.strip() and not line.startswith('#')]
            pinned_count = len([line for line in lines if '==' in line])
            
            if pinned_count < 15:
                print(f"⚠️ Only {pinned_count} pinned dependencies found")
            else:
                print(f"✅ {pinned_count} pinned dependencies found")
            
            # Check for problematic packages
            problematic = ['google-api-python-client', 'google-api-core']
            found_problematic = [pkg for pkg in problematic if pkg in requirements]
            
            if found_problematic:
                print(f"⚠️ Problematic packages found: {found_problematic}")
                return False
            
            print("✅ Requirements file is optimized")
            return True
            
        except Exception as e:
            print(f"❌ Dependency check failed: {e}")
            return False
    
    def test_cache_configuration(self):
        """Test GitHub Actions cache configuration."""
        print("\n💾 Testing cache configuration...")
        
        try:
            with open('action.yml', 'r') as f:
                action_config = yaml.safe_load(f)
            
            steps = action_config.get('runs', {}).get('steps', [])
            
            # Look for cache step
            cache_step = None
            for step in steps:
                if 'cache' in step.get('name', '').lower():
                    cache_step = step
                    break
            
            if not cache_step:
                print("❌ No cache step found")
                return False
            
            # Check cache step uses actions/cache@v4
            uses = cache_step.get('uses', '')
            if 'actions/cache@v4' not in uses:
                print(f"⚠️ Expected actions/cache@v4, found: {uses}")
            
            # Check cache configuration
            cache_with = cache_step.get('with', {})
            required_cache_fields = ['path', 'key']
            for field in required_cache_fields:
                if field not in cache_with:
                    print(f"❌ Missing cache field: {field}")
                    return False
            
            # Check key includes requirements.txt hash
            key = cache_with.get('key', '')
            if 'requirements.txt' not in key:
                print("⚠️ Cache key should include requirements.txt hash")
            
            print("✅ Cache configuration is correct")
            return True
            
        except Exception as e:
            print(f"❌ Cache configuration test failed: {e}")
            return False
    
    def run_integration_tests(self):
        """Run complete GitHub Action integration test suite."""
        print("🔧 GitHub Action Integration Test Suite")
        print("=" * 60)
        
        tests = [
            ("Action YAML Syntax", self.test_action_yml_syntax),
            ("Environment Simulation", self.test_environment_simulation),
            ("PR Event Processing", self.test_pr_event_processing),
            ("Dependency Configuration", self.test_dependency_installation_simulation),
            ("Cache Configuration", self.test_cache_configuration),
        ]
        
        passed = 0
        total_start = time.time()
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        
        total_time = time.time() - total_start
        
        print(f"\n{'='*60}")
        print(f"📊 Integration Test Results: {passed}/{len(tests)} tests passed")
        print(f"⏱️ Total test time: {total_time:.2f}s")
        
        if passed == len(tests):
            print("🎉 GitHub Action integration verified!")
            print("✅ Ready for deployment to GitHub Actions marketplace")
            return True
        else:
            print("⚠️ Some integration issues detected")
            return False

if __name__ == "__main__":
    tester = GitHubActionTest()
    success = tester.run_integration_tests()
    sys.exit(0 if success else 1) 