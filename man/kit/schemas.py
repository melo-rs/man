from datetime import datetime

from pydantic import UUID7, BaseModel, ConfigDict, Field


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDSchema(Schema):
    id: UUID7 = Field(..., description="The ID of the object.")

    model_config = ConfigDict(json_schema_mode_override="serialization")


class TimestampedSchema(Schema):
    created_at: datetime = Field(description="The creation date of the object.")
    modified_at: datetime | None = Field(
        description="Last modification date of the object."
    )
