import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
import logging

from app.database import engine, get_db, Base
from app.models import Building, Vehicle, AccessLog
from app.schemas import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
    PlateVerifyRequest,
    PlateVerifyResponse,
    AccessLogResponse,
)
from app.alpr_service import alpr_service
from app.admin import setup_admin
from starlette.middleware.sessions import SessionMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.auth import get_current_building


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield


app = FastAPI(
    title="Parking ALPR Microservice",
    description="License plate recognition microservice for building parking management.\n\n"
    "**Admin Panel:** [/admin](/admin) (login: admin/admin)\n\n"
    "**API Authentication:** Use `X-API-Key` header with the building's API token.",
    version="1.0.0",
    lifespan=lifespan,
)

# Add session middleware for admin authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
)

# Setup SQLAdmin panel
setup_admin(app, engine)


# Health check
@app.get("/health", tags=["Health"])
def health_check():
    """Check if the service is running."""
    return {"status": "ok", "service": "parking-alpr"}


# =============================================================================
# PLATE VERIFICATION
# =============================================================================


@app.post(
    "/api/v1/verify-upload",
    response_model=PlateVerifyResponse,
    tags=["Verification"],
)
async def verify_plate_upload(
    image: UploadFile = File(..., description="Image file containing license plate"),
    building: Building = Depends(get_current_building),
    db: Session = Depends(get_db),
):
    """
    Detect and read license plate from uploaded image.

    **Use this endpoint to test from Swagger UI** - just upload an image file.

    Requires `X-API-Key` header with the building's API token.
    """
    import base64

    contents = await image.read()
    image_base64 = base64.b64encode(contents).decode()

    result = alpr_service.recognize_from_base64(image_base64)

    if not result.success:
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

    # Check if vehicle is authorized for this building
    plate = result.text.upper().replace(" ", "")
    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.building_id == building.id,
            Vehicle.license_plate == plate,
            Vehicle.is_active == True,
        )
        .first()
    )

    is_authorized = vehicle is not None

    # Log the access attempt
    access_log = AccessLog(
        building_id=building.id,
        license_plate=plate,
        is_authorized=is_authorized,
        confidence=result.confidence,
    )
    db.add(access_log)
    db.commit()

    if is_authorized:
        message = f"Vehicle authorized - Owner: {vehicle.owner_name}, Apt: {vehicle.apartment}"
    else:
        message = "Vehicle not authorized for this building"

    return PlateVerifyResponse(
        license_plate=plate,
        is_authorized=is_authorized,
        confidence=result.confidence,
        message=message,
    )


@app.post("/api/v1/verify", response_model=PlateVerifyResponse, tags=["Verification"])
def verify_plate(
    request: PlateVerifyRequest,
    building: Building = Depends(get_current_building),
    db: Session = Depends(get_db),
):
    """
    Detect license plate from base64 encoded image.

    For programmatic use. Use /verify-upload for testing in Swagger UI.

    Requires `X-API-Key` header with the building's API token.
    """
    result = alpr_service.recognize_from_base64(request.image_base64)

    if not result.success:
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

    # Check if vehicle is authorized for this building
    plate = result.text.upper().replace(" ", "")
    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.building_id == building.id,
            Vehicle.license_plate == plate,
            Vehicle.is_active == True,
        )
        .first()
    )

    is_authorized = vehicle is not None

    # Log the access attempt
    access_log = AccessLog(
        building_id=building.id,
        license_plate=plate,
        is_authorized=is_authorized,
        confidence=result.confidence,
    )
    db.add(access_log)
    db.commit()

    if is_authorized:
        message = f"Vehicle authorized - Owner: {vehicle.owner_name}, Apt: {vehicle.apartment}"
    else:
        message = "Vehicle not authorized for this building"

    return PlateVerifyResponse(
        license_plate=plate,
        is_authorized=is_authorized,
        confidence=result.confidence,
        message=message,
    )


# =============================================================================
# VEHICLE MANAGEMENT
# =============================================================================


@app.get("/api/v1/vehicles", response_model=list[VehicleResponse], tags=["Vehicles"])
def list_vehicles(
    building: Building = Depends(get_current_building),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """List all vehicles registered for the authenticated building."""
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
    building: Building = Depends(get_current_building),
    db: Session = Depends(get_db),
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
    building: Building = Depends(get_current_building),
    db: Session = Depends(get_db),
):
    """Register a new authorized vehicle for the authenticated building."""
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
    building: Building = Depends(get_current_building),
    db: Session = Depends(get_db),
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
    building: Building = Depends(get_current_building),
    db: Session = Depends(get_db),
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
# ACCESS LOGS
# =============================================================================


@app.get("/api/v1/logs", response_model=list[AccessLogResponse], tags=["Access Logs"])
def list_access_logs(
    building: Building = Depends(get_current_building),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    authorized_only: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    """List access logs for the authenticated building."""
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
    building: Building = Depends(get_current_building),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get access logs for a specific vehicle in the authenticated building."""
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
