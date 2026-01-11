import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging

from app.database import engine, get_db, Base
from app.models import Building, Vehicle, AccessLog
from app.schemas import (
    BuildingCreate,
    BuildingResponse,
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
    PlateVerifyRequest,
    PlateVerifyResponse,
    AccessLogResponse,
)
from app.auth import get_current_building
from app.alpr_service import alpr_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin token for building management (set via environment variable)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me-in-production")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield


app = FastAPI(
    title="Parking ALPR Microservice",
    description="License plate recognition microservice for building parking management. "
    "Each building has its own API token for authentication.",
    version="1.0.0",
    lifespan=lifespan,
)


# Health check
@app.get("/health", tags=["Health"])
def health_check():
    """Check if the service is running."""
    return {"status": "ok", "service": "parking-alpr"}


# =============================================================================
# ADMIN ENDPOINTS (for building management)
# =============================================================================


def verify_admin_token(token: str = Query(..., alias="admin_token")):
    """Verify admin token for building management."""
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return True


@app.post(
    "/admin/buildings",
    response_model=BuildingResponse,
    status_code=201,
    tags=["Admin"],
)
def create_building(
    building_data: BuildingCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """
    Create a new building and generate its API token.
    Requires admin_token query parameter.
    """
    building = Building(
        name=building_data.name,
        address=building_data.address,
    )
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


@app.get(
    "/admin/buildings",
    response_model=list[BuildingResponse],
    tags=["Admin"],
)
def list_buildings(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """List all buildings with their API tokens. Requires admin_token."""
    return db.query(Building).all()


@app.post(
    "/admin/buildings/{building_id}/regenerate-token",
    response_model=BuildingResponse,
    tags=["Admin"],
)
def regenerate_building_token(
    building_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """Regenerate API token for a building. Requires admin_token."""
    from app.models import generate_api_token

    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    building.api_token = generate_api_token()
    db.commit()
    db.refresh(building)
    return building


# =============================================================================
# PLATE VERIFICATION (requires building API token)
# =============================================================================


@app.post("/api/v1/verify", response_model=PlateVerifyResponse, tags=["Verification"])
def verify_plate(
    request: PlateVerifyRequest,
    db: Session = Depends(get_db),
    building: Building = Depends(get_current_building),
):
    """
    Verify if a vehicle is authorized to enter the building.

    Requires X-API-Key header with building's API token.
    """
    # Recognize license plate
    result = alpr_service.recognize_from_base64(request.image_base64)

    if not result.success:
        log_entry = AccessLog(
            building_id=building.id,
            license_plate="UNREADABLE",
            is_authorized=False,
            confidence=None,
        )
        db.add(log_entry)
        db.commit()

        return PlateVerifyResponse(
            license_plate=None,
            is_authorized=False,
            confidence=None,
            message=f"Failed to read license plate: {result.error}",
        )

    if not result.text:
        return PlateVerifyResponse(
            license_plate=None,
            is_authorized=False,
            confidence=result.confidence,
            message="No license plate detected in the image",
        )

    # Check if vehicle is authorized FOR THIS BUILDING
    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.building_id == building.id,
            Vehicle.license_plate == result.text,
            Vehicle.is_active == True,
        )
        .first()
    )

    # Log access attempt
    log_entry = AccessLog(
        building_id=building.id,
        license_plate=result.text,
        is_authorized=vehicle is not None,
        confidence=result.confidence,
    )
    db.add(log_entry)
    db.commit()

    if vehicle:
        return PlateVerifyResponse(
            license_plate=result.text,
            is_authorized=True,
            confidence=result.confidence,
            owner_name=vehicle.owner_name,
            apartment=vehicle.apartment,
            message="Vehicle authorized",
        )
    else:
        return PlateVerifyResponse(
            license_plate=result.text,
            is_authorized=False,
            confidence=result.confidence,
            message="Vehicle not authorized for this building",
        )


# =============================================================================
# VEHICLE MANAGEMENT (requires building API token)
# =============================================================================


@app.get("/api/v1/vehicles", response_model=list[VehicleResponse], tags=["Vehicles"])
def list_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    building: Building = Depends(get_current_building),
):
    """List all vehicles registered for this building."""
    query = db.query(Vehicle).filter(Vehicle.building_id == building.id)
    if active_only:
        query = query.filter(Vehicle.is_active == True)
    return query.offset(skip).limit(limit).all()


@app.get(
    "/api/v1/vehicles/{license_plate}",
    response_model=VehicleResponse,
    tags=["Vehicles"],
)
def get_vehicle(
    license_plate: str,
    db: Session = Depends(get_db),
    building: Building = Depends(get_current_building),
):
    """Get a specific vehicle by license plate."""
    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.building_id == building.id,
            Vehicle.license_plate == license_plate.upper(),
        )
        .first()
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@app.post(
    "/api/v1/vehicles",
    response_model=VehicleResponse,
    status_code=201,
    tags=["Vehicles"],
)
def create_vehicle(
    vehicle_data: VehicleCreate,
    db: Session = Depends(get_db),
    building: Building = Depends(get_current_building),
):
    """Register a new authorized vehicle for this building."""
    license_plate = vehicle_data.license_plate.upper().replace(" ", "")

    # Check if already exists in this building
    existing = (
        db.query(Vehicle)
        .filter(
            Vehicle.building_id == building.id,
            Vehicle.license_plate == license_plate,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Vehicle with this license plate already registered in this building",
        )

    vehicle = Vehicle(
        building_id=building.id,
        license_plate=license_plate,
        owner_name=vehicle_data.owner_name,
        apartment=vehicle_data.apartment,
        phone=vehicle_data.phone,
        vehicle_type=vehicle_data.vehicle_type,
        vehicle_brand=vehicle_data.vehicle_brand,
        vehicle_color=vehicle_data.vehicle_color,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@app.put(
    "/api/v1/vehicles/{license_plate}",
    response_model=VehicleResponse,
    tags=["Vehicles"],
)
def update_vehicle(
    license_plate: str,
    vehicle_data: VehicleUpdate,
    db: Session = Depends(get_db),
    building: Building = Depends(get_current_building),
):
    """Update an existing vehicle."""
    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.building_id == building.id,
            Vehicle.license_plate == license_plate.upper(),
        )
        .first()
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    update_data = vehicle_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle


@app.delete("/api/v1/vehicles/{license_plate}", tags=["Vehicles"])
def delete_vehicle(
    license_plate: str,
    db: Session = Depends(get_db),
    building: Building = Depends(get_current_building),
):
    """Deactivate a vehicle (soft delete)."""
    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.building_id == building.id,
            Vehicle.license_plate == license_plate.upper(),
        )
        .first()
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    vehicle.is_active = False
    db.commit()
    return {"message": "Vehicle deactivated successfully"}


# =============================================================================
# ACCESS LOGS (requires building API token)
# =============================================================================


@app.get("/api/v1/logs", response_model=list[AccessLogResponse], tags=["Access Logs"])
def list_access_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    authorized_only: bool | None = Query(None),
    db: Session = Depends(get_db),
    building: Building = Depends(get_current_building),
):
    """List access logs for this building."""
    query = db.query(AccessLog).filter(AccessLog.building_id == building.id)
    if authorized_only is not None:
        query = query.filter(AccessLog.is_authorized == authorized_only)
    return query.order_by(AccessLog.accessed_at.desc()).offset(skip).limit(limit).all()


@app.get(
    "/api/v1/logs/{license_plate}",
    response_model=list[AccessLogResponse],
    tags=["Access Logs"],
)
def get_vehicle_logs(
    license_plate: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    building: Building = Depends(get_current_building),
):
    """Get access logs for a specific vehicle in this building."""
    return (
        db.query(AccessLog)
        .filter(
            AccessLog.building_id == building.id,
            AccessLog.license_plate == license_plate.upper(),
        )
        .order_by(AccessLog.accessed_at.desc())
        .limit(limit)
        .all()
    )
