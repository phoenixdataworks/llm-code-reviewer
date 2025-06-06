# GitHub Diff Fetching Issues - Debugging Guide

## 🔍 Problem: "No diff found or failed to fetch diff for PR"

This issue occurs when the LLM Code Reviewer can't fetch the diff from GitHub's API, even for large PRs with many changes.

## 🎯 Root Causes & Solutions

### 1. **Silent API Failures** ⭐ *Most Common*

**Problem:** Original code returned empty string without logging why
**Fix:** Enhanced error handling with detailed logging

```python
# Before (silent failure):
response = requests.get(api_url, headers=headers)
return response.text if response.status_code == 200 else ""

# After (comprehensive debugging):
print(f"🌐 Fetching diff from: {api_url}")
response = requests.get(api_url, headers=headers, timeout=30)
print(f"📊 Response status: {response.status_code}")
print(f"📏 Response size: {len(response.content)} bytes")
```

### 2. **Large PR Handling**

**Problem:** GitHub API returns 422 for very large diffs
**Solution:** PyGithub fallback method

```python
elif response.status_code == 422:
  print(f"❌ Unprocessable entity (422) - Diff might be too large")
  return self._get_diff_via_pygithub(owner, repo, pull_number)
```

### 3. **Authentication Issues**

**Problem:** Token permissions or format issues
**Signs:** 403 Forbidden responses

**Solutions:**
- Ensure token has `pull_requests: read` permission
- Check token format (should start with `ghp_`, `gho_`, etc.)
- Verify repository access

### 4. **Rate Limiting**

**Problem:** GitHub API rate limits hit
**Signs:** 429 responses or slow responses

**Solutions:**
- Check rate limit headers
- Implement exponential backoff
- Use authenticated requests (higher limits)

## 🛠️ Enhanced Solutions Implemented

### 1. **Comprehensive Error Handling**

The GitHub service now provides detailed diagnostics:

```python
def get_diff(self, owner: str, repo: str, pull_number: int) -> str:
    # ✅ Detailed logging
    # ✅ Timeout handling  
    # ✅ Status code analysis
    # ✅ Fallback mechanism
    # ✅ Error categorization
```

### 2. **PyGithub Fallback Method**

For large PRs that fail with direct API:

```python
def _get_diff_via_pygithub(self, owner: str, repo: str, pull_number: int) -> str:
    # ✅ Handles large PRs (>300 files)
    # ✅ Processes files individually
    # ✅ Limits to 50 files to avoid timeout
    # ✅ Generates diff manually from patches
```

### 3. **Diagnostic Tool**

Created `scripts/debug_github_api.py` for troubleshooting:

```bash
# Basic token check
python scripts/debug_github_api.py

# Full PR diagnostics  
python scripts/debug_github_api.py owner repo 135
```

## 🔧 Debugging Steps

### Step 1: Run Diagnostics

```bash
# Set your environment
export GITHUB_TOKEN="your_token"

# Run comprehensive check
python scripts/debug_github_api.py owner repo pr_number
```

### Step 2: Check Common Issues

1. **Token Validity:**
   ```bash
   curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
   ```

2. **PR Exists:**
   ```bash
   curl -H "Authorization: Bearer $GITHUB_TOKEN" \
        https://api.github.com/repos/owner/repo/pulls/135
   ```

3. **Diff Size:**
   ```bash
   curl -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3.diff" \
        https://api.github.com/repos/owner/repo/pulls/135.diff
   ```

### Step 3: Analyze Response

**200 + Empty:** Diff exists but empty (no changes)
**403:** Permission issue
**404:** PR or repo doesn't exist  
**422:** Diff too large for API
**429:** Rate limited

## 🚀 Performance Optimizations

### For Large PRs:

1. **File Filtering:** Skip irrelevant files early
2. **Batch Processing:** Process files in chunks
3. **Timeout Management:** 30-second timeout with fallback
4. **Caching:** Cache diff content to avoid re-fetching

### Size Limits:

- **GitHub API:** ~1MB diff size limit
- **Files:** >300 files may cause issues
- **Lines:** >50k lines changed may timeout

## 🛡️ Error Recovery

The enhanced system now:

1. **Tries direct API first** (fastest)
2. **Falls back to PyGithub** (handles large PRs)
3. **Provides detailed error logs** (for debugging)
4. **Limits processing scope** (avoids timeouts)

## 📊 Monitoring

Watch for these log patterns:

```bash
# Success patterns:
✅ Successfully fetched diff with X lines
✅ Generated diff via PyGithub: X chars, Y files

# Warning patterns:  
⚠️ Large PR: >300 files changed
⚠️ Limiting to first 50 files

# Error patterns:
❌ Access denied (403) - Token permissions
❌ Unprocessable entity (422) - Diff too large
❌ Request timed out after 30 seconds
```

## 🔮 Future Improvements

- [ ] Implement retry logic with exponential backoff
- [ ] Add progress indicators for large PR processing
- [ ] Cache successful diff fetches
- [ ] Support for partial diff processing
- [ ] Intelligent file prioritization (skip generated files)

## 🎯 Quick Fix Summary

For your "Facebook insta reorg" PR #135:

1. **Run diagnostics:** `python scripts/debug_github_api.py owner repo 135`
2. **Check the logs:** Look for specific error messages
3. **Enhanced service:** The updated GitHub service will now show exactly what's failing
4. **Fallback:** If API fails, PyGithub will try to reconstruct the diff

The enhanced error handling should resolve the silent failures and provide clear actionable feedback on what's preventing diff fetching. 