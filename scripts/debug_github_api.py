#!/usr/bin/env python3
"""
GitHub API Debug Tool for LLM Code Reviewer
Helps diagnose issues with fetching PR diffs from GitHub API.
"""

import os
import sys
import requests
import json
from datetime import datetime

def check_github_token():
    """Check if GitHub token is properly configured and has correct permissions."""
    token = os.environ.get('GITHUB_TOKEN')
    
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        return False
    
    if not token.startswith(('ghp_', 'gho_', 'ghs_', 'ghu_')):
        print("⚠️ Token format looks unusual (should start with ghp_, gho_, ghs_, or ghu_)")
    
    # Test token validity
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'LLM-Code-Reviewer-Debug/1.0'
    }
    
    try:
        response = requests.get('https://api.github.com/user', headers=headers)
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Token is valid for user: {user_info.get('login', 'Unknown')}")
            
            # Check rate limits
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'Unknown')
            rate_limit_reset = response.headers.get('X-RateLimit-Reset', 'Unknown')
            
            if rate_limit_reset != 'Unknown':
                reset_time = datetime.fromtimestamp(int(rate_limit_reset))
                print(f"📊 Rate limit remaining: {rate_limit_remaining}")
                print(f"⏰ Rate limit resets at: {reset_time}")
            
            return True
            
        elif response.status_code == 401:
            print("❌ Token is invalid or expired")
            print(f"🔍 Response: {response.text}")
            return False
            
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"🔍 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking token: {e}")
        return False

def test_pr_access(owner, repo, pr_number):
    """Test if we can access the specific PR."""
    token = os.environ.get('GITHUB_TOKEN')
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'LLM-Code-Reviewer-Debug/1.0'
    }
    
    # Test PR info access
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    
    try:
        print(f"🔍 Testing PR access: {pr_url}")
        response = requests.get(pr_url, headers=headers)
        
        if response.status_code == 200:
            pr_data = response.json()
            print(f"✅ PR accessible: #{pr_data['number']} - {pr_data['title']}")
            print(f"📊 PR stats: +{pr_data['additions']} -{pr_data['deletions']} changes")
            print(f"📁 Files changed: {pr_data['changed_files']}")
            
            # Check if PR is too large
            if pr_data['changed_files'] > 300:
                print("⚠️ Large PR: >300 files changed - may hit GitHub API limits")
            
            if pr_data['additions'] + pr_data['deletions'] > 50000:
                print("⚠️ Large diff: >50k lines changed - may hit size limits")
                
            return True
            
        elif response.status_code == 404:
            print(f"❌ PR #{pr_number} not found in {owner}/{repo}")
            print("💡 Check if PR number is correct and repository exists")
            return False
            
        elif response.status_code == 403:
            print(f"❌ Access denied to {owner}/{repo}")
            print("💡 Token might not have access to this repository")
            return False
            
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            print(f"🔍 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing PR: {e}")
        return False

def test_diff_fetch(owner, repo, pr_number):
    """Test fetching the diff directly."""
    token = os.environ.get('GITHUB_TOKEN')
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3.diff',
        'User-Agent': 'LLM-Code-Reviewer-Debug/1.0'
    }
    
    diff_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}.diff"
    
    try:
        print(f"🔍 Testing diff fetch: {diff_url}")
        response = requests.get(diff_url, headers=headers, timeout=30)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📏 Response size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            diff_text = response.text
            if diff_text.strip():
                lines_count = len(diff_text.splitlines())
                print(f"✅ Diff fetched successfully: {lines_count} lines")
                
                # Show sample of diff (first few lines)
                sample_lines = diff_text.splitlines()[:10]
                print("📝 Diff sample (first 10 lines):")
                for i, line in enumerate(sample_lines, 1):
                    print(f"  {i:2d}: {line[:80]}{'...' if len(line) > 80 else ''}")
                
                return True
            else:
                print("⚠️ Diff response was empty")
                return False
                
        elif response.status_code == 422:
            print("❌ Diff too large (422 Unprocessable Entity)")
            print("💡 Use PyGithub fallback method for large PRs")
            return False
            
        else:
            print(f"❌ Failed to fetch diff: {response.status_code}")
            print(f"🔍 Response: {response.text[:500]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (30 seconds)")
        print("💡 PR diff might be too large")
        return False
        
    except Exception as e:
        print(f"❌ Error fetching diff: {e}")
        return False

def run_diagnostics(owner=None, repo=None, pr_number=None):
    """Run comprehensive GitHub API diagnostics."""
    print("🔍 GitHub API Diagnostic Tool for LLM Code Reviewer")
    print("=" * 60)
    
    # Step 1: Check token
    print("\n1️⃣ Checking GitHub Token...")
    token_ok = check_github_token()
    
    if not token_ok:
        print("\n❌ Token issues detected. Please fix before continuing.")
        return False
    
    # Step 2: Test PR access (if PR details provided)
    if owner and repo and pr_number:
        print(f"\n2️⃣ Testing PR Access ({owner}/{repo}#{pr_number})...")
        pr_ok = test_pr_access(owner, repo, pr_number)
        
        if not pr_ok:
            print("\n❌ PR access issues detected.")
            return False
        
        # Step 3: Test diff fetch
        print(f"\n3️⃣ Testing Diff Fetch...")
        diff_ok = test_diff_fetch(owner, repo, pr_number)
        
        if not diff_ok:
            print("\n❌ Diff fetch issues detected.")
            print("💡 The enhanced GitHub service will use PyGithub fallback")
            return False
        
        print("\n✅ All tests passed! GitHub API is working correctly.")
        return True
    
    else:
        print("\n2️⃣ Skipping PR-specific tests (no PR details provided)")
        print("💡 To test specific PR, run with: owner repo pr_number")
        return token_ok

def main():
    """Main entry point."""
    if len(sys.argv) == 4:
        owner, repo, pr_number = sys.argv[1], sys.argv[2], int(sys.argv[3])
        success = run_diagnostics(owner, repo, pr_number)
    else:
        print("Usage: python debug_github_api.py [owner] [repo] [pr_number]")
        print("Example: python debug_github_api.py myorg myrepo 123")
        print("\nRunning basic diagnostics...")
        success = run_diagnostics()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 