from fastapi import APIRouter

from app.core.deps import CurrentUserDep, SessionDep
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(session: SessionDep, user: CurrentUserDep) -> DashboardResponse:
    return DashboardService.get_dashboard(session, user)
