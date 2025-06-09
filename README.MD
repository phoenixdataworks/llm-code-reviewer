# LLM Code Reviewer

This GitHub Action automatically reviews Pull Requests using multiple Language Models (LLMs) including OpenAI's GPT and Google's Gemini models. Get intelligent code reviews directly in your PR comments!

## Features

- 🤖 Multi-model support (OpenAI GPT, Google Gemini, Anthropic ClaudeAI)
- 🔄 Automatic PR code review
- 🌍 Multiple language support
- ⚙️ Configurable model selection
- 🚫 File exclusion patterns
- 🎯 Primary model selection capability

## Setup

### Prerequisites

1. Create a GitHub token with appropriate permissions
2. (Optional) Obtain API keys for:
   - Google Gemini API
   - OpenAI API
   - Anthropic API (ClaudeAI)

### Usage

Add the following workflow file to your repository (e.g., `.github/workflows/code-review.yml`):

```yaml
name: Code Review
on:
  pull_request:
    types: [opened, synchronize, reopened, edited]
jobs:
  ai-code-review:
    name: 'AI Code Review'
    runs-on: ubuntu-latest

    # Skip reviews for dependabot PRs (optional)
    if: github.actor != 'dependabot[bot]'

    permissions:
      contents: read
      pull-requests: write
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run PR Review
        uses: phoenixdataworks/llm-code-reviewer@v1.0.8
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_EVENT_PATH: ${{ github.event_path }}
          GITHUB_EVENT_NAME: ${{ github.event_name }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          PRIMARY_MODEL: 'openai' # or gemini, anthropic
          OPENAI_MODEL: 'o3'
          HUMAN_LANGUAGE: 'en'
          INPUT_EXCLUDE: |
            *.md
            *.json
            *.lock
            *.min.js
            *.min.css
            package-lock.json
            yarn.lock

```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `GITHUB_TOKEN` | GitHub token for repository interaction | Yes | - |
| `GEMINI_API_KEY` | Google Gemini API key | No | - |
| `OPENAI_API_KEY` | OpenAI API key | No | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | No | - |
| `GEMINI_MODEL` | Gemini model to use | No | `gemini-1.5-flash-002` |
| `OPENAI_MODEL` | OpenAI model to use | No | `gpt-4o-mini` |
| `ANTHROPIC_MODEL` | Anthropic model to use | No | `claude-3-opus-20240229` |
| `INPUT_EXCLUDE` | Comma-separated file patterns to exclude | No | - |
| `HUMAN_LANGUAGE` | Language for review comments | No | `en` |
| `PRIMARY_MODEL` | Primary model for review (gemini, openai, anthropic) | No | `gemini` |

## Examples

### Basic Usage

```yaml
- uses: tusgino >> phoenixdataworks/llm-code-reviewer@v1
  with:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
    PRIMARY_MODEL: 'gemini'
```

### Advanced Configuration

```yaml
- uses: tusgino >> phoenixdataworks/llm-code-reviewer@v1
  with:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GEMINI_MODEL: 'gemini-1.5-flash-002'
    OPENAI_MODEL: 'gpt-4o-mini'
    ANTHROPIC_MODEL: 'claude-3-opus-20240229'
    INPUT_EXCLUDE: '*.md,*.txt'
    HUMAN_LANGUAGE: 'vi'
    PRIMARY_MODEL: 'gemini'
```

## File Exclusion

Use `INPUT_EXCLUDE` to skip reviewing certain files. Example patterns:
- `*.md` - Exclude all Markdown files
- `docs/*` - Exclude all files in the docs directory
- `*.test.js,*.spec.js` - Exclude test files

## Language Support

Set `HUMAN_LANGUAGE` to receive reviews in your preferred language. Examples:
- `en` - English (default)
- `vi` - Vietnamese
- `ja` - Japanese
- And more...

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Created by [@tusgino](https://github.com/tusgino)
Reworked by [@phoenixdataworks](https://github.com/phoenixdataworks)

## Support

If you encounter any issues or have questions, please file them in the [Issues](https://github.com/phoenixdataworks/llm-code-reviewer/issues) section.
