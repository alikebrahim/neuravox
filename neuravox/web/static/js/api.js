/**
 * Neuravox API Client
 * Handles communication with the Neuravox API
 */

class NeuravoxAPI {
    constructor(baseURL = '/api/v1') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
        this.requestHistory = [];
        this.maxHistorySize = 100;
    }

    /**
     * Generic API request handler with enhanced error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };
        
        const requestStart = Date.now();
        const requestId = this._generateRequestId();
        
        // Log request for debugging
        this._logRequest({
            id: requestId,
            method: config.method || 'GET',
            url: url,
            timestamp: requestStart,
            headers: config.headers
        });

        try {
            const response = await fetch(url, config);
            const duration = Date.now() - requestStart;
            
            // Extract request ID from response headers
            const serverRequestId = response.headers.get('X-Request-ID');
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                
                // Create enhanced error object
                const enhancedError = this._createEnhancedError({
                    response,
                    errorData,
                    requestId,
                    serverRequestId,
                    duration,
                    endpoint,
                    method: config.method || 'GET'
                });
                
                this._logError(enhancedError);
                throw enhancedError;
            }
            
            // Log successful response
            this._logResponse({
                id: requestId,
                serverRequestId,
                status: response.status,
                duration,
                contentType: response.headers.get('content-type')
            });

            // Handle different content types
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else if (contentType && contentType.includes('text/')) {
                return await response.text();
            } else {
                return await response.blob();
            }
        } catch (error) {
            const duration = Date.now() - requestStart;
            
            // Handle network errors
            if (!error.isEnhanced) {
                const enhancedError = this._createEnhancedError({
                    networkError: error,
                    requestId,
                    duration,
                    endpoint,
                    method: config.method || 'GET'
                });
                
                this._logError(enhancedError);
                throw enhancedError;
            }
            
            throw error;
        }
    }

    /**
     * Upload a file to the API
     */
    async uploadFile(file, progressCallback = null) {
        const formData = new FormData();
        formData.append('file', file);

        const config = {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set Content-Type for FormData
        };

        // Add progress tracking if callback provided
        if (progressCallback && typeof progressCallback === 'function') {
            config.onUploadProgress = progressCallback;
        }

        return await this.request('/upload', config);
    }

    /**
     * Get available transcription models
     */
    async getModels() {
        return await this.request('/config/models');
    }

    /**
     * Create a processing job
     */
    async createJob(jobData) {
        return await this.request('/processing/pipeline', {
            method: 'POST',
            body: JSON.stringify(jobData)
        });
    }

    /**
     * Get job status and details
     */
    async getJobStatus(jobId) {
        return await this.request(`/jobs/${jobId}`);
    }

    /**
     * List all jobs
     */
    async listJobs() {
        return await this.request('/jobs');
    }

    /**
     * Download a file by ID
     */
    async downloadFile(fileId) {
        return await this.request(`/files/${fileId}/download`, {
            headers: {}
        });
    }

    /**
     * Get file metadata
     */
    async getFileMetadata(fileId) {
        return await this.request(`/files/${fileId}`);
    }

    /**
     * Cancel a job
     */
    async cancelJob(jobId) {
        return await this.request(`/jobs/${jobId}/cancel`, {
            method: 'POST'
        });
    }

    /**
     * Get system health
     */
    async getHealth() {
        return await this.request('/health');
    }

    /**
     * Get system status
     */
    async getStatus() {
        return await this.request('/status');
    }

    /**
     * Poll job status with automatic retries
     */
    async pollJobStatus(jobId, options = {}) {
        const {
            interval = 2000, // 2 seconds
            maxAttempts = 150, // 5 minutes max
            onProgress = null,
            onStatusChange = null
        } = options;

        let attempts = 0;
        let lastStatus = null;

        return new Promise((resolve, reject) => {
            const poll = async () => {
                try {
                    attempts++;
                    
                    if (attempts > maxAttempts) {
                        reject(new Error('Polling timeout exceeded'));
                        return;
                    }

                    const job = await this.getJobStatus(jobId);
                    
                    // Notify of status changes
                    if (lastStatus !== job.status && onStatusChange) {
                        onStatusChange(job.status, job);
                    }
                    lastStatus = job.status;

                    // Notify of progress
                    if (onProgress) {
                        onProgress(job);
                    }

                    // Check if job is complete
                    if (job.status === 'completed') {
                        resolve(job);
                        return;
                    } else if (job.status === 'failed') {
                        reject(new Error(job.error_message || 'Job failed'));
                        return;
                    } else if (job.status === 'cancelled') {
                        reject(new Error('Job was cancelled'));
                        return;
                    }

                    // Continue polling
                    setTimeout(poll, interval);
                } catch (error) {
                    reject(error);
                }
            };

            poll();
        });
    }

    /**
     * Helper to format file size
     */
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Helper to format duration
     */
    static formatDuration(seconds) {
        if (!seconds || seconds < 0) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }

    /**
     * Helper to validate file type
     */
    static isValidAudioFile(file) {
        const validTypes = [
            'audio/mpeg', 'audio/mp3',
            'audio/wav', 'audio/wave',
            'audio/flac',
            'audio/mp4', 'audio/m4a',
            'audio/ogg', 'audio/oga',
            'audio/opus',
            'audio/x-ms-wma',
            'audio/aac'
        ];
        
        const validExtensions = [
            '.mp3', '.wav', '.flac', '.m4a', 
            '.ogg', '.opus', '.wma', '.aac', '.mp4'
        ];
        
        // Check MIME type
        if (validTypes.includes(file.type)) {
            return true;
        }
        
        // Fallback to extension check
        const fileName = file.name.toLowerCase();
        return validExtensions.some(ext => fileName.endsWith(ext));
    }

    /**
     * Helper to estimate processing time
     */
    static estimateProcessingTime(fileSizeBytes, durationSeconds = null) {
        // Rough estimates based on file size and typical processing times
        const sizeMB = fileSizeBytes / (1024 * 1024);
        
        // Base estimate: ~1-2 seconds per MB for processing + transcription
        let estimateSeconds = sizeMB * 1.5;
        
        // If we have duration, use it for better estimation
        if (durationSeconds) {
            // Typical ratio: processing time is 0.1-0.3x the audio duration
            const durationBasedEstimate = durationSeconds * 0.2;
            estimateSeconds = Math.max(estimateSeconds, durationBasedEstimate);
        }
        
        // Add base overhead
        estimateSeconds += 10;
        
        return Math.round(estimateSeconds);
    }
    
    /**
     * Enhanced error handling methods
     */
    _generateRequestId() {
        return 'req_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    _createEnhancedError({ response, errorData, networkError, requestId, serverRequestId, duration, endpoint, method }) {
        const error = new Error();
        error.isEnhanced = true;
        error.requestId = requestId;
        error.serverRequestId = serverRequestId;
        error.endpoint = endpoint;
        error.method = method;
        error.duration = duration;
        error.timestamp = new Date().toISOString();
        
        if (networkError) {
            // Network/connection error
            error.type = 'network_error';
            error.message = `Network error: ${networkError.message}`;
            error.originalError = networkError;
            error.retryable = true;
        } else if (response && errorData) {
            // API error response
            error.status = response.status;
            error.statusText = response.statusText;
            
            if (errorData.error) {
                // Structured error response
                error.type = errorData.error.type || 'api_error';
                error.message = errorData.error.message || 'Unknown API error';
                error.details = errorData.error.details || {};
                error.retryable = errorData.error.retryable || false;
                error.operation = errorData.error.operation;
            } else {
                // Legacy error response
                error.type = 'api_error';
                error.message = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
                error.details = errorData;
                error.retryable = response.status >= 500 || response.status === 429;
            }
        } else {
            // Unknown error
            error.type = 'unknown_error';
            error.message = 'An unknown error occurred';
            error.retryable = false;
        }
        
        return error;
    }
    
    _logRequest(requestInfo) {
        console.debug('API Request:', requestInfo);
        this._addToHistory({
            type: 'request',
            ...requestInfo
        });
    }
    
    _logResponse(responseInfo) {
        console.debug('API Response:', responseInfo);
        this._addToHistory({
            type: 'response',
            ...responseInfo
        });
    }
    
    _logError(error) {
        console.error('API Error:', {
            type: error.type,
            message: error.message,
            status: error.status,
            requestId: error.requestId,
            serverRequestId: error.serverRequestId,
            endpoint: error.endpoint,
            method: error.method,
            duration: error.duration,
            details: error.details,
            retryable: error.retryable
        });
        
        this._addToHistory({
            type: 'error',
            error: {
                type: error.type,
                message: error.message,
                status: error.status,
                requestId: error.requestId,
                serverRequestId: error.serverRequestId,
                endpoint: error.endpoint,
                method: error.method,
                duration: error.duration,
                retryable: error.retryable
            },
            timestamp: error.timestamp
        });
    }
    
    _addToHistory(entry) {
        this.requestHistory.unshift(entry);
        if (this.requestHistory.length > this.maxHistorySize) {
            this.requestHistory = this.requestHistory.slice(0, this.maxHistorySize);
        }
    }
    
    /**
     * Get request history for debugging
     */
    getRequestHistory() {
        return [...this.requestHistory];
    }
    
    /**
     * Export request history as JSON
     */
    exportRequestHistory() {
        const data = {
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            history: this.requestHistory
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `neuravox-api-history-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    /**
     * Clear request history
     */
    clearRequestHistory() {
        this.requestHistory = [];
    }
}

// Export for use in other modules
window.NeuravoxAPI = NeuravoxAPI;