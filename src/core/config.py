import os
from github import Github
from ..utils.language_validator import LanguageValidator

class Config:
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is not set or is empty. Please provide a valid GitHub token.")

    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash-002')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

    _raw_language: str = os.environ.get('HUMAN_LANGUAGE', 'en')
    HUMAN_LANGUAGE = LanguageValidator.validate_language(_raw_language)
    PRIMARY_MODEL = os.environ.get('PRIMARY_MODEL', 'gemini')
    
    @classmethod
    def initialize_clients(cls):
        gh_client = Github(cls.GITHUB_TOKEN)
        return gh_client
