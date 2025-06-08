# Neuravox

A unified platform for audio processing and AI-powered transcription, combining sophisticated silence-based audio splitting with multi-model transcription capabilities.

**Project Status:** Phase 1 Complete (95%) - Core functionality implemented, tested, and production-ready.

## Features

### Core Capabilities

- **Smart Audio Processing**
  - Automatic silence detection and splitting (25+ second gaps)
  - Optimized FLAC output for transcription (16kHz, mono)
  - Batch processing with real-time progress tracking
  - Comprehensive metadata generation (JSON/CSV)
  - Support for all major audio formats (MP3, WAV, FLAC, M4A, etc.)

- **Multi-Model Transcription**
  - Support for Google Gemini, OpenAI Whisper, and Ollama models
  - Chunk-aware transcription with timestamp preservation
  - Automatic transcript merging with timing information
  - Concurrent processing for optimal performance
  - Project-based organization of outputs

- **Unified Pipeline**
  - Single command for complete audio-to-text workflow
  - SQLite-based state management with resume capability
  - Rich CLI interface with interactive file selection
  - Configurable workspace and processing parameters
  - Comprehensive error handling and validation

### Additional Features

- **Backward Compatibility**: Original module CLIs preserved
- **Flexible Configuration**: Environment variables, YAML files, and defaults
- **Progress Tracking**: Real-time updates with time estimates
- **Input Validation**: File format and API key verification
- **Comprehensive Testing**: Unit and integration test suites

## Installation

### Prerequisites

- Python 3.12 or higher
- uv package manager (recommended) or pip
- FFmpeg (for audio processing)

### Install Steps

```bash
# Clone the repository
git clone https://github.com/yourusername/neuravox.git
cd neuravox

# Create virtual environment with uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the platform in development mode
uv pip install -e .

# Or use pip if you prefer
pip install -e .
```

### Verify Installation

```bash
# Check installation
neuravox --version

# Initialize workspace
neuravox init
```

## Quick Start

### 1. Initialize Workspace

```bash
neuravox init
```

This creates the following structure in `~/neuravox/`:
- `input/` - Place audio files here
- `processed/` - Split audio chunks stored here
- `transcribed/` - Final transcripts saved here

### 2. Configure API Keys

Set up API keys for your chosen transcription service:

```bash
# Option 1: Environment variables (recommended)
export GOOGLE_API_KEY="your-google-api-key"
export OPENAI_API_KEY="your-openai-api-key"

# Option 2: Create .env file
cp .env.example .env
# Edit .env with your API keys
```

### 3. Process Audio Files

```bash
# Interactive mode (recommended for beginners)
neuravox process --interactive

# Process specific files
neuravox process audio1.mp3 audio2.wav

# Use specific model
neuravox process --model google-gemini audio.mp3

# Process all files in input directory
neuravox process ~/neuravox/input/*.mp3
```

### 4. Check Results

```bash
# View processing status
neuravox status

# Resume any failed files
neuravox resume
```

Processed files will be in:
- `~/neuravox/processed/[file_id]/` - Audio chunks
- `~/neuravox/transcribed/[file_id]/` - Transcripts

## Usage

### Commands

#### `neuravox init`
Initialize workspace and create directory structure.

Options:
- `--workspace PATH` - Custom workspace location (default: ~/neuravox)

#### `neuravox process`
Process audio files through the complete pipeline.

Options:
- `--model, -m` - Transcription model to use (google-gemini, openai-whisper, ollama)
- `--interactive, -i` - Interactive file selection mode
- Files can be specified as arguments or selected interactively

Examples:
```bash
# Interactive mode
neuravox process -i

# Process specific files
neuravox process file1.mp3 file2.wav

# Use specific model
neuravox process -m openai-whisper audio.mp3
```

#### `neuravox status`
Show pipeline status, processing statistics, and recent activity.

#### `neuravox resume`
Resume processing of failed files.

#### `neuravox config`
View and manage configuration settings.

Options:
- `show` - Display current configuration
- `set KEY VALUE` - Update configuration value

### Configuration

Configuration follows a hierarchy (highest to lowest priority):
1. Environment variables
2. User configuration file
3. Default configuration

#### Configuration File

Create `config/default.yaml` or `~/.config/neuravox/config.yaml`:

```yaml
workspace:
  base_path: "~/neuravox"  # Base directory for all operations
  input_dir: "input"             # Subdirectory for input files
  processed_dir: "processed"     # Subdirectory for processed chunks
  transcribed_dir: "transcribed" # Subdirectory for transcripts
  
processing:
  silence_threshold: 0.01        # Volume threshold for silence detection
  min_silence_duration: 25.0     # Minimum silence duration in seconds
  min_chunk_duration: 5.0        # Minimum chunk duration in seconds
  sample_rate: 16000            # Output sample rate (Hz)
  output_format: "flac"         # Output format for chunks
  compression_level: 8          # FLAC compression level (0-8)
  normalize: true               # Normalize audio volume
  chunk_boundary: "simple"      # Chunk boundary detection mode
  preserve_timestamps: true     # Preserve timing information
  
transcription:
  default_model: "google-gemini" # Default transcription model
  max_concurrent: 3             # Max concurrent transcriptions
  chunk_processing: true        # Process chunks separately
  combine_chunks: true          # Combine chunks into single transcript
  include_timestamps: true      # Include timestamps in output

# API keys are set via environment variables:
# GOOGLE_API_KEY=your-key
# OPENAI_API_KEY=your-key
```

#### Environment Variables

```bash
# API Keys
export GOOGLE_API_KEY="your-google-api-key"
export OPENAI_API_KEY="your-openai-api-key"

# Override configuration
export AUDIO_WORKFLOW_BASE_PATH="/custom/path"
export AUDIO_PROCESSING_MIN_SILENCE_DURATION=30.0
export TRANSCRIPTION_DEFAULT_MODEL="openai-whisper"
```

### Supported Models

#### Google Gemini (Recommended)
- Model: `google-gemini`
- Requires: `GOOGLE_API_KEY`
- Best for: Long audio files, high accuracy
- Get API key: https://makersuite.google.com/app/apikey

#### OpenAI Whisper
- Model: `openai-whisper`
- Requires: `OPENAI_API_KEY`
- Best for: Multiple language support
- Get API key: https://platform.openai.com/api-keys

#### Ollama (Local)
- Model: `ollama`
- Requires: Ollama installation
- Best for: Privacy, offline usage
- Setup: https://ollama.ai

## Project Structure

```
neuravox/
├── modules/               # Core functionality
│   ├── processor/         # Audio processing module
│   │   ├── audio_splitter.py      # Silence detection & splitting
│   │   ├── audio_splitter_cli.py  # Original CLI (preserved)
│   │   └── metadata_output.py     # Metadata generation
│   ├── transcriber/       # Transcription module
│   │   ├── engine.py              # Core transcription engine
│   │   ├── models/                # AI model implementations
│   │   └── cli.py                 # Original CLI (preserved)
│   └── shared/            # Shared components
│       ├── config.py              # Configuration management
│       ├── metadata.py            # Metadata structures
│       ├── progress.py            # Progress tracking
│       └── file_utils.py          # File utilities
├── core/                  # Pipeline orchestration
│   ├── pipeline.py                # Main workflow orchestrator
│   ├── state_manager.py           # SQLite state tracking
│   └── exceptions.py              # Custom exceptions
├── cli/                   # Command-line interface
│   └── main.py                    # Unified CLI
├── config/                # Configuration files
│   ├── default.yaml               # Default settings
│   └── prompts.toml               # AI prompts
├── tests/                 # Test suite
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── generate_test_audio.py     # Test fixture generator
└── workspace/             # User workspace (created on init)
    ├── input/                     # Input audio files
    ├── processed/                 # Processed chunks
    └── transcribed/               # Final transcripts
```

## Development

### Setup Development Environment

```bash
# Clone and install in development mode
git clone <repository-url>
cd neuravox
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Running Tests

```bash
# Generate test audio files
python tests/generate_test_audio.py

# Run all tests
python run_tests.py

# Run specific test types
python run_tests.py unit -v      # Unit tests only
python run_tests.py integration -v # Integration tests only

# Run with pytest directly
pytest tests/unit -v
pytest tests/integration -v
```

### Code Quality

```bash
# Lint code
ruff check .

# Format code
ruff format .

# Type checking (if mypy installed)
mypy modules/ core/ cli/
```

### Testing Approach

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test full pipeline with mocked AI services
- **Test Fixtures**: Generated audio files for reproducible testing
- **Coverage**: Aim for >80% code coverage

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`python run_tests.py`)
5. Commit with meaningful messages
6. Push to your fork
7. Create a Pull Request

## Troubleshooting

### Common Issues

#### "API key not configured"
- Ensure environment variables are set: `echo $GOOGLE_API_KEY`
- Check .env file is in the project root
- Restart terminal after setting environment variables

#### "Audio file not found"
- Use absolute paths or place files in workspace input directory
- Check file permissions
- Ensure file extension is supported (.mp3, .wav, .flac, etc.)

#### "No silence detected"
- File may not have 25+ second silence gaps
- Try adjusting `min_silence_duration` in config
- Use lower `silence_threshold` for quieter audio

#### "Import error" or "Module not found"
- Ensure installation with `-e` flag: `pip install -e .`
- Activate virtual environment
- Check Python version (3.12+)

### Getting Help

- Check the [Phase 1 documentation](Phase_1.md) for detailed implementation info
- Review [TODO.md](TODO.md) for known issues and planned features
- Submit issues on GitHub with:
  - Error messages
  - Steps to reproduce
  - System information (OS, Python version)

## Performance Tips

- **Large Files**: Files over 1GB will show a warning. Consider splitting manually first.
- **Batch Processing**: Process multiple files at once for better efficiency
- **Model Selection**: Google Gemini is fastest for long files, Whisper for short clips
- **Concurrent Processing**: Adjust `max_concurrent` based on your system resources

## Roadmap

### Phase 1 (Current - 95% Complete)
- ✅ Core audio processing pipeline
- ✅ Multi-model transcription support
- ✅ Unified CLI interface
- ✅ State management and resume capability
- ✅ Comprehensive test suite
- 🔲 Complete documentation and tutorials

### Phase 2 (Planned)
- REST API for web integration
- Real-time progress via WebSocket
- Web-based file upload interface
- Cloud storage integration

### Phase 3 (Future)
- Mobile app support
- Multi-user collaboration
- Advanced audio analysis features
- Custom model training support

## License

MIT License - see LICENSE file for details.

## Module-Specific Usage (Legacy)

The platform integrates two previously standalone modules that can still be used independently:

### Audio Processor Module
```bash
cd audio_processor
uv run python audio_splitter_cli.py process --interactive
```

### AI Transcriber Module  
```bash
cd ai_transcriber
audio-transcriber interactive
```

For new projects, use the unified `neuravox` command instead.

## Acknowledgments

- Built on the foundations of `audio_processor` and `ai_transcriber` modules
- Uses librosa for audio processing
- Integrates with Google, OpenAI, and Ollama APIs
- Rich CLI powered by Typer and Rich libraries