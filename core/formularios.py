"""Formularios de acceso: inicio de sesión y cambio de contraseña."""
import logging

import streamlit as st

from core import auth, ui
from core.database import sesion
from core.security import PASSWORD_MIN, limpiar_texto

log = logging.getLogger("informes.formularios")

_ICONO_LOGIN = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true"><path d="M9 3h6a1 1 0 0 1 1 1v1h1a2 2 0 0 1 2 2v12a2 2 0 0 1-2 '
    '2H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h1V4a1 1 0 0 1 1-1z"/><path d="M9 11h6M9 15h4"/></svg>'
)


def mostrar_login() -> None:
    """Pantalla de acceso. Se muestra sobre cualquier ruta mientras no haya sesión."""
    with st.container(key="login_card"):
        ui.html(f"""
            <div class="login-head">
                <div class="login-icon">{_ICONO_LOGIN}</div>
                <span class="eyebrow">Sistema de informes</span>
                <h1>Bienvenido</h1>
                <p>Inicia sesión para acceder al panel de informes mensuales</p>
            </div>""")
        with st.form("form_login", border=False):
            usuario = st.text_input("Usuario", placeholder="Usuario", label_visibility="collapsed",
                                    max_chars=64, autocomplete="username")
            clave = st.text_input("Contraseña", placeholder="Contraseña", type="password",
                                  label_visibility="collapsed", max_chars=72, autocomplete="current-password")
            enviar = st.form_submit_button("Ingresar", type="primary", width="stretch")

        if enviar:
            try:
                with sesion() as db:
                    user, error = auth.autenticar(db, limpiar_texto(usuario, 64), clave)
                    if user:
                        auth.iniciar_sesion(user, clave)
            except Exception:
                log.exception("Error durante el inicio de sesión")
                user, error = None, "No se pudo verificar el acceso. Inténtalo de nuevo en unos segundos."
            if user:
                st.query_params.clear()
                st.rerun()
            st.error(error)

        ui.html('<div class="login-foot">Acceso restringido · Uso interno</div>')


def mostrar_cambio_password() -> None:
    """Formulario para cambiar la contraseña del usuario con sesión iniciada."""
    ui.titulo_tarjeta("Cambiar contraseña", f"Mínimo {PASSWORD_MIN} caracteres")
    with st.form("form_password", border=False, clear_on_submit=True):
        actual = st.text_input("Contraseña actual", type="password", max_chars=72, autocomplete="current-password")
        nueva = st.text_input("Nueva contraseña", type="password", max_chars=72, autocomplete="new-password")
        repetir = st.text_input("Repite la nueva contraseña", type="password", max_chars=72, autocomplete="new-password")
        enviar = st.form_submit_button("Guardar contraseña", type="primary", width="stretch")

    if not enviar:
        return
    if nueva != repetir:
        st.error("Las contraseñas nuevas no coinciden.")
        return
    try:
        with sesion() as db:
            error = auth.cambiar_password(db, st.session_state.user_id, actual, nueva)
    except Exception:
        log.exception("Error al cambiar la contraseña")
        error = "No se pudo actualizar la contraseña. Inténtalo de nuevo."
    if error:
        st.error(error)
        return
    auth.actualizar_cookie_tras_cambio(st.session_state.user_id)
    ui.avisar("Contraseña actualizada.")
    st.rerun()
