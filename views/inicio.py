"""Inicio: resumen del mes y accesos a cada sección."""
import streamlit as st

from core import auth, ui
from core.security import sanitize_text
from services import datos, metricas

auth.require_login()

usuario = st.session_state.get("username", "")
ui.encabezado(f"Hola, {usuario}", "Sistema automático de informes mensuales")

if auth.es_admin():
    r = datos.resumen_inicio()
    ui.html(
        '<div class="kpi-grid">'
        + ui.tarjeta_metrica("Publicadores activos", metricas.numero(r["publicadores"]), "amber", "groups",
                             nota="Sin contar a los inactivos")
        + ui.tarjeta_metrica("Grupos", metricas.numero(r["grupos"]), "orange", "workspaces", nota="Grupos de servicio")
        + ui.tarjeta_metrica(f"Informes {datos.nombre_mes(r['mes'])}", metricas.numero(r["recibidos"]), "gold",
                             "description", nota=f"{metricas.porcentaje(r['porcentaje'])} de cobertura")
        + ui.tarjeta_metrica("Pendientes", metricas.numero(r["pendientes"]), "flame", "hourglass_top",
                             nota="Por entregar este mes")
        + "</div>"
    )

ACCESOS = [
    ("views/registro.py", "Registro de informe", "edit_note",
     "Registra el informe mensual: elige el mes, el publicador y su actividad."),
    ("views/dashboard.py", "Dashboard y análisis", "monitoring",
     "Indicadores, gráficos, exportación a Excel/PDF y análisis con IA."),
    ("views/publicadores.py", "Publicadores", "groups",
     "Directorio con el historial de informes, grupos y exportación a Excel."),
    ("views/informes.py", "Editar informes", "edit_square",
     "Busca, corrige o elimina informes ya registrados."),
]
if auth.es_admin():
    ACCESOS.insert(2, ("views/administracion.py", "Administración", "admin_panel_settings",
                       "Privilegios, publicadores y grupos de servicio."))

TONOS = ("amber", "orange", "gold", "flame")
for i, (pagina, titulo, icono, descripcion) in enumerate(ACCESOS):
    if i % 3 == 0:  # una fila nueva cada tres tarjetas: así quedan alineadas
        columnas = st.columns(3, gap="medium")
    with columnas[i % 3], st.container(key=f"card_acceso_{i}"):
        ui.html(f'<div class="nav-card-text"><span class="chip-icon tone-{TONOS[i % 4]}">{ui.icono(icono)}</span>'
                f'<div><h3>{sanitize_text(titulo)}</h3><p>{sanitize_text(descripcion)}</p></div></div>')
        st.page_link(pagina, label="Abrir", icon=f":material/{icono}:", width="stretch")
