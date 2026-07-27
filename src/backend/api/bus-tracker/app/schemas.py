from pydantic import BaseModel


class CreateTrackedLineRequest(BaseModel):
    line_code: str
    label: str = ""
    active: bool = True


class UpdateTrackedLineRequest(BaseModel):
    line_code: str
    label: str = ""
    active: bool = True
