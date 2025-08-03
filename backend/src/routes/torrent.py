from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import threading
import time
import uuid
import hashlib
import bencodepy
import requests
from urllib.parse import urlparse, parse_qs
import socket
import struct
import random

torrent_bp = Blueprint('torrent', __name__)

# Global storage for torrent download tasks
torrent_tasks = {}
torrent_directory = os.path.join(os.path.expanduser("~"), "Downloads", "DownloadMaster", "Torrents")

# Ensure torrent directory exists
os.makedirs(torrent_directory, exist_ok=True)

class TorrentDownloadTask:
    def __init__(self, magnet_link=None, torrent_file=None, download_path=None, max_connections=50):
        self.id = str(uuid.uuid4())
        self.magnet_link = magnet_link
        self.torrent_file = torrent_file
        self.download_path = download_path or torrent_directory
        self.max_connections = max_connections
        self.status = "pending"  # pending, parsing, downloading, seeding, completed, error
        self.progress = 0
        self.name = ""
        self.total_size = 0
        self.downloaded_size = 0
        self.uploaded_size = 0
        self.download_speed = 0
        self.upload_speed = 0
        self.peers = 0
        self.seeds = 0
        self.ratio = 0.0
        self.eta = ""
        self.error_message = None
        self.thread = None
        self.info_hash = None
        self.files = []
        self.trackers = []
        
    def start_download(self):
        """Start the torrent download in a separate thread"""
        self.thread = threading.Thread(target=self._download_worker)
        self.thread.daemon = True
        self.thread.start()
    
    def _download_worker(self):
        """Worker function that performs the actual torrent download"""
        try:
            self.status = "parsing"
            
            if self.magnet_link:
                self._parse_magnet_link()
            elif self.torrent_file:
                self._parse_torrent_file()
            else:
                self.status = "error"
                self.error_message = "No magnet link or torrent file provided"
                return
            
            # For demonstration, we'll simulate a torrent download
            # In a real implementation, you'd use a proper BitTorrent library like libtorrent
            self._simulate_torrent_download()
            
        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
    
    def _parse_magnet_link(self):
        """Parse magnet link to extract info hash and trackers"""
        try:
            parsed = urlparse(self.magnet_link)
            if parsed.scheme != 'magnet':
                raise ValueError("Invalid magnet link")
            
            params = parse_qs(parsed.query)
            
            # Extract info hash
            if 'xt' in params:
                xt = params['xt'][0]
                if xt.startswith('urn:btih:'):
                    self.info_hash = xt[9:]
                    
            # Extract display name
            if 'dn' in params:
                self.name = params['dn'][0]
            else:
                self.name = f"Torrent_{self.info_hash[:8]}"
                
            # Extract trackers
            if 'tr' in params:
                self.trackers = params['tr']
                
        except Exception as e:
            raise Exception(f"Failed to parse magnet link: {str(e)}")
    
    def _parse_torrent_file(self):
        """Parse .torrent file to extract metadata"""
        try:
            with open(self.torrent_file, 'rb') as f:
                torrent_data = bencodepy.decode(f.read())
            
            info = torrent_data[b'info']
            self.info_hash = hashlib.sha1(bencodepy.encode(info)).hexdigest()
            self.name = info[b'name'].decode('utf-8')
            
            # Calculate total size
            if b'files' in info:
                # Multi-file torrent
                self.total_size = sum(f[b'length'] for f in info[b'files'])
                self.files = [
                    {
                        'path': '/'.join(p.decode('utf-8') for p in f[b'path']),
                        'size': f[b'length']
                    }
                    for f in info[b'files']
                ]
            else:
                # Single file torrent
                self.total_size = info[b'length']
                self.files = [{'path': self.name, 'size': self.total_size}]
            
            # Extract trackers
            if b'announce' in torrent_data:
                self.trackers.append(torrent_data[b'announce'].decode('utf-8'))
            if b'announce-list' in torrent_data:
                for tier in torrent_data[b'announce-list']:
                    for tracker in tier:
                        self.trackers.append(tracker.decode('utf-8'))
                        
        except Exception as e:
            raise Exception(f"Failed to parse torrent file: {str(e)}")
    
    def _simulate_torrent_download(self):
        """Simulate torrent download progress (for demonstration)"""
        self.status = "downloading"
        
        # Simulate getting peers and starting download
        self.peers = random.randint(5, 50)
        self.seeds = random.randint(1, 10)
        
        # If no total size was determined, estimate one
        if self.total_size == 0:
            self.total_size = random.randint(100 * 1024 * 1024, 2 * 1024 * 1024 * 1024)  # 100MB to 2GB
        
        # Simulate download progress
        download_time = 60  # Simulate 60 seconds download
        chunk_size = self.total_size // download_time
        
        for i in range(download_time):
            if self.status != "downloading":
                break
                
            self.downloaded_size += chunk_size
            self.progress = min(int((self.downloaded_size / self.total_size) * 100), 100)
            
            # Simulate varying speeds
            self.download_speed = chunk_size + random.randint(-chunk_size//4, chunk_size//4)
            self.upload_speed = random.randint(0, chunk_size//2)
            self.uploaded_size += self.upload_speed
            
            # Calculate ratio
            if self.downloaded_size > 0:
                self.ratio = self.uploaded_size / self.downloaded_size
            
            # Calculate ETA
            if self.download_speed > 0:
                remaining = self.total_size - self.downloaded_size
                eta_seconds = remaining / self.download_speed
                self.eta = f"{int(eta_seconds)}s"
            
            time.sleep(1)
        
        if self.progress >= 100:
            self.status = "completed"
            self.progress = 100
    
    def pause(self):
        """Pause the torrent download"""
        if self.status == "downloading":
            self.status = "paused"
    
    def resume(self):
        """Resume the torrent download"""
        if self.status == "paused":
            self.status = "downloading"
    
    def to_dict(self):
        """Convert task to dictionary for JSON response"""
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'progress': self.progress,
            'total_size': self.total_size,
            'downloaded_size': self.downloaded_size,
            'uploaded_size': self.uploaded_size,
            'download_speed': self.download_speed,
            'upload_speed': self.upload_speed,
            'peers': self.peers,
            'seeds': self.seeds,
            'ratio': round(self.ratio, 2),
            'eta': self.eta,
            'error_message': self.error_message,
            'files': self.files,
            'trackers': len(self.trackers)
        }

@torrent_bp.route('/start', methods=['POST'])
@cross_origin()
def start_torrent_download():
    """Start a torrent download"""
    try:
        data = request.get_json()
        magnet_link = data.get('magnet_link')
        torrent_file = data.get('torrent_file')
        download_path = data.get('download_path')
        max_connections = data.get('max_connections', 50)
        
        if not magnet_link and not torrent_file:
            return jsonify({'error': 'Magnet link or torrent file is required'}), 400
        
        # Create torrent download task
        task = TorrentDownloadTask(magnet_link, torrent_file, download_path, max_connections)
        torrent_tasks[task.id] = task
        
        # Start download
        task.start_download()
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Torrent download started successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@torrent_bp.route('/upload', methods=['POST'])
@cross_origin()
def upload_torrent_file():
    """Upload and parse a .torrent file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.torrent'):
            return jsonify({'error': 'Invalid file type. Please upload a .torrent file'}), 400
        
        # Save uploaded file
        filename = f"torrent_{int(time.time())}_{file.filename}"
        filepath = os.path.join(torrent_directory, filename)
        file.save(filepath)
        
        # Parse torrent file to get info
        try:
            with open(filepath, 'rb') as f:
                torrent_data = bencodepy.decode(f.read())
            
            info = torrent_data[b'info']
            name = info[b'name'].decode('utf-8')
            
            # Calculate total size
            if b'files' in info:
                total_size = sum(f[b'length'] for f in info[b'files'])
                file_count = len(info[b'files'])
            else:
                total_size = info[b'length']
                file_count = 1
            
            return jsonify({
                'success': True,
                'filepath': filepath,
                'name': name,
                'total_size': total_size,
                'file_count': file_count,
                'message': 'Torrent file uploaded and parsed successfully'
            })
            
        except Exception as e:
            os.remove(filepath)  # Clean up on error
            return jsonify({'error': f'Failed to parse torrent file: {str(e)}'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@torrent_bp.route('/status/<task_id>', methods=['GET'])
@cross_origin()
def get_torrent_status(task_id):
    """Get status of a specific torrent download"""
    task = torrent_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Torrent download not found'}), 404
    
    return jsonify(task.to_dict())

@torrent_bp.route('/list', methods=['GET'])
@cross_origin()
def list_torrent_downloads():
    """Get list of all torrent downloads"""
    downloads = [task.to_dict() for task in torrent_tasks.values()]
    return jsonify(downloads)

@torrent_bp.route('/pause/<task_id>', methods=['POST'])
@cross_origin()
def pause_torrent_download(task_id):
    """Pause a torrent download"""
    task = torrent_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Torrent download not found'}), 404
    
    task.pause()
    return jsonify({'success': True, 'message': 'Torrent download paused'})

@torrent_bp.route('/resume/<task_id>', methods=['POST'])
@cross_origin()
def resume_torrent_download(task_id):
    """Resume a torrent download"""
    task = torrent_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Torrent download not found'}), 404
    
    task.resume()
    return jsonify({'success': True, 'message': 'Torrent download resumed'})

@torrent_bp.route('/delete/<task_id>', methods=['DELETE'])
@cross_origin()
def delete_torrent_download(task_id):
    """Delete a torrent download task"""
    task = torrent_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Torrent download not found'}), 404
    
    # Pause the download first
    task.pause()
    
    # Remove from tasks
    del torrent_tasks[task_id]
    
    return jsonify({'success': True, 'message': 'Torrent download deleted'})

@torrent_bp.route('/stats', methods=['GET'])
@cross_origin()
def get_torrent_stats():
    """Get torrent download statistics"""
    total = len(torrent_tasks)
    active = len([t for t in torrent_tasks.values() if t.status == 'downloading'])
    completed = len([t for t in torrent_tasks.values() if t.status == 'completed'])
    seeding = len([t for t in torrent_tasks.values() if t.status == 'seeding'])
    
    total_downloaded = sum(t.downloaded_size for t in torrent_tasks.values())
    total_uploaded = sum(t.uploaded_size for t in torrent_tasks.values())
    avg_ratio = sum(t.ratio for t in torrent_tasks.values()) / total if total > 0 else 0
    
    return jsonify({
        'total': total,
        'active': active,
        'completed': completed,
        'seeding': seeding,
        'total_downloaded': total_downloaded,
        'total_uploaded': total_uploaded,
        'avg_ratio': round(avg_ratio, 2)
    })

