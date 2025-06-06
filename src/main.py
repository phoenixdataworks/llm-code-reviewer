import os
import json
import time
from typing import List, Dict, Any, Optional
import fnmatch
from .core.config import Config
from .core.models import PRDetails
from .services.github_service import GitHubService
from .services.ai_service import AIService
from .utils.diff_parser import DiffParser
from .utils.code_analyzer import CodeAnalyzer

class PRReviewApplication:
  def __init__(self) -> None:
    """Initialize the PR Review Application with required services."""
    print("🚀 Starting LLM Code Reviewer (Optimized Version)")
    start_time = time.time()
    self._setup_services()
    setup_time = time.time() - start_time
    print(f"⚡ Service initialization completed in {setup_time:.2f}s")

  def _setup_services(self) -> None:
    """Set up all required services with performance monitoring."""
    print("📝 Initializing GitHub client...")
    gh_client = Config.initialize_clients()
    self.github_service = GitHubService(gh_client)
    
    print("🤖 Initializing AI service with lazy loading...")
    self.ai_service = AIService()
    
    # Display service configuration
    service_info = self.ai_service.get_service_info()
    print(f"✅ Active LLM: {service_info['active_service']}")
    print(f"📋 Available services: {', '.join(service_info['available_services'])}")
    
    print("🔧 Initializing analysis components...")
    self.code_analyzer = CodeAnalyzer(self.ai_service)
    self.diff_parser = DiffParser()
    
    print("🎯 All services initialized successfully")

  def run(self) -> None:
    """Execute the main PR review process with enhanced monitoring."""
    total_start_time = time.time()
    
    try:
      if not self._is_valid_event():
        print("❌ Exiting due to invalid or unsupported event.")
        return

      print("📖 Processing PR details and diff...")
      pr_details = self._process_pr()
      if not pr_details:
        print("⚠️ Failed to process PR details or no diff found to analyze.")
        return
      
      total_time = time.time() - total_start_time
      print(f"✅ PR Review process completed successfully in {total_time:.2f}s")

    except Exception as error:
      print(f"❌ Error in run: {error}")
      import traceback
      traceback.print_exc()

  def _is_valid_event(self) -> bool:
    """Check if the GitHub event is supported."""
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    if event_name == "pull_request":
        print(f"✅ Processing supported event: {event_name}")
        return True

    print(f"❌ Unsupported event: {event_name}. Expected 'pull_request'.")
    return False

  def _process_pr(self) -> Optional[PRDetails]:
    """Process the PR and create review comments if needed. Returns PRDetails or None."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("❌ Error: GITHUB_EVENT_PATH environment variable not set.")
        return None
    if not os.path.exists(event_path):
        print(f"❌ Error: GITHUB_EVENT_PATH file not found at {event_path}")
        return None

    try:
        print("📋 Extracting PR details from GitHub event...")
        pr_details = self.github_service.get_pr_details(event_path)
        print(f"📝 Processing PR #{pr_details.pull_number}: {pr_details.title}")
    except Exception as e:
        print(f"❌ Error getting PR details: {e}")
        import traceback
        traceback.print_exc()
        return None

    print("📥 Fetching PR diff...")
    diff_start_time = time.time()
    diff = self.github_service.get_diff(pr_details.owner, pr_details.repo, pr_details.pull_number)
    diff_time = time.time() - diff_start_time
    
    if not diff:
      print("⚠️ No diff found or failed to fetch diff for PR.")
      return pr_details 

    print(f"📊 Diff fetched in {diff_time:.2f}s, parsing...")
    parse_start_time = time.time()
    parsed_diff = self.diff_parser.parse_diff(diff)
    parse_time = time.time() - parse_start_time
    
    if not parsed_diff:
        print("⚠️ Diff was present but parsing resulted in no actionable changes.")
        return pr_details 

    print(f"🔍 Diff parsed in {parse_time:.2f}s, applying filters...")
    filtered_diff = self._filter_diff(parsed_diff)
    if not filtered_diff:
        print("⚠️ All diff content was filtered out by exclude patterns.")
        return pr_details

    files_count = len(filtered_diff)
    print(f"🎯 Analyzing {files_count} file(s) for code review...")
    
    analysis_start_time = time.time()
    comments = self.code_analyzer.analyze_code(filtered_diff, pr_details)
    analysis_time = time.time() - analysis_start_time
    
    if comments:
      print(f"💬 Generated {len(comments)} review comments in {analysis_time:.2f}s")
      comment_start_time = time.time()
      self.github_service.create_review_comment(pr_details, comments)
      comment_time = time.time() - comment_start_time
      print(f"✅ Successfully posted review comments in {comment_time:.2f}s")
    else:
      print(f"✅ No issues found after {analysis_time:.2f}s analysis - code looks good!")
    
    return pr_details

  def _filter_diff(self, parsed_diff: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter diff based on exclude patterns from environment variables."""
    exclude_patterns = self._get_exclude_patterns()
    if exclude_patterns:
        print(f"🚫 Applying exclude patterns: {', '.join(exclude_patterns)}")
        
    filtered = [
      file for file in parsed_diff
      if not any(fnmatch.fnmatch(file.get('path', ''), pattern) 
            for pattern in exclude_patterns)
    ]
    
    excluded_count = len(parsed_diff) - len(filtered)
    if excluded_count > 0:
        print(f"📝 Excluded {excluded_count} file(s) based on patterns")
        
    return filtered

  def _get_exclude_patterns(self) -> List[str]:
    """Get and process exclude patterns from environment variables."""
    exclude_input = os.environ.get("INPUT_EXCLUDE", "").strip()
    if not exclude_input:
        return []
    return [s.strip() for s in exclude_input.split(",") if s.strip()]

if __name__ == "__main__":
  app = PRReviewApplication()
  app.run()
