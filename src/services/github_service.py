import json
import requests
from typing import List, Dict, Any
from ..core.config import Config
from ..core.models import PRDetails
from github import Github
from github.Repository import Repository

class GitHubService:
  def __init__(self, gh_client: Github):
    """Initialize GitHub service with a client."""
    self.gh_client = gh_client

  def get_pr_details(self, event_path: str) -> PRDetails:
    """
    Extract pull request details from GitHub event data.
    
    Args:
      event_path: Path to GitHub event JSON file
    Returns:
      PRDetails object containing PR information
    """
    event_data = self._load_event_data(event_path)
    pull_number = self._extract_pull_number(event_data)
    repo_full_name = event_data["repository"]["full_name"]
    owner, repo = repo_full_name.split("/")
    
    repo_obj = self.gh_client.get_repo(repo_full_name)
    pr = repo_obj.get_pull(pull_number)

    return PRDetails(owner, repo_obj.name, pull_number, pr.title, pr.body)

  def get_diff(self, owner: str, repo: str, pull_number: int) -> str:
    """
    Get the diff content for a pull request with comprehensive error handling.
    
    Returns:
      Diff content as string or empty string if request fails
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}.diff"
    headers = {
      'Authorization': f'Bearer {Config.GITHUB_TOKEN}',
      'Accept': 'application/vnd.github.v3.diff',
      'User-Agent': 'LLM-Code-Reviewer/1.0'
    }

    try:
      print(f"🌐 Fetching diff from: {api_url}")
      response = requests.get(api_url, headers=headers, timeout=30)
      
      print(f"📊 Response status: {response.status_code}")
      print(f"📏 Response size: {len(response.content)} bytes")
      
      if response.status_code == 200:
        diff_text = response.text
        if diff_text.strip():
          lines_count = len(diff_text.splitlines())
          print(f"✅ Successfully fetched diff with {lines_count} lines")
          return diff_text
        else:
          print("⚠️ Diff response was empty")
          return ""
      
      elif response.status_code == 404:
        print(f"❌ PR #{pull_number} not found in {owner}/{repo}")
        print("💡 Check if PR number is correct and repository exists")
        
      elif response.status_code == 403:
        print(f"❌ Access denied (403) - Token permissions issue")
        print("💡 Ensure GITHUB_TOKEN has 'pull_requests: read' permission")
        print(f"🔍 Response headers: {dict(response.headers)}")
        
      elif response.status_code == 406:
        print(f"❌ Diff too large (406) - Exceeds GitHub's 20,000 line limit")
        print("🔄 Switching to piece-by-piece diff fetching...")
        return self._get_diff_via_pygithub(owner, repo, pull_number)
        
      elif response.status_code == 422:
        print(f"❌ Unprocessable entity (422) - Diff might be too large")
        print("💡 Try using PyGithub to fetch files individually")
        return self._get_diff_via_pygithub(owner, repo, pull_number)
        
      else:
        print(f"❌ Unexpected status code: {response.status_code}")
        print(f"🔍 Response text: {response.text[:500]}...")
        
      return ""
      
    except requests.exceptions.Timeout:
      print("❌ Request timed out after 30 seconds")
      print("💡 Large PR diff might need alternative approach")
      return self._get_diff_via_pygithub(owner, repo, pull_number)
      
    except requests.exceptions.ConnectionError as e:
      print(f"❌ Connection error: {e}")
      return ""
      
    except Exception as e:
      print(f"❌ Unexpected error fetching diff: {e}")
      import traceback
      traceback.print_exc()
      return ""

  def _get_diff_via_pygithub(self, owner: str, repo: str, pull_number: int) -> str:
    """
    Fallback method to get diff using PyGithub when direct API fails.
    This method handles large PRs by fetching files individually in pieces.
    """
    try:
      print("🔄 Fetching large PR diff piece-by-piece via PyGithub...")
      repo_obj = self.gh_client.get_repo(f"{owner}/{repo}")
      pr = repo_obj.get_pull(pull_number)
      
      # Get the list of files changed in the PR
      files = pr.get_files()
      files_list = list(files)
      
      if not files_list:
        print("⚠️ No files found in PR")
        return ""
      
      total_files = len(files_list)
      print(f"📁 Found {total_files} changed files")
      
      # Smart filtering for large PRs
      if total_files > 100:
        print(f"🔍 Large PR detected ({total_files} files)")
        files_list = self._filter_important_files(files_list)
        print(f"📝 Filtered to {len(files_list)} important files")
      
      # Process files in chunks to avoid timeouts
      diff_parts = []
      processed_files = 0
      skipped_files = 0
      total_lines = 0
      
      for i, file in enumerate(files_list):
        try:
          # Skip binary files and very large files
          if self._should_skip_file(file):
            skipped_files += 1
            print(f"⏭️ Skipping {file.filename} ({file.status}, {file.changes} changes)")
            continue
          
          if file.status in ['added', 'modified', 'removed']:
            # Get the actual diff content from the file patch
            if hasattr(file, 'patch') and file.patch:
              # Add git diff header
              diff_parts.append(f"diff --git a/{file.filename} b/{file.filename}")
              
              # Add file mode information
              if file.status == 'added':
                diff_parts.append("new file mode 100644")
                diff_parts.append("--- /dev/null")
                diff_parts.append(f"+++ b/{file.filename}")
              elif file.status == 'removed':
                diff_parts.append("deleted file mode 100644")
                diff_parts.append(f"--- a/{file.filename}")
                diff_parts.append("+++ /dev/null")
              else:  # modified
                diff_parts.append(f"--- a/{file.filename}")
                diff_parts.append(f"+++ b/{file.filename}")
              
              # Add the actual patch content
              diff_parts.append(file.patch)
              processed_files += 1
              total_lines += len(file.patch.splitlines())
              
              # Progress indicator
              if processed_files % 10 == 0:
                print(f"📊 Processed {processed_files}/{len(files_list)} files ({total_lines} lines)")
              
            # Limit to avoid memory issues and timeouts
            if processed_files >= 100:
              print(f"⚠️ Limiting to first 100 files to avoid timeout")
              remaining = len(files_list) - i - 1
              if remaining > 0:
                print(f"📋 {remaining} files remaining (will be skipped)")
              break
              
            # Memory management for very large diffs
            if total_lines > 15000:
              print(f"⚠️ Reached 15k lines limit, stopping to avoid memory issues")
              break
              
        except Exception as e:
          print(f"⚠️ Error processing file {file.filename}: {e}")
          skipped_files += 1
          continue
      
      if diff_parts:
        diff_content = '\n'.join(diff_parts)
        print(f"✅ Successfully generated piece-by-piece diff:")
        print(f"   📊 {processed_files} files processed")
        print(f"   ⏭️ {skipped_files} files skipped")
        print(f"   📏 {len(diff_content)} characters")
        print(f"   📝 {total_lines} lines")
        return diff_content
      else:
        print("❌ Failed to generate any diff content")
        return ""
        
    except Exception as e:
      print(f"❌ PyGithub piece-by-piece fetch failed: {e}")
      import traceback
      traceback.print_exc()
      return ""
  
  def _filter_important_files(self, files_list):
    """Filter files to focus on the most important ones for large PRs."""
    # Prioritize code files over config/generated files
    important_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift'}
    
    # Separate files by importance
    important_files = []
    other_files = []
    
    for file in files_list:
      filename = file.filename.lower()
      
      # Skip common unimportant files
      if any(skip in filename for skip in ['package-lock.json', 'yarn.lock', '.min.js', '.min.css', '/dist/', '/build/']):
        continue
        
      # Check file extension
      if any(filename.endswith(ext) for ext in important_extensions):
        important_files.append(file)
      else:
        other_files.append(file)
    
    # Return important files first, then others (up to reasonable limit)
    result = important_files[:80]  # Max 80 important files
    if len(result) < 50:  # If not many important files, add some others
      result.extend(other_files[:50-len(result)])
    
    return result
  
  def _should_skip_file(self, file):
    """Determine if a file should be skipped during piece-by-piece processing."""
    # Skip binary files
    if hasattr(file, 'patch') and file.patch is None:
      return True
    
    # Skip very large files (>1000 changes)
    if file.changes > 1000:
      return True
    
    # Skip common generated/vendor files
    skip_patterns = [
      'package-lock.json', 'yarn.lock', 'composer.lock',
      '.min.js', '.min.css', '.bundle.js',
      '/node_modules/', '/vendor/', '/dist/', '/build/',
      '.generated', '.auto', '_generated'
    ]
    
    filename = file.filename.lower()
    return any(pattern in filename for pattern in skip_patterns)

  def create_review_comment(self, pr_details: PRDetails, comments: List[Dict[str, Any]]) -> None:
    """Create a review comment on the pull request."""
    repo = self.gh_client.get_repo(f"{pr_details.owner}/{pr_details.repo}")
    pr = repo.get_pull(pr_details.pull_number)
    
    pr.create_review(
      body="AI generated review comments",
      comments=comments,
      event="COMMENT"
    )

  def _load_event_data(self, event_path: str) -> Dict:
    """Load GitHub event data from JSON file."""
    with open(event_path, "r") as f:
      return json.load(f)

  def _extract_pull_number(self, event_data: Dict) -> int:
    """Extract pull request number from event data."""
    if "issue" in event_data and "pull_request" in event_data["issue"]:
      return event_data["issue"]["number"]
    return event_data["number"]
