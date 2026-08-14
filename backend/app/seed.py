"""Seed inicial: status de ticket e usuário admin (se não existir)."""
from sqlalchemy import func

import bcrypt

from app.config import settings
from app.database import SessionLocal
from app.models import StatusTicket, Atendente, Tenant


def _hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _ensure_status_aguardando_atendimento(db):
    """Garante o status inicial da fila (ticket sem responsável, visível ao setor)."""
    if db.query(StatusTicket).filter(StatusTicket.slug == "aguardando_atendimento").first():
        return
    for row in db.query(StatusTicket).order_by(StatusTicket.ordem.desc()).all():
        row.ordem = int(row.ordem) + 1
    db.add(
        StatusTicket(
            nome="Aguardando atendimento",
            slug="aguardando_atendimento",
            ordem=1,
            ativo=True,
        )
    )
    db.commit()
    print("Status «Aguardando atendimento» adicionado (fila do setor).")


def _ensure_default_tenant(db):
    if not db.query(Tenant).filter(Tenant.id == 1).first():
        db.add(Tenant(id=1, nome="Padrão", ativo=True))
        db.commit()


def run_seed():
    db = SessionLocal()
    try:
        _ensure_default_tenant(db)
        if db.query(StatusTicket).count() == 0:
            for ordem, (nome, slug) in enumerate(
                [
                    ("Aguardando atendimento", "aguardando_atendimento"),
                    ("Em atendimento", "em_atendimento"),
                    ("Aguardando cliente", "aguardando_cliente"),
                    ("Resolvido", "resolvido"),
                    ("Fechado", "fechado"),
                ],
                start=1,
            ):
                db.add(StatusTicket(nome=nome, slug=slug, ordem=ordem, ativo=True))
            db.commit()
            print("Status de ticket criados.")
        else:
            _ensure_status_aguardando_atendimento(db)

        if settings.is_production:
            seed_email = (str(settings.SEED_ADMIN_EMAIL) if settings.SEED_ADMIN_EMAIL else "").strip().lower()
            pwd = (settings.SEED_ADMIN_PASSWORD or "").strip()
            if not seed_email:
                print(
                    "Produção: admin inicial não criado. Defina SEED_ADMIN_EMAIL e SEED_ADMIN_PASSWORD "
                    "(mín. 8 caracteres) no ambiente, ou crie o administrador pelo painel após o deploy."
                )
            elif len(pwd) < 8:
                print(
                    "Produção: admin inicial não criado. SEED_ADMIN_PASSWORD deve ter ao menos 8 caracteres."
                )
            elif not db.query(Atendente).filter(func.lower(Atendente.email) == seed_email).first():
                db.add(
                    Atendente(
                        email=seed_email,
                        nome="Administrador",
                        senha_hash=_hash_senha(pwd),
                        role="admin",
                        ativo=True,
                        must_change_password=True,
                    )
                )
                db.commit()
                print(
                    f"Usuário admin criado: {seed_email} — troque a senha no primeiro acesso "
                    "(must_change_password ativo)."
                )
        else:
            if not db.query(Atendente).filter(func.lower(Atendente.email) == "admin@email.com").first():
                db.add(
                    Atendente(
                        tenant_id=1,
                        email="admin@email.com",
                        nome="Administrador",
                        senha_hash=_hash_senha("admin123"),
                        role="admin",
                        ativo=True,
                        must_change_password=False,
                    )
                )
                db.commit()
                print(
                    "Usuário admin do atendimento (dev): admin@email.com / admin123 — não use em produção."
                )
            if not db.query(Atendente).filter(func.lower(Atendente.email) == "atendente@email.com").first():
                db.add(
                    Atendente(
                        tenant_id=1,
                        email="atendente@email.com",
                        nome="Atendente Demo",
                        senha_hash=_hash_senha("atendente123"),
                        role="atendente",
                        ativo=True,
                        must_change_password=False,
                    )
                )
                db.commit()
                print(
                    "Usuário atendente (dev): atendente@email.com / atendente123 — não use em produção."
                )
            if settings.SAAS_CONTROL_PLANE and not db.query(Atendente).filter(
                func.lower(Atendente.email) == "ops@deskrudder.local"
            ).first():
                db.add(
                    Atendente(
                        tenant_id=1,
                        email="ops@deskrudder.local",
                        nome="Ops SaaS DeskRudder",
                        senha_hash=_hash_senha("ops123456"),
                        role="saas_ops",
                        ativo=True,
                        must_change_password=False,
                    )
                )
                db.commit()
                print(
                    "Usuário ops SaaS (dev): ops@deskrudder.local / ops123456 — painel /login/admin."
                )
            if not db.query(Atendente).filter(func.lower(Atendente.email) == "comercial@email.com").first():
                db.add(
                    Atendente(
                        tenant_id=1,
                        email="comercial@email.com",
                        nome="Comercial",
                        senha_hash=_hash_senha("comercial123"),
                        role="comercial",
                        ativo=True,
                        must_change_password=False,
                    )
                )
                db.commit()
                print(
                    "Usuário comercial criado (desenvolvimento): comercial@email.com / comercial123 — não use em produção."
                )
            from app.services.crm import ensure_funil_padrao

            ensure_funil_padrao(db)
            db.commit()
    finally:
        db.close()


def reset_senha_admin_padrao(senha: str = "admin123", email: str = "admin@email.com") -> bool:
    """Redefine a senha do atendente com o e-mail indicado (padrão: admin@email.com)."""
    target = email.strip().lower()
    db = SessionLocal()
    try:
        a = db.query(Atendente).filter(func.lower(Atendente.email) == target).first()
        if not a:
            return False
        a.senha_hash = _hash_senha(senha)
        db.commit()
        return True
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if "--reset-admin" in sys.argv:
        i = sys.argv.index("--reset-admin")
        extra = sys.argv[i + 1] if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--") else None
        email_reset = extra if extra and "@" in extra else "admin@email.com"
        ok = reset_senha_admin_padrao(email=email_reset)
        print(
            "Senha do admin redefinida." if ok else f"Nenhum atendente com e-mail {email_reset!r} encontrado."
        )
    else:
        run_seed()
