from core import security


def test_hash_y_verificacion():
    h = security.hash_password("Una-Clave-Larga-1")
    assert security.is_bcrypt_hash(h)
    assert security.verify_password("Una-Clave-Larga-1", h) == (True, False)
    assert security.verify_password("otra", h) == (False, False)


def test_texto_plano_heredado_pide_actualizar_hash():
    assert security.verify_password("vieja", "vieja") == (True, True)
    assert security.verify_password("mala", "vieja") == (False, False)


def test_contrasena_demasiado_larga_no_rompe():
    larga = "a" * 100
    assert security.verify_password(larga, security.hash_password("corta-1234")) == (False, False)


def test_politica_de_contrasenas():
    assert security.validar_password("corta") is not None
    assert security.validar_password("admin") is not None
    assert security.validar_password("12345678901") is not None
    assert security.validar_password("maria-lopez", "Maria-Lopez") is not None
    assert security.validar_password("a" * 80) is not None
    assert security.validar_password("Nueva-Clave-2026") is None


def test_token_de_sesion_ida_y_vuelta():
    h = security.hash_password("clave-123456")
    token = security.make_session_token(7, h)
    datos = security.read_session_token(token)
    assert datos == {"user_id": 7, "huella": security.huella_password(h)}


def test_token_no_contiene_usuario_ni_rol():
    import base64
    import json
    token = security.make_session_token(7, security.hash_password("clave-123456"))
    cuerpo = token.split(".")[0]
    payload = json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))
    assert set(payload) == {"uid", "pv", "exp"}


def test_token_manipulado_o_caducado_se_rechaza():
    h = security.hash_password("clave-123456")
    token = security.make_session_token(1, h)
    cuerpo, firma = token.split(".")
    assert security.read_session_token(f"{cuerpo}x.{firma}") is None
    assert security.read_session_token(f"{cuerpo}.{firma[:-2]}AA") is None
    assert security.read_session_token("basura") is None
    assert security.read_session_token("") is None
    caducado = security.make_session_token(1, h, ttl_seconds=-1)
    assert security.read_session_token(caducado) is None


def test_cambiar_contrasena_cambia_la_huella():
    antes = security.huella_password(security.hash_password("clave-123456"))
    despues = security.huella_password(security.hash_password("clave-654321"))
    assert antes != despues


def test_saneamiento_html():
    assert security.sanitize_text('<script>alert("x")</script>') == "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"
    assert security.sanitize_text(None) == ""


def test_limpiar_texto():
    assert security.limpiar_texto("  hola \x00  mundo\n ") == "hola mundo"
    assert security.limpiar_texto("a" * 500, 10) == "a" * 10
    assert security.limpiar_texto("línea 1\nlínea 2 ", 100, multilinea=True) == "línea 1\nlínea 2"
