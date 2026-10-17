from uuid import UUID

from man.files.schemas import FileCreate
from man.integrations.vercel.blob.service import blob
from man.kit.utils import generate_uuid


class FileService:
    async def create(self, create_schema: FileCreate) -> tuple[UUID, str]:
        file_id = generate_uuid()

        upload_url = await blob.issue_signed_token(
            pathname=str(file_id), content_type=create_schema.mime_type
        )

        return file_id, upload_url


files = FileService()
