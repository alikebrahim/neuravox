"""
Central constants module for the Neuravox platform
"""


class AudioProcessing:
    """Audio processing related constants"""
    DEFAULT_SILENCE_THRESHOLD = 0.01
    DEFAULT_MIN_SILENCE_DURATION = 25.0
    DEFAULT_SAMPLE_RATE = 16000
    ALTERNATIVE_SAMPLE_RATES = [22050, 44100]
    DEFAULT_CHUNK_DURATION = 30.0
    MIN_CHUNK_DURATION = 5.0
    KEEP_SILENCE_BUFFER = 1.0
    DEFAULT_COMPRESSION_LEVEL = 8
    SILENCE_MERGE_GAP_THRESHOLD = 1.0
    
    # Librosa analysis parameters
    HOP_LENGTH = 512
    FRAME_LENGTH = 2048
    
    # File size limits and thresholds
    LARGE_FILE_WARNING_MB = 1000
    FILE_HASH_CHUNK_SIZE = 8192
    BYTES_PER_KB = 1024
    BYTES_PER_MB = 1024 * 1024


class TranscriptionDefaults:
    """Transcription related defaults"""
    DEFAULT_MODEL = "google-gemini"
    MAX_CONCURRENT = 3
    CHUNK_PROCESSING = True
    COMBINE_CHUNKS = True
    INCLUDE_TIMESTAMPS = True
    
    # OpenAI specific
    OPENAI_MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    
    # Temperature settings
    GOOGLE_TEMPERATURE = 0.1
    OPENAI_TEMPERATURE = 0.0
    WHISPER_TEMPERATURE = 0.0
    
    # Whisper specific thresholds
    WHISPER_COMPRESSION_RATIO_THRESHOLD = 2.4
    WHISPER_LOGPROB_THRESHOLD = -1.0
    WHISPER_NO_SPEECH_THRESHOLD = 0.6


class FileFormats:
    """File format and extension constants"""
    # Audio file extensions
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.opus', '.wma', '.aac', '.mp4']
    
    # Output formats
    OUTPUT_FORMATS = ["flac", "wav", "mp3"]
    
    # SoundFile format constants
    FLAC_FORMAT = "FLAC"
    WAV_FORMAT = "WAV"
    MP3_FORMAT = "MP3"
    PCM_16_SUBTYPE = "PCM_16"


class EnvironmentVariables:
    """Environment variable names"""
    NEURAVOX_CONFIG = "NEURAVOX_CONFIG"
    NEURAVOX_WORKSPACE = "NEURAVOX_WORKSPACE"
    OPENAI_API_KEY = "OPENAI_API_KEY"
    GOOGLE_API_KEY = "GOOGLE_API_KEY"
    WHISPER_MODEL = "WHISPER_MODEL"
    WHISPER_DEVICE = "WHISPER_DEVICE"


class DirectoryNames:
    """Directory and file names"""
    CONFIG_DIR = ".neuravox"
    CONFIG_FILE = "config.yaml"
    ENV_FILE = ".env"
    WORKSPACE_DIR = "workspace"
    INPUT_DIR = "input"
    PROCESSED_DIR = "processed"
    TRANSCRIBED_DIR = "transcribed"
    CHUNKS_DIR = "chunks"


class ModelIdentifiers:
    """Model and provider identifiers"""
    # Default model keys
    GOOGLE_GEMINI = "google-gemini"
    OPENAI_WHISPER = "openai-whisper"
    WHISPER_BASE = "whisper-base"
    WHISPER_TURBO = "whisper-turbo"
    
    # Model IDs
    GEMINI_MODEL_ID = "gemini-2.0-flash-exp"
    OPENAI_WHISPER_MODEL_ID = "whisper-1"
    
    # Providers
    GOOGLE_PROVIDER = "google"
    OPENAI_PROVIDER = "openai"
    WHISPER_LOCAL_PROVIDER = "whisper-local"
    
    # Whisper model sizes
    WHISPER_MODELS = {
        "tiny": "39M parameters - Fastest, lowest accuracy",
        "tiny.en": "39M parameters - English-only, slightly better for English",
        "base": "74M parameters - Fast, good accuracy",
        "base.en": "74M parameters - English-only, better for English",
        "small": "244M parameters - Good balance of speed and accuracy",
        "small.en": "244M parameters - English-only, better for English",
        "medium": "769M parameters - High accuracy, slower",
        "medium.en": "769M parameters - English-only, better for English",
        "large": "1550M parameters - Best accuracy, slowest",
        "large-v2": "1550M parameters - Improved large model",
        "large-v3": "1550M parameters - Latest large model",
        "turbo": "809M parameters - Optimized for speed"
    }


class FileNaming:
    """File naming patterns and conventions"""
    CHUNK_PATTERN = "chunk_{:03d}.flac"
    FULL_FILE_NAME = "full-file.flac"
    TRANSCRIPT_SUFFIX = "_transcript.md"
    METADATA_SUFFIX = "_metadata.json"
    MANIFEST_SUFFIX = "_manifest.json"
    PROCESSING_METADATA_FILE = "processing_metadata.json"
    TRANSCRIPTION_METADATA_SUFFIX = "_transcription_metadata.json"
    CHUNKS_DETAIL_SUFFIX = "_chunks.json"


class DefaultPrompts:
    """Default prompt templates"""
    GOOGLE_TRANSCRIPTION = """Please transcribe the audio in this file. Provide only the transcribed text without any additional commentary, explanations, or formatting. 
If there are multiple speakers, indicate speaker changes with [Speaker 1], [Speaker 2], etc.
Ensure the transcription is accurate and includes proper punctuation."""


class ResponseFormats:
    """API response format constants"""
    TEXT = "text"
    JSON = "json"
    VERBOSE_JSON = "verbose_json"


class WhisperTasks:
    """Whisper task types"""
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"


class ChunkBoundaryMethods:
    """Chunk boundary detection methods"""
    SIMPLE = "simple"
    ADVANCED = "advanced"


class ProcessingStages:
    """Pipeline processing stage names"""
    INITIALIZED = "initialized"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"