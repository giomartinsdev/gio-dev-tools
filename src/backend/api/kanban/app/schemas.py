from pydantic import BaseModel


class CreateBoardRequest(BaseModel):
    name: str


class BoardResponse(BaseModel):
    id: str
    name: str


class CreateCardRequest(BaseModel):
    title: str
    content: str = ""
    status: str


class UpdateCardRequest(BaseModel):
    title: str
    content: str = ""
    status: str
    board_id: str


class CardResponse(BaseModel):
    id: str
    board_id: str
    title: str
    content: str
    status: str
