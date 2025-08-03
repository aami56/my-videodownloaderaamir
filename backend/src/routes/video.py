from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import subprocess
import os
import json
import threading
import uuid
import time
from urllib.parse import urlparse

video_bp = Blueprint('video', __name__)

# Global storage for video download tasks
video_tasks = {}
video_directory = os.path.join(os.path.expanduser("~"), "Downloads", "DownloadMaster", "Videos")

# Ensure video directory exists
os.makedirs(video_directory, exist_ok=True)

class VideoDownloadTask:
    def __init__(self, url, quality="best", format_type="mp4", download_path=None, audio_only=False):
        self.id = str(uuid.uuid4())
        self.url = url
        self.quality = quality
        self.format_type = format_type
        self.download_path = download_path or video_directory
        self.audio_only = audio_only
        self.status = "pending"  # pending, analyzing, downloading, completed, error
        self.progress = 0
        self.title = ""
        self.duration = ""
        self.file_size = 0
        self.downloaded_size = 0
        self.speed = ""
        self.eta = ""
        self.error_message = None
        self.thread = None
        self.process = None
        self.output_file = ""
        
    def start_download(self):
        """Start the video download in a separate thread"""
        self.thread = threading.Thread(target=self._download_worker)
        self.thread.daemon = True
        self.thread.start()
    
    def _download_worker(self):
        """Worker function that performs the actual video download"""
        try:
            self.status = "analyzing"
            
            # First, get video info
            info_cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-playlist",
                self.url
            ]
            
            try:
                result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    info = json.loads(result.stdout)
                    self.title = info.get('title', 'Unknown')
                    self.duration = str(info.get('duration', 0))
                    
                    # Get available formats
                    formats = info.get('formats', [])
                    self._select_best_format(formats)
                else:
                    self.status = "error"
                    self.error_message = f"Failed to get video info: {result.stderr}"
                    return
            except subprocess.TimeoutExpired:
                self.status = "error"
                self.error_message = "Timeout while getting video information"
                return
            except Exception as e:
                self.status = "error"
                self.error_message = f"Error getting video info: {str(e)}"
                return
            
            # Build download command
            self.status = "downloading"
            
            # Create safe filename
            safe_title = "".join(c for c in self.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_title:
                safe_title = f"video_{int(time.time())}"
            
            if self.audio_only:
                output_template = os.path.join(self.download_path, f"{safe_title}.%(ext)s")
                format_selector = "bestaudio/best"
            else:
                output_template = os.path.join(self.download_path, f"{safe_title}.%(ext)s")
                if self.quality == "best":
                    format_selector = f"best[ext={self.format_type}]/best"
                else:
                    format_selector = f"best[height<={self.quality.replace('p', '')}][ext={self.format_type}]/best[height<={self.quality.replace('p', '')}]"
            
            cmd = [
                "yt-dlp",
                "--no-playlist",
                "--format", format_selector,
                "--output", output_template,
                "--newline",
                self.url
            ]
            
            if self.audio_only:
                cmd.extend(["--extract-audio", "--audio-format", "mp3"])
            
            # Start download process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor progress
            for line in iter(self.process.stdout.readline, ''):
                if self.process.poll() is not None:
                    break
                
                line = line.strip()
                if line:
                    self._parse_progress(line)
            
            # Wait for process to complete
            self.process.wait()
            
            if self.process.returncode == 0:
                self.status = "completed"
                self.progress = 100
            else:
                self.status = "error"
                self.error_message = "Download failed"
                
        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
    
    def _select_best_format(self, formats):
        """Select the best format based on user preferences"""
        # This is a simplified format selection
        # In a real implementation, you'd want more sophisticated logic
        pass
    
    def _parse_progress(self, line):
        """Parse yt-dlp output to extract progress information"""
        try:
            if "[download]" in line:
                if "%" in line:
                    # Extract percentage
                    parts = line.split()
                    for part in parts:
                        if "%" in part:
                            self.progress = float(part.replace("%", ""))
                            break
                
                # Extract speed
                if "at" in line:
                    speed_part = line.split("at")[-1].strip()
                    self.speed = speed_part.split()[0] if speed_part else ""
                
                # Extract ETA
                if "ETA" in line:
                    eta_part = line.split("ETA")[-1].strip()
                    self.eta = eta_part if eta_part else ""
                    
        except Exception:
            pass  # Ignore parsing errors
    
    def pause(self):
        """Pause the download (terminate process)"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status = "paused"
    
    def to_dict(self):
        """Convert task to dictionary for JSON response"""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'duration': self.duration,
            'speed': self.speed,
            'eta': self.eta,
            'quality': self.quality,
            'format': self.format_type,
            'audio_only': self.audio_only,
            'error_message': self.error_message
        }

@video_bp.route('/analyze', methods=['POST'])
@cross_origin()
def analyze_video():
    """Analyze video URL to get available formats and info"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Get video info using yt-dlp
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return jsonify({'error': 'Failed to analyze video'}), 400
        
        info = json.loads(result.stdout)
        
        # Extract relevant information
        video_info = {
            'title': info.get('title', 'Unknown'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown'),
            'view_count': info.get('view_count', 0),
            'thumbnail': info.get('thumbnail', ''),
            'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
            'formats': []
        }
        
        # Process available formats
        formats = info.get('formats', [])
        quality_set = set()
        
        for fmt in formats:
            if fmt.get('height'):
                quality = f"{fmt['height']}p"
                if quality not in quality_set:
                    quality_set.add(quality)
                    video_info['formats'].append({
                        'quality': quality,
                        'format': fmt.get('ext', 'mp4'),
                        'filesize': fmt.get('filesize', 0)
                    })
        
        # Sort by quality (highest first)
        video_info['formats'].sort(key=lambda x: int(x['quality'].replace('p', '')), reverse=True)
        
        return jsonify(video_info)
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout while analyzing video'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@video_bp.route('/download', methods=['POST'])
@cross_origin()
def start_video_download():
    """Start a video download"""
    try:
        data = request.get_json()
        url = data.get('url')
        quality = data.get('quality', 'best')
        format_type = data.get('format', 'mp4')
        download_path = data.get('download_path')
        audio_only = data.get('audio_only', False)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Create video download task
        task = VideoDownloadTask(url, quality, format_type, download_path, audio_only)
        video_tasks[task.id] = task
        
        # Start download
        task.start_download()
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Video download started successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@video_bp.route('/playlist', methods=['POST'])
@cross_origin()
def download_playlist():
    """Download entire playlist"""
    try:
        data = request.get_json()
        url = data.get('url')
        quality = data.get('quality', 'best')
        format_type = data.get('format', 'mp4')
        download_path = data.get('download_path', video_directory)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Get playlist info first
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            return jsonify({'error': 'Failed to get playlist info'}), 400
        
        # Parse playlist entries
        entries = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except:
                    continue
        
        # Create download tasks for each video
        task_ids = []
        for entry in entries:
            video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
            task = VideoDownloadTask(video_url, quality, format_type, download_path)
            video_tasks[task.id] = task
            task.start_download()
            task_ids.append(task.id)
        
        return jsonify({
            'success': True,
            'task_ids': task_ids,
            'playlist_count': len(task_ids),
            'message': f'Started downloading {len(task_ids)} videos from playlist'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@video_bp.route('/status/<task_id>', methods=['GET'])
@cross_origin()
def get_video_status(task_id):
    """Get status of a specific video download"""
    task = video_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Video download not found'}), 404
    
    return jsonify(task.to_dict())

@video_bp.route('/list', methods=['GET'])
@cross_origin()
def list_video_downloads():
    """Get list of all video downloads"""
    downloads = [task.to_dict() for task in video_tasks.values()]
    return jsonify(downloads)

@video_bp.route('/pause/<task_id>', methods=['POST'])
@cross_origin()
def pause_video_download(task_id):
    """Pause a video download"""
    task = video_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Video download not found'}), 404
    
    task.pause()
    return jsonify({'success': True, 'message': 'Video download paused'})

@video_bp.route('/delete/<task_id>', methods=['DELETE'])
@cross_origin()
def delete_video_download(task_id):
    """Delete a video download task"""
    task = video_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Video download not found'}), 404
    
    # Pause the download first
    task.pause()
    
    # Remove from tasks
    del video_tasks[task_id]
    
    return jsonify({'success': True, 'message': 'Video download deleted'})

