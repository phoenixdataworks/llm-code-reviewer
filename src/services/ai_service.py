from typing import List, Dict, Optional
from unidiff import Hunk, PatchedFile

from ..core.config import Config
from ..core.models import PRDetails

class AIService:
    """
    Optimized service manager that handles selection and usage of available LLM services.
    Uses lazy loading to avoid importing unused LLM dependencies.
    """
    
    def __init__(self):
        """Initialize with deferred service loading for optimal startup time."""
        self.active_service = None
        self._service_cache = {}
        self._initialize_service()

    def _initialize_service(self) -> None:
        """Initialize the appropriate LLM service using lazy loading strategy."""
        PRIMARY_MODEL = getattr(Config, 'PRIMARY_MODEL', 'gemini').lower()
        
        # Define service priority order
        if PRIMARY_MODEL in ['gemini', 'openai', 'anthropic']:
            ordered_models = [PRIMARY_MODEL] + [
                model for model in ['gemini', 'openai', 'anthropic'] 
                if model != PRIMARY_MODEL
            ]
        else:
            print(f"Unknown PRIMARY_MODEL '{PRIMARY_MODEL}'. Using default order.")
            ordered_models = ['gemini', 'openai', 'anthropic']

        # Try to initialize services in priority order
        for model in ordered_models:
            if self._check_api_key_availability(model):
                try:
                    self.active_service = self._get_service_instance(model)
                    print(f"✅ Initialized {model.title()} service successfully")
                    break
                except Exception as e:
                    print(f"❌ Failed to initialize {model.title()} service: {e}")
                    continue

        if not self.active_service:
            available_keys = [model for model in ordered_models if self._check_api_key_availability(model)]
            raise ValueError(
                f"No LLM service could be initialized. "
                f"Available API keys: {available_keys}. "
                f"Please check your API key configuration."
            )

    def _get_service_instance(self, model: str):
        """Get service instance with lazy loading and caching."""
        if model in self._service_cache:
            return self._service_cache[model]
            
        # Lazy import to avoid loading unused dependencies
        if model == 'gemini':
            from .llms.gemini import GeminiService
            service = GeminiService()
        elif model == 'openai':
            from .llms.openai import OpenAIService
            service = OpenAIService()
        elif model == 'anthropic':
            from .llms.anthropic import AnthropicService
            service = AnthropicService()
        else:
            raise ValueError(f"Unsupported model: {model}")
            
        self._service_cache[model] = service
        return service

    def _check_api_key_availability(self, model: str) -> bool:
        """Check if the API key for specified model is available.

        Args:
            model: Service name ('openai', 'gemini', or 'anthropic')

        Returns:
            bool: True if API key is available and non-empty
        """
        key_mapping = {
            'gemini': 'GEMINI_API_KEY',
            'openai': 'OPENAI_API_KEY', 
            'anthropic': 'ANTHROPIC_API_KEY'
        }
        
        key_name = key_mapping.get(model)
        if not key_name:
            return False
            
        api_key = getattr(Config, key_name, None)
        return api_key is not None and api_key.strip() != ""

    def create_prompt(self, file: PatchedFile, hunk: Hunk, pr_details: PRDetails) -> str:
        """
        Create a prompt using the active LLM service.
        
        Args:
            file: The file being reviewed
            hunk: The code hunk to review
            pr_details: Pull request details
            
        Returns:
            str: Formatted prompt for the active LLM service
        """
        if not self.active_service:
            raise RuntimeError("No active LLM service available")
        return self.active_service.create_prompt(file, hunk, pr_details)

    def get_ai_response(self, prompt: str) -> List[Dict[str, str]]:
        """
        Get response from the active LLM service with enhanced error handling.
        
        Args:
            prompt: The formatted prompt to send to the LLM
            
        Returns:
            List[Dict[str, str]]: List of review comments
        """
        if not self.active_service:
            raise RuntimeError("No active LLM service available")
            
        try:
            response = self.active_service.get_ai_response(prompt)
            print(f"✅ Generated {len(response)} review comments")
            return response
        except Exception as e:
            service_name = self.get_active_service_name()
            print(f"❌ Error getting AI response from {service_name}: {e}")
            
            # Attempt fallback to another service if available
            return self._attempt_fallback_response(prompt)

    def _attempt_fallback_response(self, prompt: str) -> List[Dict[str, str]]:
        """Attempt to get response from fallback services."""
        current_service_name = self.get_active_service_name().lower().replace('service', '')
        fallback_models = [model for model in ['gemini', 'openai', 'anthropic'] 
                          if model != current_service_name and self._check_api_key_availability(model)]
        
        for fallback_model in fallback_models:
            try:
                print(f"🔄 Attempting fallback to {fallback_model.title()}...")
                fallback_service = self._get_service_instance(fallback_model)
                response = fallback_service.get_ai_response(prompt)
                print(f"✅ Fallback successful: Generated {len(response)} review comments")
                return response
            except Exception as e:
                print(f"❌ Fallback to {fallback_model.title()} failed: {e}")
                continue
        
        print("❌ All fallback attempts failed")
        return []

    def get_active_service_name(self) -> str:
        """
        Get the name of the currently active service.
        
        Returns:
            str: Name of the active service or 'None' if no service is active
        """
        if not self.active_service:
            return "None"
        return self.active_service.__class__.__name__

    def get_service_info(self) -> Dict[str, any]:
        """Get information about the current service configuration."""
        available_services = []
        for model in ['gemini', 'openai', 'anthropic']:
            if self._check_api_key_availability(model):
                available_services.append(model)
        
        return {
            'active_service': self.get_active_service_name(),
            'available_services': available_services,
            'primary_model': getattr(Config, 'PRIMARY_MODEL', 'gemini'),
            'cached_services': list(self._service_cache.keys())
        }
