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
    This method handles large PRs by fetching files individually.
    """
    try:
      print("🔄 Attempting to fetch diff via PyGithub (fallback method)...")
      repo_obj = self.gh_client.get_repo(f"{owner}/{repo}")
      pr = repo_obj.get_pull(pull_number)
      
      # Get the list of files changed in the PR
      files = pr.get_files()
      files_list = list(files)
      
      if not files_list:
        print("⚠️ No files found in PR")
        return ""
      
      print(f"📁 Found {len(files_list)} changed files")
      
      # Check if there are too many files (GitHub API limit)
      if len(files_list) > 300:
        print(f"⚠️ PR has {len(files_list)} files, which may be too large to process")
        print("💡 Consider processing in batches or excluding some file types")
      
      # Generate diff manually from file contents
      diff_parts = []
      processed_files = 0
      
      for file in files_list:
        try:
          if file.status in ['added', 'modified', 'removed']:
            # Get the actual diff content from the file patch
            if hasattr(file, 'patch') and file.patch:
              diff_parts.append(f"diff --git a/{file.filename} b/{file.filename}")
              if file.status == 'added':
                diff_parts.append(f"new file mode {file.additions}")
                diff_parts.append("--- /dev/null")
                diff_parts.append(f"+++ b/{file.filename}")
              elif file.status == 'removed':
                diff_parts.append(f"deleted file mode {file.deletions}")
                diff_parts.append(f"--- a/{file.filename}")
                diff_parts.append("+++ /dev/null")
              else:  # modified
                diff_parts.append(f"--- a/{file.filename}")
                diff_parts.append(f"+++ b/{file.filename}")
              
              diff_parts.append(file.patch)
              processed_files += 1
              
            # Limit processing to avoid timeouts
            if processed_files >= 50:
              print(f"⚠️ Limiting to first 50 files to avoid timeout")
              break
              
        except Exception as e:
          print(f"⚠️ Error processing file {file.filename}: {e}")
          continue
      
      if diff_parts:
        diff_content = '\n'.join(diff_parts)
        print(f"✅ Generated diff via PyGithub: {len(diff_content)} chars, {processed_files} files")
        return diff_content
      else:
        print("❌ Failed to generate diff via PyGithub")
        return ""
        
    except Exception as e:
      print(f"❌ PyGithub fallback also failed: {e}")
      import traceback
      traceback.print_exc()
      return ""

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
