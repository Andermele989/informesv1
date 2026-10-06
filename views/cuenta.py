"""Mi cuenta: datos del usuario y cambio de contraseña."""
import streamlit as st

from core import auth, formularios, ui

auth.require_login()

ui.encabezado("Mi cuenta", "Administra el acceso a tu cuenta", etiqueta="Seguridad", insignias=(
    ("Usuario", st.session_state.get("username", "")),
    ("Rol", "Administrador" if auth.es_admin() else "Usuario"),
))

_, centro, _ = st.columns([1, 1.6, 1])
with centro, st.container(key="card_cuenta"):
    formularios.mostrar_cambio_password()
