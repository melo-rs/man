from fastapi import APIRouter

from man.files.schemas import FileCreate, FileSchema
from man.files.service import files

router = APIRouter()


@router.post("/files")
async def create_file(create_schema: FileCreate) -> FileSchema:
    file_id, upload_url = await files.create(create_schema)
    return FileSchema.model_validate(
        {"id": file_id, "upload_url": upload_url, "mime_type": create_schema.mime_type}
    )
