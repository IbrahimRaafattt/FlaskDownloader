# app.py

import os
from flask import Flask, request, jsonify
# Keep existing imports for download/status functionality
from download import handle_download, get_job_status
# Import the new function from folderUpload.py
from folderUpload import upload_folder_to_gcs
from flask_cors import CORS
import logging
from dotenv import load_dotenv # Import load_dotenv

load_dotenv() # Load variables from .env file into environment


# Set up logging (consistent with folderUpload.py)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Consider restricting origins in production for better security
CORS(app, origins=["*"])

# --- Get GCS Bucket Name (centralized) ---
# Ensure this environment variable is set in your Cloud Run service configuration
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
if not GCS_BUCKET_NAME:
    logger.critical("CRITICAL ERROR: GCS_BUCKET_NAME environment variable not set (checked .env and shell env).")

    # The application might not function correctly.

# --- Routes ---

@app.route('/download', methods=['POST'])
def download_route():
    # Check if GCS is configured, as download.py now depends on it
    if not GCS_BUCKET_NAME:
         logger.error("Download request failed: Server GCS bucket not configured.")
         return jsonify({'error': 'Server configuration error: GCS bucket not set.'}), 500
    return handle_download() # handle_download likely uses GCS_BUCKET_NAME now

@app.route('/status/<job_id>', methods=['GET'])
def status_route(job_id):
    return get_job_status(job_id)

# --- NEW ROUTE for uploading a folder ---
@app.route('/upload-folder', methods=['POST'])
def upload_folder_route():
    """
    API endpoint to trigger the upload of a folder from the container's
    filesystem to Google Cloud Storage.

    Requires JSON payload:
    {
        "source_folder": "/path/inside/container/to/upload",
        "destination_prefix": "target/folder/in/gcs"
    }

    WARNING: Cloud Run instances have ephemeral filesystems.
             Files stored in arbitrary directories within the container
             will NOT persist across instance restarts or scaling events.
             This endpoint is primarily useful for uploading folders that
             are part of the container image or generated/placed in a known
             location during a single instance's lifetime with the explicit
             understanding that the source data might disappear.
             For persistent needs, upload files individually right after
             creation/download (like the /download endpoint does) or use
             mounted volumes like GCS FUSE (adds complexity).
    """
    logger.info("Received request for /upload-folder")

    if not GCS_BUCKET_NAME:
        logger.error("Upload folder request failed: Server GCS bucket not configured.")
        return jsonify({'error': 'Server configuration error: GCS bucket not set.'}), 500

    data = request.get_json()
    if not data:
        logger.warning("Upload folder request rejected: Missing JSON payload.")
        return jsonify({'error': 'Missing JSON payload'}), 400

    source_folder_path = data.get('source_folder')
    destination_prefix = data.get('destination_prefix') # Allows "" as a valid prefix

    # Validate required parameters
    if not source_folder_path:
        logger.warning("Upload folder request rejected: Missing 'source_folder' in payload.")
        return jsonify({'error': "Missing required field: 'source_folder'"}), 400
    if destination_prefix is None:
        logger.warning("Upload folder request rejected: Missing 'destination_prefix' in payload.")
        return jsonify({'error': "Missing required field: 'destination_prefix'"}), 400

    # Log the request details and the warning
    logger.info(f"Attempting folder upload: source='{source_folder_path}', dest_prefix='{destination_prefix}', bucket='{GCS_BUCKET_NAME}'")
    logger.warning("Reminder: Ensure the source folder exists and contains the intended files within the container's ephemeral filesystem at the time of execution.")

    try:
        # Call the imported function
        upload_summary = upload_folder_to_gcs(
            bucket_name=GCS_BUCKET_NAME,
            source_folder=source_folder_path,
            destination_prefix=destination_prefix
        )
        # Return the summary report from the upload function
        return jsonify(upload_summary), 200
    except FileNotFoundError as e:
        logger.error(f"Upload folder error: Source folder not found. {e}")
        return jsonify({'error': str(e), 'message': 'The specified source folder was not found inside the container.'}), 404
    except ValueError as e: # Catch configuration errors like missing bucket
        logger.error(f"Upload folder configuration error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Catch-all for other unexpected errors (GCS issues, etc.)
        logger.error(f"Unexpected error during folder upload process: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected server error occurred during the upload process.'}), 500


# --- Main Execution ---
if __name__ == '__main__':
    # Gunicorn or other WSGI server is recommended for production instead of app.run()
    # Cloud Run automatically sets the PORT environment variable.
    port = int(os.environ.get("PORT", 8080))
    # Debug should be False in production environments like Cloud Run
    app.run(debug=False, host='0.0.0.0', port=port)