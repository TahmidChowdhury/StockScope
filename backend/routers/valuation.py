"""Authenticated, read-only financial quality and valuation evidence."""

import asyncio
from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth import verify_password_with_role
from backend.services.research import normalized_symbol
from backend.services.valuation import get_valuation, ValuationBusy

router = APIRouter()


@router.get("/{ticker}")
async def valuation_evidence(ticker: str, current_user: str = Depends(verify_password_with_role)):
    try:
        symbol = normalized_symbol(ticker).replace(".", "-")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    try:
        return await get_valuation(symbol)
    except ValuationBusy as error:
        raise HTTPException(status_code=503, detail="Valuation providers are busy. Try again shortly.") from error
    except asyncio.TimeoutError as error:
        raise HTTPException(status_code=504, detail="Valuation providers took too long. Try again shortly.") from error
