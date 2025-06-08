# Whisper Migration Guide

## Overview

Neuravox has replaced Ollama support with local Whisper models for improved offline transcription. This guide helps you migrate from Ollama to local Whisper models.

## Why the Change?

1. **Purpose-built**: Whisper is specifically designed for speech recognition, while Ollama uses general language models
2. **Better accuracy**: Whisper provides superior transcription quality
3. **No server required**: Whisper runs directly in your Python environment
4. **Multiple model sizes**: Choose the right balance of speed and accuracy
5. **GPU acceleration**: Automatic GPU detection for faster processing

## Migration Steps

### 1. Update Neuravox

```bash
cd neuravox
git pull
uv pip install -e .
```

### 2. Install FFmpeg (if not already installed)

```bash
# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows - automatically handled
```

### 3. Update Your Commands

#### Old (Ollama):
```bash
neuravox process audio.mp3 --model ollama-phi4
```

#### New (Whisper Local):
```bash
# For fast processing
neuravox process audio.mp3 --model whisper-base

# For best quality
neuravox process audio.mp3 --model whisper-large

# For optimized speed
neuravox process audio.mp3 --model whisper-turbo
```

## Available Whisper Models

| Model | Size | Parameters | Speed | Quality | Use Case |
|-------|------|------------|-------|---------|----------|
| `whisper-tiny` | 39 MB | 39M | Fastest | Good | Quick drafts |
| `whisper-base` | 74 MB | 74M | Fast | Better | **Recommended default** |
| `whisper-small` | 244 MB | 244M | Medium | Good | Balanced option |
| `whisper-medium` | 769 MB | 769M | Slow | Very Good | High quality |
| `whisper-large` | 1550 MB | 1550M | Slowest | Best | Maximum quality |
| `whisper-turbo` | 809 MB | 809M | Fast | Very Good | **Speed optimized** |

### English-Only Models

For better English transcription, use the `.en` variants:
- `whisper-tiny.en`
- `whisper-base.en`
- `whisper-small.en`
- `whisper-medium.en`

## Key Differences

### API Keys
- **Ollama**: Required Ollama server running
- **Whisper**: No API key or server needed

### First Run
- Whisper models download automatically on first use
- Models are cached in `~/.cache/whisper/`

### GPU Support
- Automatically detects and uses GPU if available
- Falls back to CPU if no GPU found

### Configuration

Update your config files:

```yaml
# Old (Ollama)
transcription:
  default_model: "ollama-phi4"

# New (Whisper)
transcription:
  default_model: "whisper-base"
```

## Performance Tips

1. **Start with `whisper-base`** - Good balance of speed and quality
2. **Use `whisper-turbo`** for long audio files
3. **GPU acceleration** - Ensure CUDA is installed for 10x speedup
4. **Model selection**:
   - Podcasts/interviews: `whisper-base` or `whisper-small`
   - Lectures/presentations: `whisper-medium` or `whisper-large`
   - Quick processing: `whisper-tiny` or `whisper-turbo`

## Troubleshooting

### "Whisper not installed" Error
```bash
uv pip install openai-whisper
```

### "FFmpeg not found" Error
Install FFmpeg for your platform (see installation steps above)

### Slow Processing
1. Check if GPU is being used: Watch for CUDA messages during startup
2. Use a smaller model: `whisper-tiny` or `whisper-base`
3. Enable turbo mode: Use `whisper-turbo` model

### Out of Memory
Use a smaller model or process shorter audio chunks

## Advanced Configuration

```python
# In your config
"whisper-custom": {
    "name": "Whisper Custom",
    "provider": "whisper-local",
    "model_id": "base",
    "device": "cuda",  # Force GPU
    "parameters": {
        "language": "en",  # Force English
        "temperature": 0.0,  # Deterministic
        "word_timestamps": true  # Word-level timing
    }
}
```

## Benefits of Local Whisper

1. **Complete privacy** - Audio never leaves your machine
2. **No internet required** - Work offline
3. **No API costs** - Unlimited transcription
4. **Consistent results** - Same model version always
5. **Full control** - Customize all parameters

## Need Help?

- Check model info: `neuravox list-models`
- View configuration: `neuravox config`
- Process interactively: `neuravox process --interactive`

The migration from Ollama to Whisper provides better transcription quality and a more streamlined experience for audio processing.