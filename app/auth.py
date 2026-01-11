from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_building(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db),
) -> Building:
    """
    Validate API key and return the associated building.

    Usage: Add as dependency to protected endpoints.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'X-API-Key' header.",
        )

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
