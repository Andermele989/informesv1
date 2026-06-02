import os
import sys
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from database import SessionLocal
import models

if not st.session_state.get("logged_in", False):
    st.warning("Por favor, inicia sesión en la página principal para acceder a esta página.")
    st.stop()

# ========================= CARGAR ESTILOS RESPONSIVOS =========================
from styles_loader import cargar_estilos_responsivos

cargar_estilos_responsivos()

st.markdown("""
<div class="registro-header">
    <h1>📝 Registro de Informe Mensual</h1>
    <p>Registra la actividad del mes para un publicador del grupo</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state for date if not exists
if "año_sel" not in st.session_state:
    hoy = datetime.datetime.now()
    primero_mes = hoy.replace(day=1)
    mes_anterior_fecha = primero_mes - datetime.timedelta(days=1)
    st.session_state.año_sel = mes_anterior_fecha.year
    st.session_state.mes_sel = mes_anterior_fecha.month

# ========================= FORMULARIO EN 2 COLUMNAS =========================
if "success_msg" in st.session_state:
    st.success(st.session_state.success_msg)
    st.balloons()
    del st.session_state["success_msg"]

col_izq, col_der = st.columns([1, 1], gap="large")

with col_izq:
    st.subheader("📌 ¿Para quién?")

    # Selector de Mes con selectboxes
    st.markdown("**Mes de Actividad**")
    col_año, col_mes = st.columns(2)
    
    with col_año:
        rango_años = list(range(st.session_state.año_sel - 2, st.session_state.año_sel + 3))
        try:
            indice_año = rango_años.index(st.session_state.año_sel)
        except ValueError:
            indice_año = 2
        st.session_state.año_sel = st.selectbox("Año", options=rango_años, index=indice_año, key="ano_widget")
    
    with col_mes:
        meses_nombre = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        st.session_state.mes_sel = st.selectbox("Mes", options=list(meses_nombre.keys()),
                               format_func=lambda x: meses_nombre[x],
                               index=st.session_state.mes_sel - 1, key="mes_widget")

    mes_seleccionado = f"{st.session_state.año_sel}-{st.session_state.mes_sel:02d}"

    # Obtener grupos para el selector
    db = SessionLocal()
    try:
        grupos = db.query(models.Group).order_by(models.Group.name).all()
        grupo_nombres = ["Todos"] + [g.name for g in grupos]
        grupo_map = {g.name: g.id for g in grupos}
    finally:
        db.close()

    st.markdown("**Grupo**")
    grupo_seleccionado = st.selectbox("Seleccionar Grupo", options=grupo_nombres, key="grupo_widget", label_visibility="collapsed")

    # Obtener publicadores que NO han informado este mes
    db = SessionLocal()
    try:
        # IDs de publicadores que ya informaron este mes
        ya_informaron_ids = [r.publisher_id for r in db.query(models.MonthlyReport.publisher_id).filter(models.MonthlyReport.month == mes_seleccionado).all()]
        
        privileges = db.query(models.Privilege).all()
        privilege_names = [p.name for p in privileges]
        
        # Filtrar publicadores activos que NO están en la lista de ya informaron
        pub_query = db.query(models.Publisher).filter(
            models.Publisher.is_inactive == False,
            ~models.Publisher.id.in_(ya_informaron_ids) if ya_informaron_ids else True
        )
        if grupo_seleccionado != "Todos":
            pub_query = pub_query.filter(models.Publisher.group_id == grupo_map[grupo_seleccionado])
        publishers = pub_query.all()
    finally:
        db.close()

    if not publishers:
        st.info(f"✨ Todos los publicadores han entregado su informe para {meses_nombre[st.session_state.mes_sel]} {st.session_state.año_sel} en este grupo.")
        pub_seleccionado = None
        nombre_seleccionado = "Seleccione..."
    else:
        # Selector de Publicador
        pub_nombres = {"Seleccione...": None}
        for p in publishers:
            pub_nombres[p.name] = p
        nombre_seleccionado = st.selectbox("Publicador", options=list(pub_nombres.keys()), key="pub_widget")
        pub_seleccionado = pub_nombres[nombre_seleccionado]

    # Privilegio
    opciones_privilegio = ["Ninguno"] + privilege_names
    privilegio_seleccionado = st.selectbox("Privilegio Asignado este mes", options=opciones_privilegio, key="priv_widget")

with col_der:
    st.subheader("📋 Actividad del Mes")

    es_precursor = "precursor" in privilegio_seleccionado.lower()

    if es_precursor:
        st.info("📊 Al ser precursor, ingresa tus horas y estudios bíblicos.")
        horas = st.number_input("Horas de Servicio", min_value=0, step=1, key="horas_widget")
        informe_servicio = f"{horas} horas"
        cursos_biblicos = st.number_input("Cursos Bíblicos Dirigidos", min_value=0, step=1, key="cursos_widget")
    else:
        st.info("✏️ Indica tu participación en el ministerio de forma cualitativa.")
        tipo_informe = st.radio("¿Participaste en el ministerio?", ["Sí, participé", "No participé"], horizontal=True, key="tipo_widget")
        detalles = st.text_input("Detalles adicionales (Ej: facetas)", help="Opcional", key="detalles_widget")
        if tipo_informe == "Sí, participé":
            informe_servicio = "Sí participé" + (f" ({detalles})" if detalles else "")
        else:
            informe_servicio = "No participé" + (f" ({detalles})" if detalles else "")
        cursos_biblicos = 0

    notas = st.text_area(
        "Notas (Opcional)",
        help="Si no predicó o no participó, indique por qué. Ej: 'Enfermo', 'De viaje', etc.",
        height=80,
        key="notas_widget"
    )

# ========================= RESUMEN Y VALIDACIÓN =========================
st.divider()

if pub_seleccionado and nombre_seleccionado != "Seleccione...":
    st.markdown(f"""
    <div class="resumen-box">
        <h4>📄 Resumen del Informe</h4>
        <div class="resumen-item"><span class="resumen-label">Publicador:</span> <span class="resumen-value">{pub_seleccionado.name}</span></div>
        <div class="resumen-item"><span class="resumen-label">Mes:</span> <span class="resumen-value">{meses_nombre[st.session_state.mes_sel]} {st.session_state.año_sel}</span></div>
        <div class="resumen-item"><span class="resumen-label">Privilegio:</span> <span class="resumen-value">{privilegio_seleccionado}</span></div>
        <div class="resumen-item"><span class="resumen-label">Informe:</span> <span class="resumen-value">{informe_servicio}</span></div>
        <div class="resumen-item"><span class="resumen-label">Cursos Bíblicos:</span> <span class="resumen-value">{cursos_biblicos}</span></div>
    </div>
    """, unsafe_allow_html=True)

# Botón de guardar
deshabilitar = (pub_seleccionado is None) or (nombre_seleccionado == "Seleccione...")
submit = st.button("✅ Guardar Informe", disabled=deshabilitar, use_container_width=False, type="primary")

if submit:
    if not pub_seleccionado or nombre_seleccionado == "Seleccione...":
        st.error("Por favor, selecciona un Publicador válido.")
    elif es_precursor and horas == 0 and (not notas or "No participé" not in notas):
        st.warning("Has indicado 0 horas siendo precursor. Asegúrate de añadir una justificación en 'Notas'.")
    else:
        db2 = SessionLocal()
        try:
            nuevo_informe = models.MonthlyReport(
                user_id=st.session_state.user_id,
                publisher_id=pub_seleccionado.id,
                full_name=pub_seleccionado.name,
                month=mes_seleccionado,
                assigned_privileges=privilegio_seleccionado,
                service_report=informe_servicio,
                notes=notas,
                bible_courses=int(cursos_biblicos)
            )
            db2.add(nuevo_informe)
            db2.commit()
            
            st.session_state.success_msg = f"✅ Informe de **{meses_nombre[st.session_state.mes_sel]} {st.session_state.año_sel}** para **{pub_seleccionado.name}** guardado exitosamente."
            
            # Limpiar entradas de datos por completo para que la pantalla se limpie por completo
            keys_to_clear = ["pub_widget", "priv_widget", "horas_widget", "cursos_widget", "tipo_widget", "detalles_widget", "notas_widget", "grupo_widget", "ano_widget", "mes_widget"]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.rerun()
        except Exception as e:
            db2.rollback()
            st.error(f"❌ Error al guardar el informe: {e}")
        finally:
            db2.close()
