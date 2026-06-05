import streamlit as st
import hashlib
import os

def get_session_signature(user_id, username, role):
    # Clave secreta estática para firmar los datos de sesión en la URL
    secret = os.getenv("SECRET_KEY", "informes-app-secret-2026")
    msg = f"{user_id}:{username}:{role}:{secret}"
    return hashlib.sha256(msg.encode()).hexdigest()

def check_session_cookie_or_localstorage():
    # 0. Si el usuario cerró sesión explícitamente en esta sesión de Streamlit, no auto-loguear
    if st.session_state.get("logged_out", False):
        return False

    # 1. Si ya está logueado en Streamlit, mantenemos la URL con los parámetros de sesión
    if st.session_state.get("logged_in", False):
        sig = get_session_signature(st.session_state.user_id, st.session_state.username, st.session_state.role)
        if st.query_params.get("token") != sig:
            st.query_params["token"] = sig
            st.query_params["username"] = st.session_state.username
            st.query_params["role"] = st.session_state.role
            st.query_params["user_id"] = str(st.session_state.user_id)
        return True

    # 2. Si no está logueado, intentamos restaurar la sesión desde los parámetros de la URL
    q_token = st.query_params.get("token")
    q_user = st.query_params.get("username")
    q_role = st.query_params.get("role")
    q_uid = st.query_params.get("user_id")

    if q_token and q_user and q_role and q_uid:
        expected_sig = get_session_signature(q_uid, q_user, q_role)
        if q_token == expected_sig:
            st.session_state.logged_in = True
            st.session_state.username = q_user
            st.session_state.role = q_role
            try:
                st.session_state.user_id = int(q_uid)
            except ValueError:
                st.session_state.user_id = None
            return True
        else:
            # Firma inválida, limpiar parámetros de consulta por seguridad
            st.query_params.clear()

    return False
