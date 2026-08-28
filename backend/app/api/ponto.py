"""API de controle de ponto (#761 / #766 / #767 / #768)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import exigir_admin, obter_atendente_atual
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.ponto import (
    PontoAjusteCreate,
    PontoAjusteUpdate,
    PontoAlertasMe,
    PontoAnularBody,
    PontoAusenciaConceder,
    PontoAusenciaCreate,
    PontoAusenciaDecisao,
    PontoAusenciaRead,
    PontoBancoHorasRead,
    PontoBatidaAdminItem,
    PontoBatidaRead,
    PontoBaterRequest,
    PontoCalendarioRead,
    PontoCienciaItem,
    PontoCienciaMe,
    PontoCoberturaColega,
    PontoCoberturaConceder,
    PontoCoberturaCreate,
    PontoCoberturaDecisao,
    PontoCoberturaRead,
    PontoCoberturaResposta,
    PontoCompetenciaRead,
    PontoCompetenciaReabrir,
    PontoDiaConvocadoCreate,
    PontoDiaConvocadoRead,
    PontoDigestRead,
    PontoEstadoRead,
    PontoFeriadoCreate,
    PontoFeriadoRead,
    PontoHistoricoRead,
    PontoHojeRead,
    PontoHoraExtraConceder,
    PontoHoraExtraCreate,
    PontoHoraExtraDecisao,
    PontoHoraExtraMeStatus,
    PontoHoraExtraRead,
    PontoJustificativaCreate,
    PontoJustificativaDecisao,
    PontoJustificativaRead,
    PontoLocalCreate,
    PontoLocalRead,
    PontoLocalUpdate,
    PontoResumoSemanaRead,
    PontoSettingsPublicRead,
    PontoSettingsRead,
    PontoSettingsUpdate,
    PontoSetupStatus,
)
from app.services import ponto as ponto_svc
from app.services import ponto_ausencia as ausencia_svc
from app.services import ponto_cobertura as cob_svc
from app.services import ponto_convocado as convocado_svc
from app.services import ponto_competencia as comp_svc
from app.services import ponto_folha as folha_svc
from app.services import ponto_hora_extra as he_svc
from app.services import ponto_justificativa as just_svc
from app.services import ponto_justificativa_storage as just_anexo_svc
from app.services import ponto_relatorio as ponto_relatorio_svc
from app.services import ponto_settings as ponto_settings_svc

router = APIRouter(prefix="/ponto", tags=["ponto"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post("/bater", response_model=PontoBatidaRead)
def bater_ponto(
    data: PontoBaterRequest,
    request: Request,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    ip, ua = _client_meta(request)
    batida = ponto_svc.bater(
        db,
        atendente,
        data.tipo,
        origem=data.origem,
        ip=ip,
        user_agent=ua,
        latitude=data.latitude,
        longitude=data.longitude,
        accuracy_metros=data.accuracy_metros,
    )
    return PontoBatidaRead.model_validate(batida)


@router.get("/me", response_model=PontoEstadoRead)
def meu_estado(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return ponto_svc.estado_atual(db, atendente)


@router.get("/me/batidas", response_model=PontoHistoricoRead)
def meu_historico(
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return ponto_svc.historico(db, atendente, desde=desde, ate=ate, offset=offset, limit=limit)


@router.get("/me/alertas", response_model=PontoAlertasMe)
def meus_alertas(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return ponto_svc.alertas_me(db, atendente)


@router.get("/me/calendario", response_model=PontoCalendarioRead)
def meu_calendario(
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return ponto_svc.calendario(db, atendente, ano, mes)


@router.get("/me/settings", response_model=PontoSettingsPublicRead)
def minhas_settings_ponto(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    out = ponto_settings_svc.settings_public_read(db, atendente)
    db.commit()
    return out


@router.get("/batidas/export.csv")
def exportar_csv(
    atendente_id: int | None = Query(None),
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    conteudo = ponto_svc.export_csv_admin(
        db, admin, atendente_id=atendente_id, desde=desde, ate=ate
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ponto_batidas.csv"'},
    )


@router.get("/batidas/export.pdf")
def exportar_pdf(
    atendente_id: int | None = Query(None),
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    pdf = ponto_relatorio_svc.export_pdf_mensal(
        db, admin, atendente_id=atendente_id, desde=desde, ate=ate
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ponto_relatorio.pdf"'},
    )


@router.get("/batidas/export.xlsx")
def exportar_xlsx(
    atendente_id: int | None = Query(None),
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    xlsx = ponto_relatorio_svc.export_xlsx_mensal(
        db, admin, atendente_id=atendente_id, desde=desde, ate=ate
    )
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ponto_relatorio.xlsx"'},
    )


@router.get("/export/folha.csv")
def exportar_folha_csv(
    atendente_id: int | None = Query(None),
    desde: date = Query(...),
    ate: date = Query(...),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    """Template contábil/folha RH (#975) — colunas documentadas no cabeçalho CSV."""
    conteudo = folha_svc.export_folha_csv(
        db, admin, atendente_id=atendente_id, desde=desde, ate=ate
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ponto_folha.csv"'},
    )


@router.get("/export/folha.xlsx")
def exportar_folha_xlsx(
    atendente_id: int | None = Query(None),
    desde: date = Query(...),
    ate: date = Query(...),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    xlsx = folha_svc.export_folha_xlsx(
        db, admin, atendente_id=atendente_id, desde=desde, ate=ate
    )
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ponto_folha.xlsx"'},
    )


@router.post("/coberturas", response_model=PontoCoberturaRead, status_code=201)
def solicitar_cobertura(
    data: PontoCoberturaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return cob_svc.solicitar(
        db,
        atendente,
        cobertor_id=data.cobertor_id,
        data_ref=data.data_ref,
        motivo=data.motivo,
    )


@router.get("/coberturas/me", response_model=list[PontoCoberturaRead])
def minhas_coberturas(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return cob_svc.listar_me(db, atendente)


@router.get("/coberturas/colegas", response_model=list[PontoCoberturaColega])
def colegas_cobertura(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return cob_svc.listar_colegas(db, atendente)


@router.post("/coberturas/{cobertura_id}/responder", response_model=PontoCoberturaRead)
def responder_cobertura(
    cobertura_id: int,
    data: PontoCoberturaResposta,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return cob_svc.responder_cobertor(db, atendente, cobertura_id, aceitar=data.aceitar)


@router.get("/coberturas", response_model=list[PontoCoberturaRead])
def listar_coberturas_admin(
    estado: str | None = Query("pendente_admin"),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return cob_svc.listar_admin(db, admin, estado=estado)


@router.post("/coberturas/conceder", response_model=PontoCoberturaRead, status_code=201)
def conceder_cobertura(
    data: PontoCoberturaConceder,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return cob_svc.conceder_admin(
        db,
        admin,
        solicitante_id=data.solicitante_id,
        cobertor_id=data.cobertor_id,
        data_ref=data.data_ref,
        motivo=data.motivo,
    )


@router.post("/coberturas/{cobertura_id}/decidir", response_model=PontoCoberturaRead)
def decidir_cobertura(
    cobertura_id: int,
    data: PontoCoberturaDecisao,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return cob_svc.decidir_admin(
        db,
        admin,
        cobertura_id,
        aprovar=data.aprovar,
        decisao_motivo=data.decisao_motivo,
    )


@router.get("/setup-status", response_model=PontoSetupStatus)
def ponto_setup_status(
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    """Checklist de configuração do módulo ponto (#981)."""
    return comp_svc.setup_status(db, admin)


@router.get("/competencias", response_model=list[PontoCompetenciaRead])
def listar_competencias(
    ano: int | None = Query(None),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return comp_svc.listar_competencias(db, admin, ano=ano)


@router.get("/competencias/{ano}/{mes}", response_model=PontoCompetenciaRead)
def obter_competencia(
    ano: int,
    mes: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return comp_svc.obter_competencia(db, admin, ano=ano, mes=mes)


@router.post("/competencias/{ano}/{mes}/fechar", response_model=PontoCompetenciaRead)
def fechar_competencia(
    ano: int,
    mes: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return comp_svc.fechar_competencia(db, admin, ano=ano, mes=mes)


@router.post("/competencias/{ano}/{mes}/reabrir", response_model=PontoCompetenciaRead)
def reabrir_competencia(
    ano: int,
    mes: int,
    data: PontoCompetenciaReabrir,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return comp_svc.reabrir_competencia(db, admin, ano=ano, mes=mes, motivo=data.motivo)


@router.get("/competencias/{ano}/{mes}/ciencias", response_model=list[PontoCienciaItem])
def listar_ciencias(
    ano: int,
    mes: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return comp_svc.listar_ciencias_admin(db, admin, ano=ano, mes=mes)


@router.get("/me/ciencia", response_model=PontoCienciaMe)
def minha_ciencia(
    ano: int = Query(...),
    mes: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return comp_svc.ciencia_me(db, atendente, ano=ano, mes=mes)


@router.post("/me/ciencia", response_model=PontoCienciaMe)
def confirmar_ciencia(
    ano: int = Query(...),
    mes: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return comp_svc.confirmar_ciencia(db, atendente, ano=ano, mes=mes)


@router.get("/batidas", response_model=ListaPaginada[PontoBatidaAdminItem])
def listar_batidas_admin(
    atendente_id: int | None = Query(None),
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    itens, total = ponto_svc.listar_batidas_admin(
        db,
        admin,
        atendente_id=atendente_id,
        desde=desde,
        ate=ate,
        offset=offset,
        limit=limit,
    )
    return ListaPaginada(items=itens, total=total)


@router.post("/batidas", response_model=PontoBatidaRead, status_code=201)
def criar_batida_admin(
    data: PontoAjusteCreate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    batida = ponto_svc.admin_criar_batida(
        db,
        admin,
        atendente_id=data.atendente_id,
        tipo=data.tipo,
        registrado_em=data.registrado_em,
        motivo=data.motivo.strip(),
    )
    return PontoBatidaRead.model_validate(batida)


@router.patch("/batidas/{batida_id}", response_model=PontoBatidaRead)
def atualizar_batida_admin(
    batida_id: int,
    data: PontoAjusteUpdate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    batida = ponto_svc.admin_atualizar_batida(
        db,
        admin,
        batida_id,
        tipo=data.tipo,
        registrado_em=data.registrado_em,
        motivo=data.motivo.strip(),
    )
    return PontoBatidaRead.model_validate(batida)


@router.post("/batidas/{batida_id}/anular", response_model=PontoBatidaRead)
def anular_batida_admin(
    batida_id: int,
    data: PontoAnularBody,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    batida = ponto_svc.admin_anular_batida(db, admin, batida_id, motivo=data.motivo.strip())
    return PontoBatidaRead.model_validate(batida)


@router.get("/calendario", response_model=PontoCalendarioRead)
def calendario_admin(
    atendente_id: int = Query(...),
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    alvo = (
        db.query(Atendente)
        .filter(Atendente.id == atendente_id, Atendente.tenant_id == admin.tenant_id)
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    return ponto_svc.calendario(db, alvo, ano, mes)


@router.get("/hoje", response_model=PontoHojeRead)
def visao_hoje(
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_svc.visao_hoje(db, admin)


@router.get("/digest", response_model=PontoDigestRead)
def digest_diario(
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_svc.digest_hoje(db, admin)


@router.get("/me/banco-horas", response_model=PontoBancoHorasRead)
def meu_banco_horas(
    desde: date = Query(...),
    ate: date = Query(...),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return ponto_svc.banco_horas(db, atendente, desde=desde, ate=ate)


@router.get("/me/resumo-semana", response_model=PontoResumoSemanaRead)
def meu_resumo_semana(
    ref: date | None = Query(None, description="Qualquer dia da semana (padrão: hoje)"),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return ponto_svc.resumo_semana(db, atendente, ref=ref)


@router.get("/banco-horas", response_model=PontoBancoHorasRead)
def banco_horas_admin(
    atendente_id: int = Query(...),
    desde: date = Query(...),
    ate: date = Query(...),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    alvo = (
        db.query(Atendente)
        .filter(Atendente.id == atendente_id, Atendente.tenant_id == admin.tenant_id)
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    return ponto_svc.banco_horas(db, alvo, desde=desde, ate=ate)


@router.get("/settings", response_model=PontoSettingsRead)
def ler_settings_ponto(
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    out = ponto_settings_svc.settings_read(db, admin.tenant_id)
    db.commit()
    return out


@router.patch("/settings", response_model=PontoSettingsRead)
def atualizar_settings_ponto(
    data: PontoSettingsUpdate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_settings_svc.settings_update(db, admin, data)


@router.get("/feriados", response_model=list[PontoFeriadoRead])
def listar_feriados(
    ano: int | None = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_settings_svc.listar_feriados(db, admin.tenant_id, ano=ano)


@router.post("/feriados", response_model=PontoFeriadoRead, status_code=201)
def criar_feriado(
    data: PontoFeriadoCreate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_settings_svc.criar_feriado(db, admin, data)


@router.delete("/feriados/{feriado_id}", status_code=204)
def remover_feriado(
    feriado_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    ponto_settings_svc.remover_feriado(db, admin, feriado_id)
    return Response(status_code=204)


@router.get("/locais", response_model=list[PontoLocalRead])
def listar_locais(
    atendente_id: int | None = Query(None),
    so_orfos: bool = Query(False, description="Só locais legados sem atendente"),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_settings_svc.listar_locais(
        db, admin.tenant_id, atendente_id=atendente_id, so_orfos=so_orfos
    )


@router.post("/locais", response_model=PontoLocalRead, status_code=201)
def criar_local(
    data: PontoLocalCreate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_settings_svc.criar_local(db, admin, data)


@router.patch("/locais/{local_id}", response_model=PontoLocalRead)
def atualizar_local(
    local_id: int,
    data: PontoLocalUpdate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_settings_svc.atualizar_local(db, admin, local_id, data)


@router.delete("/locais/{local_id}", status_code=204)
def remover_local(
    local_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    ponto_settings_svc.remover_local(db, admin, local_id)
    return Response(status_code=204)


@router.post("/justificativas", response_model=PontoJustificativaRead, status_code=201)
def criar_justificativa(
    data: PontoJustificativaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return just_svc.criar(
        db,
        atendente,
        data_ref=data.data_ref,
        tipo=data.tipo,
        motivo=data.motivo,
    )


@router.post("/justificativas/upload", response_model=PontoJustificativaRead, status_code=201)
async def criar_justificativa_com_anexo(
    data_ref: date = Form(...),
    tipo: str = Form(...),
    motivo: str = Form(...),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    raw = await arquivo.read()
    try:
        nome, mime = just_anexo_svc.validar_anexo_justificativa(
            arquivo.filename, arquivo.content_type, len(raw)
        )
        key = just_anexo_svc.gravar_bytes(raw, mimetype=mime, nome_original=nome)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return just_svc.criar(
        db,
        atendente,
        data_ref=data_ref,
        tipo=tipo,
        motivo=motivo,
        anexo_nome=nome,
        anexo_content_type=mime,
        anexo_storage_key=key,
        anexo_tamanho_bytes=len(raw),
    )


@router.get("/justificativas/{justificativa_id}/anexo")
def baixar_anexo_justificativa(
    justificativa_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    row = just_svc.obter_para_anexo(
        db,
        justificativa_id=justificativa_id,
        tenant_id=atendente.tenant_id,
        solicitante=atendente,
    )
    path = just_anexo_svc.caminho_absoluto(row.anexo_storage_key)
    if path is None:
        raise HTTPException(status_code=404, detail="Arquivo do anexo não encontrado")
    return FileResponse(
        path,
        media_type=row.anexo_content_type or "application/octet-stream",
        filename=row.anexo_nome or path.name,
    )


@router.get("/justificativas/me", response_model=list[PontoJustificativaRead])
def minhas_justificativas(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return just_svc.listar_me(db, atendente)


@router.get("/justificativas", response_model=list[PontoJustificativaRead])
def listar_justificativas_admin(
    estado: str | None = Query("pendente"),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return just_svc.listar_admin(db, admin, estado=estado)


@router.post("/justificativas/{justificativa_id}/decidir", response_model=PontoJustificativaRead)
def decidir_justificativa(
    justificativa_id: int,
    data: PontoJustificativaDecisao,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return just_svc.decidir(
        db,
        admin,
        justificativa_id,
        estado=data.estado,
        decisao_motivo=data.decisao_motivo,
        aplicar_batidas=data.aplicar_batidas,
    )


@router.post("/ausencias", response_model=PontoAusenciaRead, status_code=201)
def solicitar_ausencia(
    data: PontoAusenciaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return ausencia_svc.solicitar(
        db,
        atendente,
        tipo=data.tipo,
        desde=data.desde,
        ate=data.ate,
        motivo=data.motivo,
    )


@router.get("/ausencias/me", response_model=list[PontoAusenciaRead])
def minhas_ausencias(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return ausencia_svc.listar_me(db, atendente)


@router.get("/ausencias", response_model=list[PontoAusenciaRead])
def listar_ausencias_admin(
    estado: str | None = Query("pendente"),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ausencia_svc.listar_admin(db, admin, estado=estado)


@router.post("/ausencias/conceder", response_model=PontoAusenciaRead, status_code=201)
def conceder_ausencia(
    data: PontoAusenciaConceder,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ausencia_svc.conceder_admin(
        db,
        admin,
        atendente_id=data.atendente_id,
        tipo=data.tipo,
        desde=data.desde,
        ate=data.ate,
        motivo=data.motivo,
    )


@router.post("/ausencias/{ausencia_id}/decidir", response_model=PontoAusenciaRead)
def decidir_ausencia(
    ausencia_id: int,
    data: PontoAusenciaDecisao,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ausencia_svc.decidir(
        db,
        admin,
        ausencia_id,
        aprovar=data.aprovar,
        decisao_motivo=data.decisao_motivo,
    )


@router.delete("/ausencias/{ausencia_id}", status_code=204)
def remover_ausencia(
    ausencia_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    ausencia_svc.remover_admin(db, admin, ausencia_id)
    return Response(status_code=204)


@router.post("/convocados/conceder", response_model=PontoDiaConvocadoRead, status_code=201)
def conceder_dia_convocado(
    data: PontoDiaConvocadoCreate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return convocado_svc.criar_admin(
        db,
        admin,
        atendente_id=data.atendente_id,
        data_ref=data.data_ref,
        inicio=data.inicio,
        fim=data.fim,
        motivo=data.motivo,
        tolerancia_minutos=data.tolerancia_minutos,
    )


@router.get("/convocados", response_model=list[PontoDiaConvocadoRead])
def listar_dias_convocados(
    atendente_id: int | None = Query(None),
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    estado: str | None = Query("ativa"),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return convocado_svc.listar_admin(
        db,
        admin,
        atendente_id=atendente_id,
        desde=desde,
        ate=ate,
        estado=estado,
    )


@router.delete("/convocados/{convocado_id}", response_model=PontoDiaConvocadoRead)
def cancelar_dia_convocado(
    convocado_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return convocado_svc.cancelar_admin(db, admin, convocado_id)


@router.get("/hora-extra/me/status", response_model=PontoHoraExtraMeStatus)
def hora_extra_me_status(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return PontoHoraExtraMeStatus(**he_svc.me_status(db, atendente))


@router.get("/hora-extra/me", response_model=list[PontoHoraExtraRead])
def minhas_hora_extra(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return he_svc.listar_me(db, atendente)


@router.post("/hora-extra", response_model=PontoHoraExtraRead, status_code=201)
def solicitar_hora_extra(
    data: PontoHoraExtraCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return he_svc.solicitar(
        db,
        atendente,
        motivo=data.motivo,
        modo=data.modo,
        ate_horario=data.ate_horario,
        duracao_minutos=data.duracao_minutos,
    )


@router.get("/hora-extra", response_model=list[PontoHoraExtraRead])
def listar_hora_extra_admin(
    estado: str | None = Query("pendente"),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return he_svc.listar_admin(db, admin, estado=estado)


@router.post("/hora-extra/{he_id}/decidir", response_model=PontoHoraExtraRead)
def decidir_hora_extra(
    he_id: int,
    data: PontoHoraExtraDecisao,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return he_svc.decidir(
        db,
        admin,
        he_id,
        aprovar=data.aprovar,
        modo=data.modo,
        ate_horario=data.ate_horario,
        duracao_minutos=data.duracao_minutos,
        decisao_motivo=data.decisao_motivo,
    )


@router.post("/hora-extra/conceder", response_model=PontoHoraExtraRead, status_code=201)
def conceder_hora_extra(
    data: PontoHoraExtraConceder,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return he_svc.conceder_admin(
        db,
        admin,
        atendente_id=data.atendente_id,
        modo=data.modo,
        ate_horario=data.ate_horario,
        duracao_minutos=data.duracao_minutos,
        motivo=data.motivo,
    )
