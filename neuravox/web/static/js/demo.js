/**
 * Main Demo Application
 * Orchestrates the entire file upload -> configure -> process -> results workflow
 */

class NeuravoxDemo {
    constructor() {
        this.api = new NeuravoxAPI();
        this.config = new ConfigManager();
        this.currentFile = null;
        this.uploadedFileId = null;
        this.currentJob = null;
        this.pollInterval = null;
        
        this.initializeEventListeners();
        this.showSection('upload');
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // File upload
        this.setupFileUpload();
        
        // Configuration
        document.getElementById('start-processing').addEventListener('click', () => {
            this.startProcessing();
        });
        
        // Results
        document.getElementById('download-transcript').addEventListener('click', () => {
            this.downloadTranscript();
        });
        
        document.getElementById('download-audio').addEventListener('click', () => {
            this.downloadAudioFiles();
        });
        
        document.getElementById('start-new').addEventListener('click', () => {
            this.startNew();
        });
        
        // File change
        document.getElementById('change-file').addEventListener('click', () => {
            this.changeFile();
        });
    }

    /**
     * Setup file upload functionality
     */
    setupFileUpload() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        
        // Click to upload
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelection(e.target.files[0]);
            }
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                this.handleFileSelection(e.dataTransfer.files[0]);
            }
        });
    }

    /**
     * Handle file selection and validation
     */
    async handleFileSelection(file) {
        // Validate file type
        if (!NeuravoxAPI.isValidAudioFile(file)) {
            this.showError('Please select a valid audio file (MP3, WAV, FLAC, M4A, OGG, OPUS, WMA, AAC, MP4)');
            return;
        }
        
        // Validate file size (1GB limit)
        const maxSize = 1024 * 1024 * 1024; // 1GB
        if (file.size > maxSize) {
            this.showError('File size must be less than 1GB');
            return;
        }
        
        this.currentFile = file;
        this.showFileInfo(file);
        
        // Upload file immediately
        try {
            await this.uploadFile(file);
            this.showSection('config');
        } catch (error) {
            this.showEnhancedError(error, 'File Upload');
        }
    }

    /**
     * Upload file to API
     */
    async uploadFile(file) {
        try {
            this.showUploadProgress(true);
            
            const response = await this.api.uploadFile(file);
            this.uploadedFileId = response.id;
            
            this.showUploadProgress(false);
            console.log('File uploaded successfully:', response);
        } catch (error) {
            this.showUploadProgress(false);
            throw error;
        }
    }

    /**
     * Start processing job
     */
    async startProcessing() {
        if (!this.uploadedFileId) {
            this.showError('No file uploaded');
            return;
        }
        
        // Validate configuration
        if (!this.config.validateConfig()) {
            this.showError('Please check your configuration settings');
            return;
        }
        
        try {
            // Build job payload
            const jobPayload = this.config.buildJobPayload([this.uploadedFileId]);
            
            // Create job
            const jobResponse = await this.api.createJob(jobPayload);
            this.currentJob = jobResponse;
            
            console.log('Job created:', jobResponse);
            
            // Show progress section
            this.showSection('progress');
            this.setupJobInfo(jobResponse);
            
            // Start polling for progress
            this.startJobPolling(jobResponse.job_id);
            
        } catch (error) {
            this.showEnhancedError(error, 'Start Processing');
        }
    }

    /**
     * Start polling job status
     */
    async startJobPolling(jobId) {
        try {
            const job = await this.api.pollJobStatus(jobId, {
                interval: 2000,
                maxAttempts: 150,
                onProgress: (job) => this.updateProgress(job),
                onStatusChange: (status, job) => this.updateJobStatus(status, job)
            });
            
            // Job completed successfully
            this.handleJobCompletion(job);
            
        } catch (error) {
            this.handleJobError(error);
        }
    }

    /**
     * Update progress display
     */
    updateProgress(job) {
        const progressFill = document.getElementById('progress-fill');
        const progressMessage = document.getElementById('progress-message');
        const progressPercent = document.getElementById('progress-percent');
        
        let progress = 0;
        let message = 'Processing...';
        
        // Calculate progress based on job status
        switch (job.status) {
            case 'pending':
                progress = 5;
                message = 'Job queued...';
                break;
            case 'running':
                // Try to get more specific progress if available
                if (job.result_summary && job.result_summary.progress) {
                    progress = 10 + (job.result_summary.progress * 0.8); // 10-90%
                    message = `Processing... ${job.result_summary.current_stage || ''}`;
                } else {
                    progress = 50;
                    message = 'Processing audio...';
                }
                break;
            case 'completed':
                progress = 100;
                message = 'Processing complete!';
                break;
            case 'failed':
                progress = 0;
                message = 'Processing failed';
                break;
            default:
                progress = 10;
                message = 'Processing...';
        }
        
        progressFill.style.width = `${progress}%`;
        progressMessage.textContent = message;
        progressPercent.textContent = `${Math.round(progress)}%`;
    }

    /**
     * Update job status in UI
     */
    updateJobStatus(status, job) {
        // Update stage indicators
        this.updateStageStatus('stage-upload', 'completed');
        
        if (status === 'running') {
            this.updateStageStatus('stage-processing', 'active');
            this.updateStageStatus('stage-transcription', 'pending');
        } else if (status === 'completed') {
            this.updateStageStatus('stage-processing', 'completed');
            this.updateStageStatus('stage-transcription', 'completed');
            this.updateStageStatus('stage-complete', 'completed');
        } else if (status === 'failed') {
            this.updateStageStatus('stage-processing', 'failed');
        }
        
        // Update job info
        document.getElementById('job-status').textContent = status;
    }

    /**
     * Update stage status
     */
    updateStageStatus(stageId, status) {
        const stage = document.getElementById(stageId);
        if (stage) {
            // Remove all status classes
            stage.classList.remove('pending', 'active', 'completed', 'failed');
            // Add new status
            stage.classList.add(status);
            
            // Update status text
            const statusSpan = stage.querySelector('.stage-status');
            if (statusSpan) {
                statusSpan.textContent = status;
            }
        }
    }

    /**
     * Setup job info display
     */
    setupJobInfo(job) {
        document.getElementById('job-id').textContent = job.job_id;
        document.getElementById('job-status').textContent = job.status;
        document.getElementById('job-created').textContent = new Date(job.created_at).toLocaleString();
        document.getElementById('job-info').style.display = 'block';
    }

    /**
     * Handle successful job completion
     */
    async handleJobCompletion(job) {
        console.log('Job completed:', job);
        
        try {
            // Get fresh job details for results
            const jobDetails = await this.api.getJobStatus(job.job_id);
            this.displayResults(jobDetails);
            this.showSection('results');
        } catch (error) {
            this.showEnhancedError(error, 'Load Results');
        }
    }

    /**
     * Handle job errors
     */
    handleJobError(error) {
        console.error('Job error:', error);
        this.showError(`Processing failed: ${error.message}`);
        this.updateStageStatus('stage-processing', 'failed');
    }

    /**
     * Display processing results
     */
    displayResults(job) {
        const resultsummary = document.getElementById('results-summary');
        const transcriptContent = document.getElementById('transcript-content');
        
        // Build results summary
        let summaryHTML = '<h3>Processing Summary</h3>';
        
        if (job.result_summary) {
            const summary = job.result_summary;
            summaryHTML += '<div class="summary-grid">';
            
            if (summary.total_duration) {
                summaryHTML += `<div class="summary-item"><strong>Duration:</strong> ${NeuravoxAPI.formatDuration(summary.total_duration)}</div>`;
            }
            
            if (summary.chunks_processed) {
                summaryHTML += `<div class="summary-item"><strong>Chunks Processed:</strong> ${summary.chunks_processed}</div>`;
            }
            
            if (summary.word_count) {
                summaryHTML += `<div class="summary-item"><strong>Word Count:</strong> ${summary.word_count.toLocaleString()}</div>`;
            }
            
            if (summary.transcription_model) {
                summaryHTML += `<div class="summary-item"><strong>Model Used:</strong> ${summary.transcription_model}</div>`;
            }
            
            summaryHTML += '</div>';
        }
        
        resultsummary.innerHTML = summaryHTML;
        
        // Display transcript
        if (job.result_data && job.result_data.results && job.result_data.results.length > 0) {
            const result = job.result_data.results[0];
            if (result.transcription) {
                transcriptContent.textContent = result.transcription;
            } else {
                transcriptContent.textContent = 'Transcript processing completed. Use the download button to access the full transcript.';
            }
        } else {
            transcriptContent.textContent = 'Transcript is ready for download.';
        }
        
        // Store job for download functionality
        this.currentJob = job;
    }

    /**
     * Download transcript files
     */
    async downloadTranscript() {
        if (!this.currentJob || !this.currentJob.output_files) {
            this.showError('No transcript files available');
            return;
        }
        
        try {
            // Find transcript files (markdown files)
            const transcriptFiles = this.currentJob.output_files.filter(file => 
                file.filename.endsWith('.md')
            );
            
            for (const file of transcriptFiles) {
                const blob = await this.api.downloadFile(file.id);
                this.downloadBlob(blob, file.filename);
            }
        } catch (error) {
            this.showEnhancedError(error, 'Download Transcript');
        }
    }

    /**
     * Download audio files
     */
    async downloadAudioFiles() {
        if (!this.currentJob || !this.currentJob.output_files) {
            this.showError('No audio files available');
            return;
        }
        
        try {
            // Find audio files
            const audioFiles = this.currentJob.output_files.filter(file => 
                file.filename.endsWith('.flac') || 
                file.filename.endsWith('.wav') || 
                file.filename.endsWith('.mp3')
            );
            
            for (const file of audioFiles) {
                const blob = await this.api.downloadFile(file.id);
                this.downloadBlob(blob, file.filename);
            }
        } catch (error) {
            this.showEnhancedError(error, 'Download Audio Files');
        }
    }

    /**
     * Download blob as file
     */
    downloadBlob(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    /**
     * Start new processing session
     */
    startNew() {
        // Reset state
        this.currentFile = null;
        this.uploadedFileId = null;
        this.currentJob = null;
        
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        
        // Reset form
        document.getElementById('file-input').value = '';
        this.config.applyConfig(this.config.getDefaultConfig());
        
        // Show upload section
        this.showSection('upload');
    }

    /**
     * Change current file
     */
    changeFile() {
        document.getElementById('file-input').click();
    }

    /**
     * Show specific section
     */
    showSection(sectionName) {
        const sections = ['upload', 'config', 'progress', 'results'];
        
        sections.forEach(section => {
            const element = document.getElementById(`${section}-section`);
            if (element) {
                element.style.display = section === sectionName ? 'block' : 'none';
            }
        });
    }

    /**
     * Show file information
     */
    showFileInfo(file) {
        document.getElementById('file-name').textContent = file.name;
        document.getElementById('file-size').textContent = NeuravoxAPI.formatFileSize(file.size);
        document.getElementById('upload-area').style.display = 'none';
        document.getElementById('file-info').style.display = 'flex';
    }

    /**
     * Show upload progress
     */
    showUploadProgress(show) {
        const uploadArea = document.getElementById('upload-area');
        if (show) {
            uploadArea.classList.add('loading');
        } else {
            uploadArea.classList.remove('loading');
        }
    }

    /**
     * Show simple error message (legacy method)
     */
    showError(message) {
        this.showEnhancedError({ message, type: 'simple_error' }, 'General');
    }
    
    /**
     * Show enhanced error message with debugging information
     */
    showEnhancedError(error, operation) {
        // Determine error type and message
        let errorType = 'error';
        let errorMessage = 'An unknown error occurred';
        let errorDetails = {};
        let retryable = false;
        
        if (error.isEnhanced) {
            errorType = error.type;
            errorMessage = error.message;
            errorDetails = {
                requestId: error.requestId,
                serverRequestId: error.serverRequestId,
                status: error.status,
                endpoint: error.endpoint,
                duration: error.duration,
                details: error.details
            };
            retryable = error.retryable;
        } else if (error.message) {
            errorMessage = error.message;
        } else if (typeof error === 'string') {
            errorMessage = error;
        }
        
        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification enhanced';
        
        const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        
        errorDiv.innerHTML = `
            <div class="error-content">
                <div class="error-header">
                    <span class="error-icon">${this._getErrorIcon(errorType)}</span>
                    <span class="error-title">${operation} Failed</span>
                    <button class="error-close" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="error-message">${errorMessage}</div>
                ${retryable ? '<div class="error-retry">This error may be temporary. You can try again.</div>' : ''}
                ${isDevelopment ? this._createErrorDetails(errorDetails) : ''}
                <div class="error-actions">
                    ${retryable ? '<button class="retry-btn" onclick="window.demo._retryLastOperation()">Retry</button>' : ''}
                    ${isDevelopment ? '<button class="debug-btn" onclick="window.demo._showDebugInfo()">Debug Info</button>' : ''}
                    <button class="export-btn" onclick="window.demo.api.exportRequestHistory()">Export Logs</button>
                </div>
            </div>
        `;
        
        // Add enhanced styles
        errorDiv.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: var(--error-color, #dc3545);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 1000;
            max-width: 450px;
            font-family: system-ui, -apple-system, sans-serif;
        `;
        
        // Style error header
        const errorHeader = errorDiv.querySelector('.error-header');
        errorHeader.style.cssText = `
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
        `;
        
        // Style close button
        const closeBtn = errorDiv.querySelector('.error-close');
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 1.25rem;
            cursor: pointer;
            margin-left: auto;
            padding: 0.25rem;
        `;
        
        // Style action buttons
        const actionBtns = errorDiv.querySelectorAll('.error-actions button');
        actionBtns.forEach(btn => {
            btn.style.cssText = `
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                padding: 0.4rem 0.8rem;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.85rem;
                margin-right: 0.5rem;
                margin-top: 0.5rem;
            `;
            
            btn.addEventListener('mouseenter', () => {
                btn.style.background = 'rgba(255,255,255,0.3)';
            });
            
            btn.addEventListener('mouseleave', () => {
                btn.style.background = 'rgba(255,255,255,0.2)';
            });
        });
        
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 10 seconds (longer for enhanced errors)
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 10000);
        
        // Store error for retry functionality
        this.lastError = { error, operation };
        
        console.error('Enhanced Demo Error:', {
            operation,
            type: errorType,
            message: errorMessage,
            details: errorDetails,
            retryable
        });
    }
    
    _getErrorIcon(errorType) {
        const icons = {
            'network_error': '🌐',
            'validation_error': '⚠️',
            'authentication_error': '🔒',
            'processing_error': '⚙️',
            'not_found': '❓',
            'rate_limit_error': '⏱️',
            'service_unavailable': '🚫',
            'simple_error': '⚠️'
        };
        return icons[errorType] || '❌';
    }
    
    _createErrorDetails(details) {
        if (!details || Object.keys(details).length === 0) {
            return '';
        }
        
        const filteredDetails = Object.entries(details)
            .filter(([key, value]) => value !== undefined && value !== null)
            .map(([key, value]) => `<div><strong>${key}:</strong> ${value}</div>`)
            .join('');
        
        return `
            <details class="error-details" style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.9;">
                <summary style="cursor: pointer; margin-bottom: 0.25rem;">Technical Details</summary>
                <div style="margin-left: 1rem;">${filteredDetails}</div>
            </details>
        `;
    }
    
    _retryLastOperation() {
        if (!this.lastError) {
            console.warn('No operation to retry');
            return;
        }
        
        const { operation } = this.lastError;
        
        // Simple retry logic - could be enhanced based on operation type
        if (operation === 'File Upload' && this.currentFile) {
            this.uploadFile(this.currentFile);
        } else if (operation === 'Start Processing') {
            this.startProcessing();
        } else {
            console.warn('Retry not implemented for operation:', operation);
        }
    }
    
    _showDebugInfo() {
        const debugInfo = {
            currentState: {
                currentFile: this.currentFile ? {
                    name: this.currentFile.name,
                    size: this.currentFile.size,
                    type: this.currentFile.type
                } : null,
                uploadedFileId: this.uploadedFileId,
                currentJob: this.currentJob
            },
            apiHistory: this.api.getRequestHistory().slice(0, 10), // Last 10 requests
            lastError: this.lastError,
            userAgent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString()
        };
        
        console.group('🐛 Neuravox Debug Information');
        console.log('Current State:', debugInfo.currentState);
        console.log('Recent API Requests:', debugInfo.apiHistory);
        console.log('Last Error:', debugInfo.lastError);
        console.log('Environment:', {
            userAgent: debugInfo.userAgent,
            url: debugInfo.url
        });
        console.groupEnd();
        
        // Also show in a modal for easier copying
        const debugText = JSON.stringify(debugInfo, null, 2);
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        modal.innerHTML = `
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 8px;
                max-width: 80vw;
                max-height: 80vh;
                overflow: auto;
                color: #333;
            ">
                <h3>Debug Information</h3>
                <textarea readonly style="
                    width: 100%;
                    height: 400px;
                    font-family: monospace;
                    font-size: 12px;
                    border: 1px solid #ccc;
                    padding: 1rem;
                ">${debugText}</textarea>
                <div style="margin-top: 1rem; text-align: right;">
                    <button onclick="navigator.clipboard.writeText('${debugText.replace(/'/g, "\\'")}')">Copy to Clipboard</button>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
}

// Initialize the demo when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.demo = new NeuravoxDemo();
});

// Add CSS for additional styling needed by JavaScript
document.addEventListener('DOMContentLoaded', () => {
    const additionalStyles = `
        <style>
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .summary-item {
            padding: 0.75rem;
            background: white;
            border-radius: 6px;
            border: 1px solid var(--border);
        }
        
        .summary-item strong {
            color: var(--text-primary);
        }
        
        input.invalid {
            border-color: var(--error-color) !important;
            box-shadow: 0 0 0 3px rgb(239 68 68 / 0.1) !important;
        }
        
        input.valid {
            border-color: var(--success-color) !important;
        }
        
        .error-message {
            display: block;
            margin-top: 0.25rem;
            font-size: 0.875rem;
            color: var(--error-color);
        }
        </style>
    `;
    
    document.head.insertAdjacentHTML('beforeend', additionalStyles);
});