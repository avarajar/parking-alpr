from pydantic import BaseModel, Field
from datetime import datetime


# Building schemas
class BuildingCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, examples=["Tower A"])
    address: str | None = Field(None, max_length=255, examples=["123 Main St"])


class BuildingResponse(BaseModel):
    id: int
    name: str
    address: str | None
    api_token: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BuildingPublicResponse(BaseModel):
    id: int
    name: str
    address: str | None
    is_active: bool

    class Config:
        from_attributes = True


# Vehicle schemas
class VehicleBase(BaseModel):
    license_plate: str = Field(..., min_length=4, max_length=20, examples=["ABC123"])
    owner_name: str = Field(..., min_length=2, max_length=100, examples=["John Doe"])
    apartment: str | None = Field(None, max_length=20, examples=["101A"])
    phone: str | None = Field(None, max_length=20, examples=["+1234567890"])
    vehicle_type: str | None = Field(None, max_length=50, examples=["car"])
    vehicle_brand: str | None = Field(None, max_length=50, examples=["Toyota"])
    vehicle_color: str | None = Field(None, max_length=30, examples=["black"])


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    owner_name: str | None = Field(None, min_length=2, max_length=100)
    apartment: str | None = Field(None, max_length=20)
    phone: str | None = Field(None, max_length=20)
    vehicle_type: str | None = Field(None, max_length=50)
    vehicle_brand: str | None = Field(None, max_length=50)
    vehicle_color: str | None = Field(None, max_length=30)
    is_active: bool | None = None


class VehicleResponse(VehicleBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


# Plate recognition schemas
class PlateVerifyRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image of the license plate")


class PlateVerifyResponse(BaseModel):
    license_plate: str | None = Field(None, description="Detected license plate text")
    is_authorized: bool = Field(..., description="Whether the vehicle is authorized")
    confidence: int | None = Field(None, description="OCR confidence percentage (0-100)")
    owner_name: str | None = Field(None, description="Owner name if authorized")
    apartment: str | None = Field(None, description="Apartment if authorized")
    message: str = Field(..., description="Status message")


# Access log schemas
class AccessLogResponse(BaseModel):
    id: int
    license_plate: str
    is_authorized: bool
    confidence: int | None
    accessed_at: datetime

    class Config:
        from_attributes = True
