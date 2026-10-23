"""Authenticated, bounded, saved-news sentiment research endpoints."""

import asyncio
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.auth import verify_password_with_role
from backend.sentiment.lab import BenchmarkBusy, benchmark, label_template
from backend.services.research import normalized_symbol

router = APIRouter()


class Annotation(BaseModel):
    sample_id: str = Field(min_length=24, max_length=24)
    text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    label: Literal["positive", "neutral", "negative"]


class EvaluationRequest(BaseModel):
    limit: int = Field(default=12, ge=1, le=30)
    labels: List[Annotation] = Field(max_length=30)


def _symbol(value):
    try:
        return normalized_symbol(value)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{symbol}")
async def preview(symbol: str, limit: int = Query(default=12, ge=1, le=30), compare: bool = False,
                  current_user: str = Depends(verify_password_with_role)):
    try:
        return await asyncio.to_thread(benchmark, _symbol(symbol), limit, compare)
    except BenchmarkBusy as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{symbol}/labels")
async def labels(symbol: str, limit: int = Query(default=12, ge=1, le=30),
                 current_user: str = Depends(verify_password_with_role)):
    return await asyncio.to_thread(label_template, _symbol(symbol), limit)


@router.post("/{symbol}/evaluate")
async def evaluate(symbol: str, request: EvaluationRequest, current_user: str = Depends(verify_password_with_role)):
    try:
        return await asyncio.to_thread(benchmark, _symbol(symbol), request.limit, True,
                                       [item.model_dump() for item in request.labels])
    except BenchmarkBusy as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
