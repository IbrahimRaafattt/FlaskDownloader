import subprocess
import json
import os
import time
import random
from pathlib import Path
import threading
from flask import request, jsonify
from datetime import datetime
import re

# In-memory job tracker
jobs = {}

def generate_job_id():
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=9))

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "_", title)

def handle_download():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    job_id = generate_job_id()
    jobs[job_id] = {
        'status': 'queued',
        'progress': 0,
        'title': 'Fetching...',
        'duration': 'Fetching...',
        'size': 'Fetching...',
    }

    downloads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'downloads'))
    timestamp = datetime.now().strftime('%H_%M_%S_%d-%m-%Y')
    initial_title = 'Untitled'
    quality = 'best'
    duration_minutes = '0'
    final_filename_base = f"{timestamp}_{sanitize_filename(initial_title)}_{quality}.mp4"
    final_path = Path(f"{downloads_dir}/{final_filename_base}")

    command = [
        'yt-dlp',
        '--cookies', 'cookies.txt',
        '--no-check-certificate',
        '--verbose',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
        '-f', 'bestvideo+bestaudio/best',
        '--merge-output-format', 'mp4',
        '-o', str(final_path),
        '--print-json', url
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def update_progress():
        nonlocal initial_title, quality, duration_minutes, final_path, final_filename_base
        json_data = []
        for line in process.stdout:
            try:
                json_line = json.loads(line.strip())
                json_data.append(json_line)
                if 'progress' in json_line:
                    jobs[job_id]['progress'] = int(json_line['progress'])
                elif 'total_bytes_estimate' in json_line and 'downloaded_bytes' in json_line:
                    total_chunks = json_line['total_bytes_estimate']
                    downloaded_chunks = json_line['downloaded_bytes']
                    jobs[job_id]['progress'] = int((downloaded_chunks / total_chunks) * 100)
                if 'title' in json_line:
                    initial_title = json_line['title'] or 'Untitled'
                    jobs[job_id]['title'] = initial_title
                    final_filename_base = f"{timestamp}_{sanitize_filename(initial_title)}_{quality}.mp4"
                    final_path = Path(f"{downloads_dir}/{final_filename_base}") # Update path
                if 'format_note' in json_line:
                    quality = json_line['format_note']
                if 'duration' in json_line:
                    duration_seconds = int(json_line['duration'])
                    duration_minutes = str(int(duration_seconds / 60))
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}, Line: {line.strip()}")
            except Exception as e:
                print(f"Error parsing yt-dlp output: {e}")
        process.stdout.close()

    def handle_error():
        error_output = ""
        for line in process.stderr:
            print(f"stderr: {line}")
            error_output += line
        process.stderr.close()
        if 'error' not in jobs[job_id]:
            jobs[job_id]['error'] = error_output.strip()

    update_progress_thread = threading.Thread(target=update_progress)
    update_error_thread = threading.Thread(target=handle_error)

    update_progress_thread.start()
    update_error_thread.start()

    process.wait()

    response_data = {'jobId': job_id}

    if process.returncode == 0:
        jobs[job_id]['status'] = 'completed'
        final_title = jobs[job_id]['title']
        sanitized_title = sanitize_filename(final_title)
        new_filename = f"{timestamp}_{sanitized_title}_{quality}.mp4"
        new_path = Path(f"{downloads_dir}/{new_filename}")

        if final_path.exists() and new_filename != final_filename_base:
            try:
                os.rename(final_path, new_path)
                jobs[job_id]['filename'] = new_filename
                response_data['filename'] = new_filename
            except OSError as e:
                jobs[job_id]['error'] = f"Error renaming file: {e}"
                jobs[job_id]['status'] = 'failed'
        else:
            jobs[job_id]['filename'] = final_filename_base
            response_data['filename'] = final_filename_base

        jobs[job_id]['quality'] = quality
        jobs[job_id]['duration_minutes'] = duration_minutes

    else:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = jobs[job_id].get('error', f"Process exited with code {process.returncode}")

    return jsonify(response_data)

def get_job_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(jobs[job_id])

if __name__ == '__main__':
    # This block is for testing download.py independently (optional)
    # You can add code here to simulate requests and test the functions
    pass