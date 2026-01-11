from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building

api_key_header = APIKeyHeader(
    name="X-API-Key",
    description="API token for building authentication. Get it from the admin panel.",
)


def get_current_building(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db),
) -> Building:
    """
    Validate API key and return the associated building.

    Usage: Add as dependency to protected endpoints.
    """
    building = (
        db.query(Building)
        .filter(Building.api_token == api_key, Building.is_active == True)
        .first()
    )

    if not building:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key.",
        )

    return building
