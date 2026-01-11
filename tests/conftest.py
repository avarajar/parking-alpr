import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["ADMIN_TOKEN"] = "test-admin-token"

from app.database import Base, get_db
from app.main import app
from app.models import Building, Vehicle


# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token():
    """Return the admin token for tests."""
    return "test-admin-token"


@pytest.fixture
def test_building(db_session):
    """Create a test building."""
    building = Building(
        name="Test Building",
        address="123 Test Street",
        api_token="test-building-token",
    )
    db_session.add(building)
    db_session.commit()
    db_session.refresh(building)
    return building


@pytest.fixture
def test_vehicle(db_session, test_building):
    """Create a test vehicle."""
    vehicle = Vehicle(
        building_id=test_building.id,
        license_plate="ABC123",
        owner_name="John Doe",
        apartment="101A",
        phone="+1234567890",
        vehicle_type="car",
        vehicle_brand="Toyota",
        vehicle_color="black",
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)
    return vehicle


@pytest.fixture
def building_headers(test_building):
    """Return headers with building API key."""
    return {"X-API-Key": test_building.api_token}


@pytest.fixture
def sample_image_base64():
    """Return a minimal valid base64 encoded image (1x1 white PNG)."""
    # 1x1 white PNG image
    return (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
