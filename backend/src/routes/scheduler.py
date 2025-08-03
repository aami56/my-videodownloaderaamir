from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import threading
import time
import uuid
import schedule
import json
from datetime import datetime, timedelta
from .download import DownloadTask, download_tasks
from .video import VideoDownloadTask, video_tasks
from .torrent import TorrentDownloadTask, torrent_tasks

scheduler_bp = Blueprint('scheduler', __name__)

# Global storage for scheduled tasks
scheduled_tasks = {}
scheduler_thread = None
scheduler_running = False

class ScheduledTask:
    def __init__(self, name, task_type, task_data, schedule_type, schedule_value, repeat=True):
        self.id = str(uuid.uuid4())
        self.name = name
        self.task_type = task_type  # 'download', 'video', 'torrent'
        self.task_data = task_data
        self.schedule_type = schedule_type  # 'once', 'daily', 'weekly', 'interval'
        self.schedule_value = schedule_value
        self.repeat = repeat
        self.status = "active"  # active, paused, completed
        self.created_at = datetime.now()
        self.next_run = None
        self.last_run = None
        self.run_count = 0
        self.error_message = None
        
    def execute(self):
        """Execute the scheduled task"""
        try:
            self.last_run = datetime.now()
            self.run_count += 1
            
            if self.task_type == 'download':
                task = DownloadTask(
                    url=self.task_data['url'],
                    filename=self.task_data.get('filename'),
                    download_path=self.task_data.get('download_path'),
                    max_connections=self.task_data.get('max_connections', 4)
                )
                download_tasks[task.id] = task
                task.start_download()
                
            elif self.task_type == 'video':
                task = VideoDownloadTask(
                    url=self.task_data['url'],
                    quality=self.task_data.get('quality', 'best'),
                    format_type=self.task_data.get('format', 'mp4'),
                    download_path=self.task_data.get('download_path'),
                    audio_only=self.task_data.get('audio_only', False)
                )
                video_tasks[task.id] = task
                task.start_download()
                
            elif self.task_type == 'torrent':
                task = TorrentDownloadTask(
                    magnet_link=self.task_data.get('magnet_link'),
                    torrent_file=self.task_data.get('torrent_file'),
                    download_path=self.task_data.get('download_path'),
                    max_connections=self.task_data.get('max_connections', 50)
                )
                torrent_tasks[task.id] = task
                task.start_download()
            
            # Update next run time
            self._calculate_next_run()
            
            # Mark as completed if not repeating
            if not self.repeat:
                self.status = "completed"
                
        except Exception as e:
            self.error_message = str(e)
    
    def _calculate_next_run(self):
        """Calculate the next run time based on schedule"""
        if not self.repeat:
            self.next_run = None
            return
            
        now = datetime.now()
        
        if self.schedule_type == 'daily':
            self.next_run = now + timedelta(days=1)
        elif self.schedule_type == 'weekly':
            self.next_run = now + timedelta(weeks=1)
        elif self.schedule_type == 'interval':
            self.next_run = now + timedelta(seconds=self.schedule_value)
        else:
            self.next_run = None
    
    def to_dict(self):
        """Convert task to dictionary for JSON response"""
        return {
            'id': self.id,
            'name': self.name,
            'task_type': self.task_type,
            'task_data': self.task_data,
            'schedule_type': self.schedule_type,
            'schedule_value': self.schedule_value,
            'repeat': self.repeat,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'run_count': self.run_count,
            'error_message': self.error_message
        }

def scheduler_worker():
    """Background worker that runs scheduled tasks"""
    global scheduler_running
    
    while scheduler_running:
        try:
            now = datetime.now()
            
            for task_id, task in list(scheduled_tasks.items()):
                if (task.status == "active" and 
                    task.next_run and 
                    now >= task.next_run):
                    
                    # Execute the task
                    task.execute()
                    
                    # Remove completed tasks
                    if task.status == "completed":
                        del scheduled_tasks[task_id]
            
            time.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            print(f"Scheduler error: {e}")
            time.sleep(10)

def start_scheduler():
    """Start the scheduler background thread"""
    global scheduler_thread, scheduler_running
    
    if not scheduler_running:
        scheduler_running = True
        scheduler_thread = threading.Thread(target=scheduler_worker)
        scheduler_thread.daemon = True
        scheduler_thread.start()

def stop_scheduler():
    """Stop the scheduler background thread"""
    global scheduler_running
    scheduler_running = False

# Start scheduler when module is imported
start_scheduler()

@scheduler_bp.route('/create', methods=['POST'])
@cross_origin()
def create_scheduled_task():
    """Create a new scheduled task"""
    try:
        data = request.get_json()
        
        name = data.get('name')
        task_type = data.get('task_type')
        task_data = data.get('task_data')
        schedule_type = data.get('schedule_type')
        schedule_value = data.get('schedule_value')
        repeat = data.get('repeat', True)
        
        if not all([name, task_type, task_data, schedule_type]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if task_type not in ['download', 'video', 'torrent']:
            return jsonify({'error': 'Invalid task type'}), 400
        
        # Create scheduled task
        task = ScheduledTask(name, task_type, task_data, schedule_type, schedule_value, repeat)
        
        # Calculate initial next run time
        now = datetime.now()
        if schedule_type == 'once':
            if isinstance(schedule_value, str):
                task.next_run = datetime.fromisoformat(schedule_value)
            else:
                task.next_run = now + timedelta(seconds=schedule_value)
        elif schedule_type == 'daily':
            task.next_run = now + timedelta(days=1)
        elif schedule_type == 'weekly':
            task.next_run = now + timedelta(weeks=1)
        elif schedule_type == 'interval':
            task.next_run = now + timedelta(seconds=schedule_value)
        
        scheduled_tasks[task.id] = task
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Scheduled task created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scheduler_bp.route('/list', methods=['GET'])
@cross_origin()
def list_scheduled_tasks():
    """Get list of all scheduled tasks"""
    tasks = [task.to_dict() for task in scheduled_tasks.values()]
    return jsonify(tasks)

@scheduler_bp.route('/status/<task_id>', methods=['GET'])
@cross_origin()
def get_scheduled_task_status(task_id):
    """Get status of a specific scheduled task"""
    task = scheduled_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Scheduled task not found'}), 404
    
    return jsonify(task.to_dict())

@scheduler_bp.route('/pause/<task_id>', methods=['POST'])
@cross_origin()
def pause_scheduled_task(task_id):
    """Pause a scheduled task"""
    task = scheduled_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Scheduled task not found'}), 404
    
    task.status = "paused"
    return jsonify({'success': True, 'message': 'Scheduled task paused'})

@scheduler_bp.route('/resume/<task_id>', methods=['POST'])
@cross_origin()
def resume_scheduled_task(task_id):
    """Resume a scheduled task"""
    task = scheduled_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Scheduled task not found'}), 404
    
    task.status = "active"
    return jsonify({'success': True, 'message': 'Scheduled task resumed'})

@scheduler_bp.route('/delete/<task_id>', methods=['DELETE'])
@cross_origin()
def delete_scheduled_task(task_id):
    """Delete a scheduled task"""
    task = scheduled_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Scheduled task not found'}), 404
    
    del scheduled_tasks[task_id]
    return jsonify({'success': True, 'message': 'Scheduled task deleted'})

@scheduler_bp.route('/execute/<task_id>', methods=['POST'])
@cross_origin()
def execute_scheduled_task_now(task_id):
    """Execute a scheduled task immediately"""
    task = scheduled_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Scheduled task not found'}), 404
    
    try:
        task.execute()
        return jsonify({'success': True, 'message': 'Scheduled task executed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scheduler_bp.route('/stats', methods=['GET'])
@cross_origin()
def get_scheduler_stats():
    """Get scheduler statistics"""
    total = len(scheduled_tasks)
    active = len([t for t in scheduled_tasks.values() if t.status == 'active'])
    paused = len([t for t in scheduled_tasks.values() if t.status == 'paused'])
    completed = len([t for t in scheduled_tasks.values() if t.status == 'completed'])
    
    total_executions = sum(t.run_count for t in scheduled_tasks.values())
    
    return jsonify({
        'total': total,
        'active': active,
        'paused': paused,
        'completed': completed,
        'total_executions': total_executions,
        'scheduler_running': scheduler_running
    })

