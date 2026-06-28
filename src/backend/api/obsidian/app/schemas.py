from pydantic import BaseModel, Field


class CreateFileRequest(BaseModel):
    action: str = "create"
    path: str
    content: str = ""


class WriteFileRequest(BaseModel):
    path: str
    content: str = ""


class DeleteRequest(BaseModel):
    path: str


class MoveRequest(BaseModel):
    from_path: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}
