"""Administración: privilegios, publicadores y grupos (solo administradores)."""
import logging

import pandas as pd
import streamlit as st
from sqlalchemy.exc import IntegrityError

from core import auth, models, ui
from core.database import sesion
from core.security import limpiar_texto, sanitize_text
from services import datos

log = logging.getLogger("informes.admin")

auth.require_admin()
ui.encabezado("Administración", "Gestiona privilegios, publicadores y grupos del sistema", etiqueta="Administración")

NOMBRE_MAX = 100


def _guardar(operacion, exito: str, *, invalida_datos: bool = True) -> None:
    """Ejecuta `operacion(db)` en una transacción; avisa del resultado y recarga la página."""
    try:
        with sesion() as db:
            operacion(db)
            db.commit()
    except IntegrityError:
        st.error("Ese nombre ya existe. Elige otro.")
        return
    except Exception:
        log.exception("Error en administración")
        st.error("No se pudo completar la operación. Inténtalo de nuevo.")
        return
    if invalida_datos:
        datos.invalidar_cache()
    ui.avisar(exito)
    st.rerun()


def _nombre(valor) -> str:
    return limpiar_texto(valor, NOMBRE_MAX)


# ----------------------------------------------------------------------------
# Privilegios
# ----------------------------------------------------------------------------
def tab_privilegios() -> None:
    with sesion() as db:
        privilegios = [p.name for p in db.query(models.Privilege).order_by(models.Privilege.id)]

    col_lista, col_form = st.columns(2, gap="large")
    with col_lista, st.container(key="card_priv_lista"):
        ui.titulo_tarjeta("Privilegios registrados", str(len(privilegios)))
        if privilegios:
            st.markdown("\n".join(f"- **{sanitize_text(n)}**" for n in privilegios))
        else:
            st.info("Aún no hay privilegios.")

    with col_form:
        with st.container(key="card_priv_nuevo"):
            ui.titulo_tarjeta("Añadir privilegio")
            with st.form("form_priv_nuevo", border=False, clear_on_submit=True):
                nombre = _nombre(st.text_input("Nombre del privilegio", max_chars=NOMBRE_MAX))
                if st.form_submit_button("Añadir", icon=":material/add:", width="stretch") and nombre:
                    _guardar(lambda db: db.add(models.Privilege(name=nombre)), f"Privilegio «{nombre}» añadido.", invalida_datos=False)
        if privilegios:
            with st.container(key="card_priv_borrar"):
                ui.titulo_tarjeta("Eliminar privilegio")
                with st.form("form_priv_borrar", border=False):
                    objetivo = st.selectbox("Privilegio", privilegios)
                    if st.form_submit_button("Eliminar", icon=":material/delete:", width="stretch"):
                        _guardar(lambda db: db.query(models.Privilege).filter(models.Privilege.name == objetivo).delete(),
                                 f"Privilegio «{objetivo}» eliminado.", invalida_datos=False)


# ----------------------------------------------------------------------------
# Publicadores
# ----------------------------------------------------------------------------
def tab_publicadores() -> None:
    with sesion() as db:
        grupos = {g.name: g.id for g in db.query(models.Group).order_by(models.Group.name)}
        publicadores = db.query(models.Publisher).order_by(models.Publisher.name).all()
        nombre_grupo = {v: k for k, v in grupos.items()}
        por_id = {p.id: (p.name, p.group_id, bool(p.is_inactive)) for p in publicadores}

    col_nuevo, col_editar = st.columns(2, gap="large")

    with col_nuevo, st.container(key="card_pub_nuevo"):
        ui.titulo_tarjeta("Añadir publicador")
        if not grupos:
            st.warning("Crea primero un grupo en la pestaña «Grupos».")
        with st.form("form_pub_nuevo", border=False, clear_on_submit=True):
            nombre = _nombre(st.text_input("Nombre del publicador", max_chars=NOMBRE_MAX))
            grupo = st.selectbox("Grupo", list(grupos)) if grupos else None
            if st.form_submit_button("Añadir publicador", icon=":material/person_add:", width="stretch") and nombre:
                _guardar(lambda db: db.add(models.Publisher(name=nombre, group_id=grupos.get(grupo))),
                         f"Publicador «{nombre}» añadido.")

    with col_editar, st.container(key="card_pub_editar"):
        ui.titulo_tarjeta("Editar publicador")
        if not por_id:
            st.info("Aún no hay publicadores.")
        else:
            # El selector va fuera del formulario: dentro, al cambiar de publicador los
            # campos conservarían los valores del anterior.
            if st.session_state.get("adm_pub_sel") not in por_id:
                st.session_state.pop("adm_pub_sel", None)  # p. ej. el publicador fue eliminado
            pub_id = st.selectbox("Publicador", list(por_id), key="adm_pub_sel", format_func=lambda i: por_id[i][0])
            nombre_actual, grupo_actual, inactivo = por_id[pub_id]
            with st.form(f"form_pub_editar_{pub_id}", border=False):
                nuevo_nombre = _nombre(st.text_input("Nombre", value=nombre_actual, max_chars=NOMBRE_MAX))
                nombres_grupo = list(grupos)
                indice = nombres_grupo.index(nombre_grupo[grupo_actual]) if grupo_actual in nombre_grupo else 0
                nuevo_grupo = st.selectbox("Grupo", nombres_grupo, index=indice) if nombres_grupo else None
                activo = st.toggle("Activo", value=not inactivo)
                if st.form_submit_button("Guardar cambios", icon=":material/save:", width="stretch"):
                    if not nuevo_nombre:
                        st.error("El nombre no puede estar vacío.")
                    else:
                        def editar(db):
                            pub = db.get(models.Publisher, pub_id)
                            pub.name, pub.is_inactive = nuevo_nombre, not activo
                            if nuevo_grupo:
                                pub.group_id = grupos[nuevo_grupo]
                            # Mantiene coherente el nombre guardado en los informes históricos.
                            db.query(models.MonthlyReport).filter(models.MonthlyReport.publisher_id == pub_id).update(
                                {models.MonthlyReport.full_name: nuevo_nombre})
                        _guardar(editar, f"Publicador «{nuevo_nombre}» actualizado.")

    if por_id:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        with st.container(key="card_pub_tabla"):
            ui.titulo_tarjeta("Publicadores actuales", str(len(por_id)))
            tabla = pd.DataFrame(
                [{"Publicador": n, "Grupo": nombre_grupo.get(g, "Sin grupo"), "Estado": "Inactivo" if i else "Activo"}
                 for n, g, i in por_id.values()])
            st.dataframe(tabla, hide_index=True, width="stretch", height=min(420, 38 + 35 * len(tabla)))

        with (st.expander("Zona de peligro: eliminar publicador", icon=":material/warning:"),
              st.form("form_pub_borrar", border=False)):
            pub_id = st.selectbox("Publicador a eliminar", list(por_id), format_func=lambda i: por_id[i][0])
            st.caption("Se eliminarán también todos sus informes. Si solo dejó de participar, márcalo como inactivo.")
            confirmar = st.checkbox("Entiendo que esta acción no se puede deshacer")
            if st.form_submit_button("Eliminar publicador", icon=":material/delete_forever:", width="stretch"):
                if not confirmar:
                    st.error("Marca la casilla de confirmación.")
                else:
                    def borrar(db):
                        db.query(models.MonthlyReport).filter(models.MonthlyReport.publisher_id == pub_id).delete()
                        db.query(models.Publisher).filter(models.Publisher.id == pub_id).delete()
                    _guardar(borrar, f"Publicador «{por_id[pub_id][0]}» y sus informes eliminados.")


# ----------------------------------------------------------------------------
# Grupos
# ----------------------------------------------------------------------------
def tab_grupos() -> None:
    with sesion() as db:
        grupos = db.query(models.Group).order_by(models.Group.name).all()
        miembros = {g.id: [] for g in grupos}
        for p in db.query(models.Publisher).order_by(models.Publisher.name):
            if p.group_id in miembros:
                miembros[p.group_id].append(p.name)
        ids = {g.name: g.id for g in grupos}

    col_nuevo, col_renombrar = st.columns(2, gap="large")
    with col_nuevo, st.container(key="card_grupo_nuevo"):
        ui.titulo_tarjeta("Crear grupo")
        with st.form("form_grupo_nuevo", border=False, clear_on_submit=True):
            nombre = _nombre(st.text_input("Nombre del grupo", placeholder="Ej: Grupo 2", max_chars=NOMBRE_MAX))
            if st.form_submit_button("Crear grupo", icon=":material/add:", width="stretch") and nombre:
                _guardar(lambda db: db.add(models.Group(name=nombre)), f"Grupo «{nombre}» creado.")

    with col_renombrar, st.container(key="card_grupo_renombrar"):
        ui.titulo_tarjeta("Renombrar grupo")
        if ids:
            if st.session_state.get("adm_grupo_sel") not in ids:
                st.session_state.pop("adm_grupo_sel", None)
            actual = st.selectbox("Grupo", list(ids), key="adm_grupo_sel")
            with st.form(f"form_grupo_renombrar_{ids[actual]}", border=False):
                nuevo = _nombre(st.text_input("Nuevo nombre", value=actual, max_chars=NOMBRE_MAX))
                if st.form_submit_button("Renombrar", icon=":material/edit:", width="stretch") and nuevo:
                    def renombrar(db):
                        db.get(models.Group, ids[actual]).name = nuevo
                    _guardar(renombrar, f"Grupo renombrado a «{nuevo}».")
        else:
            st.info("Aún no hay grupos.")

    st.markdown("&nbsp;", unsafe_allow_html=True)
    ui.titulo_tarjeta("Grupos actuales", str(len(grupos)))
    columnas = st.columns(2, gap="medium")
    for i, g in enumerate(grupos):
        gente = miembros[g.id]
        with columnas[i % 2], st.container(key=f"card_grupo_{g.id}"):
            ui.html(f"""<div class="group-name">{sanitize_text(g.name)}</div>
                <div class="group-count">{len(gente)} integrante{'s' if len(gente) != 1 else ''}</div>
                <div class="group-members">{sanitize_text(', '.join(gente)) if gente else 'Sin integrantes'}</div>""")

    if len(grupos) > 1:
        with st.expander("Zona de peligro: eliminar grupo", icon=":material/warning:"):
            if st.session_state.get("adm_grupo_borrar") not in ids:
                st.session_state.pop("adm_grupo_borrar", None)
            borrar = st.selectbox("Grupo a eliminar", list(ids), key="adm_grupo_borrar")
            destinos = [n for n in ids if n != borrar]
            with st.form(f"form_grupo_borrar_{ids[borrar]}", border=False):
                destino = st.selectbox("Mover sus publicadores a", destinos)
                st.caption("Los publicadores pasan al grupo destino antes de eliminar el grupo.")
                if st.form_submit_button("Eliminar grupo", icon=":material/delete_forever:", width="stretch"):
                    def eliminar(db):
                        db.query(models.Publisher).filter(models.Publisher.group_id == ids[borrar]).update(
                            {models.Publisher.group_id: ids[destino]})
                        db.query(models.Group).filter(models.Group.id == ids[borrar]).delete()
                    _guardar(eliminar, f"Grupo «{borrar}» eliminado; sus publicadores pasaron a «{destino}».")


tab_priv, tab_pub, tab_grp = st.tabs(["Privilegios", "Publicadores", "Grupos"])
with tab_priv:
    tab_privilegios()
with tab_pub:
    tab_publicadores()
with tab_grp:
    tab_grupos()
