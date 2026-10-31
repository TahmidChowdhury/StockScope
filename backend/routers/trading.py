"""Shared paper research: all roles can read; admin alone can change saved ledgers."""
from __future__ import annotations

import csv
import io
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response

from backend.core.auth import verify_password_with_role
from backend.trading import congress, risk, service, storage
from backend.trading.models import BacktestInput, BacktestNameInput, CongressImport, OrderInput, PortfolioInput

router = APIRouter()


def admin(role=Depends(verify_password_with_role)):
    if role != "admin":
        raise HTTPException(403, "Admin access is required to modify shared trading research")
    return role


def call(operation, *args):
    try:
        return operation(*args)
    except KeyError:
        raise HTTPException(404, "Trading record not found") from None
    except service.Conflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except OSError:
        raise HTTPException(503, "Trading file storage is unavailable") from None


@router.get("/portfolios")
def portfolios(role=Depends(verify_password_with_role)):
    return call(storage.listing, "portfolio")


@router.post("/portfolios", status_code=201)
def create_portfolio(request: PortfolioInput, role=Depends(admin)):
    return call(service.create_portfolio, request)


@router.get("/portfolios/{portfolio_id}")
def portfolio(portfolio_id: str, role=Depends(verify_password_with_role)):
    if not portfolio_id.startswith("portfolio-"):
        raise HTTPException(404, "Portfolio not found")
    return service.public_portfolio(call(service.get_document, portfolio_id))


@router.get("/portfolios/{portfolio_id}/export")
def export_portfolio(portfolio_id: str, role=Depends(verify_password_with_role)):
    import json
    if not portfolio_id.startswith("portfolio-"):
        raise HTTPException(404, "Portfolio not found")
    document = call(service.get_document, portfolio_id)
    return Response(json.dumps(document, allow_nan=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{portfolio_id}.json"'})


@router.post("/portfolios/{portfolio_id}/orders", status_code=201)
def order(portfolio_id: str, request: OrderInput, role=Depends(admin)):
    if not portfolio_id.startswith("portfolio-"):
        raise HTTPException(404, "Portfolio not found")
    return call(service.place_order, portfolio_id, request)


@router.post("/portfolios/{portfolio_id}/orders/{order_id}/cancel")
def cancel(portfolio_id: str, order_id: str, role=Depends(admin)):
    if not portfolio_id.startswith("portfolio-"):
        raise HTTPException(404, "Portfolio not found")
    return call(service.cancel_order, portfolio_id, order_id)


@router.post("/portfolios/{portfolio_id}/refresh")
def refresh(portfolio_id: str, role=Depends(admin)):
    if not portfolio_id.startswith("portfolio-"):
        raise HTTPException(404, "Portfolio not found")
    return call(service.refresh_portfolio, portfolio_id)


@router.get("/backtests")
def backtests(role=Depends(verify_password_with_role)):
    return call(storage.listing, "run")


@router.post("/backtests", status_code=201)
def backtest(request: BacktestInput, role=Depends(admin)):
    document = call(service.run_backtest, request)
    return {k: v for k, v in document.items() if k != "data"}


@router.get("/backtests/{run_id}")
def get_backtest(run_id: str, role=Depends(verify_password_with_role)):
    if not run_id.startswith("run-"):
        raise HTTPException(404, "Backtest not found")
    document = call(service.get_document, run_id)
    return {k: v for k, v in document.items() if k != "data"}


@router.get("/backtests/{run_id}/export")
def export_backtest(run_id: str, role=Depends(verify_password_with_role)):
    if not run_id.startswith("run-"):
        raise HTTPException(404, "Backtest not found")
    # Complete saved inputs, raw daily observations, disclosure subset, and outputs for reproducibility.
    import json
    document = call(service.get_document, run_id)
    return Response(json.dumps(document, allow_nan=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{run_id}.json"'})


@router.get("/backtests/{run_id}/risk")
def backtest_risk(run_id: str, role=Depends(verify_password_with_role)):
    if not run_id.startswith("run-"):
        raise HTTPException(404, "Backtest not found")
    document = call(service.get_document, run_id)
    try:
        return call(risk.analyze, document)
    except risk.RiskUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/backtests/{run_id}/name")
def rename_backtest(run_id: str, request: BacktestNameInput, role=Depends(admin)):
    if not run_id.startswith("run-"):
        raise HTTPException(404, "Backtest not found")
    document = call(service.rename_backtest, run_id, request)
    return {k: v for k, v in document.items() if k != "data"}


@router.get("/congress")
def disclosures(member: str = Query(default="", max_length=150), offset: int = Query(default=0, ge=0, le=60000),
                limit: int = Query(default=100, ge=1, le=200), symbol: str = Query(default="", max_length=10),
                side: Literal["", "buy", "sell"] = "", q: str = Query(default="", max_length=120),
                role=Depends(verify_password_with_role)):
    from backend.trading import disclosure_browser
    return call(disclosure_browser.browse, member, symbol, side, q, offset, limit)


@router.get("/congress/collection")
def collection_status(role=Depends(verify_password_with_role)):
    from backend.trading import disclosure_collector
    return call(disclosure_collector.status)


@router.post("/congress/collection/refresh", status_code=202)
def refresh_collection(background: BackgroundTasks, role=Depends(admin)):
    from backend.trading import disclosure_collector
    current = call(disclosure_collector.status)
    if not current["enabled"]:
        raise HTTPException(409, "Automatic disclosure collection is disabled in this environment")
    if current["state"] != "running":
        background.add_task(disclosure_collector.collect, force=True)
    return {**current, "state": "running"}


@router.get("/congress/template")
def template(role=Depends(verify_password_with_role)):
    buffer = io.StringIO()
    csv.writer(buffer).writerow(congress.COLUMNS)
    return Response(buffer.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="congress-template.csv"'})


@router.post("/congress/import")
def import_disclosures(request: CongressImport, role=Depends(admin)):
    rows = call(congress.parse_csv, request.csv_text)
    document = call(storage.mutate, "congress", lambda previous: congress.merge_import(previous, rows))
    return {**document["last_import"], "total": len(document["records"])}
