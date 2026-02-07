from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
from common.blob_manager import BlobManager

load_dotenv()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}


# Endpoint to upload any file to blob storage by clicking on choose file and then clicking on upload. The file will be uploaded to the blob storage with the name of the file as the blob name. The file will be uploaded to the container specified in the .env file. The endpoint will return a message indicating that the file has been uploaded successfully. The endpoint will also return the name of the blob that was uploaded. The endpoint will also return the URL of the blob that was uploaded. The URL of the blob will be in the format https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}. The endpoint will also return the size of the blob that was uploaded.

@app.post("/api/files/upload-blob", tags=["files"])
async def upload_file(filename: str, file: UploadFile = File(...)):
    blob_manager = BlobManager()
    container_name = os.getenv("AZURE_BLOB_STORAGE_CONTAINER_NAME")
    file_bytes = await file.read()
    blob_manager.upload_blob(container_name, filename, file_bytes)
    return {
        "message": "File uploaded successfully",
        "blob_name": filename,
        "blob_url": f"{os.getenv('AZURE_BLOB_STORAGE_ACCOUNT_URL')}{container_name}/{filename}",
        "size": len(file_bytes)
    }

# endpoint to delete blob
@app.delete("/api/files/delete-blob", tags=["files"])
async def delete_blob(blob_name: str):
    blob_manager = BlobManager()
    container_name = os.getenv("AZURE_BLOB_STORAGE_CONTAINER_NAME")
    blob_manager.delete_blob(container_name, blob_name)
    return {
        "message": "Blob deleted successfully",
        "blob_name": blob_name
    }

# endpoint to list blobs in container
@app.get("/api/files/list-blobs", tags=["files"])
async def list_blobs():
    blob_manager = BlobManager()
    container_name = os.getenv("AZURE_BLOB_STORAGE_CONTAINER_NAME")
    blob_list = blob_manager.list_blobs(container_name)
    return {
        "blobs": blob_list
    }

@app.get("/api/files/read-blob", tags=["files"])
async def read_blob(blob_name: str):
    blob_manager = BlobManager()
    container_name = os.getenv("AZURE_BLOB_STORAGE_CONTAINER_NAME")
    blob_content = blob_manager.read_blob(container_name, blob_name)
    blob_url = f"{os.getenv('AZURE_BLOB_STORAGE_ACCOUNT_URL')}{container_name}/{blob_name}"
    return {
        "blob_content": blob_content,
        "size": len(blob_content),
        "blob_url": blob_url
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
