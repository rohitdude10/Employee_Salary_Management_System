from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.employees import router as employees_router
from app.api.routes.salary import router as salary_router

__all__ = [
    "analytics_router",
    "auth_router",
    "employees_router",
    "salary_router",
]
