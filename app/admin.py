from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
import os

from app.models import Building, Vehicle, AccessLog


# Simple authentication backend
# TODO: Replace with proper user management in production
class AdminAuth(AuthenticationBackend):
    """Simple authentication for admin panel."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Get credentials from environment variables
        admin_user = os.getenv("ADMIN_USER", "admin")
        admin_pass = os.getenv("ADMIN_PASSWORD", "admin")

        if username == admin_user and password == admin_pass:
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> RedirectResponse | bool:
        if request.session.get("authenticated"):
            return True
        return RedirectResponse(url="/admin/login", status_code=302)


# Model Views
class BuildingAdmin(ModelView, model=Building):
    """Admin view for Buildings."""

    name = "Building"
    name_plural = "Buildings"
    icon = "fa-solid fa-building"

    column_list = [
        Building.id,
        Building.name,
        Building.address,
        Building.api_token,
        Building.is_active,
        Building.created_at,
    ]

    column_searchable_list = [Building.name, Building.address]
    column_sortable_list = [Building.id, Building.name, Building.created_at]
    column_default_sort = ("created_at", True)

    # Show full token in detail view, truncated in list
    column_formatters = {
        Building.api_token: lambda m, a: m.api_token[:20] + "..." if m.api_token else ""
    }

    # Only allow editing name, address, and is_active
    # Token is auto-generated
    form_columns = [
        Building.name,
        Building.address,
        Building.is_active,
    ]


class VehicleAdmin(ModelView, model=Vehicle):
    """Admin view for Vehicles."""

    name = "Vehicle"
    name_plural = "Vehicles"
    icon = "fa-solid fa-car"

    column_list = [
        Vehicle.id,
        Vehicle.license_plate,
        Vehicle.owner_name,
        Vehicle.apartment,
        Vehicle.building,
        Vehicle.is_active,
        Vehicle.created_at,
    ]

    column_searchable_list = [Vehicle.license_plate, Vehicle.owner_name, Vehicle.apartment]
    column_sortable_list = [Vehicle.id, Vehicle.license_plate, Vehicle.owner_name, Vehicle.created_at]
    column_default_sort = ("created_at", True)

    form_columns = [
        Vehicle.building,
        Vehicle.license_plate,
        Vehicle.owner_name,
        Vehicle.apartment,
        Vehicle.phone,
        Vehicle.vehicle_type,
        Vehicle.vehicle_brand,
        Vehicle.vehicle_color,
        Vehicle.is_active,
    ]


class AccessLogAdmin(ModelView, model=AccessLog):
    """Admin view for Access Logs (read-only)."""

    name = "Access Log"
    name_plural = "Access Logs"
    icon = "fa-solid fa-clipboard-list"

    column_list = [
        AccessLog.id,
        AccessLog.license_plate,
        AccessLog.is_authorized,
        AccessLog.confidence,
        AccessLog.building,
        AccessLog.accessed_at,
    ]

    column_searchable_list = [AccessLog.license_plate]
    column_sortable_list = [AccessLog.id, AccessLog.license_plate, AccessLog.accessed_at]
    column_default_sort = ("accessed_at", True)

    # Read-only - logs should not be editable
    can_create = False
    can_edit = False
    can_delete = False


def setup_admin(app, engine):
    """Setup SQLAdmin with the FastAPI app."""
    authentication_backend = AdminAuth(secret_key=os.getenv("SECRET_KEY", "change-me-in-production"))

    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="Parking ALPR Admin",
    )

    admin.add_view(BuildingAdmin)
    admin.add_view(VehicleAdmin)
    admin.add_view(AccessLogAdmin)

    return admin
