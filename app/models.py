import secrets
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


def generate_api_token():
    """Generate a secure random API token."""
    return secrets.token_urlsafe(32)


class Building(Base):
    """Model for buildings with API authentication."""

    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=True)
    api_token = Column(String(64), unique=True, index=True, default=generate_api_token)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    vehicles = relationship("Vehicle", back_populates="building")
    access_logs = relationship("AccessLog", back_populates="building")


class Vehicle(Base):
    """Model for authorized vehicles in a building."""

    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    license_plate = Column(String(20), index=True, nullable=False)
    owner_name = Column(String(100), nullable=False)
    apartment = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    vehicle_type = Column(String(50), nullable=True)
    vehicle_brand = Column(String(50), nullable=True)
    vehicle_color = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    building = relationship("Building", back_populates="vehicles")


class AccessLog(Base):
    """Model to log vehicle access attempts."""

    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    license_plate = Column(String(20), index=True, nullable=False)
    is_authorized = Column(Boolean, nullable=False)
    confidence = Column(Integer, nullable=True)
    image_path = Column(String(255), nullable=True)
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    building = relationship("Building", back_populates="access_logs")
