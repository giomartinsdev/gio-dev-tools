from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from shared.logger import get_logger
from src.application.commands.create_service import CreateServiceCommand, CreateServiceHandler
from src.application.commands.update_service import UpdateServiceCommand, UpdateServiceHandler
from src.application.commands.delete_service import DeleteServiceCommand, DeleteServiceHandler
from src.infrastructure.repository import PostgresServiceRepository
from src.infrastructure.event_bus import EventBus

from .deps import get_repo, get_bus
from .schemas import CreateServiceRequest, UpdateServiceRequest

logger = get_logger(__name__)

router = APIRouter()


@router.get("/services")
def list_services(repo: PostgresServiceRepository = Depends(get_repo)):
    return [s.to_dict() for s in repo.find_all()]


@router.post("/services", status_code=201)
def create_service(
    body: CreateServiceRequest,
    repo: PostgresServiceRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        service = CreateServiceHandler(repo, bus).handle(CreateServiceCommand(
            name=body.name,
            category=body.category,
            status=body.status,
            secret_ref=body.secret_ref,
            notes=body.notes,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return service.to_dict()


@router.patch("/services/{service_id}", status_code=200)
def update_service(
    service_id: str,
    body: UpdateServiceRequest,
    repo: PostgresServiceRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        service = UpdateServiceHandler(repo, bus).handle(UpdateServiceCommand(
            service_id=service_id,
            name=body.name,
            category=body.category,
            status=body.status,
            secret_ref=body.secret_ref,
            notes=body.notes,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if service is None:
        raise HTTPException(status_code=404, detail="service not found")
    return service.to_dict()


@router.delete("/services/{service_id}", status_code=200)
def delete_service(
    service_id: str,
    repo: PostgresServiceRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    deleted = DeleteServiceHandler(repo, bus).handle(DeleteServiceCommand(service_id=service_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="service not found")
    return {"deleted": True}
