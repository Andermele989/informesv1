import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from database import SessionLocal
import models

if not st.session_state.get("logged_in", False):
    st.warning("Por favor, inicia sesión en la página principal para acceder a esta página.")
    st.stop()

# ========================= CARGAR ESTILOS RESPONSIVOS =========================
from styles_loader import cargar_estilos_responsivos

cargar_estilos_responsivos()

# Lógica de mensaje de éxito post-rerun
if st.session_state.get("report_modified"):
    st.success(st.session_state.report_modified)
    st.balloons()
    del st.session_state.report_modified

st.markdown("""
<div class="edit-header">
    <h1>✏️ Edición de Informes</h1>
    <p>Busca y modifica informes previamente registrados.</p>
</div>
""", unsafe_allow_html=True)

db = SessionLocal()
try:
    reports = db.query(models.MonthlyReport).all()
    publishers = db.query(models.Publisher).all()
    privileges_list = [p.name for p in db.query(models.Privilege).all()]
finally:
    db.close()

if not reports:
    st.info("No hay informes registrados para editar.")
    st.stop()

publisher_map = {p.id: p.name for p in publishers}

# Crear un DataFrame para facilitar filtros
data = []
for r in reports:
    pub_name = r.full_name or publisher_map.get(r.publisher_id, "Desconocido")
    data.append({
        "id": r.id,
        "Publicador": pub_name,
        "Mes": r.month,
        "Privilegios": r.assigned_privileges,
        "Cursos Bíblicos": r.bible_courses,
        "Informe": r.service_report,
        "Notas": r.notes or ""
    })

df_editables = pd.DataFrame(data)

st.sidebar.header("🔍 Buscar Informe")
edit_pub_opciones = sorted(df_editables["Publicador"].unique().tolist())
edit_pub = st.sidebar.selectbox("1. Selecciona Publicador", edit_pub_opciones, key="edit_pub_sel")

# Meses disponibles de ese publicador
df_edit_pub = df_editables[df_editables["Publicador"] == edit_pub]
edit_meses = sorted(df_edit_pub["Mes"].unique().tolist(), reverse=True)
edit_mes = st.sidebar.selectbox("2. Selecciona Mes", edit_meses, key="edit_mes_sel")

# Obtener el informe actual
informe_row = df_edit_pub[df_edit_pub["Mes"] == edit_mes].iloc[0]
report_id = int(informe_row["id"])

st.markdown('<div class="section-title">Detalles del Informe</div>', unsafe_allow_html=True)

opciones_privilegio = ["Ninguno"] + privileges_list
current_priv = informe_row["Privilegios"]
priv_index = opciones_privilegio.index(current_priv) if current_priv in opciones_privilegio else 0

# Envolvemos todo en una columna central para que los campos sean menos anchos
col_espacio_izq, col_centro, col_espacio_der = st.columns([1, 2, 1])

with col_centro:
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        nuevo_privilegio = st.selectbox("Privilegio Actual", opciones_privilegio, index=priv_index, key=f"edit_priv_{report_id}")
    with col_e2:
        nuevo_cursos = st.number_input("Cursos Bíblicos", min_value=0, value=int(informe_row["Cursos Bíblicos"]), key=f"edit_cursos_{report_id}")

    nuevo_informe = st.text_input("Participación / Horas", value=informe_row["Informe"], key=f"edit_informe_{report_id}")
    nuevas_notas = st.text_area("Notas / Observaciones", value=informe_row["Notas"], height=120, key=f"edit_notas_{report_id}")

    st.write("")
    if st.button("GUARDAR CAMBIOS", type="primary", use_container_width=True, key="btn_guardar_edit"):
        db_save = SessionLocal()
        try:
            report_obj = db_save.query(models.MonthlyReport).filter(models.MonthlyReport.id == report_id).first()
            if report_obj:
                report_obj.assigned_privileges = nuevo_privilegio
                report_obj.bible_courses = int(nuevo_cursos)
                report_obj.service_report = nuevo_informe
                report_obj.notes = nuevas_notas
                db_save.commit()
                st.session_state.report_modified = f"✅ Informe de **{edit_pub}** ({edit_mes}) guardado con éxito."
                st.rerun()
            else:
                st.error("No se encontró el informe.")
        except Exception as e:
            db_save.rollback()
            st.error(f"Error técnico: {e}")
        finally:
            db_save.close()

