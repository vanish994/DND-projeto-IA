"""Rota de saúde do serviço."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/v1/status")
def status() -> dict[str, str]:
    return {
        "status": "online",
        "servico": "mj-deepseek",
        "motor_regras": "deterministico",
    }
