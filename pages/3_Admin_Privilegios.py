import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from database import SessionLocal
import models

from auth_helper import check_session_cookie_or_localstorage
check_session_cookie_or_localstorage()

if not st.session_state.get("logged_in", False):
    st.warning("Por favor, inicia sesión.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("🚫 Acceso denegado. Solo los administradores pueden acceder a esta página.")
    st.stop()

# ========================= CARGAR ESTILOS RESPONSIVOS =========================
from styles_loader import cargar_estilos_responsivos

cargar_estilos_responsivos()

st.markdown("""
<div class="admin-header">
    <h1>🛡️ Administración</h1>
    <p>Gestiona privilegios, publicadores y grupos del sistema</p>
</div>
""", unsafe_allow_html=True)

# ========================= TABS =========================
tab_privs, tab_pubs, tab_groups = st.tabs(["📋 Privilegios", "👥 Publicadores", "🏘️ Grupos"])

db = SessionLocal()
try:
    # ========================= TAB PRIVILEGIOS =========================
    with tab_privs:
        privileges = db.query(models.Privilege).all()

        col_list, col_add = st.columns([1, 1], gap="large")

        with col_list:
            st.subheader("Privilegios Registrados")
            if privileges:
                for p in privileges:
                    st.markdown(f"- **{p.name}**")
            else:
                st.info("No hay privilegios registrados todavía.")

            if privileges:
                st.markdown("---")
                st.subheader("Eliminar Privilegio")
                with st.form("eliminar_privilegio"):
                    priv_names = [p.name for p in privileges]
                    priv_a_eliminar = st.selectbox("Selecciona el privilegio a eliminar", priv_names)
                    eliminar = st.form_submit_button("🗑️ Eliminar", use_container_width=True)
                    if eliminar:
                        priv_obj = db.query(models.Privilege).filter(models.Privilege.name == priv_a_eliminar).first()
                        if priv_obj:
                            db.delete(priv_obj)
                            db.commit()
                            st.success(f"✅ Privilegio '{priv_a_eliminar}' eliminado.")
                            st.rerun()

        with col_add:
            st.subheader("Añadir Nuevo Privilegio")
            with st.form("nuevo_privilegio"):
                nuevo_nombre = st.text_input("Nombre del Privilegio")
                submit = st.form_submit_button("➕ Añadir", use_container_width=True)
                if submit and nuevo_nombre:
                    exists = db.query(models.Privilege).filter(models.Privilege.name == nuevo_nombre).first()
                    if exists:
                        st.error("Ese privilegio ya existe.")
                    else:
                        db.add(models.Privilege(name=nuevo_nombre))
                        db.commit()
                        st.success(f"✅ Privilegio '{nuevo_nombre}' añadido correctamente.")
                        st.rerun()

    # ========================= TAB PUBLICADORES =========================
    with tab_pubs:
        st.subheader("Gestión de Publicadores")
        st.caption("Añade hermanos a la lista del grupo, márcalos como inactivos o elimínalos.")

        col_add_pub, col_del_pub = st.columns([1, 1], gap="large")

        with col_add_pub:
            with st.form("nuevo_publicador"):
                st.markdown("**Añadir Publicador**")
                nuevo_pub = st.text_input("Nombre del Nuevo Publicador")
                # Selector de grupo al crear publicador
                all_groups = db.query(models.Group).order_by(models.Group.name).all()
                group_options = {g.name: g.id for g in all_groups}
                if group_options:
                    grupo_para_pub = st.selectbox("Asignar a Grupo", list(group_options.keys()))
                else:
                    grupo_para_pub = None
                    st.caption("⚠️ No hay grupos creados. Crea uno en la pestaña 'Grupos'.")
                btn_crear = st.form_submit_button("➕ Añadir Publicador", use_container_width=True)
                if btn_crear and nuevo_pub:
                    exists = db.query(models.Publisher).filter(models.Publisher.name == nuevo_pub).first()
                    if exists:
                        st.error("Ese publicador ya existe.")
                    else:
                        gid = group_options.get(grupo_para_pub) if grupo_para_pub else None
                        db.add(models.Publisher(name=nuevo_pub, group_id=gid))
                        db.commit()
                        st.success(f"✅ Publicador '{nuevo_pub}' añadido al grupo '{grupo_para_pub}'.")
                        st.rerun()

        with col_del_pub:
            pubs_all = db.query(models.Publisher).all()
            if pubs_all:
                with st.form("eliminar_publicador"):
                    st.markdown("**Eliminar Publicador**")
                    pub_names = [p.name for p in pubs_all]
                    pub_a_eliminar = st.selectbox("Selecciona el publicador a eliminar", pub_names)
                    st.caption("⚠️ Si tiene informes asociados, se eliminarán también.")
                    btn_eliminar = st.form_submit_button("🗑️ Eliminar Publicador", use_container_width=True)
                    if btn_eliminar:
                        pub_obj = db.query(models.Publisher).filter(models.Publisher.name == pub_a_eliminar).first()
                        if pub_obj:
                            db.query(models.MonthlyReport).filter(
                                models.MonthlyReport.publisher_id == pub_obj.id
                            ).delete()
                            db.delete(pub_obj)
                            db.commit()
                            st.success(f"✅ Publicador '{pub_a_eliminar}' y sus informes eliminados.")
                            st.rerun()

        st.divider()
        st.subheader("Publicadores Actuales")

        pubs = db.query(models.Publisher).order_by(models.Publisher.name).all()
        group_map = {g.id: g.name for g in db.query(models.Group).all()}
        if pubs:
            for p in pubs:
                status_class = "status-inactivo" if p.is_inactive else "status-activo"
                status_text = "Inactivo" if p.is_inactive else "Activo"
                grp_label = group_map.get(p.group_id, "Sin Grupo")
                st.markdown(f"""
                <div class="pub-card">
                    <span class="pub-name">{p.name} <span style="font-weight:400; color:#888; font-size:15px;">— {grp_label}</span></span>
                    <span class="pub-status {status_class}">{status_text}</span>
                </div>
                """, unsafe_allow_html=True)

            st.divider()
            st.subheader("Cambiar Estado Activo/Inactivo")
            with st.form("cambiar_estado"):
                pub_nombres_estado = [p.name for p in pubs]
                pub_sel_estado = st.selectbox("Selecciona publicador", pub_nombres_estado)
                nuevo_estado = st.radio("Nuevo estado", ["Activo", "Inactivo"], horizontal=True)
                btn_estado = st.form_submit_button("✅ Actualizar Estado", use_container_width=True)
                if btn_estado:
                    pub_obj = db.query(models.Publisher).filter(models.Publisher.name == pub_sel_estado).first()
                    if pub_obj:
                        pub_obj.is_inactive = (nuevo_estado == "Inactivo")
                        db.commit()
                        st.success(f"✅ Estado de '{pub_sel_estado}' actualizado a {nuevo_estado}.")
                        st.rerun()
        else:
            st.info("No hay publicadores registrados todavía.")

    # ========================= TAB GRUPOS =========================
    with tab_groups:
        st.subheader("Gestión de Grupos")
        st.caption("Crea grupos, visualiza sus integrantes y mueve publicadores entre grupos.")

        all_groups = db.query(models.Group).order_by(models.Group.name).all()
        all_pubs = db.query(models.Publisher).order_by(models.Publisher.name).all()

        # --- Crear nuevo grupo ---
        col_g1, col_g2 = st.columns([1, 1], gap="large")

        with col_g1:
            with st.form("crear_grupo"):
                st.markdown("**Crear Nuevo Grupo**")
                nombre_grupo = st.text_input("Nombre del Grupo", placeholder="Ej: Grupo 2")
                btn_crear_grupo = st.form_submit_button("➕ Crear Grupo", use_container_width=True)
                if btn_crear_grupo and nombre_grupo:
                    exists = db.query(models.Group).filter(models.Group.name == nombre_grupo).first()
                    if exists:
                        st.error("Ya existe un grupo con ese nombre.")
                    else:
                        db.add(models.Group(name=nombre_grupo))
                        db.commit()
                        st.success(f"✅ Grupo '{nombre_grupo}' creado exitosamente.")
                        st.rerun()

        with col_g2:
            if len(all_groups) > 1:
                with st.form("eliminar_grupo"):
                    st.markdown("**Eliminar Grupo**")
                    grupo_names = [g.name for g in all_groups]
                    grupo_a_eliminar = st.selectbox("Selecciona grupo", grupo_names)
                    # Grupo al que mover los publicadores
                    otros_grupos = [g.name for g in all_groups if g.name != grupo_a_eliminar]
                    grupo_destino = st.selectbox("Mover publicadores a", otros_grupos) if otros_grupos else None
                    st.caption("⚠️ Los publicadores serán movidos al grupo destino antes de eliminar.")
                    btn_del_grupo = st.form_submit_button("🗑️ Eliminar Grupo", use_container_width=True)
                    if btn_del_grupo and grupo_destino:
                        grp_del = db.query(models.Group).filter(models.Group.name == grupo_a_eliminar).first()
                        grp_dest = db.query(models.Group).filter(models.Group.name == grupo_destino).first()
                        if grp_del and grp_dest:
                            # Mover publicadores
                            db.query(models.Publisher).filter(
                                models.Publisher.group_id == grp_del.id
                            ).update({models.Publisher.group_id: grp_dest.id})
                            db.delete(grp_del)
                            db.commit()
                            st.success(f"✅ Grupo '{grupo_a_eliminar}' eliminado. Publicadores movidos a '{grupo_destino}'.")
                            st.rerun()
            else:
                st.info("Necesitas al menos 2 grupos para poder eliminar uno.")

        # --- Vista de grupos existentes ---
        st.divider()
        st.subheader("Grupos Actuales")

        # Refresh data
        all_groups = db.query(models.Group).order_by(models.Group.name).all()

        for g in all_groups:
            members = db.query(models.Publisher).filter(models.Publisher.group_id == g.id).order_by(models.Publisher.name).all()
            member_names = ", ".join([m.name for m in members]) if members else "Sin integrantes"
            st.markdown(f"""
            <div class="group-card">
                <div class="group-name">🏘️ {g.name}</div>
                <div class="group-count">{len(members)} integrante{'s' if len(members) != 1 else ''}</div>
                <div class="group-members">👥 {member_names}</div>
            </div>
            """, unsafe_allow_html=True)

        # --- Mover publicador entre grupos ---
        st.divider()
        st.subheader("Mover Publicador de Grupo")

        if all_groups and all_pubs:
            with st.form("mover_publicador"):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    pub_a_mover = st.selectbox("Publicador", [p.name for p in all_pubs])
                with col_m2:
                    grupo_destino_mover = st.selectbox("Nuevo Grupo", [g.name for g in all_groups])
                btn_mover = st.form_submit_button("🔄 Mover Publicador", use_container_width=True)
                if btn_mover:
                    pub_obj = db.query(models.Publisher).filter(models.Publisher.name == pub_a_mover).first()
                    grp_obj = db.query(models.Group).filter(models.Group.name == grupo_destino_mover).first()
                    if pub_obj and grp_obj:
                        pub_obj.group_id = grp_obj.id
                        db.commit()
                        st.success(f"✅ '{pub_a_mover}' movido a '{grupo_destino_mover}'.")
                        st.rerun()
        else:
            st.info("Crea al menos un grupo y un publicador para usar esta función.")

except Exception as e:
    st.error(f"❌ Error: {e}")
finally:
    db.close()
