import os
from flask import Flask, request, jsonify, send_from_directory
from download import handle_download, get_job_status
from flask_cors import CORS
from folderUpload import upload_folder  # Import the upload function

app = Flask(__name__)
CORS(app, origins=["*"])
# Define the "downloads" folder path relative to where this file is located
DOWNLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'downloads'))

# Ensure the "downloads" folder exists
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Google Cloud Storage Configuration (Replace with your actual values)
BUCKET_NAME = "hidden-matter-450501-n0_cloudbuild"
DESTINATION_PREFIX = "source"

# Modify the download route to include upload functionality
@app.route('/download', methods=['POST'])
def download():
    result = handle_download()  # Get the result from handle_download

    if result.status_code == 200:  # Check if download was successful
        try:
            # Assuming handle_download returns a JSON response with 'filename'
            filename = result.get_json().get('filename')
            if filename:
                source_folder = DOWNLOAD_FOLDER
                upload_folder(BUCKET_NAME, source_folder, DESTINATION_PREFIX)
            else:
                print("Filename not found in handle_download's response.")
        except Exception as e:
            print(f"Error during upload: {e}")
    else:
        print(f"Download failed with status code: {result.status_code}")

    return result  # Return the original result from handle_download

@app.route('/status/<job_id>', methods=['GET'])
def status(job_id):
    return get_job_status(job_id)

@app.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080) # Cloud Run port