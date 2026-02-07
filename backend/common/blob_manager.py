import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO, StringIO
import csv

load_dotenv()
print(os.getenv("AZURE_BLOB_STORAGE_ACCOUNT_URL"))


class BlobManager:
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(
            conn_str=os.getenv("AZURE_BLOB_STORAGE_CONNECTION_STRING")
            )

    def upload_blob(self, container_name, blob_name, data):
        container_client = self.blob_service_client.get_container_client(container_name)
        container_client.upload_blob(blob_name, data)

    def list_blobs(self, container_name):
        container_client = self.blob_service_client.get_container_client(container_name)
        return [blob.name for blob in container_client.list_blobs()]

    def download_blob(self, container_name, blob_name):
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

    def delete_blob(self, container_name, blob_name):
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()

    def read_blob(self, container_name, blob_name):
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_data = blob_client.download_blob().readall()
        if blob_name.endswith(".txt"):
            return blob_data.decode("utf-8")
        elif blob_name.endswith(".csv"):
            csv_file = StringIO(blob_data.decode("utf-8"))
            reader = csv.DictReader(csv_file)
            return list(reader)
        elif blob_name.endswith(".xlsx"):
            excel_file = BytesIO(blob_data)
            df = pd.read_excel(excel_file)
            return df.to_dict(orient="records")
        elif blob_name.endswith(".json"):
            return blob_data.decode("utf-8")