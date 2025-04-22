import os
from flask import Flask, request, jsonify, send_from_directory
from download import handle_download, get_job_status
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["*"])
# Define the "downloads" folder path relative to where this file is located
DOWNLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'downloads'))

# Ensure the "downloads" folder exists
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Register download and status routes
@app.route('/download', methods=['POST'])
def download():
    return handle_download()





if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080) # Cloud Run port