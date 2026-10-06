"""Pruebas de las pantallas con AppTest (sin navegador). Usan SQLite temporal y una IA simulada."""
import os

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from conftest import PASSWORD_ADMIN, RAIZ
from core import models
from core.database import sesion
from core.security import hash_password
from services import ia


@pytest.fixture(autouse=True)
def sin_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def abrir(vista: str, user_id: int | None = None, usuario: str = "admin", rol: str = "admin", **estado) -> AppTest:
    """Abre una vista (o main.py) con la sesión de `user_id` ya iniciada."""
    app = AppTest.from_file(os.path.join(RAIZ, vista), default_timeout=60)
    if user_id is not None:
        for clave, valor in {"logged_in": True, "user_id": user_id, "username": usuario, "role": rol,
                             "password_debil": False, **estado}.items():
            app.session_state[clave] = valor
    return app.run()


def sin_errores(app: AppTest) -> None:
    assert not app.exception, [e.value for e in app.exception]


@pytest.mark.parametrize("vista", ["registro", "dashboard", "administracion", "publicadores", "informes", "cuenta"])
def test_cada_vista_carga_sin_errores(datos_ejemplo, vista):
    sin_errores(abrir(f"views/{vista}.py", datos_ejemplo["admin_id"]))


@pytest.mark.parametrize("vista", ["registro", "dashboard", "administracion", "publicadores", "informes", "cuenta"])
def test_vistas_sin_datos_no_fallan(bd, vista):
    with sesion() as db:
        admin = models.User(username="admin", password_hash=hash_password(PASSWORD_ADMIN), role="admin")
        db.add(admin)
        db.commit()
        sin_errores(abrir(f"views/{vista}.py", admin.id))


def test_vista_sin_sesion_no_muestra_nada(datos_ejemplo):
    app = abrir("views/dashboard.py")
    assert [w.value for w in app.warning] == ["Inicia sesión para continuar."]
    assert not app.get("plotly_chart")


def test_vista_admin_rechaza_a_un_usuario_normal(datos_ejemplo):
    with sesion() as db:
        db.add(models.User(username="pepe", password_hash=hash_password(PASSWORD_ADMIN), role="user"))
        db.commit()
    app = abrir("views/administracion.py", 2, usuario="pepe", rol="user")
    assert any("Acceso denegado" in e.value for e in app.error)


# --------------------------------------------------------------------------- login
def test_login_muestra_formulario_y_sin_menu(datos_ejemplo):
    app = abrir("main.py")
    sin_errores(app)
    assert len(app.text_input) == 2 and not app.sidebar.button


def test_login_correcto_abre_la_sesion(datos_ejemplo):
    app = abrir("main.py")
    app.text_input[0].set_value("admin")
    app.text_input[1].set_value(PASSWORD_ADMIN)
    app.button[0].click().run()
    sin_errores(app)
    assert app.session_state["logged_in"] is True and app.session_state["role"] == "admin"
    assert any("Hola, admin" in m.value for m in app.markdown)


def test_login_incorrecto_y_bloqueo(datos_ejemplo):
    app = abrir("main.py")
    for _ in range(5):
        app.text_input[0].set_value("admin")
        app.text_input[1].set_value("mala")
        app.button[0].click().run()
    assert any("Demasiados intentos" in e.value for e in app.error)
    assert not app.session_state["logged_in"] if "logged_in" in app.session_state else True


def test_contrasena_debil_obliga_a_cambiarla(bd):
    with sesion() as db:
        admin = models.User(username="admin", password_hash=hash_password("admin"), role="admin")
        db.add(admin)
        db.commit()
    app = abrir("main.py")
    app.text_input[0].set_value("admin")
    app.text_input[1].set_value("admin")
    app.button[0].click().run()
    sin_errores(app)
    assert app.session_state["password_debil"] is True
    assert [t.label for t in app.text_input] == ["Contraseña actual", "Nueva contraseña", "Repite la nueva contraseña"]
    assert not app.get("plotly_chart")  # no se renderiza nada más
    app.text_input[0].set_value("admin")
    app.text_input[1].set_value("Nueva-Clave-2026")
    app.text_input[2].set_value("Nueva-Clave-2026")
    app.button[0].click().run()
    sin_errores(app)
    assert app.session_state["password_debil"] is False
    assert any("Hola, admin" in m.value for m in app.markdown)


def test_cerrar_sesion_vacia_el_estado(datos_ejemplo):
    app = abrir("main.py", datos_ejemplo["admin_id"])
    [b for b in app.sidebar.button if b.label == "Cerrar sesión"][0].click().run()
    assert app.session_state["logged_in"] is False and app.session_state["user_id"] is None


def test_usuario_eliminado_pierde_la_sesion(datos_ejemplo):
    app = abrir("main.py", 999)  # sesión de un usuario que ya no existe
    assert app.session_state["logged_in"] is False


# --------------------------------------------------------------------------- registro
def test_registro_guarda_y_no_duplica(datos_ejemplo):
    uid = datos_ejemplo["admin_id"]
    app = abrir("views/registro.py", uid, reg_anio=2026, reg_mes=11)
    assert "Carla" in app.selectbox(key="reg_pub").options
    app.selectbox(key="reg_pub").set_value("Carla").run()
    assert app.selectbox(key="reg_priv").value == "Precursor Regular"  # sugerido del último informe
    app.number_input(key="reg_horas").set_value(40)
    [b for b in app.button if b.label == "Guardar informe"][0].click().run()
    sin_errores(app)
    with sesion() as db:
        guardado = db.query(models.MonthlyReport).filter_by(month="2026-11", full_name="Carla").one()
    assert guardado.service_report == "40 horas" and guardado.assigned_privileges == "Precursor Regular"
    assert "Carla" not in app.selectbox(key="reg_pub").options  # ya no está pendiente


def test_registro_precursor_con_cero_horas_pide_justificacion(datos_ejemplo):
    app = abrir("views/registro.py", datos_ejemplo["admin_id"], reg_anio=2026, reg_mes=11)
    app.selectbox(key="reg_pub").set_value("Carla").run()
    [b for b in app.button if b.label == "Guardar informe"][0].click().run()
    assert any("justificación" in w.value for w in app.warning)
    with sesion() as db:
        assert db.query(models.MonthlyReport).filter_by(month="2026-11").count() == 0


# --------------------------------------------------------------------------- administración
def test_admin_edita_un_publicador_que_no_es_el_primero(datos_ejemplo):
    app = abrir("views/administracion.py", datos_ejemplo["admin_id"])
    with sesion() as db:
        beto = db.query(models.Publisher).filter_by(name="Beto").one().id
    app.selectbox(key="adm_pub_sel").set_value(beto).run()
    [t for t in app.text_input if t.label == "Nombre"][0].set_value("Beto Renombrado")
    [b for b in app.button if b.label == "Guardar cambios"][0].click().run()
    sin_errores(app)
    with sesion() as db:
        assert sorted(p.name for p in db.query(models.Publisher)) == ["Ana", "Beto Renombrado", "Carla", "Nico"]
        assert db.query(models.MonthlyReport).filter_by(full_name="Beto Renombrado").count() == 2  # historial coherente


def test_admin_no_borra_publicador_sin_confirmar(datos_ejemplo):
    app = abrir("views/administracion.py", datos_ejemplo["admin_id"])
    [b for b in app.button if b.label == "Eliminar publicador"][0].click().run()
    assert any("casilla" in e.value for e in app.error)
    with sesion() as db:
        assert db.query(models.Publisher).count() == 4


def test_admin_crea_grupo_y_rechaza_duplicado(datos_ejemplo):
    app = abrir("views/administracion.py", datos_ejemplo["admin_id"])
    [t for t in app.text_input if t.label == "Nombre del grupo"][0].set_value("Grupo 3")
    [b for b in app.button if b.label == "Crear grupo"][0].click().run()
    sin_errores(app)
    [t for t in app.text_input if t.label == "Nombre del grupo"][0].set_value("Grupo 3")
    [b for b in app.button if b.label == "Crear grupo"][0].click().run()
    assert any("ya existe" in e.value for e in app.error)
    with sesion() as db:
        assert db.query(models.Group).count() == 3


# --------------------------------------------------------------------------- editar informes
def test_editar_informe_guarda_y_valida_en_bd(datos_ejemplo):
    app = abrir("views/informes.py", datos_ejemplo["admin_id"])
    app.selectbox(key="edit_pub").set_value("Ana").run()
    app.selectbox(key="edit_mes").set_value("2026-09").run()
    informe_id = app.number_input[0].key.split("_")[-1]
    app.number_input(key=f"edit_cursos_{informe_id}").set_value(7)
    [b for b in app.button if b.label == "Guardar cambios"][0].click().run()
    sin_errores(app)
    with sesion() as db:
        assert db.get(models.MonthlyReport, int(informe_id)).bible_courses == 7


def test_solo_el_admin_puede_eliminar_informes(datos_ejemplo):
    with sesion() as db:
        db.add(models.User(username="pepe", password_hash=hash_password(PASSWORD_ADMIN), role="user"))
        db.commit()
    app = abrir("views/informes.py", 2, usuario="pepe", rol="user")
    sin_errores(app)
    assert not any("Eliminar" in getattr(p, "label", "") for p in app.get("popover"))


# --------------------------------------------------------------------------- dashboard + IA
def test_dashboard_calcula_bien_los_indicadores(datos_ejemplo):
    app = abrir("views/dashboard.py", datos_ejemplo["admin_id"])
    app.multiselect[0].set_value(["2026-10"]).run()
    html = " ".join(m.value for m in app.markdown)
    # 3 informes en octubre: Ana 50 h, Beto "No participé", Carla precursora con 0 h -> 2 sin actividad
    assert "Informes recibidos" in html and ">3<" in html.replace(" ", "")
    assert ">50<" in html.replace(" ", "")


def test_dashboard_analisis_ia_genera_pdf_y_sobrevive_a_recargas(datos_ejemplo, monkeypatch):
    monkeypatch.setattr(ia, "generar_analisis", lambda motor, prompt: ("## Resumen ejecutivo\nTodo bien.", "modelo-simulado"))
    app = abrir("views/dashboard.py", datos_ejemplo["admin_id"])
    app.multiselect[0].set_value(["2026-10"]).run()
    [b for b in app.button if b.label == "Generar análisis"][0].click().run()
    sin_errores(app)
    resultado = app.session_state["ia_resultado"]
    assert resultado["pdf"].startswith(b"%PDF") and resultado["modelo"] == "modelo-simulado"
    app.run()  # p. ej. al pulsar «Descargar»: el análisis no debe desaparecer
    assert any("Resumen ejecutivo" in m.value for m in app.markdown)
    app.multiselect[0].set_value(["2026-09"]).run()
    assert any("Cambiaste los filtros" in w.value for w in app.warning)


def test_dashboard_limita_la_frecuencia_de_la_ia(datos_ejemplo, monkeypatch):
    llamadas = []

    def simulada(motor, prompt):
        llamadas.append(1)
        return "## Resumen ejecutivo" + chr(10) + "Todo bien.", "modelo-simulado"

    monkeypatch.setattr(ia, "generar_analisis", simulada)
    app = abrir("views/dashboard.py", datos_ejemplo["admin_id"])
    for _ in range(2):  # el segundo clic inmediato se rechaza sin llamar a la IA
        [b for b in app.button if b.label == "Generar análisis"][0].click().run()
    assert len(llamadas) == 1 and any("Espera" in w.value for w in app.warning)


def test_dashboard_error_de_ia_muestra_mensaje_seguro(datos_ejemplo, monkeypatch):
    def falla(motor, prompt):
        raise ia.ErrorIA("Gemini no respondió.")
    monkeypatch.setattr(ia, "generar_analisis", falla)
    app = abrir("views/dashboard.py", datos_ejemplo["admin_id"])
    [b for b in app.button if b.label == "Generar análisis"][0].click().run()
    assert any("Gemini no respondió." in e.value for e in app.error)
    assert "ia_resultado" not in app.session_state
