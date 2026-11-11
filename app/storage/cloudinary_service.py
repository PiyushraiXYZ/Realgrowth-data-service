import cloudinary
import cloudinary.uploader

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.config.settings import settings


class CloudinaryStorageService:

    def __init__(self):
        self._configure()

    def _configure(self):
        if not all([
            settings.cloudinary_cloud_name,
            settings.cloudinary_api_key,
            settings.cloudinary_api_secret,
        ]):
            raise RuntimeError(
                "Cloudinary credentials are missing. "
                "Please configure them in your .env file."
            )

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

    async def upload_image(
        self,
        file: UploadFile,
        folder: str | None = None,
    ) -> dict:

        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }

        if file.content_type not in allowed_types:
            raise ValueError(
                "Only JPEG, PNG, and WEBP images are supported."
            )

        image_bytes = await file.read()

        if not image_bytes:
            raise ValueError("Uploaded image is empty.")

        max_size = 10 * 1024 * 1024

        if len(image_bytes) > max_size:
            raise ValueError(
                "Image size cannot exceed 10 MB."
            )

        upload_result = await run_in_threadpool(
            cloudinary.uploader.upload,
            image_bytes,
            folder=folder or settings.cloudinary_folder,
            resource_type="image",
            overwrite=False,
        )

        return {
            "public_id": upload_result["public_id"],
            "image_url": upload_result["secure_url"],
            "format": upload_result.get("format"),
            "width": upload_result.get("width"),
            "height": upload_result.get("height"),
            "bytes": upload_result.get("bytes"),
        }

    async def delete_image(self, public_id: str):
        return await run_in_threadpool(
            cloudinary.uploader.destroy,
            public_id,
            resource_type="image",
        )


cloudinary_storage = CloudinaryStorageService()
