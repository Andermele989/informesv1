"""Casos límite: valores guardados en sesión que dejan de existir entre una ejecución y otra."""
from conftest import RAIZ  # noqa: F401
from core import models
from core.database import sesion
from test_vistas import abrir, sin_errores


def test_informes_cambiar_de_grupo_con_publicador_que_ya_no_esta(datos_ejemplo):
    app = abrir("views/informes.py", datos_ejemplo["admin_id"])
    app.selectbox(key="edit_pub").set_value("Ana").run()           # Ana está en Grupo 1
    app.selectbox(key="edit_grupo").set_value("Grupo 2").run()      # en Grupo 2 solo hay informes de Carla
    sin_errores(app)
    assert app.selectbox(key="edit_pub").value == "Carla"


def test_registro_publicador_obsoleto_tras_registrarlo_otro_usuario(datos_ejemplo):
    uid = datos_ejemplo["admin_id"]
    app = abrir("views/registro.py", uid, reg_anio=2026, reg_mes=11)
    app.selectbox(key="reg_pub").set_value("Beto").run()
    with sesion() as db:  # otro usuario registra a Beto mientras esta pantalla sigue abierta
        beto = db.query(models.Publisher).filter_by(name="Beto").one()
        db.add(models.MonthlyReport(user_id=uid, publisher_id=beto.id, full_name="Beto", month="2026-11"))
        db.commit()
    app.run()
    sin_errores(app)
    assert "Beto" not in app.selectbox(key="reg_pub").options


def test_registro_privilegio_eliminado_mientras_estaba_elegido(datos_ejemplo):
    app = abrir("views/registro.py", datos_ejemplo["admin_id"], reg_anio=2026, reg_mes=11)
    app.selectbox(key="reg_priv").set_value("Precursor Regular").run()
    with sesion() as db:
        db.query(models.Privilege).filter_by(name="Precursor Regular").delete()
        db.commit()
    app.run()
    sin_errores(app)
    assert app.selectbox(key="reg_priv").value == "Ninguno"


def test_administracion_publicador_eliminado_mientras_estaba_elegido(datos_ejemplo):
    app = abrir("views/administracion.py", datos_ejemplo["admin_id"])
    with sesion() as db:
        carla = db.query(models.Publisher).filter_by(name="Carla").one().id
    app.selectbox(key="adm_pub_sel").set_value(carla).run()
    with sesion() as db:
        db.query(models.MonthlyReport).filter_by(full_name="Carla").delete()
        db.query(models.Publisher).filter_by(id=carla).delete()
        db.commit()
    app.run()
    sin_errores(app)


def test_dashboard_filtros_obsoletos_al_cambiar_de_anio(datos_ejemplo):
    app = abrir("views/dashboard.py", datos_ejemplo["admin_id"])
    app.multiselect[0].set_value(["2026-10"]).run()
    app.selectbox[0].set_value("Todos").run()
    sin_errores(app)
