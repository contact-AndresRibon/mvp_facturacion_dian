from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, SessionDep
from app.schemas.dashboard import TopProductItem
from app.schemas.report import SalesReportResponse, TopProductsReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/sales", response_model=SalesReportResponse)
def sales_report(
    session: SessionDep,
    user: CurrentUserDep,
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> SalesReportResponse:
    return ReportService.sales_report(session, user, date_from=date_from, date_to=date_to)


@router.get("/top-products", response_model=TopProductsReportResponse)
def top_products(
    session: SessionDep,
    user: CurrentUserDep,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(default=10, ge=1, le=50),
) -> TopProductsReportResponse:
    items = ReportService.top_products(
        session, user, date_from=date_from, date_to=date_to, limit=limit
    )
    return TopProductsReportResponse(date_from=date_from, date_to=date_to, items=items)
