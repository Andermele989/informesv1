"""Punto de entrada: configuración, base de datos, sesión y navegación.

Ejecutar con `streamlit run main.py`. Las páginas están en `views/`. Sin sesión se muestra
el login sobre cualquier ruta (los scripts de las páginas ni se ejecutan); con la contraseña
débil o predeterminada solo se permite cambiarla.
"""
import logging

import streamlit as st
from sqlalchemy.exc import OperationalError

from core.errores import ErrorDeConfiguracion

st.set_page_config(page_title="Sistema de Informes", page_icon="📋", layout="wide")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("informes")

try:
    from core import auth, database, diagnostico, formularios, ui
    from core.arranque import preparar_base_de_datos
except ErrorDeConfiguracion as error:  # p. ej. DATABASE_URL mal escrita: el mensaje es seguro de mostrar
    log.error("ARRANQUE FALLIDO: configuración inválida: %s", error)
    st.error(f"Configuración inválida. {error}")
    st.stop()

try:
    preparar_base_de_datos()
except (OperationalError, UnicodeDecodeError) as error:
    log.exception("ARRANQUE FALLIDO: sin conexión con la base de datos (%s)", database.describir_destino())
    st.error("No se pudo conectar a la base de datos.")
    st.warning(diagnostico.causa_de_conexion(error))
    st.caption(f"Configuración leída de: {database.origen_conexion()}. El detalle exacto está en el registro del servidor "
               "(busca «ARRANQUE FALLIDO»).")
    st.stop()
except Exception:
    log.exception("ARRANQUE FALLIDO: error al preparar la base de datos")
    st.error("No se pudo preparar la base de datos. El registro del servidor indica la causa "
             "(busca «ARRANQUE FALLIDO»); `python -m scripts.audit` revisa el estado de la base.")
    st.stop()

ui.inyectar_estilos()
auth.restaurar_sesion()
if auth.hay_sesion() and not auth.validar_sesion_vigente():
    st.rerun()


def paginas(administrador: bool) -> dict:
    menu = {
        "Principal": [
            st.Page("views/inicio.py", title="Inicio", icon=":material/home:", default=True),
            st.Page("views/registro.py", title="Registro", icon=":material/edit_note:", url_path="registro"),
            st.Page("views/dashboard.py", title="Dashboard", icon=":material/monitoring:", url_path="dashboard"),
        ],
        "Gestión": [
            st.Page("views/publicadores.py", title="Publicadores", icon=":material/groups:", url_path="publicadores"),
            st.Page("views/informes.py", title="Editar informes", icon=":material/edit_square:", url_path="informes"),
        ],
        "Cuenta": [st.Page("views/cuenta.py", title="Mi cuenta", icon=":material/lock:", url_path="cuenta")],
    }
    if administrador:
        menu["Gestión"].insert(0, st.Page("views/administracion.py", title="Administración",
                                          icon=":material/admin_panel_settings:", url_path="administracion"))
    return menu


con_sesion = auth.hay_sesion()
debil = con_sesion and st.session_state.get("password_debil")
# Sin sesión se registran todas las rutas (menú oculto) para que una URL directa no dé "página no encontrada"
# mientras se restaura la cookie; el contenido de la página no se ejecuta hasta tener sesión.
pagina = st.navigation(paginas(administrador=auth.es_admin() or not con_sesion),
                       position="hidden" if (not con_sesion or debil) else "sidebar")

if not con_sesion:
    formularios.mostrar_login()
    st.stop()

ui.perfil_sidebar()
if debil:
    ui.encabezado("Cambia tu contraseña", "La contraseña actual es débil o predeterminada. "
                  "Elige una nueva para continuar.")
    _, centro, _ = st.columns([1, 1.6, 1])
    with centro, st.container(key="card_cuenta"):
        formularios.mostrar_cambio_password()
    st.stop()

ui.mostrar_aviso()
pagina.run()
