# Parking ALPR Microservice

A license plate recognition microservice for building parking management. Uses AI-powered OCR to detect and read license plates from images, then verifies if vehicles are authorized to enter.

## Features

- **Automatic License Plate Recognition (ALPR)** - AI-powered plate detection and OCR
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
│  │                  Authentication                      │   │
│  │  Admin Token (building mgmt) │ API Key (per building)│   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/avarajar/parking-alpr.git
cd parking-alpr
```

2. Build and start:
```bash
make build
make up
```

3. Access the API at `http://localhost:8000`

### Makefile Commands

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
make create-building  # Create a test building
make list-buildings   # List all buildings
```

### Local Development (without Docker)

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start PostgreSQL (or use Docker):
```bash
docker run -d --name parking-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=parking_db \
  -p 5432:5432 \
  postgres:16-alpine
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once running, access the interactive documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

The API uses two levels of authentication:

### Admin Token
Used for building management operations. Pass as query parameter:
```
?admin_token=your-admin-token
```

### Building API Key
Each building receives a unique API token. Pass in the header:
```
X-API-Key: building-api-token
```

## API Endpoints

### Health Check

```http
GET /health
```

Returns service status. No authentication required.

---

### Admin Endpoints

#### Create a Building
```http
POST /admin/buildings?admin_token=xxx
Content-Type: application/json

{
  "name": "Tower A",
  "address": "123 Main Street"
}
```

Response:
```json
{
  "id": 1,
  "name": "Tower A",
  "address": "123 Main Street",
  "api_token": "abc123...",
  "is_active": true,
  "created_at": "2025-01-11T10:00:00Z"
}
```

#### List All Buildings
```http
GET /admin/buildings?admin_token=xxx
```

#### Regenerate Building Token
```http
POST /admin/buildings/{building_id}/regenerate-token?admin_token=xxx
```

---

### Plate Verification

#### Verify a License Plate
```http
POST /api/v1/verify
X-API-Key: building-api-token
Content-Type: application/json

{
  "image_base64": "base64-encoded-image-data"
}
```

Response (Authorized):
```json
{
  "license_plate": "ABC123",
  "is_authorized": true,
  "confidence": 95,
  "owner_name": "John Doe",
  "apartment": "101A",
  "message": "Vehicle authorized"
}
```

Response (Not Authorized):
```json
{
  "license_plate": "XYZ789",
  "is_authorized": false,
  "confidence": 92,
  "owner_name": null,
  "apartment": null,
  "message": "Vehicle not authorized for this building"
}
```

---

### Vehicle Management

#### List Vehicles
```http
GET /api/v1/vehicles
X-API-Key: building-api-token
```

Query parameters:
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Max results (default: 100, max: 1000)
- `active_only` (bool): Only active vehicles (default: true)

#### Get Vehicle by Plate
```http
GET /api/v1/vehicles/{license_plate}
X-API-Key: building-api-token
```

#### Register a Vehicle
```http
POST /api/v1/vehicles
X-API-Key: building-api-token
Content-Type: application/json

{
  "license_plate": "ABC123",
  "owner_name": "John Doe",
  "apartment": "101A",
  "phone": "+1234567890",
  "vehicle_type": "car",
  "vehicle_brand": "Toyota",
  "vehicle_color": "black"
}
```

#### Update a Vehicle
```http
PUT /api/v1/vehicles/{license_plate}
X-API-Key: building-api-token
Content-Type: application/json

{
  "apartment": "102B",
  "phone": "+0987654321"
}
```

#### Deactivate a Vehicle
```http
DELETE /api/v1/vehicles/{license_plate}
X-API-Key: building-api-token
```

---

### Access Logs

#### List Access Logs
```http
GET /api/v1/logs
X-API-Key: building-api-token
```

Query parameters:
- `skip` (int): Pagination offset
- `limit` (int): Max results (default: 100)
- `authorized_only` (bool): Filter by authorization status

#### Get Logs for a Vehicle
```http
GET /api/v1/logs/{license_plate}
X-API-Key: building-api-token
```

## Usage Examples

### Python

```python
import requests
import base64

API_URL = "http://localhost:8000"
API_KEY = "your-building-api-token"

# Read and encode image
with open("plate.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

# Verify plate
response = requests.post(
    f"{API_URL}/api/v1/verify",
    headers={"X-API-Key": API_KEY},
    json={"image_base64": image_base64}
)

result = response.json()
if result["is_authorized"]:
    print(f"Welcome, {result['owner_name']}!")
else:
    print(f"Vehicle {result['license_plate']} not authorized")
```

### cURL

```bash
# Create a building (admin)
curl -X POST "http://localhost:8000/admin/buildings?admin_token=your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "Tower A", "address": "123 Main St"}'

# Register a vehicle
curl -X POST http://localhost:8000/api/v1/vehicles \
  -H "X-API-Key: building-token" \
  -H "Content-Type: application/json" \
  -d '{"license_plate": "ABC123", "owner_name": "John Doe", "apartment": "101"}'

# Verify a plate (with base64 image)
curl -X POST http://localhost:8000/api/v1/verify \
  -H "X-API-Key: building-token" \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "'$(base64 -i plate.jpg)'"}'
```

### JavaScript/Node.js

```javascript
const fs = require('fs');

const API_URL = 'http://localhost:8000';
const API_KEY = 'your-building-api-token';

// Read and encode image
const imageBuffer = fs.readFileSync('plate.jpg');
const imageBase64 = imageBuffer.toString('base64');

// Verify plate
fetch(`${API_URL}/api/v1/verify`, {
  method: 'POST',
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ image_base64: imageBase64 })
})
  .then(res => res.json())
  .then(result => {
    if (result.is_authorized) {
      console.log(`Welcome, ${result.owner_name}!`);
    } else {
      console.log(`Vehicle ${result.license_plate} not authorized`);
    }
  });
```

## Project Structure

```
reconocimiento-placas/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application and endpoints
│   ├── auth.py           # Authentication logic
│   ├── alpr_service.py   # License plate recognition service
│   ├── database.py       # Database connection and session
│   ├── models.py         # SQLAlchemy models
│   └── schemas.py        # Pydantic schemas
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # Pytest fixtures
│   ├── test_health.py    # Health endpoint tests
│   ├── test_admin.py     # Admin endpoints tests
│   ├── test_vehicles.py  # Vehicle CRUD tests
│   ├── test_verify.py    # Plate verification tests
│   ├── test_logs.py      # Access logs tests
│   ├── test_auth.py      # Authentication tests
│   └── test_alpr_service.py  # ALPR service tests
├── .env.example          # Environment variables template
├── .gitignore
├── pytest.ini            # Pytest configuration
├── requirements.txt      # Python dependencies
├── Makefile              # Development commands
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Testing

The project includes a comprehensive test suite using pytest.

### Running Tests

```bash
# Install dependencies (includes test dependencies)
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_vehicles.py

# Run specific test class
pytest tests/test_vehicles.py::TestCreateVehicle

# Run specific test
pytest tests/test_vehicles.py::TestCreateVehicle::test_create_vehicle_success
```

### Test Coverage

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test Categories

| Test File | Description | Tests |
|-----------|-------------|-------|
| `test_health.py` | Health check endpoint | 1 |
| `test_admin.py` | Building management (create, list, regenerate token) | 9 |
| `test_vehicles.py` | Vehicle CRUD operations | 18 |
| `test_verify.py` | License plate verification | 7 |
| `test_logs.py` | Access logs retrieval | 9 |
| `test_auth.py` | Authentication and multi-tenant isolation | 7 |
| `test_alpr_service.py` | ALPR service unit tests | 12 |

### Test Database

Tests use an in-memory SQLite database, so no external database is required. Each test runs in isolation with a fresh database.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/parking_db` |
| `ADMIN_TOKEN` | Token for admin operations | `change-me-in-production` |

## Database Schema

### Buildings
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(100) | Building name |
| address | String(255) | Building address |
| api_token | String(64) | Unique API token |
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
| image_path | String(255) | Stored image path |
| accessed_at | DateTime | Access timestamp |

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **ALPR Engine**: FastALPR (YOLO + OCR)
- **Containerization**: Docker + Docker Compose
- **Python**: 3.12+

## Performance Considerations

- ALPR model is lazily loaded on first request
- Database connections are pooled via SQLAlchemy
- Async-ready with FastAPI (upgrade to async endpoints for higher throughput)
- For GPU acceleration, use `fast-alpr[onnx-gpu]` instead of `fast-alpr[onnx]`

## Security Best Practices

1. **Change the default ADMIN_TOKEN** before deploying to production
2. **Use HTTPS** in production (put behind a reverse proxy like nginx)
3. **Regenerate building tokens** if compromised
4. **Set strong database passwords** in production
5. **Limit network access** to the database container

## Troubleshooting

### ALPR not detecting plates
- Ensure the image is clear and well-lit
- Try higher resolution images
- Check that the plate is not too small in the frame

### Database connection errors
- Verify PostgreSQL is running: `docker ps`
- Check DATABASE_URL is correct
- Ensure the database exists

### Authentication errors
- Verify the API key is correct
- Check the building is active
- Ensure you're using the correct header (`X-API-Key`)

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
