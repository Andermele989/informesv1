import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from database import SessionLocal
import models

from auth_helper import check_session_cookie_or_localstorage
check_session_cookie_or_localstorage()

if not st.session_state.get("logged_in", False):
    st.warning("Por favor, inicia sesión. Si no has iniciado sesión, por favor hazlo en la página principal.")
    st.stop()

# ========================= CARGAR ESTILOS RESPONSIVOS =========================
from styles_loader import cargar_estilos_responsivos

cargar_estilos_responsivos()

st.markdown("""
<div class="lista-header">
    <h1>👥 Lista y Directorio de Publicadores</h1>
    <p>Explora el historial de privilegios e informes de los publicadores</p>
</div>
""", unsafe_allow_html=True)

db = SessionLocal()
try:
    reports = db.query(models.MonthlyReport).all()
    publishers = db.query(models.Publisher).all()
finally:
    db.close()

if not publishers:
    st.info("No hay publicadores registrados en el sistema.")
    st.stop()

# Construir datos cruzando Publicadores y Reportes
data = []

for r in reports:
    pub_name = r.full_name or next((p.name for p in publishers if p.id == r.publisher_id), "Desconocido")
    data.append({
        "Publicador": pub_name,
        "Mes del Informe": r.month,
        "Privilegio": r.assigned_privileges,
        "Cursos Bíblicos": r.bible_courses,
        "Informe": r.service_report,
        "Estado": "Inactivo" if any(p.is_inactive for p in publishers if p.id == r.publisher_id) else "Activo"
    })

# Añadir publicadores sin reportes
for p in publishers:
    if not any(d["Publicador"] == p.name for d in data):
        data.append({
            "Publicador": p.name,
            "Mes del Informe": "Sin Informes",
            "Privilegio": "—",
            "Cursos Bíblicos": 0,
            "Informe": "Sin datos",
            "Estado": "Inactivo" if p.is_inactive else "Activo"
        })

df = pd.DataFrame(data)

# ========================= FILTROS =========================
col1, col2 = st.columns(2)
with col1:
    filtro_nombre = st.text_input("🔍 Buscar por Nombre")
with col2:
    privilegios_unicos = ["Todos"] + sorted(list(set(df["Privilegio"].dropna().unique())))
    filtro_privilegio = st.selectbox("🎯 Filtrar por Privilegio", privilegios_unicos)

# Aplicar filtros (CORREGIDO: buscar en columna "Publicador")
df_filtrado = df.copy()

if filtro_nombre:
    df_filtrado = df_filtrado[
        df_filtrado["Publicador"].str.contains(filtro_nombre, case=False, na=False)
    ]

if filtro_privilegio != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Privilegio"] == filtro_privilegio]

st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# ========================= ESTADÍSTICAS =========================
st.subheader("Estadísticas del Filtro")
col_est1, col_est2, col_est3 = st.columns(3)
with col_est1:
    st.metric("Total de Registros", len(df_filtrado))
with col_est2:
    if len(df_filtrado) > 0:
        total_cursos = df_filtrado["Cursos Bíblicos"].sum()
        st.metric("Cursos Bíblicos Totales", total_cursos)
with col_est3:
    pubs_unicos = df_filtrado["Publicador"].nunique()
    st.metric("Publicadores Únicos", pubs_unicos)
