from urllib.parse import urlparse
from minio import Minio
from ..config import settings

class StorageProvider:
    def __init__(self):
        # Parse endpoint to derive host and scheme
        print("Initializing StorageProvider...")
        ep = settings.minio_endpoint
        parsed = urlparse(ep)
        if parsed.scheme:
            endpoint = parsed.netloc
            secure = parsed.scheme == "https"
        else:
            endpoint = ep.replace("http://", "").replace("https://", "")
            secure = False
        self.client = Minio(
            endpoint=endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=secure,
        )
        self.ensure_bucket(settings.minio_bucket)

    def ensure_bucket(self, bucket: str):
        exists = self.client.bucket_exists(bucket)
        if not exists:
            self.client.make_bucket(bucket)

    def delete_prefix(self, bucket: str, prefix: str):
        # Remove all objects under prefix (non-recursive recursion via list)
        objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
        for obj in objects:
            try:
                self.client.remove_object(bucket, obj.object_name)
            except Exception:
                pass
