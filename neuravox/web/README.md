# Neuravox Web Demo Interface

A web-based demonstration interface for the Neuravox audio processing and transcription API. This interface provides an intuitive workflow for uploading audio files, configuring processing parameters, monitoring progress, and downloading results.

## Features

### 🎯 Complete Workflow
- **File Upload**: Drag-and-drop or click to upload audio files
- **Configuration**: Interactive settings matching CLI `--interactive` mode
- **Progress Tracking**: Real-time job monitoring with visual progress indicators
- **Results Display**: Transcript preview and file downloads

### 🔧 Configuration Options

#### Audio Processing
- **Silence Threshold**: Sensitivity for silence detection (0.001-1.0)
- **Silence Duration**: Minimum silence length for chunk boundaries (0.1-300s)
- **Sample Rate**: Target audio sample rate (8kHz-48kHz)
- **Output Format**: Audio output format (FLAC, WAV, MP3)
- **Normalization**: Audio level normalization

#### Transcription
- **Model Selection**: Choose from Google Gemini, OpenAI Whisper, or local Whisper models
- **Concurrency**: Control parallel transcription jobs (1-10)
- **Chunk Processing**: Enable/disable audio chunking
- **Timestamps**: Include word-level timestamps
- **Chunk Combination**: Merge individual chunk transcriptions

### 📱 User Interface
- **Responsive Design**: Works on desktop and mobile devices
- **Step-by-Step Workflow**: Clear progression through upload → configure → process → results
- **Real-time Updates**: Live progress tracking and status updates
- **Error Handling**: User-friendly error messages and validation

## File Structure

```
neuravox/web/
├── index.html              # Main demo interface
├── static/
│   ├── css/
│   │   └── demo.css        # Styling and responsive design
│   └── js/
│       ├── api.js          # API client for Neuravox backend
│       ├── config.js       # Configuration management and validation
│       └── demo.js         # Main application logic
└── README.md               # This file
```

## Usage

### 1. Start the Neuravox API Server

First, ensure the Neuravox API server is running:

```bash
# From the project root
python -m neuravox api
```

The API will be available at `http://localhost:8000` by default.

### 2. Serve the Web Interface

Serve the web directory using any static file server. For development:

```bash
# Using Python's built-in server
cd neuravox/web
python -m http.server 8080

# Using Node.js serve (if installed)
npx serve .

# Using any other static file server
```

### 3. Access the Demo

Open your browser and navigate to the served address (e.g., `http://localhost:8080`).

## API Integration

The web interface communicates with the Neuravox API using these endpoints:

- `POST /api/v1/files/upload` - Upload audio files
- `POST /api/v1/processing/pipeline` - Create processing jobs
- `GET /api/v1/jobs/{job_id}` - Monitor job progress
- `GET /api/v1/files/{file_id}/download` - Download results
- `GET /api/v1/config/models` - Get available models

## Configuration Mapping

The web interface configuration maps directly to the CLI interactive mode:

| Web Interface | CLI Interactive | API Parameter |
|---------------|-----------------|---------------|
| Silence Threshold | "Silence threshold" | `processing_config.silence_threshold` |
| Min Silence Duration | "Minimum silence duration" | `processing_config.min_silence_duration` |
| Sample Rate | "Sample rate" | `processing_config.sample_rate` |
| Output Format | "Output format" | `processing_config.output_format` |
| Model Selection | "Choose model" | `transcription_config.model` |
| Max Concurrent | "Maximum concurrent" | `transcription_config.max_concurrent` |

## Supported File Formats

**Input**: MP3, WAV, FLAC, M4A, OGG, OPUS, WMA, AAC, MP4  
**Output**: Markdown transcripts, FLAC/WAV/MP3 audio chunks  
**Size Limit**: 1GB per file

## Browser Compatibility

- **Chrome/Edge**: Full support
- **Firefox**: Full support  
- **Safari**: Full support
- **Mobile Browsers**: Responsive design with touch support

## Development

### Architecture

The web interface is built with vanilla JavaScript using a modular architecture:

- **NeuravoxAPI**: HTTP client for API communication
- **ConfigManager**: Configuration validation and form management
- **NeuravoxDemo**: Main application orchestration

### Key Features

- **File Upload**: Drag-and-drop with validation and progress tracking
- **Real-time Polling**: Automatic job status updates every 2 seconds
- **Error Handling**: Comprehensive error display and recovery
- **Progress Visualization**: Multi-stage progress with visual indicators
- **Download Management**: Automatic file downloads with proper naming

### Customization

The interface can be customized by modifying:

- **Styling**: Edit `static/css/demo.css` for visual changes
- **Configuration**: Modify `ConfigManager` class for different defaults
- **API Endpoints**: Update `NeuravoxAPI` base URL for different backends
- **Workflow**: Adjust `NeuravoxDemo` for different user flows

## Future Enhancements

See `FUTURE_IMPROVEMENTS.md` for planned features:

- **Real-time Progress**: Server-Sent Events for live updates
- **FLAC Download Management**: Enhanced audio file download options
- **Batch Processing**: Multiple file uploads and processing
- **Advanced Configuration**: Extended model and processing options

## Production Deployment

For production use:

1. **Static Hosting**: Deploy to CDN or static hosting service
2. **API Configuration**: Update API base URL for production backend
3. **HTTPS**: Ensure secure connections for file uploads
4. **Error Monitoring**: Add application monitoring and error tracking
5. **Performance**: Consider asset optimization and caching strategies