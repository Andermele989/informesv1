"""Edición y eliminación de informes ya registrados."""
import logging

import streamlit as st

from core import auth, models, ui
from core.database import sesion
from core.security import limpiar_texto, sanitize_text
from services import datos

log = logging.getLogger("informes.edicion")

auth.require_login()
ui.encabezado("Editar informes", "Busca, corrige o elimina informes registrados previamente", etiqueta="Gestión")

informes, _ = datos.cargar_datos()
informes = informes[informes["id"].notna()]
if informes.empty:
    st.info("No hay informes registrados para editar.")
    st.stop()

# ----------------------------------------------------------------------------
# Selección: grupo -> publicador -> mes
# ----------------------------------------------------------------------------
with st.container(key="card_filtros"):
    c_grupo, c_pub, c_mes = st.columns(3)
    grupo = c_grupo.selectbox("Grupo", ["Todos", *sorted(informes["Grupo"].unique())], key="edit_grupo")
    de_grupo = informes if grupo == "Todos" else informes[informes["Grupo"] == grupo]
    publicador = c_pub.selectbox("Publicador", sorted(de_grupo["Publicador"].unique()), key="edit_pub")
    del_publicador = de_grupo[de_grupo["Publicador"] == publicador]
    mes = c_mes.selectbox("Mes del informe", sorted(del_publicador["Mes"].unique(), reverse=True), key="edit_mes")

informe_id = int(del_publicador[del_publicador["Mes"] == mes].iloc[0]["id"])

# Los valores del formulario se leen frescos de la BD, no de la caché.
with sesion() as db:
    informe = db.get(models.MonthlyReport, informe_id)
    if informe is None:
        datos.invalidar_cache()
        st.warning("Ese informe ya no existe. Recarga la página.")
        st.stop()
    actual = {"privilegio": informe.assigned_privileges or "Ninguno", "cursos": informe.bible_courses or 0,
              "informe": informe.service_report or "", "notas": informe.notes or ""}
    opciones_priv = ["Ninguno", *[p.name for p in db.query(models.Privilege).order_by(models.Privilege.id)]]

if actual["privilegio"] not in opciones_priv:
    opciones_priv.append(actual["privilegio"])  # privilegio histórico ya eliminado del catálogo

ui.html(
    f"""<div class="summary"><div class="card-title">{sanitize_text(publicador)} · {sanitize_text(mes)}</div>
    <div class="summary-grid">
    <div><span>Grupo</span><b>{sanitize_text(del_publicador.iloc[0]['Grupo'])}</b></div>
    <div><span>Privilegio</span><b>{sanitize_text(actual['privilegio'])}</b></div>
    <div><span>Actividad</span><b>{sanitize_text(actual['informe'] or '—')}</b></div>
    <div><span>Cursos bíblicos</span><b>{int(actual['cursos'])}</b></div></div></div>"""
)

# ----------------------------------------------------------------------------
# Edición
# ----------------------------------------------------------------------------
with st.container(key="card_edicion"):
    ui.titulo_tarjeta("Modificar datos del informe")
    c1, c2 = st.columns(2)
    privilegio = c1.selectbox("Privilegio asignado", opciones_priv, index=opciones_priv.index(actual["privilegio"]),
                              key=f"edit_priv_{informe_id}")
    cursos = c2.number_input("Cursos bíblicos", 0, 50, value=int(actual["cursos"]), key=f"edit_cursos_{informe_id}")
    texto = limpiar_texto(st.text_input("Participación / horas registradas", value=actual["informe"], max_chars=200,
                                        key=f"edit_informe_{informe_id}"), 200)
    notas = limpiar_texto(st.text_area("Notas / observaciones", value=actual["notas"], height=100, max_chars=500,
                                       key=f"edit_notas_{informe_id}"), 500, multilinea=True)

    c_guardar, c_borrar = st.columns([2, 1], vertical_alignment="top")
    if c_guardar.button("Guardar cambios", type="primary", icon=":material/save:", width="stretch", key="edit_guardar"):
        try:
            with sesion() as db:
                destino = db.get(models.MonthlyReport, informe_id)
                destino.assigned_privileges = None if privilegio == "Ninguno" else privilegio
                destino.bible_courses, destino.service_report, destino.notes = int(cursos), texto, notas
                db.commit()
        except Exception:
            log.exception("Error al guardar el informe %s", informe_id)
            st.error("No se pudo guardar. Inténtalo de nuevo.")
        else:
            datos.invalidar_cache()
            ui.avisar(f"Informe de {publicador} ({mes}) actualizado.")
            st.rerun()

    # Borrar informes es una acción de administrador.
    if auth.es_admin():
        with c_borrar.popover("Eliminar", icon=":material/delete:", width="stretch"):
            st.caption("Esta acción no se puede deshacer.")
            if st.button("Confirmar eliminación", key=f"edit_borrar_{informe_id}", width="stretch"):
                try:
                    with sesion() as db:
                        db.query(models.MonthlyReport).filter(models.MonthlyReport.id == informe_id).delete()
                        db.commit()
                except Exception:
                    log.exception("Error al eliminar el informe %s", informe_id)
                    st.error("No se pudo eliminar. Inténtalo de nuevo.")
                else:
                    datos.invalidar_cache()
                    ui.avisar(f"Informe de {publicador} ({mes}) eliminado.", "🗑️")
                    st.rerun()
