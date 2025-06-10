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
            this.showError(`Upload failed: ${error.message}`);
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
            this.showError(`Failed to start processing: ${error.message}`);
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
            this.showError(`Failed to load results: ${error.message}`);
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
            this.showError(`Download failed: ${error.message}`);
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
            this.showError(`Download failed: ${error.message}`);
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
     * Show error message
     */
    showError(message) {
        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification';
        errorDiv.innerHTML = `
            <div class="error-content">
                <span class="error-icon">⚠️</span>
                <span class="error-message">${message}</span>
                <button class="error-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        // Add styles
        errorDiv.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: var(--error-color);
            color: white;
            padding: 1rem;
            border-radius: var(--radius);
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            max-width: 400px;
        `;
        
        errorDiv.querySelector('.error-content').style.cssText = `
            display: flex;
            align-items: center;
            gap: 0.75rem;
        `;
        
        errorDiv.querySelector('.error-close').style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 1.25rem;
            cursor: pointer;
            margin-left: auto;
        `;
        
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
        
        console.error('Demo Error:', message);
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