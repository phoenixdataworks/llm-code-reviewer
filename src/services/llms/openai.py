from typing import List, Dict, Any, Optional
from openai import OpenAI
from unidiff import Hunk, PatchedFile
from ...core.config import Config
from ...core.models import PRDetails
from .base import BaseLLMService

# Model configuration registry with per-model parameters
MODEL_CONFIG = {
    # "Reasoning" models - deterministic, low temp
    "gpt-4o-mini": {"temperature": 0.0, "top_p": 1.0},
    # O-series models (o1, o3, etc.) only support default temperature (1.0)
    "o3":          {},  # Use default parameters only
    "o3-mini":     {},  # Use default parameters only
    "o1":          {},  # Use default parameters only
    "o4-mini":     {},  # Use default parameters only
    # "Regular" chat models - mildly creative
    "gpt-3.5-turbo": {"temperature": 0.3, "top_p": 1.0},
    "gpt-4o":        {"temperature": 0.3, "top_p": 1.0},
}

class OpenAIService(BaseLLMService):
    """
    Implementation of BaseLLMService for OpenAI's models.
    """
    
    def __init__(self):
        """Initialize the OpenAI client with configuration."""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        
    def create_prompt(self, file: PatchedFile, hunk: Hunk, pr_details: PRDetails) -> str:
        """Create a prompt formatted for OpenAI's expectations."""
        return f"""
        Your task is to review the following code changes. Please follow these guidelines:
        Provide your response in this JSON format:
        {{"reviews": [{{"lineNumber": <line_number>, "reviewComment": "<review comment>, side: "<left or right >, "filepath": "<file path>"}}]}}
        Important Rules:
        1. Line Number Validation:
        - For "left" side: {hunk.source_start} ≤ lineNumber < {hunk.source_start + hunk.source_length}
        - For "right" side: {hunk.target_start} ≤ lineNumber < {hunk.target_start + hunk.target_length}

        2. Review Focus Areas:
        - Critical bugs and errors
        - Security vulnerabilities and risks
        - Performance optimization opportunities 
        - Code architecture and maintainability issues
        - Suggest code for improvement and optimization

        3. Key Requirements:
        - Return empty "reviews" array if no issues found
        - Use GitHub Markdown formatting in your comments
        - Do NOT suggest adding code comments
        - Provide feedback in language: {Config.HUMAN_LANGUAGE}

        Context Information:
        File: {file.path}
        PR Title: {pr_details.title}
        PR Description: 
        ---
        {pr_details.description or 'No description provided'}
        ---

        Git Diff Details:
        - Source Start: {hunk.source_start}
        - Source Length: {hunk.source_length} 
        - Target Start: {hunk.target_start}
        - Target Length: {hunk.target_length}

        Code Diff to Review:
        ```diff
        {hunk.__str__()}
        ```
        """

    def _build_messages(self, prompt: str) -> List[Dict[str, str]]:
        """Build messages array for chat completions API."""
        return [
            {"role": "system", "content": "You are an expert code reviewer."},
            {"role": "user", "content": prompt}
        ]
    
    def _call_chat_completions(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """Make the API call to OpenAI chat completions endpoint with proper parameters."""
        completion_params = {
            "model": self.model,
            "messages": messages,
            **kwargs  # Include any model-specific parameters
        }
        
        return self.client.chat.completions.create(**completion_params)
    
    def _extract_content(self, api_response: Any) -> Optional[str]:
        """Extract content from API response, handling different response structures."""
        if (hasattr(api_response, 'choices') and 
            api_response.choices and 
            hasattr(api_response.choices[0], 'message') and 
            api_response.choices[0].message):
            return api_response.choices[0].message.content
        
        print(f"OpenAI API call to model {self.model} returned an unexpected response structure.")
        print(f"Response object: {api_response}")
        return None

    def get_ai_response(self, prompt: str) -> List[Dict[str, str]]:
        """Get response from OpenAI model, using the appropriate API endpoint."""
        response_text = None

        try:
            # Get model-specific configuration or fall back to default
            model_config = MODEL_CONFIG.get(self.model, {"temperature": 0.3, "top_p": 1.0})
            
            # Log which model we're using
            reasoning_models = {"gpt-4o-mini", "o3", "o3-mini", "o1", "o4-mini"}
            model_type = "Reasoning" if self.model in reasoning_models else "Standard"
            print(f"Using {model_type} model: {self.model} with config: {model_config}")
            
            # Make API call with unified method
            api_response = self._call_chat_completions(
                self._build_messages(prompt),
                **model_config
            )
            
            # Extract content from response
            response_text = self._extract_content(api_response)

            # Process the response if present
            if response_text:
                cleaned_text = self._clean_response_text(response_text)
                return self._parse_response(cleaned_text)
            else:
                print(f"No valid response text received from model {self.model}.")
                return []

        except Exception as e:
            print(f"Error during OpenAI API call to model {self.model}: {e}")
            import traceback
            traceback.print_exc()
            return []
