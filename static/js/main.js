document.addEventListener('DOMContentLoaded', function() {
    const extractForm = document.getElementById('extractForm');
    const youtubeUrlInput = document.getElementById('youtubeUrl');
    const urlError = document.getElementById('urlError');
    const resultsSection = document.getElementById('resultsSection');
    const downloadBtn = document.getElementById('downloadBtn');
    
    // Video Info Elements
    const videoTitle = document.getElementById('videoTitle');
    const videoThumbnail = document.getElementById('videoThumbnail');
    const videoDuration = document.getElementById('videoDuration');
    const videoUploader = document.getElementById('videoUploader');
    const qualitySelect = document.getElementById('qualitySelect');
    
    // Time Inputs (HH:MM:SS format - now dropdowns)
    const startHourInput = document.getElementById('startHour');
    const startMinInput = document.getElementById('startMin');
    const startSecInput = document.getElementById('startSec');
    const endHourInput = document.getElementById('endHour');
    const endMinInput = document.getElementById('endMin');
    const endSecInput = document.getElementById('endSec');
    const segmentPreview = document.getElementById('segmentPreview');
    const durationBadge = document.getElementById('durationBadge');
    
    // Legacy hidden inputs for API compatibility
    const startTimeInput = document.getElementById('startTime');
    const endTimeInput = document.getElementById('endTime');
    
    // Progress Elements
    const progressSection = document.getElementById('progressSection');
    const progressBar = document.getElementById('progressBar');
    const progressStatus = document.getElementById('progressStatus');
    const downloadLinkContainer = document.getElementById('downloadLinkContainer');
    const finalDownloadLink = document.getElementById('finalDownloadLink');
    const errorContainer = document.getElementById('errorContainer');

    let currentVideoDuration = 0;
    let pollInterval = null;
    let currentTaskId = null;
    let isDownloading = false;

    // Helper: Format seconds to MM:SS or HH:MM:SS
    function formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        
        if (h > 0) {
            return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }
        return `${m}:${s.toString().padStart(2, '0')}`;
    }
    
    // Helper: Populate a dropdown with options
    function populateDropdown(select, max, defaultVal = 0) {
        select.innerHTML = '';
        for (let i = 0; i <= max; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = i.toString().padStart(2, '0');
            if (i === defaultVal) option.selected = true;
            select.appendChild(option);
        }
    }
    
    // Helper: Populate all time dropdowns based on video duration
    function populateTimeDropdowns(duration) {
        const maxHours = Math.ceil(duration / 3600);
        
        // For hours, we need up to the maximum hours in the video
        populateDropdown(startHourInput, maxHours, 0);
        populateDropdown(endHourInput, maxHours, Math.floor(duration / 3600));
        
        populateDropdown(startMinInput, 59, 0);
        populateDropdown(endMinInput, 59, Math.floor((duration % 3600) / 60));
        
        populateDropdown(startSecInput, 59, 0);
        populateDropdown(endSecInput, 59, duration % 60);
        
        updateTimePreview();
    }
    
    // Helper: Convert HH:MM:SS inputs to total seconds
    function hmsToSeconds() {
        const h = parseInt(startHourInput.value) || 0;
        const m = parseInt(startMinInput.value) || 0;
        const s = parseInt(startSecInput.value) || 0;
        return (h * 3600) + (m * 60) + s;
    }
    
    function hmsToSecondsEnd() {
        const h = parseInt(endHourInput.value) || 0;
        const m = parseInt(endMinInput.value) || 0;
        const s = parseInt(endSecInput.value) || 0;
        return (h * 3600) + (m * 60) + s;
    }
    
    // Update duration badge and clip preview
    function updateTimePreview() {
        let startSeconds = hmsToSeconds();
        let endSeconds = hmsToSecondsEnd();
        
        // Validate and cap values
        startSeconds = Math.min(Math.max(0, startSeconds), currentVideoDuration);
        endSeconds = Math.min(Math.max(0, endSeconds), currentVideoDuration);
        
        // Ensure end is after start
        if (endSeconds <= startSeconds) {
            endSeconds = startSeconds + 60; // Minimum 1 minute clip
            if (endSeconds > currentVideoDuration) {
                endSeconds = currentVideoDuration;
            }
            // Update the display to reflect corrected end time
            endHourInput.value = Math.floor(endSeconds / 3600);
            endMinInput.value = Math.floor((endSeconds % 3600) / 60);
            endSecInput.value = endSeconds % 60;
        }
        
        // Update hidden inputs for API
        startTimeInput.value = startSeconds;
        endTimeInput.value = endSeconds;
        
        // Update preview badges
        segmentPreview.textContent = `clip: ${formatTime(startSeconds)} - ${formatTime(endSeconds)}`;
        
        const duration = Math.max(0, endSeconds - startSeconds);
        durationBadge.textContent = `Duration: ${formatTime(duration)}`;
    }
    
    // Add event listeners to all time inputs
    [startHourInput, startMinInput, startSecInput, endHourInput, endMinInput, endSecInput].forEach(input => {
        input.addEventListener('change', updateTimePreview);
    });
    
    // Show warning when user tries to leave during download
    function setDownloadWarning(enable) {
        isDownloading = enable;
        if (enable) {
            window.onbeforeunload = function() {
                return 'A download is in progress. Are you sure you want to leave? Your download will be cancelled.';
            };
            // Also show a toast/alert
            showWarningToast('Please do not close this page. Your download is in progress...');
        } else {
            window.onbeforeunload = null;
        }
    }
    
    // Show warning toast notification
    function showWarningToast(message) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'alert alert-warning position-fixed top-0 start-50 translate-middle-x mt-3 z-index-1000';
        toast.style.zIndex = '9999';
        toast.innerHTML = `<i class="fa-solid fa-triangle-exclamation me-2"></i> ${message}`;
        document.body.appendChild(toast);
        
        // Auto remove after 5 seconds if still downloading
        setTimeout(() => {
            if (isDownloading) {
                toast.remove();
                showWarningToast('Please do not close this page. Your download is in progress...');
            } else {
                toast.remove();
            }
        }, 5000);
    }

    // Stop polling and cleanup
    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
        setDownloadWarning(false);
        currentTaskId = null;
    }

    // Reset UI for new video
    function resetUI() {
        stopPolling();
        resultsSection.style.display = 'none';
        progressSection.style.display = 'none';
        downloadLinkContainer.style.display = 'none';
        errorContainer.style.display = 'none';
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
    }

    // 1. Extract Video Info
    // Auto-submit when URL is pasted
    youtubeUrlInput.addEventListener('paste', function(e) {
        // Small delay to allow the paste to complete
        setTimeout(function() {
            const url = youtubeUrlInput.value.trim();
            if (url && validateYouTubeUrl(url)) {
                // Auto-submit the form
                extractForm.dispatchEvent(new Event('submit'));
            }
        }, 100);
    });
    
    // Helper to validate YouTube URL
    function validateYouTubeUrl(url) {
        const youtubeRegex = /^(https?\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/(watch\?v=|embed\/|v\/|.+\?v=)?([^&=%?]{11})/;
        return youtubeRegex.test(url);
    }
    
    extractForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const url = youtubeUrlInput.value.trim();
        if (!url) return;

        // Reset UI before new extraction
        resetUI();

        // Reset UI
        urlError.style.display = 'none';
        const submitBtn = extractForm.querySelector('button');
        const originalBtnHtml = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        submitBtn.disabled = true;

        try {
            const response = await fetch('/api/extract-info/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ youtube_url: url })
            });

            const data = await response.json();

            if (response.ok) {
                // Populate UI
                videoTitle.textContent = data.title;
                videoThumbnail.src = data.thumbnail_url || data.thumbnail;
                currentVideoDuration = data.duration;
                videoDuration.textContent = formatTime(data.duration);
                videoUploader.textContent = data.uploader;
                
                // Setup Time Inputs - Set end time to video duration using dropdowns
                populateTimeDropdowns(data.duration);

                // Populate Qualities
                qualitySelect.innerHTML = '';
                const qualities = data.formats || [];
                qualities.forEach(fmt => {
                    const option = document.createElement('option');
                    option.value = fmt.quality;
                    let label = fmt.quality;
                    if (fmt.filesize) {
                         const sizeMB = (fmt.filesize / (1024 * 1024)).toFixed(1);
                         label += ` (approx. ${sizeMB} MB)`;
                    }
                    option.textContent = label;
                    qualitySelect.appendChild(option);
                });

                resultsSection.style.display = 'block';
                resultsSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                urlError.textContent = data.error || 'Failed to fetch video info';
                urlError.style.display = 'block';
            }
        } catch (error) {
            urlError.textContent = 'Network error occurred';
            urlError.style.display = 'block';
        } finally {
            submitBtn.innerHTML = originalBtnHtml;
            submitBtn.disabled = false;
        }
    });

    // 2. Download clip
    downloadBtn.addEventListener('click', async function() {
        // Get values from hidden inputs (which are updated by HH:MM:SS inputs)
        const start = parseInt(startTimeInput.value);
        const end = parseInt(endTimeInput.value);
        const quality = qualitySelect.value;
        const url = youtubeUrlInput.value;

        // Basic Validation
        if (start >= end) {
            alert('End time must be greater than start time');
            return;
        }

        // Show Progress
        progressSection.style.display = 'block';
        downloadLinkContainer.style.display = 'none';
        errorContainer.style.display = 'none';
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
        progressBar.classList.add('progress-bar-animated');
        progressBar.classList.remove('bg-danger');
        progressStatus.textContent = 'Initiating download...';
        progressStatus.className = 'text-center text-muted mt-2 small';
        downloadBtn.disabled = true;

        try {
            const response = await fetch('/api/download-clip/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    youtube_url: url,
                    start_time: start,
                    end_time: end,
                    quality: quality
                })
            });

            const data = await response.json();

            if (response.status === 202) { // HTTP 202 Accepted
                const taskId = data.task_id;
                currentTaskId = taskId;
                setDownloadWarning(true); // Show warning not to close page
                startPolling(taskId);
            } else {
                showError(data.error || 'Download failed to start');
                downloadBtn.disabled = false;
            }
        } catch (error) {
            showError('Network error');
            downloadBtn.disabled = false;
        }
    });

    // 3. Poll Status
    function startPolling(taskId) {
        if (pollInterval) clearInterval(pollInterval);
        
        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/task-status/${taskId}/`);
                const data = await response.json();

                if (response.ok) {
                    const status = data.status;
                    const percent = data.progress || 0;
                    
                    progressBar.style.width = `${percent}%`;
                    progressBar.textContent = `${percent}%`;

                    if (status === 'processing') {
                         progressStatus.textContent = 'Processing... Downloading video and extracting clip...';
                    } else if (status === 'completed') {
                        clearInterval(pollInterval);
                        progressBar.style.width = '100%';
                        progressBar.textContent = '100%';
                        progressStatus.textContent = 'Processing Complete! Your video is ready for download.';
                        progressStatus.className = 'text-center text-success mt-2 fw-bold';
                        progressBar.classList.remove('progress-bar-animated');
                        
                        // Show Download Link
                        finalDownloadLink.href = data.download_url;
                        downloadLinkContainer.style.display = 'block';
                        downloadBtn.disabled = false;
                        
                        // Stop warning
                        setDownloadWarning(false);
                        
                        // Show success alert
                        alert('Download complete! Click "Save File" to download your video.');
                    } else if (status === 'failed') {
                        clearInterval(pollInterval);
                        showError(data.error_message || 'Download failed during processing');
                        downloadBtn.disabled = false;
                        setDownloadWarning(false);
                    }
                }
            } catch (error) {
                console.error('Polling error', error);
            }
        }, 2000); // Check every 2 seconds
    }

    function showError(msg) {
        errorContainer.textContent = msg;
        errorContainer.style.display = 'block';
        progressStatus.textContent = 'Error occurred';
        progressBar.classList.add('bg-danger');
    }
});
