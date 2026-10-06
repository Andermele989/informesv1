"""Directorio de publicadores con su historial de informes."""
import streamlit as st

from core import auth, ui
from services import datos, excel, metricas

auth.require_login()
ui.encabezado("Publicadores", "Directorio con el historial de privilegios, grupos e informes")

informes, publicadores = datos.cargar_datos()
if publicadores.empty:
    st.info("No hay publicadores registrados en el sistema.")
    st.stop()

tabla = datos.directorio(informes, publicadores)

with st.container(key="card_filtros"):
    c_nombre, c_grupo, c_priv, c_estado = st.columns([1.6, 1, 1, 1])
    nombre = c_nombre.text_input("Buscar por nombre", placeholder="Escribe para buscar…", max_chars=100)
    grupo = c_grupo.selectbox("Grupo", ["Todos", *sorted(tabla["Grupo"].dropna().unique())])
    privilegio = c_priv.selectbox("Privilegio", ["Todos", *sorted(tabla["Privilegio"].dropna().unique())])
    estado = c_estado.selectbox("Estado", ["Todos", "Activo", "Inactivo"])

vista = tabla
if nombre.strip():
    vista = vista[vista["Publicador"].str.contains(nombre.strip(), case=False, regex=False, na=False)]
if grupo != "Todos":
    vista = vista[vista["Grupo"] == grupo]
if privilegio != "Todos":
    vista = vista[vista["Privilegio"] == privilegio]
if estado != "Todos":
    vista = vista[vista["Estado"] == estado]

ui.html(
    '<div class="kpi-grid compact">'
    + ui.tarjeta_metrica("Registros", metricas.numero(len(vista)), "amber", "list_alt", nota="Filas del directorio")
    + ui.tarjeta_metrica("Publicadores", metricas.numero(vista["Publicador"].nunique()), "orange", "person", nota="Distintos en la vista")
    + ui.tarjeta_metrica("Cursos bíblicos", metricas.numero(int(vista["Cursos Bíblicos"].sum())), "gold", "menu_book",
                         nota="Suma de la vista")
    + "</div>"
)

with st.container(key="card_tabla"):
    cabecera, boton = st.columns([3, 1], vertical_alignment="center")
    with cabecera:
        ui.titulo_tarjeta("Directorio", f"{len(vista)} registros")
    with boton:
        if not vista.empty:
            st.download_button(
                "Exportar a Excel", icon=":material/download:", width="stretch", on_click="ignore",
                data=lambda: excel.generar_excel_simple(vista, "Directorio de publicadores", "Publicadores"),
                file_name="Directorio_Publicadores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    st.dataframe(
        vista, hide_index=True, width="stretch", height=min(560, 38 + 35 * max(len(vista), 1)),
        column_config={
            "Mes del Informe": st.column_config.TextColumn("Mes", width="small"),
            "Cursos Bíblicos": st.column_config.NumberColumn("Cursos", format="%d", width="small"),
            "Informe": st.column_config.TextColumn("Informe de servicio", width="large"),
            "Estado": st.column_config.TextColumn(width="small"),
        },
    )
