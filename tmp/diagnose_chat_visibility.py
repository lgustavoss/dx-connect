import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Match test environment from backend/tests/conftest.py
os.environ["DX_CONNECT_TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "01234567890123456789012345678901"
os.environ["ENVIRONMENT"] = "development"
os.environ["DEFAULT_TENANT_ID"] = "1"
os.environ["INBOUND_EMAIL_DOMAIN"] = "inbound.dx.test"

from app.main import app
from app.database import SessionLocal
from app.core.security import criar_access_token
from app.models import Atendente, Empresa, Rede, Setor, StatusTicket, Tenant
from app.api.whatsapp_chats import _pode_ver_chat
from fastapi.testclient import TestClient

client = TestClient(app)

def auth(email):
    tok = criar_access_token({"sub": email, "tid": 1})
    return {"Authorization": f"Bearer {tok}", "X-Dx-Tenant-Id": "1"}

# Seed minimal test data
with client as c:
    db = SessionLocal()
    t = Tenant(id=1, nome="Teste", ativo=True)
    db.add(t)
    db.flush()
    s1 = Setor(tenant_id=1, nome="Suporte", slug="suporte", ativo=True)
    s2 = Setor(tenant_id=1, nome="Financeiro", slug="financeiro", ativo=True)
    db.add_all([s1, s2])
    r = Rede(tenant_id=1, nome="Rede Teste", ativo=True)
    db.add(r)
    db.flush()
    e = Empresa(tenant_id=1, rede_id=r.id, nome="Empresa Teste", ativo=True)
    db.add(e)
    st = StatusTicket(nome="Aguardando atendimento", slug="aguardando_atendimento", ordem=1, ativo=True)
    db.add(st)
    admin = Atendente(
        tenant_id=1,
        email="admin@test.local",
        nome="Admin",
        senha_hash="x",
        role="admin",
        ativo=True,
        must_change_password=False,
    )
    a1 = Atendente(
        tenant_id=1,
        email="atendente1@test.local",
        nome="Atendente 1",
        senha_hash="x",
        role="atendente",
        ativo=True,
        must_change_password=False,
    )
    a2 = Atendente(
        tenant_id=1,
        email="atendente2@test.local",
        nome="Atendente 2",
        senha_hash="x",
        role="atendente",
        ativo=True,
        must_change_password=False,
    )
    db.add_all([admin, a1, a2])
    db.flush()
    a1.setores.append(s1)
    a2.setores.append(s2)
    db.commit()
    db.close()

    # setup settings
    assert c.patch("/v1/settings/whatsapp", json={"webhook_secret": "rbac-1"}, headers=auth('admin@test.local')).status_code == 200
    h = {"X-Dx-Webhook-Secret": "rbac-1"}
    c.post(
        "/v1/webhooks/evolution",
        json={
            "event": "messages.upsert",
            "data": {
                "messages": [
                    {
                        "key": {
                            "remoteJid": "5511999111122@s.whatsapp.net",
                            "fromMe": False,
                            "id": "chat-a-1",
                        },
                        "message": {"conversation": "A"},
                    }
                ]
            },
        },
        headers=h,
    )
    r_fila = c.get("/v1/whatsapp/chats/fila", headers=auth('admin@test.local'))
    chat_a_id = r_fila.json()[0]["id"]
    c.post(f"/v1/whatsapp/chats/{chat_a_id}/assumir", headers=auth('atendente1@test.local'))
    c.post(f"/v1/whatsapp/chats/{chat_a_id}/encerrar", headers=auth('atendente1@test.local'))
    c.post(
        "/v1/webhooks/evolution",
        json={
            "event": "messages.upsert",
            "data": {
                "messages": [
                    {
                        "key": {
                            "remoteJid": "5511999222233@s.whatsapp.net",
                            "fromMe": False,
                            "id": "chat-b-1",
                        },
                        "message": {"conversation": "B"},
                    }
                ]
            },
        },
        headers=h,
    )
    r_fila = c.get("/v1/whatsapp/chats/fila", headers=auth('admin@test.local'))
    chat_b_id = next(item["id"] for item in r_fila.json() if item["id"] != chat_a_id)
    c.post(f"/v1/whatsapp/chats/{chat_b_id}/assumir", headers=auth('atendente2@test.local'))
    c.post(f"/v1/whatsapp/chats/{chat_b_id}/encerrar", headers=auth('atendente2@test.local'))
    r = c.get(f"/v1/whatsapp/chats/{chat_b_id}", headers=auth('atendente1@test.local'))
    print('chat_b_id', chat_b_id)
    print('get status', r.status_code)

    db = SessionLocal()
    from app.models import WhatsappChat
    chat_b = db.query(WhatsappChat).filter(WhatsappChat.id == chat_b_id).first()
    a1 = db.query(Atendente).filter(Atendente.email == 'atendente1@test.local').first()
    print('chat_b estado', chat_b.estado, 'setor_id', chat_b.setor_id, 'atendente_id', chat_b.atendente_id)
    print('a1 id', a1.id, 'role', a1.role, 'setores', [s.id for s in a1.setores])
    print('visible setores', [s for s in [s.id for s in a1.setores]])
    print('_pode_ver_chat', _pode_ver_chat(db, a1, chat_b))
    db.close()
