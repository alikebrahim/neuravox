/**
 * Configuration Management
 * Handles form validation and configuration building
 */

class ConfigManager {
    constructor() {
        this.config = this.getDefaultConfig();
        this.initializeEventListeners();
    }

    /**
     * Get default configuration matching CLI interactive defaults
     */
    getDefaultConfig() {
        return {
            processing: {
                silence_threshold: 0.01,
                min_silence_duration: 25.0,
                sample_rate: 16000,
                output_format: "flac",
                normalize: true,
                compression_level: 8,
                chunk_boundary: "simple"
            },
            transcription: {
                default_model: "google-gemini",
                max_concurrent: 3,
                chunk_processing: true,
                combine_chunks: true,
                include_timestamps: true,
                language: null,
                temperature: null
            }
        };
    }

    /**
     * Initialize form event listeners
     */
    initializeEventListeners() {
        // Slider value updates
        this.setupSlider('silence-threshold', 'silence-threshold-value');
        this.setupSlider('max-concurrent', 'max-concurrent-value');

        // Chunk processing dependency
        this.setupChunkProcessingDependency();

        // Form validation
        this.setupFormValidation();
    }

    /**
     * Setup slider with live value display
     */
    setupSlider(sliderId, valueId) {
        const slider = document.getElementById(sliderId);
        const valueDisplay = document.getElementById(valueId);
        
        if (slider && valueDisplay) {
            const updateValue = () => {
                valueDisplay.textContent = slider.value;
            };
            
            slider.addEventListener('input', updateValue);
            updateValue(); // Set initial value
        }
    }

    /**
     * Setup chunk processing dependency logic
     */
    setupChunkProcessingDependency() {
        const chunkProcessing = document.getElementById('chunk-processing');
        const combineChunksRow = document.getElementById('combine-chunks-row');
        
        if (chunkProcessing && combineChunksRow) {
            const toggleCombineChunks = () => {
                if (chunkProcessing.checked) {
                    combineChunksRow.style.display = 'block';
                } else {
                    combineChunksRow.style.display = 'none';
                    // Automatically check combine chunks when processing is disabled
                    document.getElementById('combine-chunks').checked = true;
                }
            };
            
            chunkProcessing.addEventListener('change', toggleCombineChunks);
            toggleCombineChunks(); // Set initial state
        }
    }

    /**
     * Setup form validation
     */
    setupFormValidation() {
        // Number input validation
        const numberInputs = document.querySelectorAll('input[type="number"]');
        numberInputs.forEach(input => {
            input.addEventListener('blur', () => this.validateNumberInput(input));
            input.addEventListener('input', () => this.validateNumberInput(input));
        });

        // Range input validation
        const rangeInputs = document.querySelectorAll('input[type="range"]');
        rangeInputs.forEach(input => {
            input.addEventListener('input', () => this.validateRangeInput(input));
        });
    }

    /**
     * Validate number inputs
     */
    validateNumberInput(input) {
        const min = parseFloat(input.min);
        const max = parseFloat(input.max);
        const value = parseFloat(input.value);
        
        let isValid = true;
        let errorMessage = '';
        
        if (isNaN(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid number';
        } else if (!isNaN(min) && value < min) {
            isValid = false;
            errorMessage = `Value must be at least ${min}`;
            input.value = min;
        } else if (!isNaN(max) && value > max) {
            isValid = false;
            errorMessage = `Value must be no more than ${max}`;
            input.value = max;
        }
        
        this.setInputValidation(input, isValid, errorMessage);
        return isValid;
    }

    /**
     * Validate range inputs
     */
    validateRangeInput(input) {
        const min = parseFloat(input.min);
        const max = parseFloat(input.max);
        const value = parseFloat(input.value);
        
        const isValid = !isNaN(value) && value >= min && value <= max;
        this.setInputValidation(input, isValid);
        return isValid;
    }

    /**
     * Set input validation state
     */
    setInputValidation(input, isValid, errorMessage = '') {
        // Remove existing validation classes
        input.classList.remove('invalid', 'valid');
        
        // Remove existing error message
        const existingError = input.parentNode.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        if (isValid) {
            input.classList.add('valid');
        } else {
            input.classList.add('invalid');
            
            if (errorMessage) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = errorMessage;
                errorDiv.style.color = 'var(--error-color)';
                errorDiv.style.fontSize = '0.875rem';
                errorDiv.style.marginTop = '0.25rem';
                input.parentNode.appendChild(errorDiv);
            }
        }
    }

    /**
     * Get current configuration from form
     */
    getCurrentConfig() {
        const config = JSON.parse(JSON.stringify(this.getDefaultConfig())); // Deep copy
        
        // Processing configuration
        config.processing.silence_threshold = parseFloat(document.getElementById('silence-threshold').value);
        config.processing.min_silence_duration = parseFloat(document.getElementById('min-silence-duration').value);
        config.processing.sample_rate = parseInt(document.getElementById('sample-rate').value);
        config.processing.output_format = document.getElementById('output-format').value;
        config.processing.normalize = document.getElementById('normalize').checked;
        
        // Transcription configuration
        const selectedModel = document.querySelector('input[name="model"]:checked');
        if (selectedModel) {
            config.transcription.default_model = selectedModel.value;
        }
        
        config.transcription.max_concurrent = parseInt(document.getElementById('max-concurrent').value);
        config.transcription.chunk_processing = document.getElementById('chunk-processing').checked;
        config.transcription.combine_chunks = document.getElementById('combine-chunks').checked;
        config.transcription.include_timestamps = document.getElementById('include-timestamps').checked;
        
        return config;
    }

    /**
     * Apply configuration to form
     */
    applyConfig(config) {
        // Processing configuration
        if (config.processing) {
            this.setInputValue('silence-threshold', config.processing.silence_threshold);
            this.setInputValue('min-silence-duration', config.processing.min_silence_duration);
            this.setInputValue('sample-rate', config.processing.sample_rate);
            this.setInputValue('output-format', config.processing.output_format);
            this.setInputValue('normalize', config.processing.normalize);
        }
        
        // Transcription configuration
        if (config.transcription) {
            const modelRadio = document.querySelector(`input[name="model"][value="${config.transcription.default_model}"]`);
            if (modelRadio) {
                modelRadio.checked = true;
            }
            
            this.setInputValue('max-concurrent', config.transcription.max_concurrent);
            this.setInputValue('chunk-processing', config.transcription.chunk_processing);
            this.setInputValue('combine-chunks', config.transcription.combine_chunks);
            this.setInputValue('include-timestamps', config.transcription.include_timestamps);
        }
        
        // Update slider displays
        this.updateSliderDisplays();
        
        // Update chunk processing dependency
        this.setupChunkProcessingDependency();
    }

    /**
     * Set input value by ID
     */
    setInputValue(inputId, value) {
        const input = document.getElementById(inputId);
        if (input) {
            if (input.type === 'checkbox') {
                input.checked = Boolean(value);
            } else {
                input.value = value;
            }
        }
    }

    /**
     * Update slider value displays
     */
    updateSliderDisplays() {
        const sliders = [
            { id: 'silence-threshold', valueId: 'silence-threshold-value' },
            { id: 'max-concurrent', valueId: 'max-concurrent-value' }
        ];
        
        sliders.forEach(({ id, valueId }) => {
            const slider = document.getElementById(id);
            const valueDisplay = document.getElementById(valueId);
            if (slider && valueDisplay) {
                valueDisplay.textContent = slider.value;
            }
        });
    }

    /**
     * Validate entire configuration
     */
    validateConfig() {
        const inputs = document.querySelectorAll('input[type="number"], input[type="range"]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (input.type === 'number') {
                if (!this.validateNumberInput(input)) {
                    isValid = false;
                }
            } else if (input.type === 'range') {
                if (!this.validateRangeInput(input)) {
                    isValid = false;
                }
            }
        });
        
        // Check required fields
        const selectedModel = document.querySelector('input[name="model"]:checked');
        if (!selectedModel) {
            isValid = false;
            console.error('No transcription model selected');
        }
        
        return isValid;
    }

    /**
     * Build API request payload from configuration
     */
    buildJobPayload(fileIds) {
        const config = this.getCurrentConfig();
        
        return {
            file_ids: fileIds,
            config: {
                processing: {
                    silence_threshold: config.processing.silence_threshold,
                    min_silence_duration: config.processing.min_silence_duration,
                    sample_rate: config.processing.sample_rate,
                    output_format: config.processing.output_format,
                    normalize: config.processing.normalize,
                    compression_level: config.processing.compression_level,
                    chunk_boundary: config.processing.chunk_boundary
                },
                transcription: {
                    model: config.transcription.default_model,
                    max_concurrent: config.transcription.max_concurrent,
                    chunk_processing: config.transcription.chunk_processing,
                    combine_chunks: config.transcription.combine_chunks,
                    include_timestamps: config.transcription.include_timestamps,
                    language: config.transcription.language,
                    temperature: config.transcription.temperature
                }
            }
        };
    }

    /**
     * Get configuration summary for display
     */
    getConfigSummary() {
        const config = this.getCurrentConfig();
        
        return {
            processing: [
                `Silence Threshold: ${config.processing.silence_threshold}`,
                `Min Silence Duration: ${config.processing.min_silence_duration}s`,
                `Sample Rate: ${config.processing.sample_rate.toLocaleString()} Hz`,
                `Output Format: ${config.processing.output_format.toUpperCase()}`,
                `Normalize Audio: ${config.processing.normalize ? 'Yes' : 'No'}`
            ],
            transcription: [
                `Model: ${this.getModelDisplayName(config.transcription.default_model)}`,
                `Max Concurrent: ${config.transcription.max_concurrent}`,
                `Chunk Processing: ${config.transcription.chunk_processing ? 'Yes' : 'No'}`,
                `Combine Chunks: ${config.transcription.combine_chunks ? 'Yes' : 'No'}`,
                `Include Timestamps: ${config.transcription.include_timestamps ? 'Yes' : 'No'}`
            ]
        };
    }

    /**
     * Get display name for model
     */
    getModelDisplayName(modelKey) {
        const modelNames = {
            'google-gemini': 'Google Gemini Flash',
            'openai-whisper': 'OpenAI Whisper',
            'whisper-base': 'Whisper Base (Local)',
            'whisper-turbo': 'Whisper Turbo (Local)'
        };
        
        return modelNames[modelKey] || modelKey;
    }
}

// Export for use in other modules
window.ConfigManager = ConfigManager;