from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import subprocess
import threading
import time
import uuid
import shutil
import zipfile
import json
from datetime import datetime
import psutil

advanced_bp = Blueprint('advanced', __name__)

# Global storage for advanced tasks
conversion_tasks = {}
bandwidth_settings = {
    'enabled': False,
    'download_limit': 0,  # KB/s, 0 = unlimited
    'upload_limit': 0     # KB/s, 0 = unlimited
}

class FileConverter:
    def __init__(self, input_file, output_format, output_path=None):
        self.id = str(uuid.uuid4())
        self.input_file = input_file
        self.output_format = output_format.lower()
        self.output_path = output_path or os.path.dirname(input_file)
        self.status = "pending"  # pending, converting, completed, error
        self.progress = 0
        self.error_message = None
        self.thread = None
        self.output_file = ""
        
    def start_conversion(self):
        """Start the file conversion in a separate thread"""
        self.thread = threading.Thread(target=self._conversion_worker)
        self.thread.daemon = True
        self.thread.start()
    
    def _conversion_worker(self):
        """Worker function that performs the actual conversion"""
        try:
            self.status = "converting"
            
            # Get input file info
            input_name = os.path.splitext(os.path.basename(self.input_file))[0]
            self.output_file = os.path.join(self.output_path, f"{input_name}.{self.output_format}")
            
            # Determine conversion type
            input_ext = os.path.splitext(self.input_file)[1].lower()
            
            if self._is_video_format(input_ext) and self._is_video_format(f".{self.output_format}"):
                self._convert_video()
            elif self._is_audio_format(input_ext) and self._is_audio_format(f".{self.output_format}"):
                self._convert_audio()
            elif self._is_image_format(input_ext) and self._is_image_format(f".{self.output_format}"):
                self._convert_image()
            elif self._is_document_format(input_ext) and self._is_document_format(f".{self.output_format}"):
                self._convert_document()
            else:
                raise Exception(f"Unsupported conversion: {input_ext} to .{self.output_format}")
            
            self.status = "completed"
            self.progress = 100
            
        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
    
    def _is_video_format(self, ext):
        return ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
    
    def _is_audio_format(self, ext):
        return ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']
    
    def _is_image_format(self, ext):
        return ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    def _is_document_format(self, ext):
        return ext in ['.pdf', '.docx', '.txt', '.html', '.md']
    
    def _convert_video(self):
        """Convert video files using ffmpeg"""
        cmd = [
            'ffmpeg', '-i', self.input_file,
            '-c:v', 'libx264', '-c:a', 'aac',
            '-y', self.output_file
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Simulate progress (in real implementation, parse ffmpeg output)
        for i in range(101):
            if process.poll() is not None:
                break
            self.progress = i
            time.sleep(0.1)
        
        process.wait()
        if process.returncode != 0:
            raise Exception("Video conversion failed")
    
    def _convert_audio(self):
        """Convert audio files using ffmpeg"""
        cmd = [
            'ffmpeg', '-i', self.input_file,
            '-acodec', 'libmp3lame' if self.output_format == 'mp3' else 'copy',
            '-y', self.output_file
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Simulate progress
        for i in range(101):
            if process.poll() is not None:
                break
            self.progress = i
            time.sleep(0.05)
        
        process.wait()
        if process.returncode != 0:
            raise Exception("Audio conversion failed")
    
    def _convert_image(self):
        """Convert image files using PIL/Pillow"""
        try:
            from PIL import Image
            
            with Image.open(self.input_file) as img:
                # Convert RGBA to RGB for JPEG
                if self.output_format.lower() == 'jpg' and img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                img.save(self.output_file, self.output_format.upper())
                
        except ImportError:
            raise Exception("PIL/Pillow not installed for image conversion")
        except Exception as e:
            raise Exception(f"Image conversion failed: {str(e)}")
    
    def _convert_document(self):
        """Convert document files (simplified implementation)"""
        # This is a simplified implementation
        # In a real application, you'd use libraries like pandoc, python-docx, etc.
        
        if self.output_format == 'txt':
            # Simple text extraction
            with open(self.input_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            raise Exception("Document conversion not implemented")
    
    def to_dict(self):
        """Convert task to dictionary for JSON response"""
        return {
            'id': self.id,
            'input_file': self.input_file,
            'output_format': self.output_format,
            'output_file': self.output_file,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message
        }

class PostDownloadActions:
    @staticmethod
    def extract_archive(file_path, extract_to=None):
        """Extract archive files"""
        try:
            if extract_to is None:
                extract_to = os.path.dirname(file_path)
            
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
            elif file_path.endswith(('.tar', '.tar.gz', '.tgz')):
                import tarfile
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_to)
            else:
                raise Exception("Unsupported archive format")
            
            return True, f"Extracted to {extract_to}"
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def move_file(file_path, destination):
        """Move file to destination"""
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.move(file_path, destination)
            return True, f"Moved to {destination}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def run_command(command, file_path):
        """Run custom command on downloaded file"""
        try:
            # Replace {file} placeholder with actual file path
            command = command.replace('{file}', f'"{file_path}"')
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
                
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def send_notification(title, message):
        """Send system notification"""
        try:
            # For Windows
            if os.name == 'nt':
                import win10toast
                toaster = win10toast.ToastNotifier()
                toaster.show_toast(title, message, duration=5)
            # For Linux
            else:
                subprocess.run(['notify-send', title, message])
            
            return True, "Notification sent"
            
        except Exception as e:
            return False, str(e)

@advanced_bp.route('/convert', methods=['POST'])
@cross_origin()
def start_file_conversion():
    """Start file conversion"""
    try:
        data = request.get_json()
        input_file = data.get('input_file')
        output_format = data.get('output_format')
        output_path = data.get('output_path')
        
        if not input_file or not output_format:
            return jsonify({'error': 'Input file and output format are required'}), 400
        
        if not os.path.exists(input_file):
            return jsonify({'error': 'Input file does not exist'}), 400
        
        # Create conversion task
        converter = FileConverter(input_file, output_format, output_path)
        conversion_tasks[converter.id] = converter
        
        # Start conversion
        converter.start_conversion()
        
        return jsonify({
            'success': True,
            'task_id': converter.id,
            'message': 'File conversion started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@advanced_bp.route('/convert/status/<task_id>', methods=['GET'])
@cross_origin()
def get_conversion_status(task_id):
    """Get conversion task status"""
    task = conversion_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Conversion task not found'}), 404
    
    return jsonify(task.to_dict())

@advanced_bp.route('/convert/list', methods=['GET'])
@cross_origin()
def list_conversions():
    """Get list of all conversion tasks"""
    tasks = [task.to_dict() for task in conversion_tasks.values()]
    return jsonify(tasks)

@advanced_bp.route('/bandwidth', methods=['GET'])
@cross_origin()
def get_bandwidth_settings():
    """Get current bandwidth settings"""
    return jsonify(bandwidth_settings)

@advanced_bp.route('/bandwidth', methods=['POST'])
@cross_origin()
def set_bandwidth_settings():
    """Set bandwidth limits"""
    try:
        data = request.get_json()
        
        bandwidth_settings['enabled'] = data.get('enabled', False)
        bandwidth_settings['download_limit'] = data.get('download_limit', 0)
        bandwidth_settings['upload_limit'] = data.get('upload_limit', 0)
        
        return jsonify({
            'success': True,
            'message': 'Bandwidth settings updated',
            'settings': bandwidth_settings
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@advanced_bp.route('/system/info', methods=['GET'])
@cross_origin()
def get_system_info():
    """Get system information"""
    try:
        # Get system stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network stats
        network = psutil.net_io_counters()
        
        return jsonify({
            'cpu_percent': cpu_percent,
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            },
            'network': {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@advanced_bp.route('/post-download/extract', methods=['POST'])
@cross_origin()
def extract_archive():
    """Extract downloaded archive"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        extract_to = data.get('extract_to')
        
        if not file_path:
            return jsonify({'error': 'File path is required'}), 400
        
        success, message = PostDownloadActions.extract_archive(file_path, extract_to)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@advanced_bp.route('/post-download/move', methods=['POST'])
@cross_origin()
def move_file():
    """Move downloaded file"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        destination = data.get('destination')
        
        if not file_path or not destination:
            return jsonify({'error': 'File path and destination are required'}), 400
        
        success, message = PostDownloadActions.move_file(file_path, destination)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@advanced_bp.route('/post-download/command', methods=['POST'])
@cross_origin()
def run_post_download_command():
    """Run custom command on downloaded file"""
    try:
        data = request.get_json()
        command = data.get('command')
        file_path = data.get('file_path')
        
        if not command or not file_path:
            return jsonify({'error': 'Command and file path are required'}), 400
        
        success, output = PostDownloadActions.run_command(command, file_path)
        
        if success:
            return jsonify({'success': True, 'output': output})
        else:
            return jsonify({'error': output}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@advanced_bp.route('/notification', methods=['POST'])
@cross_origin()
def send_notification():
    """Send system notification"""
    try:
        data = request.get_json()
        title = data.get('title', 'DownloadMaster')
        message = data.get('message', 'Download completed')
        
        success, result = PostDownloadActions.send_notification(title, message)
        
        if success:
            return jsonify({'success': True, 'message': result})
        else:
            return jsonify({'error': result}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@advanced_bp.route('/cleanup', methods=['POST'])
@cross_origin()
def cleanup_temp_files():
    """Clean up temporary files"""
    try:
        temp_dirs = [
            os.path.join(os.path.expanduser("~"), "Downloads", "DownloadMaster", "temp"),
            "/tmp/downloadmaster"
        ]
        
        cleaned_size = 0
        cleaned_files = 0
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleaned_size += file_size
                            cleaned_files += 1
                        except:
                            pass
        
        return jsonify({
            'success': True,
            'cleaned_files': cleaned_files,
            'cleaned_size': cleaned_size,
            'message': f'Cleaned {cleaned_files} files ({cleaned_size} bytes)'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

