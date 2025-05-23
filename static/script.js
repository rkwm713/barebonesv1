document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const filename = document.getElementById('filename');
    const filesize = document.getElementById('filesize');
    const uploadButton = document.getElementById('upload-button');
    const uploadCard = document.getElementById('upload-card');
    const processingCard = document.getElementById('processing-card');
    const resultsCard = document.getElementById('results-card');
    const errorCard = document.getElementById('error-card');
    const progressBar = document.getElementById('progress-bar');
    const processingStatus = document.getElementById('processing-status');
    const downloadLinks = document.getElementById('download-links');
    const resetButton = document.getElementById('reset-button');
    const errorResetButton = document.getElementById('error-reset-button');
    const errorMessage = document.getElementById('error-message');

    // Current task ID
    let currentTaskId = null;
    let statusCheckInterval = null;

    // Event listeners for drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('drag-over');
    }

    function unhighlight() {
        dropArea.classList.remove('drag-over');
    }

    // Handle file drop
    dropArea.addEventListener('drop', handleDrop, false);
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            handleFiles(files);
        }
    }

    // Handle file browse
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFiles(this.files);
        }
    });

    // Click on drop area to trigger file input
    dropArea.addEventListener('click', function() {
        fileInput.click();
    });

    // Handle file selection
    function handleFiles(files) {
        const file = files[0];
        
        // Check if it's a JSON file
        if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
            showError('Please select a JSON file.');
            return;
        }
        
        // Display file info
        filename.textContent = file.name;
        filesize.textContent = formatFileSize(file.size);
        fileInfo.style.display = 'block';
        
        // Store the file for upload
        fileInput.files = files;
    }

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Handle upload button
    uploadButton.addEventListener('click', function() {
        if (!fileInput.files || fileInput.files.length === 0) {
            showError('Please select a file first.');
            return;
        }
        
        const file = fileInput.files[0];
        uploadFile(file);
    });

    // Upload file to server
    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        // Show processing card
        showProcessingCard();
        
        // Reset progress
        progressBar.style.width = '0%';
        
        // Send the file
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Upload failed');
            }
            return response.json();
        })
        .then(data => {
            currentTaskId = data.task_id;
            
            // Start checking status
            checkStatus();
            
            // Set interval to check status every 2 seconds
            statusCheckInterval = setInterval(checkStatus, 2000);
            
            // Simulate progress for visual feedback
            simulateProgress();
        })
        .catch(error => {
            console.error('Error:', error);
            showErrorCard('Failed to upload the file. Please try again.');
        });
    }

    // Check processing status
    function checkStatus() {
        if (!currentTaskId) return;
        
        fetch(`/status/${currentTaskId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Status check failed');
                }
                return response.json();
            })
            .then(data => {
                updateStatus(data);
            })
            .catch(error => {
                console.error('Error checking status:', error);
                // Don't show error, just keep checking
            });
    }

    // Update UI based on status
    function updateStatus(data) {
        const status = data.status;
        
        if (status === 'processing') {
            processingStatus.textContent = 'Processing your file...';
        } else if (status === 'complete') {
            clearInterval(statusCheckInterval);
            showResultsCard(data.files);
            
            // Clean up task on server
            cleanupTask();
        } else if (status === 'failed') {
            clearInterval(statusCheckInterval);
            showErrorCard(data.error || 'Processing failed. Please try again.');
            
            // Clean up task on server
            cleanupTask();
        }
    }

    // Clean up task on server
    function cleanupTask() {
        if (!currentTaskId) return;
        
        fetch(`/cleanup/${currentTaskId}`, {
            method: 'POST'
        }).catch(error => {
            console.error('Error cleaning up task:', error);
        });
    }

    // Simulate progress for visual feedback
    function simulateProgress() {
        let progress = 0;
        const interval = setInterval(() => {
            progress += 5;
            if (progress > 90) {
                clearInterval(interval);
                return;
            }
            progressBar.style.width = `${progress}%`;
        }, 500);
    }

    // Show processing card
    function showProcessingCard() {
        fadeOut(uploadCard);
        setTimeout(() => {
            uploadCard.style.display = 'none';
            processingCard.style.display = 'block';
            fadeIn(processingCard);
        }, 300);
    }

    // Show results card
    function showResultsCard(files) {
        // Create download links
        downloadLinks.innerHTML = '';
        if (files && files.length > 0) {
            files.forEach(file => {
                const fileType = file.type === 'excel' ? 'Excel Report' : 'Processing Log';
                const fileIcon = file.type === 'excel' ? 
                    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 13H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 17H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 9H9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' :
                    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 13H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 17H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
                
                const link = document.createElement('a');
                link.href = `/download/${file.filename}`;
                link.className = 'download-link';
                link.innerHTML = `
                    <div class="download-link-icon">${fileIcon}</div>
                    <div class="download-link-text">
                        <p>${file.filename}</p>
                        <p class="file-type">${fileType}</p>
                    </div>
                    <div class="download-link-arrow">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 15V3M12 15L8 11M12 15L16 11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M3 21H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                `;
                downloadLinks.appendChild(link);
            });
        } else {
            downloadLinks.innerHTML = '<p>No files were generated.</p>';
        }
        
        fadeOut(processingCard);
        setTimeout(() => {
            processingCard.style.display = 'none';
            resultsCard.style.display = 'block';
            fadeIn(resultsCard);
        }, 300);
    }

    // Show error card
    function showErrorCard(message) {
        errorMessage.textContent = message;
        
        fadeOut(processingCard);
        setTimeout(() => {
            processingCard.style.display = 'none';
            errorCard.style.display = 'block';
            fadeIn(errorCard);
        }, 300);
    }

    // Show error in upload card
    function showError(message) {
        alert(message);
    }

    // Reset to upload card
    function resetToUpload() {
        // Reset file input
        fileInput.value = '';
        fileInfo.style.display = 'none';
        
        // Hide current card and show upload card
        const currentCard = resultsCard.style.display === 'block' ? resultsCard : errorCard;
        fadeOut(currentCard);
        setTimeout(() => {
            currentCard.style.display = 'none';
            uploadCard.style.display = 'block';
            fadeIn(uploadCard);
        }, 300);
        
        // Reset task ID
        currentTaskId = null;
    }

    // Reset button click
    resetButton.addEventListener('click', resetToUpload);
    errorResetButton.addEventListener('click', resetToUpload);

    // Animation helpers
    function fadeIn(element) {
        element.classList.remove('fade-out');
        element.classList.add('fade-in');
    }

    function fadeOut(element) {
        element.classList.remove('fade-in');
        element.classList.add('fade-out');
    }
});
