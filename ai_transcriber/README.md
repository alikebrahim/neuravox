# AI Transcriber Module

This module is now part of the **Audio Workflow Platform**.

## For New Users

Please see the main project README at the repository root:
- [Audio Workflow Platform README](../README.md)

## For Legacy Usage

This module can still be used standalone:

```bash
# Install the module
pip install -e .

# Set up API keys
export GOOGLE_API_KEY="your_google_api_key"
export OPENAI_API_KEY="your_openai_api_key"

# Run interactive mode
audio-transcriber interactive

# Or transcribe directly
audio-transcriber transcribe audio.mp3 --model google-gemini
```

For the full integrated experience with automatic audio splitting, use the unified platform:

```bash
cd ..
cd audio-workflow-platform
uv pip install -e .
audio-workflow process --interactive
```

## Documentation

- Main documentation: [../README.md](../README.md)
- Implementation details: [../Phase_1.md](../Phase_1.md)
- Integration guide: [../INTEGRATION.md](../INTEGRATION.md)