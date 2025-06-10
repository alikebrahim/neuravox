"""Configuration management endpoints"""

from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Depends

from neuravox.shared.config import UnifiedConfig
from neuravox.api.models.responses import ConfigResponse, ModelInfoResponse
from neuravox.api.middleware.auth import require_api_key


router = APIRouter()


class UpdateConfigRequest(BaseModel):
    """Request to update configuration"""
    processing: Optional[Dict[str, Any]] = Field(None, description="Processing configuration updates")
    transcription: Optional[Dict[str, Any]] = Field(None, description="Transcription configuration updates")
    workspace: Optional[str] = Field(None, description="Workspace path update")


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get current configuration"""
    
    try:
        config = UnifiedConfig()
        
        # Convert models to response format
        models = []
        for key, model_config in config.models.items():
            # Check model availability
            try:
                from neuravox.transcriber.engine import AudioTranscriber
                transcriber = AudioTranscriber(config)
                available = transcriber.validate_model(key)
            except Exception:
                available = False
            
            models.append(ModelInfoResponse(
                key=key,
                name=model_config.name,
                provider=model_config.provider,
                model_id=model_config.model_id,
                available=available,
                parameters=model_config.parameters
            ))
        
        return ConfigResponse(
            workspace=str(config.workspace),
            processing={
                "silence_threshold": config.processing.silence_threshold,
                "min_silence_duration": config.processing.min_silence_duration,
                "sample_rate": config.processing.sample_rate,
                "output_format": config.processing.output_format,
                "compression_level": config.processing.compression_level,
                "normalize": config.processing.normalize,
                "chunk_boundary": config.processing.chunk_boundary
            },
            transcription={
                "default_model": config.transcription.default_model,
                "max_concurrent": config.transcription.max_concurrent,
                "chunk_processing": config.transcription.chunk_processing,
                "combine_chunks": config.transcription.combine_chunks,
                "include_timestamps": config.transcription.include_timestamps
            },
            models=models
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.get("/models")
async def list_models():
    """List available transcription models"""
    
    try:
        config = UnifiedConfig()
        
        models = []
        for key, model_config in config.models.items():
            # Check model availability
            try:
                from neuravox.transcriber.engine import AudioTranscriber
                transcriber = AudioTranscriber(config)
                available = transcriber.validate_model(key)
            except Exception:
                available = False
            
            models.append({
                "key": key,
                "name": model_config.name,
                "provider": model_config.provider,
                "model_id": model_config.model_id,
                "available": available,
                "parameters": model_config.parameters
            })
        
        return {
            "models": models,
            "total": len(models),
            "available": len([m for m in models if m["available"]])
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.put("/config", response_model=ConfigResponse)
async def update_config(
    request: UpdateConfigRequest,
    _api_key = Depends(require_api_key)
):
    """Update configuration (mirrors CLI 'config' command with --set)"""
    
    try:
        import yaml
        
        config = UnifiedConfig()
        config_data = {}
        
        # Load existing config if it exists
        if config.config_path.exists():
            with open(config.config_path) as f:
                config_data = yaml.safe_load(f) or {}
        
        # Apply updates
        if request.processing:
            if "processing" not in config_data:
                config_data["processing"] = {}
            config_data["processing"].update(request.processing)
        
        if request.transcription:
            if "transcription" not in config_data:
                config_data["transcription"] = {}
            config_data["transcription"].update(request.transcription)
        
        if request.workspace:
            config_data["workspace"] = request.workspace
        
        # Ensure config directory exists
        config.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write updated config
        with open(config.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        # Reload config to get updated values
        updated_config = UnifiedConfig()
        
        # Return updated configuration using existing get_config logic
        return await get_config()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@router.get("/config/options")
async def get_config_options():
    """Get available configuration options (for interactive mode support)"""
    
    return {
        "processing": {
            "silence_threshold": {
                "type": "float",
                "default": 0.01,
                "range": [0.001, 1.0],
                "description": "RMS threshold for silence detection"
            },
            "min_silence_duration": {
                "type": "float",
                "default": 25.0,
                "range": [1.0, 300.0],
                "description": "Minimum silence duration in seconds"
            },
            "sample_rate": {
                "type": "integer",
                "default": 16000,
                "options": [8000, 16000, 22050, 44100, 48000],
                "description": "Output sample rate in Hz"
            },
            "output_format": {
                "type": "string",
                "default": "flac",
                "options": ["flac", "wav", "mp3"],
                "description": "Output audio format"
            },
            "normalize": {
                "type": "boolean",
                "default": True,
                "description": "Normalize audio levels"
            }
        },
        "transcription": {
            "default_model": {
                "type": "string",
                "default": "google-gemini",
                "options": ["google-gemini", "openai-whisper", "whisper-base", "whisper-turbo"],
                "description": "Default transcription model"
            },
            "max_concurrent": {
                "type": "integer",
                "default": 3,
                "range": [1, 10],
                "description": "Maximum concurrent transcriptions"
            },
            "chunk_processing": {
                "type": "boolean",
                "default": True,
                "description": "Process audio in chunks"
            },
            "combine_chunks": {
                "type": "boolean",
                "default": True,
                "description": "Combine chunk transcriptions"
            },
            "include_timestamps": {
                "type": "boolean",
                "default": True,
                "description": "Include timestamps in output"
            }
        }
    }