from pydantic import BaseModel


class CreateServiceRequest(BaseModel):
    name: str
    category: str
    status: str = "disconnected"
    secret_ref: str = ""
    notes: str = ""


class UpdateServiceRequest(BaseModel):
    name: str
    category: str
    status: str
    secret_ref: str = ""
    notes: str = ""
