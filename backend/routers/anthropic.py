from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix='/api/usage/anthropic', tags=['anthropic'])


@router.get('')
async def get_anthropic_usage(request: Request, refresh: bool = Query(default=False)):
    app_state = request.app.state
    if refresh:
        await app_state.scheduler.refresh_anthropic()
    payload = app_state.cache.get('anthropic')
    if payload is None:
        await app_state.scheduler.refresh_anthropic()
        payload = app_state.cache.get('anthropic')
    if payload is None:
        raise HTTPException(status_code=503, detail='Anthropic data unavailable')
    return payload
