"""Geofence e política de geolocalização (#844)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ponto_settings import PontoLocal, PontoSettings

POLITICAS_VALIDAS = frozenset({"opcional", "recomendada", "obrigatoria"})


@dataclass
class ResultadoGeofence:
    fora_area: bool = False
    distancia_metros: float | None = None
    local_id: int | None = None
    local_nome: str | None = None


def distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine — distância em metros."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def locais_ativos(db: Session, tenant_id: int) -> list[PontoLocal]:
    return (
        db.query(PontoLocal)
        .filter(PontoLocal.tenant_id == tenant_id, PontoLocal.ativo.is_(True))
        .order_by(PontoLocal.nome.asc())
        .all()
    )


def avaliar_coordenadas(
    db: Session,
    tenant_id: int,
    latitude: float,
    longitude: float,
) -> ResultadoGeofence:
    """Encontra o local mais próximo e se está dentro do raio."""
    locais = locais_ativos(db, tenant_id)
    if not locais:
        return ResultadoGeofence()
    melhor: PontoLocal | None = None
    melhor_dist = float("inf")
    dentro_de: PontoLocal | None = None
    dist_dentro = float("inf")
    for loc in locais:
        d = distancia_metros(latitude, longitude, float(loc.latitude), float(loc.longitude))
        if d < melhor_dist:
            melhor_dist = d
            melhor = loc
        if d <= int(loc.raio_metros or 200) and d < dist_dentro:
            dist_dentro = d
            dentro_de = loc
    if dentro_de is not None:
        return ResultadoGeofence(
            fora_area=False,
            distancia_metros=round(dist_dentro, 1),
            local_id=dentro_de.id,
            local_nome=dentro_de.nome,
        )
    return ResultadoGeofence(
        fora_area=True,
        distancia_metros=round(melhor_dist, 1) if melhor is not None else None,
        local_id=melhor.id if melhor is not None else None,
        local_nome=melhor.nome if melhor is not None else None,
    )


def validar_batida_geolocalizacao(
    db: Session,
    tenant_id: int,
    *,
    latitude: float | None,
    longitude: float | None,
) -> ResultadoGeofence:
    """Aplica política da instância; levanta 400 se obrigatória e inválida."""
    from app.services.ponto_settings import get_or_create_settings

    settings = get_or_create_settings(db, tenant_id)
    politica = (getattr(settings, "politica_geolocalizacao", None) or "opcional").strip().lower()
    if politica not in POLITICAS_VALIDAS:
        politica = "opcional"
    locais = locais_ativos(db, tenant_id)
    has_coords = latitude is not None and longitude is not None

    if politica == "obrigatoria" and locais:
        if not has_coords:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geolocalização obrigatória para bater o ponto nesta instância.",
            )
        res = avaliar_coordenadas(db, tenant_id, float(latitude), float(longitude))
        if res.fora_area:
            nome = res.local_nome or "área permitida"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Você está fora da área permitida ({nome}). Aproxime-se do local de trabalho.",
            )
        return res

    if not has_coords or not locais:
        return ResultadoGeofence()

    res = avaliar_coordenadas(db, tenant_id, float(latitude), float(longitude))
    if politica == "recomendada" and res.fora_area:
        return res
    if politica == "opcional":
        return res
    return res
