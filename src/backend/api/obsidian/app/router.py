from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src import webdav
from .schemas import CreateFileRequest, WriteFileRequest, DeleteRequest, MoveRequest

router = APIRouter()


@router.get("/files")
def get_files(path: str = "gio", type: str = "dir"):
    try:
        if type == "file":
            content = webdav.read_file(path)
            return {"content": content, "path": path}
        entries = webdav.list_directory(path)
        return entries
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/files", status_code=201)
def create_file(body: CreateFileRequest):
    try:
        if body.action == "mkdir":
            webdav.make_directory(body.path)
            return {"created": True, "path": body.path}
        if not body.path:
            raise ValueError("path is required")
        webdav.write_file(body.path, body.content)
        return {"created": True, "path": body.path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="internal server error")


@router.put("/files")
def update_file(body: WriteFileRequest):
    try:
        if not body.path:
            raise ValueError("path is required")
        webdav.write_file(body.path, body.content)
        return {"updated": True, "path": body.path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="internal server error")


@router.delete("/files")
def delete_file(body: DeleteRequest):
    try:
        if not body.path:
            raise ValueError("path is required")
        webdav.delete_resource(body.path)
        return {"deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="internal server error")


@router.patch("/files")
def move_file(body: MoveRequest):
    try:
        if not body.from_path or not body.to:
            raise ValueError("from and to are required")
        webdav.move_resource(body.from_path, body.to)
        return {"moved": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="internal server error")
