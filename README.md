# Parking ALPR Microservice

A license plate recognition microservice for building parking management. Uses AI-powered OCR to detect and read license plates from images, then verifies if vehicles are authorized to enter.

## Features

- **Automatic License Plate Recognition (ALPR)** - AI-powered plate detection using YOLO + OCR
- **Admin Panel** - Web-based admin interface powered by SQLAdmin
- **Multi-tenant Architecture** - Each building has its own API token and isolated data
- **Vehicle Management** - Register, update, and deactivate authorized vehicles
- **Access Logging** - Complete history of all access attempts
- **REST API** - Simple JSON API with OpenAPI documentation
- **Docker Ready** - Easy deployment with Docker Compose

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PARKING ALPR MICROSERVICE                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   FastAPI    │───▶│   FastALPR   │───▶│  PostgreSQL   │  │
│  │  REST API    │    │  (YOLO+OCR)  │    │   Database    │  │
│  └──────────────┘    └──────────────┘    └───────────────┘  │
│         │                                        │          │
│         ▼                                        ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    SQLAdmin Panel                    │   │
│  │         Manage Buildings, Vehicles, Logs            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/avarajar/parking-alpr.git
cd parking-alpr

# Copy environment file
cp .env.example .env

# Edit .env with your settings (optional for development)
```

### 2. Build and start

```bash
make build
make up
```

### 3. Access the services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Admin Panel** | http://localhost:8000/admin/ | admin / admin |
| **API Docs (Swagger)** | http://localhost:8000/docs | - |
| **API Docs (ReDoc)** | http://localhost:8000/redoc | - |
| **Health Check** | http://localhost:8000/health | - |

## Testing Guide

### Step 1: Create a Building (Admin Panel)

1. Go to http://localhost:8000/admin/
2. Login with `admin` / `admin`
3. Click on **Buildings** in the sidebar
4. Click **+ Create**
5. Fill in the building name and address
6. Click **Save**
7. **Copy the API Token** from the building list (you'll need this for API calls)

```
┌─────────────────────────────────────────────────────────────┐
│  Buildings                                                   │
│  ┌─────┬────────────┬─────────────────────────────┬────────┐│
│  │ ID  │ Name       │ API Token                   │ Active ││
│  ├─────┼────────────┼─────────────────────────────┼────────┤│
│  │ 1   │ Tower A    │ a1b2c3d4e5f6g7h8i9j0... ← Copy this  ││
│  └─────┴────────────┴─────────────────────────────┴────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Step 2: Register a Vehicle (Admin Panel or Swagger)

**Option A: Using Admin Panel**
1. Click on **Vehicles** in the sidebar
2. Click **+ Create**
3. Select the building, enter license plate, owner name, apartment
4. Click **Save**

**Option B: Using Swagger UI**
1. Go to http://localhost:8000/docs
2. Click the **Authorize** button (lock icon at top right)
3. Enter your API token in the `X-API-Key` field
4. Click **Authorize**, then **Close**
5. Find `POST /api/v1/vehicles` and click **Try it out**
6. Enter the vehicle data and click **Execute**

### Step 3: Test Plate Verification (Swagger UI)

1. Go to http://localhost:8000/docs
2. Make sure you're authorized (Step 2, Option B)
3. Find `POST /api/v1/verify-upload`
4. Click **Try it out**
5. Upload an image with a license plate
6. Click **Execute**

**Response for authorized vehicle:**
```json
{
  "license_plate": "ABC123",
  "is_authorized": true,
  "confidence": 95,
  "message": "Vehicle authorized - Owner: John Doe, Apt: 101"
}
```

**Response for unauthorized vehicle:**
```json
{
  "license_plate": "XYZ789",
  "is_authorized": false,
  "confidence": 92,
  "message": "Vehicle not authorized for this building"
}
```

### Step 4: View Access Logs

**Option A: Admin Panel**
- Click on **Access Logs** in the sidebar to see all access attempts

**Option B: Swagger UI**
- Use `GET /api/v1/logs` to see logs for your building

## Environment Variables

All configuration is done via the `.env` file:

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=parking_db
DATABASE_URL=postgresql://postgres:postgres@db:5432/parking_db

# Admin Panel
ADMIN_USER=admin
ADMIN_PASSWORD=change-me-in-production
SECRET_KEY=change-me-in-production-use-random-string
```

## Makefile Commands

```bash
make help           # Show all available commands
make build          # Build Docker images
make up             # Start all services
make down           # Stop all services
make logs           # View service logs
make test           # Run tests in Docker
make test-cov       # Run tests with coverage
make shell          # Open shell in API container
make db-shell       # Open PostgreSQL shell
make clean          # Remove containers and volumes
make health         # Check API health
```

## Admin Panel

The admin panel is available at `/admin/` and provides a web interface to manage:

- **Buildings** - Create buildings and view their API tokens
- **Vehicles** - Register and manage authorized vehicles
- **Access Logs** - View history of all access attempts (read-only)

### Screenshots

```
┌─────────────────────────────────────────────────────────────┐
│  Parking ALPR Admin                    [Buildings ▼]        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Buildings                                                   │
│  ┌─────┬────────────┬─────────────────────┬────────┐        │
│  │ ID  │ Name       │ API Token           │ Active │        │
│  ├─────┼────────────┼─────────────────────┼────────┤        │
│  │ 1   │ Tower A    │ abc123xyz...        │ ✓      │        │
│  │ 2   │ Tower B    │ def456uvw...        │ ✓      │        │
│  └─────┴────────────┴─────────────────────┴────────┘        │
│                                                              │
│  [+ Create]                                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

All `/api/v1/*` endpoints require authentication via the `X-API-Key` header with the building's API token.

### Plate Verification

#### Verify with Image Upload (Swagger UI friendly)
```http
POST /api/v1/verify-upload
Content-Type: multipart/form-data
X-API-Key: <building-api-token>

[Upload image file directly]
```

**This is the easiest way to test** - go to http://localhost:8000/docs, find this endpoint, click "Try it out", add the X-API-Key header, and upload an image.

#### Verify with Base64 (for programmatic use)
```http
POST /api/v1/verify
Content-Type: application/json
X-API-Key: <building-api-token>

{
  "image_base64": "base64-encoded-image-data"
}
```

**Response (authorized vehicle):**
```json
{
  "license_plate": "ABC123",
  "is_authorized": true,
  "confidence": 95,
  "message": "Vehicle authorized - Owner: John Doe, Apt: 101"
}
```

**Response (unauthorized vehicle):**
```json
{
  "license_plate": "XYZ789",
  "is_authorized": false,
  "confidence": 92,
  "message": "Vehicle not authorized for this building"
}
```

### Building Management

Buildings are managed through the **Admin Panel** at http://localhost:8000/admin/

- Login with `admin` / `admin`
- Click on **Buildings** to create, edit, or view API tokens

### Vehicle Management (requires X-API-Key)

```http
GET    /api/v1/vehicles              # List vehicles for authenticated building
POST   /api/v1/vehicles              # Register vehicle
GET    /api/v1/vehicles/{plate}      # Get vehicle
PUT    /api/v1/vehicles/{plate}      # Update vehicle
DELETE /api/v1/vehicles/{plate}      # Deactivate vehicle
```

### Access Logs (requires X-API-Key)

```http
GET /api/v1/logs                     # List access logs for authenticated building
GET /api/v1/logs/{plate}             # Get vehicle logs
```

## Usage Examples

### Python

```python
import requests
import base64

API_URL = "http://localhost:8000"
API_KEY = "your-building-api-token"  # Get this from admin panel

headers = {"X-API-Key": API_KEY}

# Read and encode image
with open("plate.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

# Verify plate
response = requests.post(
    f"{API_URL}/api/v1/verify",
    headers=headers,
    json={"image_base64": image_base64}
)

result = response.json()
print(f"Plate: {result['license_plate']}")
print(f"Authorized: {result['is_authorized']}")
print(f"Confidence: {result['confidence']}%")
```

### cURL

```bash
# First, create a building in the Admin Panel and copy the API token
# Then use it for all API calls:
API_KEY="your-building-api-token"

# Register a vehicle
curl -X POST http://localhost:8000/api/v1/vehicles \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"license_plate": "ABC123", "owner_name": "John Doe", "apartment": "101"}'

# Verify a plate (upload image)
curl -X POST http://localhost:8000/api/v1/verify-upload \
  -H "X-API-Key: $API_KEY" \
  -F "image=@plate.jpg"

# List all vehicles
curl http://localhost:8000/api/v1/vehicles \
  -H "X-API-Key: $API_KEY"

# View access logs
curl http://localhost:8000/api/v1/logs \
  -H "X-API-Key: $API_KEY"
```

## Project Structure

```
parking-alpr/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application and endpoints
│   ├── admin.py          # SQLAdmin configuration
│   ├── auth.py           # Authentication logic (TODO)
│   ├── alpr_service.py   # License plate recognition service
│   ├── database.py       # Database connection and session
│   ├── models.py         # SQLAlchemy models
│   └── schemas.py        # Pydantic schemas
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_health.py
│   ├── test_admin.py
│   ├── test_vehicles.py
│   ├── test_verify.py
│   ├── test_logs.py
│   ├── test_auth.py
│   └── test_alpr_service.py
├── .env                  # Environment variables (create from .env.example)
├── .env.example          # Environment variables template
├── .gitignore
├── pytest.ini
├── requirements.txt
├── Makefile
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
docker-compose run --rm api pytest tests/test_vehicles.py -v
```

## Database Schema

### Buildings
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(100) | Building name |
| address | String(255) | Building address |
| api_token | String(64) | Unique API token (auto-generated) |
| is_active | Boolean | Active status |
| created_at | DateTime | Creation timestamp |

### Vehicles
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| building_id | Integer | Foreign key to buildings |
| license_plate | String(20) | Vehicle plate number |
| owner_name | String(100) | Owner's name |
| apartment | String(20) | Apartment number |
| phone | String(20) | Contact phone |
| vehicle_type | String(50) | car, motorcycle, truck |
| vehicle_brand | String(50) | Brand name |
| vehicle_color | String(30) | Color |
| is_active | Boolean | Active status |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### Access Logs
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| building_id | Integer | Foreign key to buildings |
| license_plate | String(20) | Detected plate |
| is_authorized | Boolean | Authorization result |
| confidence | Integer | OCR confidence (0-100) |
| accessed_at | DateTime | Access timestamp |

## Technology Stack

- **Framework**: FastAPI
- **Admin Panel**: SQLAdmin
- **Database**: PostgreSQL + SQLAlchemy
- **ALPR Engine**: FastALPR (YOLO + OCR)
- **Containerization**: Docker + Docker Compose
- **Testing**: Pytest
- **Python**: 3.12+

## TODO

- [x] Implement API authentication with building tokens
- [x] Add authorization check in verify endpoints
- [ ] Store access log images
- [ ] Add rate limiting
- [ ] Add webhook notifications

## Security Notes (Production)

1. **Change default credentials** in `.env`:
   - `ADMIN_PASSWORD` - Use a strong password
   - `SECRET_KEY` - Use a random 32+ character string
   - `POSTGRES_PASSWORD` - Use a strong password

2. **Use HTTPS** - Put behind nginx/traefik with SSL

3. **Restrict network access** - Don't expose database port in production

## License

MIT License
