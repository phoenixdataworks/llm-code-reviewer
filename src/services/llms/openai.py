from typing import List, Dict
from openai import OpenAI
from unidiff import Hunk, PatchedFile
from ...core.config import Config
from ...core.models import PRDetails
from .base import BaseLLMService

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

    def get_ai_response(self, prompt: str) -> List[Dict[str, str]]:
        """Get response from OpenAI model, using the appropriate API endpoint."""
        # Models that should use the responses.create endpoint
        # Based on user feedback and logs (gpt-4o-mini being called 'o3')
        reasoning_models_list = ["gpt-4o-mini", "o3", "o3-mini", "o1", "o4-mini"] 

        response_text = None

        try:
            if self.model in reasoning_models_list:
                # Use responses.create for specified reasoning models
                print(f"Using responses.create for model: {self.model}")
                api_response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    reasoning={"effort": "medium", "summary": "auto"} # Default reasoning params
                )
                if hasattr(api_response, 'output_text'):
                    response_text = api_response.output_text
                else:
                    # Fallback for older/different response objects, or if output_text is missing
                    # This part might need adjustment based on the actual response structure of client.responses.create
                    # For now, assuming it might be in a similar place as chat completions if not output_text
                    if hasattr(api_response, 'choices') and api_response.choices and hasattr(api_response.choices[0], 'message') and api_response.choices[0].message:
                         response_text = api_response.choices[0].message.content
                    elif hasattr(api_response, 'message') and api_response.message: # Another possible structure
                         response_text = api_response.message.content
                    else:
                        print(f"OpenAI API call (responses.create) to model {self.model} returned an unexpected response structure.")
                        print(f"Response object: {api_response}")


            else:
                # Use chat.completions.create for other models
                print(f"Using chat.completions.create for model: {self.model}")
                completion_params = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are an expert code reviewer."},
                        {"role": "user", "content": prompt}
                    ]
                }
                # Temperature for non-reasoning models (excluding gpt-4o-mini/o3 as they're now handled above)
                # If a new model is added here that needs specific temperature, adjust accordingly.
                # For now, if it's not a reasoning model, and not the ones previously needing default, use 0.3.
                if self.model not in ["gpt-4o-mini", "o3"]: #This check is somewhat redundant now but kept for safety for other chat models
                     completion_params["temperature"] = 0.3
                
                api_response = self.client.chat.completions.create(**completion_params)
                
                if api_response.choices and api_response.choices[0].message:
                    response_text = api_response.choices[0].message.content
                else:
                    print(f"OpenAI API call (chat.completions.create) to model {self.model} returned no choices or empty message.")

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
