
import shutil
from typing import Union
from fastapi import HTTPException, UploadFile
from tempfile import NamedTemporaryFile
from b2sdk.v2 import InMemoryAccountInfo, B2Api
import os
from app.settings.config import settings

info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", settings.BACKBLAZE_ID, settings.BACKBLAZE_KEY)



async def upload_to_backblaze(file: Union[UploadFile, str], filename_id: str) -> str:
    """
    Uploads a file or a file at a given path to the specified Backblaze B2 bucket.
    """
    try:
        # Determine if the input is a file path or an UploadFile
        if isinstance(file, str):
            # If it's a string, assume it's a file path
            file_path = file
            file_name = os.path.basename(file_path)
        else:
            # It's an UploadFile; create a temporary file to copy to
            with NamedTemporaryFile(delete=False) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                file_path = temp_file.name
                file_name = file.filename

        # Ensure the filename is unique

        bucket_name = settings.BUCKET_NAME_ITEMS
        bucket = b2_api.get_bucket_by_name(bucket_name)

        # Upload file to Backblaze B2
        bucket.upload_local_file(
            local_file=file_path,
            file_name=filename_id
        )

        # Get public URL of the uploaded file
        download_url = b2_api.get_download_url_for_file_name(bucket_name, filename_id)
        return download_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    finally:
        # Clean up if a temporary file was used
        if isinstance(file, UploadFile) and file and hasattr(file, 'file'):
            file.file.close()
        if isinstance(file, str):
            os.remove(file_path)  # Remove the generated image file after uploading