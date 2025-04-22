import os
from google.cloud import storage

def upload_folder(bucket_name, source_folder, destination_prefix):
    """Uploads all files from a local folder to a GCS bucket, handling folder permission errors."""

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    try:
        for root, _, files in os.walk(source_folder):
            print(f"Checking folder: {root}")  # Added line for debugging
            for filename in files:
                local_file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_file_path, source_folder)
                blob_name = os.path.join(destination_prefix, relative_path)
                blob = bucket.blob(blob_name)

                try:
                    blob.upload_from_filename(local_file_path)
                    print(f"File {local_file_path} uploaded to gs://{bucket_name}/{blob_name}.")
                except Exception as e:
                    print(f"Error uploading {local_file_path}: {e}")
    except PermissionError as e:
        print(f"Permission error in: {root}. Error: {e}")

# Example usage:
bucket_name = "hidden-matter-450501-n0_cloudbuild"
source_folder = "downloads"  # Replace with your local folder path
destination_prefix = "source"  # Replace with your desired prefix (folder) in the bucket

# Ensure the local folder exists
if not os.path.exists(source_folder):
    print(f"Error: Local folder '{source_folder}' not found.")
else:
    upload_folder(bucket_name, source_folder, destination_prefix)