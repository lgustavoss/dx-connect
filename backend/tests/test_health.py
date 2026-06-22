def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert "capabilities" in body


def test_health_capabilities_detect_routes(client):
    """Regressão: FastAPI >= 0.137 não expõe rotas incluídas em app.routes plano."""
    caps = client.get("/health").json()["capabilities"]
    assert caps["settings_empresa_sistema"] is True
    assert caps["settings_email"] is True
    assert caps["tenant_atual"] is True
    assert caps["pdv_catalogos"] is True
    assert caps["empresa_pdvs"] is True
