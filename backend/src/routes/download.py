
from flask import Blueprint, request, jsonify, Response
from flask_cors import cross_origin
import requests
import os
import threading
import time
import uuid
import subprocess
import signal

from urllib.parse import urlparse
import json
import concurrent.futures
from threading import Lock
import sys

download_bp = Blueprint('download', __name__)

# Global dictionary to keep track of download tasks
download_tasks = {}

# Define a default download directory
download_directory = os.path.join(os.getcwd(), "downloads")
os.makedirs(download_directory, exist_ok=True)

class DownloadTask:
    def __init__(self, url, filename=None, download_path=None, max_connections=4):
        self.id = str(uuid.uuid4())
        self.url = url
        self.title = None
        self.filename = filename or self._get_filename_from_url(url)
        self.download_path = download_path or download_directory
        self.full_path = os.path.join(self.download_path, self.filename)
        self.status = "pending"  # pending, downloading, paused, completed, error
        self.progress = 0
        self.total_size = 0
        self.downloaded_size = 0
        self.speed = 0
        self.start_time = None
        self.thread = None
        self.paused = False
        self.error_message = None
        self.max_connections = max_connections
        self.supports_range = False
        self.chunks = []
        self.lock = Lock()
        
    def _get_filename_from_url(self, url):
        """Extract filename from URL"""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename or '.' not in filename:
            filename = f"download_{int(time.time())}"
        return filename
    
    def _check_range_support(self):
        """Check if server supports range requests"""
        try:
            response = requests.head(self.url, allow_redirects=True)
            self.supports_range = 'accept-ranges' in response.headers and response.headers['accept-ranges'] == 'bytes'
            if 'content-length' in response.headers:
                self.total_size = int(response.headers['content-length'])
            return True
        except Exception as e:
            self.error_message = f"Failed to check server capabilities: {str(e)}"
            return False
    
    def _create_chunks(self):
        """Create download chunks for multipart downloading"""
        if not self.supports_range or self.total_size <= 0:
            return [(0, self.total_size - 1 if self.total_size > 0 else None)]
        
        chunk_size = max(self.total_size // self.max_connections, 1024 * 1024)  # At least 1MB per chunk
        chunks = []
        
        for i in range(self.max_connections):
            start = i * chunk_size
            end = min(start + chunk_size - 1, self.total_size - 1)
            if start <= end:
                chunks.append((start, end))
        
        return chunks
    
    def start_download(self):
        """Start the download in a separate thread"""
        print(f"[Download] Starting: {self.url} as {self.filename}")
        self.thread = threading.Thread(target=self._download_worker)
        self.thread.daemon = True
        self.thread.start()
    
    def _download_worker(self):
        """Worker function that performs the actual download"""
        try:
            self.status = "downloading"
            self.start_time = time.time()
            # Check if URL is YouTube or similar (yt-dlp supported)
            if any(domain in self.url for domain in ["youtube.com", "youtu.be", "tiktok.com", "facebook.com", "instagram.com", "twitter.com"]):
                # Placeholder for yt-dlp download logic
                # You should implement the actual download logic here
                pass
            else:
                # Placeholder for normal download logic
                pass
        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self.progress = 100
    
    def _single_part_download(self, resume_pos=0):
        """Download file in a single stream"""
        headers = {}
        if resume_pos > 0 and self.total_size > 0:
            headers['Range'] = f'bytes={resume_pos}-'
        
        response = requests.get(self.url, headers=headers, stream=True, allow_redirects=True)
        response.raise_for_status()
        
        mode = 'ab' if resume_pos > 0 else 'wb'
        
        with open(self.full_path, mode) as file:
            chunk_size = 8192
            last_time = time.time()
            last_downloaded = self.downloaded_size
            
            for chunk in response.iter_content(chunk_size=chunk_size):
                if self.paused:
                    self.status = "paused"
                    return
                
                if chunk:
                    file.write(chunk)
                    with self.lock:
                        self.downloaded_size += len(chunk)
                        
                        # Calculate progress and speed
                        if self.total_size > 0:
                            self.progress = int((self.downloaded_size / self.total_size) * 100)
                        
                        current_time = time.time()
                        if current_time - last_time >= 1:  # Update speed every second
                            speed_bytes = self.downloaded_size - last_downloaded
                            self.speed = speed_bytes / (current_time - last_time)
                            last_time = current_time
                            last_downloaded = self.downloaded_size
    
    def _multipart_download(self, chunks, resume_pos=0):
        """Download file using multiple parallel connections"""
        # Create temporary files for each chunk
        temp_files = []
        for i, (start, end) in enumerate(chunks):
            temp_file = f"{self.full_path}.part{i}"
            temp_files.append(temp_file)
        
        # Download chunks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_connections) as executor:
            futures = []
            for i, (start, end) in enumerate(chunks):
                if start >= resume_pos:  # Skip already downloaded chunks
                    future = executor.submit(self._download_chunk, start, end, temp_files[i], i)
                    futures.append(future)
            
            # Wait for all chunks to complete
            for future in concurrent.futures.as_completed(futures):
                if self.paused:
                    break
                try:
                    future.result()
                except Exception as e:
                    self.status = "error"
                    self.error_message = f"Chunk download failed: {str(e)}"
                    return
        
        if not self.paused and self.status != "error":
            # Combine all chunks into final file
            self._combine_chunks(temp_files)
    
    def _download_chunk(self, start, end, temp_file, chunk_id):
        """Download a specific chunk of the file"""
        headers = {'Range': f'bytes={start}-{end}'}
        
        try:
            response = requests.get(self.url, headers=headers, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            with open(temp_file, 'wb') as file:
                chunk_size = 8192
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self.paused:
                        return
                    
                    if chunk:
                        file.write(chunk)
                        with self.lock:
                            self.downloaded_size += len(chunk)
                            if self.total_size > 0:
                                self.progress = int((self.downloaded_size / self.total_size) * 100)
                                
        except Exception as e:
            raise Exception(f"Failed to download chunk {chunk_id}: {str(e)}")
    
    def _combine_chunks(self, temp_files):
        """Combine downloaded chunks into final file"""
        try:
            with open(self.full_path, 'wb') as final_file:
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        with open(temp_file, 'rb') as chunk_file:
                            final_file.write(chunk_file.read())
                        os.remove(temp_file)  # Clean up temp file
        except Exception as e:
            self.status = "error"
            self.error_message = f"Failed to combine chunks: {str(e)}"
    
    def pause(self):
        """Pause the download"""
        self.paused = True
    
    def resume(self):
        """Resume the download"""
        if self.status == "paused":
            self.paused = False
            self.start_download()
    
    def to_dict(self):
        """Convert task to dictionary for JSON response"""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'filename': self.filename,
            'status': self.status,
            'progress': self.progress,
            'total_size': self.total_size,
            'downloaded_size': self.downloaded_size,
            'speed': self.speed,
            'error_message': self.error_message,
            'supports_multipart': self.supports_range,
            'connections': self.max_connections
        }

@download_bp.route('/start', methods=['POST'])
@cross_origin()
def start_download():
    """Start a new download"""
    try:
        data = request.get_json()
        url = data.get('url')
        filename = data.get('filename')
        download_path = data.get('download_path')
        max_connections = data.get('max_connections', 4)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Create download task
        task = DownloadTask(url, filename, download_path, max_connections)
        download_tasks[task.id] = task
        
        # Start download
        task.start_download()
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Download started successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@download_bp.route('/bulk', methods=['POST'])
@cross_origin()
def start_bulk_download():
    """Start multiple downloads"""
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        download_path = data.get('download_path')
        max_concurrent = data.get('max_concurrent', 3)
        delay = data.get('delay', 0)
        
        if not urls:
            return jsonify({'error': 'URLs are required'}), 400
        
        task_ids = []
        
        for i, url in enumerate(urls):
            if i > 0 and delay > 0:
                time.sleep(delay)
            
            task = DownloadTask(url, download_path=download_path)
            download_tasks[task.id] = task
            task.start_download()
            task_ids.append(task.id)
            
            # Limit concurrent downloads
            active_downloads = len([t for t in download_tasks.values() if t.status == 'downloading'])
            while active_downloads >= max_concurrent:
                time.sleep(1)
                active_downloads = len([t for t in download_tasks.values() if t.status == 'downloading'])
        
        return jsonify({
            'success': True,
            'task_ids': task_ids,
            'message': f'Started {len(task_ids)} downloads'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@download_bp.route('/status/<task_id>', methods=['GET'])
@cross_origin()
def get_download_status(task_id):
    """Get status of a specific download"""
    task = download_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Download not found'}), 404
    
    return jsonify(task.to_dict())

@download_bp.route('/list', methods=['GET'])
@cross_origin()
def list_downloads():
    """Get list of all downloads"""
    downloads = [task.to_dict() for task in download_tasks.values()]
    return jsonify(downloads)

@download_bp.route('/pause/<download_id>', methods=['POST'])
@cross_origin()
def pause_download_route(download_id):
    """Pause a download"""
    task = download_tasks.get(download_id)
    if not task:
        return jsonify({'error': 'Download not found'}), 404
    
    task.pause()
    return jsonify({'status': 'paused', 'success': True})

@download_bp.route('/resume/<download_id>', methods=['POST'])
@cross_origin()
def resume_download_route(download_id):
    """Resume a paused download"""
    task = download_tasks.get(download_id)
    if not task:
        return jsonify({'error': 'Download not found'}), 404
    
    task.resume()
    return jsonify({'status': 'resumed', 'success': True})

@download_bp.route('/delete/<download_id>', methods=['DELETE'])
@download_bp.route('/cancel/<download_id>', methods=['DELETE'])
@cross_origin()
def cancel_download_route(download_id):
    """Delete or cancel a download task"""
    task = download_tasks.get(download_id)
    if not task:
        return jsonify({'error': 'Download not found'}), 404
    
    # Pause the download first
    task.pause()
    
    # Remove from tasks
    del download_tasks[download_id]
    
    return jsonify({'status': 'cancelled', 'success': True})

@download_bp.route('/stats', methods=['GET'])
@cross_origin()
def get_stats():
    """Get download statistics"""
    total = len(download_tasks)
    active = len([t for t in download_tasks.values() if t.status == 'downloading'])
    completed = len([t for t in download_tasks.values() if t.status == 'completed'])
    paused = len([t for t in download_tasks.values() if t.status == 'paused'])
    
    total_size = sum(t.total_size for t in download_tasks.values() if t.total_size > 0)
    avg_speed = sum(t.speed for t in download_tasks.values() if t.status == 'downloading')
    
    return jsonify({
        'total': total,
        'active': active,
        'completed': completed,
        'paused': paused,
        'total_size': total_size,
        'avg_speed': avg_speed
    })

@download_bp.route('/settings', methods=['POST'])
@cross_origin()
def update_settings():
    """Update download settings"""
    try:
        data = request.get_json()
        # Here you can implement settings like max concurrent downloads, 
        # default download path, bandwidth limits, etc.
        return jsonify({'success': True, 'message': 'Settings updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
