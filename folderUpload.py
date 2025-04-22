# folderUpload.py

import os
from google.cloud import storage
import logging

# Use Python's logging module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def upload_folder_to_gcs(bucket_name, source_folder, destination_prefix):
    """
    Uploads all files from a specified local folder (within the container)
    to a GCS bucket, handling potential errors.

    Args:
        bucket_name (str): The name of the target GCS bucket.
        source_folder (str): The path to the local folder inside the container.
        destination_prefix (str): The prefix (folder path) within the GCS bucket.

    Returns:
        dict: A summary of the upload operation.

    Raises:
        ValueError: If bucket_name is not provided.
        FileNotFoundError: If the source_folder does not exist or is not a directory.
        Exception: For other GCS or OS errors during the process.
    """

    if not bucket_name:
        logger.error("GCS bucket name is required but was not provided.")
        raise ValueError("GCS bucket name is required.")

    # Check if the source folder exists and is a directory
    if not os.path.isdir(source_folder):
        logger.error(f"Source folder '{source_folder}' not found or is not a directory.")
        raise FileNotFoundError(f"Source folder '{source_folder}' not found or is not a directory.")

    # Initialize client within the function call (or pass it if reused frequently)
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        logger.info(f"Attempting to upload contents of '{source_folder}' to gs://{bucket_name}/{destination_prefix}")

        uploaded_files_count = 0
        skipped_folders_count = 0
        permission_errors = []
        upload_errors = []

        # Use onerror to handle permission issues during walk gracefully
        for root, dirs, files in os.walk(source_folder, topdown=True, onerror=lambda e: permission_errors.append(e)):
            # Check if the current root itself caused a permission error during listing
            if any(err.filename == root for err in permission_errors):
                logger.warning(f"Skipping folder due to access permission error: {root}")
                skipped_folders_count += 1
                # Prevent os.walk from descending further into this directory
                dirs[:] = []
                files[:] = []
                continue

            logger.info(f"Processing folder: {root}")
            for filename in files:
                local_file_path = os.path.join(root, filename)

                # Ensure it's a file (and not a broken symlink, etc.)
                if not os.path.isfile(local_file_path):
                     logger.warning(f"Skipping non-file item: {local_file_path}")
                     continue

                relative_path = os.path.relpath(local_file_path, source_folder)
                # GCS uses forward slashes for paths
                blob_name = os.path.join(destination_prefix, relative_path).replace("\\", "/")
                blob = bucket.blob(blob_name)

                try:
                    logger.info(f"Uploading {local_file_path} to gs://{bucket_name}/{blob_name}...")
                    blob.upload_from_filename(local_file_path)
                    uploaded_files_count += 1
                    # logger.info(f"Successfully uploaded gs://{bucket_name}/{blob_name}") # Can be verbose
                except PermissionError as pe:
                    logger.error(f"Permission error uploading file {local_file_path}: {pe}")
                    permission_errors.append(pe)
                except Exception as e:
                    logger.error(f"Error uploading file {local_file_path}: {e}")
                    upload_errors.append({"file": local_file_path, "error": str(e)})

        status = "completed"
        if permission_errors or upload_errors:
            status = "completed_with_errors"

        summary = {
            "status": status,
            "source_folder": source_folder,
            "destination_prefix": destination_prefix,
            "uploaded_files_count": uploaded_files_count,
            "skipped_folders_count": skipped_folders_count,
            "permission_error_count": len(permission_errors),
            "upload_error_count": len(upload_errors),
            # Optionally include error details (can be large)
            # "permission_errors": [str(e) for e in permission_errors],
            # "upload_errors": upload_errors
        }
        logger.info(f"Folder upload finished. Summary: {summary}")
        return summary

    except FileNotFoundError as e: # Catch the initial check error
        logger.error(f"Upload failed: {e}")
        raise e # Re-raise specific error
    except Exception as e:
        logger.error(f"An unexpected error occurred during the GCS operation: {e}", exc_info=True)
        raise e # Re-raise unexpected errors


# Remove the example usage block as it will be called from app.py
# if __name__ == "__main__":
#    ... (example usage code removed) ...