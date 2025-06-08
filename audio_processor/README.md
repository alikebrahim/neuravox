# Audio Processor Module

This module is now part of the **Audio Workflow Platform**.

## For New Users

Please see the main project README at the repository root:
- [Audio Workflow Platform README](../README.md)

## For Legacy Usage

This module can still be used standalone:

```bash
# Install dependencies
uv sync

# Run interactive mode
uv run python audio_splitter_cli.py process --interactive

# Run batch processing
uv run python run.py
```

For the full integrated experience with transcription capabilities, use the unified platform:

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