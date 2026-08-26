"""Geofence e política de geolocalização (#844 / #984)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.atendente import Atendente
from app.models.empresa_sistema import EmpresaSistema
from app.models.ponto_settings import PontoLocal

POLITICAS_VALIDAS = frozenset({"opcional", "recomendada", "obrigatoria"})


@dataclass
class LocalEfetivo:
    id: int | None
    nome: str
    latitude: float
    longitude: float
    raio_metros: int


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


def _empresa_sistema(db: Session) -> EmpresaSistema | None:
    return db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()


def locais_efetivos_ativos(db: Session, atendente: Atendente) -> list[LocalEfetivo]:
    """Locais ativos do atendente: empresa (se ligada + pin) + extras cadastrados."""
    out: list[LocalEfetivo] = []
    if bool(getattr(atendente, "usar_local_empresa", True)):
        emp = _empresa_sistema(db)
        if emp is not None and emp.latitude is not None and emp.longitude is not None:
            raio_at = getattr(atendente, "local_empresa_raio_metros", None)
            raio_emp = getattr(emp, "ponto_raio_metros", None) or 200
            raio = int(raio_at) if raio_at is not None else int(raio_emp)
            out.append(
                LocalEfetivo(
                    id=None,
                    nome="Empresa",
                    latitude=float(emp.latitude),
                    longitude=float(emp.longitude),
                    raio_metros=max(20, raio),
                )
            )
    rows = (
        db.query(PontoLocal)
        .filter(
            PontoLocal.tenant_id == atendente.tenant_id,
            PontoLocal.atendente_id == atendente.id,
            PontoLocal.ativo.is_(True),
        )
        .order_by(PontoLocal.nome.asc())
        .all()
    )
    for loc in rows:
        out.append(
            LocalEfetivo(
                id=int(loc.id),
                nome=str(loc.nome),
                latitude=float(loc.latitude),
                longitude=float(loc.longitude),
                raio_metros=int(loc.raio_metros or 200),
            )
        )
    return out


def locais_ativos(db: Session, tenant_id: int) -> list[PontoLocal]:
    """Legado: locais da instância ainda atribuídos a alguém e ativos (admin/listagens)."""
    return (
        db.query(PontoLocal)
        .filter(
            PontoLocal.tenant_id == tenant_id,
            PontoLocal.ativo.is_(True),
            PontoLocal.atendente_id.isnot(None),
        )
        .order_by(PontoLocal.nome.asc())
        .all()
    )


def avaliar_coordenadas_locais(
    locais: list[LocalEfetivo],
    latitude: float,
    longitude: float,
) -> ResultadoGeofence:
    if not locais:
        return ResultadoGeofence()
    melhor: LocalEfetivo | None = None
    melhor_dist = float("inf")
    dentro_de: LocalEfetivo | None = None
    dist_dentro = float("inf")
    for loc in locais:
        d = distancia_metros(latitude, longitude, loc.latitude, loc.longitude)
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


def avaliar_coordenadas(
    db: Session,
    atendente: Atendente,
    latitude: float,
    longitude: float,
) -> ResultadoGeofence:
    return avaliar_coordenadas_locais(
        locais_efetivos_ativos(db, atendente),
        latitude,
        longitude,
    )


def validar_batida_geolocalizacao(
    db: Session,
    atendente: Atendente,
    *,
    latitude: float | None,
    longitude: float | None,
) -> ResultadoGeofence:
    """Aplica política da instância; levanta 400 se obrigatória e inválida."""
    from app.services.ponto_settings import get_or_create_settings

    settings = get_or_create_settings(db, atendente.tenant_id)
    politica = (getattr(settings, "politica_geolocalizacao", None) or "opcional").strip().lower()
    if politica not in POLITICAS_VALIDAS:
        politica = "opcional"
    locais = locais_efetivos_ativos(db, atendente)
    has_coords = latitude is not None and longitude is not None

    if politica == "obrigatoria" and locais:
        if not has_coords:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geolocalização obrigatória para bater o ponto nesta instância.",
            )
        res = avaliar_coordenadas_locais(locais, float(latitude), float(longitude))
        if res.fora_area:
            nome = res.local_nome or "área permitida"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Você está fora da área permitida ({nome}). Aproxime-se do local de trabalho.",
            )
        return res

    if not has_coords or not locais:
        return ResultadoGeofence()

    res = avaliar_coordenadas_locais(locais, float(latitude), float(longitude))
    if politica == "recomendada" and res.fora_area:
        return res
    if politica == "opcional":
        return res
    return res
