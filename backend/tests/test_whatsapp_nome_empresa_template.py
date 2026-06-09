from __future__ import annotations

from app.models.empresa_sistema import EmpresaSistema
from app.services.whatsapp_auto_messages import resolver_nome_empresa_para_template


def test_nome_empresa_usa_fantasia_da_empresa_sistema(db_session):
    db_session.add(
        EmpresaSistema(
            cnpj="63.420.877/0001-51",
            razao_social="DUPLEX SISTEMAS E AUTOMACAO LTDA",
            nome_fantasia="DUPLEX SOFT",
        )
    )
    db_session.commit()
    assert resolver_nome_empresa_para_template(db_session) == "DUPLEX SOFT"


def test_nome_empresa_prioriza_override_whatsapp(db_session):
    from app.models.whatsapp_chat import WhatsappSettings

    db_session.add(EmpresaSistema(nome_fantasia="DUPLEX SOFT"))
    db_session.add(WhatsappSettings(nome_empresa_exibicao="DX Connect"))
    db_session.commit()
    assert resolver_nome_empresa_para_template(db_session) == "DX Connect"


def test_nome_empresa_cai_para_razao_social_sem_fantasia(db_session):
    db_session.add(EmpresaSistema(razao_social="Razão Teste Ltda", nome_fantasia=None))
    db_session.commit()
    assert resolver_nome_empresa_para_template(db_session) == "Razão Teste Ltda"
