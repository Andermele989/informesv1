import os
import sys
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from database import SessionLocal
import models

from auth_helper import check_session_cookie_or_localstorage
check_session_cookie_or_localstorage()

if not st.session_state.get("logged_in", False):
    st.warning("Por favor, inicia sesión.")
    st.stop()

from styles_loader import cargar_estilos_responsivos
cargar_estilos_responsivos()

# ========================= ESTILOS PREMIUM =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"], .stApp { font-family: 'Outfit', sans-serif; }

/* Header */
.reg-header {
    background: linear-gradient(135deg, rgba(20,241,178,0.08) 0%, rgba(56,189,248,0.05) 100%);
    border: 1px solid rgba(20,241,178,0.15);
    border-radius: 20px;
    padding: 32px 36px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.reg-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #14f1b2, #38bdf8, transparent);
}
.reg-header h1 {
    font-size: 1.9rem;
    font-weight: 800;
    background: linear-gradient(135deg, #14f1b2, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 6px 0;
}
.reg-header p {
    color: #94a3b8;
    font-size: 0.95rem;
    margin: 0;
    font-weight: 400;
}

/* Sección cards */
.section-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.1);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    transition: border-color 0.3s;
}
.section-card:hover {
    border-color: rgba(20,241,178,0.2);
}
.section-title-reg {
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #14f1b2;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title-reg::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(20,241,178,0.3), transparent);
}

/* Resumen box premium */
.resumen-premium {
    background: linear-gradient(135deg, rgba(20,241,178,0.06), rgba(56,189,248,0.04));
    border: 1px solid rgba(20,241,178,0.2);
    border-radius: 16px;
    padding: 24px 28px;
    margin: 24px 0;
    position: relative;
    overflow: hidden;
}
.resumen-premium::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, #14f1b2, #38bdf8);
    border-radius: 3px 0 0 3px;
}
.resumen-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #14f1b2;
    margin-bottom: 16px;
}
.resumen-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}
.resumen-item {
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.resumen-label {
    font-size: 0.72rem;
    color: #64748b;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.resumen-value {
    font-size: 0.95rem;
    color: #e2e8f0;
    font-weight: 600;
}
.resumen-value.highlight {
    color: #14f1b2;
    font-family: 'JetBrains Mono', monospace;
}

/* Badge mes */
.mes-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(56,189,248,0.1);
    border: 1px solid rgba(56,189,248,0.25);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.8rem;
    color: #38bdf8;
    font-weight: 600;
    margin-bottom: 16px;
    font-family: 'JetBrains Mono', monospace;
}

/* Success */
.success-premium {
    background: linear-gradient(135deg, rgba(20,241,178,0.1), rgba(52,211,153,0.06));
    border: 1px solid rgba(20,241,178,0.3);
    border-radius: 12px;
    padding: 16px 20px;
    color: #14f1b2;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
    animation: slideIn 0.4s ease;
}
@keyframes slideIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Streamlit overrides */
div[data-testid="stSelectbox"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stTextArea"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stRadio"] label {
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
}
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input {
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(148,163,184,0.15) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Outfit', sans-serif !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stSelectbox"] > div > div:focus-within,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus {
    border-color: rgba(20,241,178,0.4) !important;
    box-shadow: 0 0 0 3px rgba(20,241,178,0.06) !important;
}

/* Info box */
div[data-testid="stInfo"] {
    background: rgba(56,189,248,0.06) !important;
    border: 1px solid rgba(56,189,248,0.2) !important;
    border-radius: 10px !important;
    color: #7dd3fc !important;
}

/* Warning */
div[data-testid="stWarning"] {
    background: rgba(251,191,36,0.06) !important;
    border: 1px solid rgba(251,191,36,0.2) !important;
    border-radius: 10px !important;
}

/* Button primario */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #14f1b2, #0ea5e9) !important;
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 32px !important;
    letter-spacing: 0.04em !important;
    transition: all 0.3s !important;
    box-shadow: 0 4px 20px rgba(20,241,178,0.25) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(20,241,178,0.4) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:disabled {
    background: rgba(148,163,184,0.15) !important;
    color: #475569 !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Divider */
hr {
    border-color: rgba(148,163,184,0.08) !important;
    margin: 28px 0 !important;
}

/* Completado badge */
.all-done {
    background: linear-gradient(135deg, rgba(20,241,178,0.08), rgba(52,211,153,0.05));
    border: 1px solid rgba(20,241,178,0.2);
    border-radius: 14px;
    padding: 20px 24px;
    text-align: center;
    color: #14f1b2;
    font-weight: 600;
    font-size: 1rem;
}
.all-done .emoji { font-size: 2rem; display: block; margin-bottom: 8px; }

@media (max-width: 640px) {
    .resumen-grid { grid-template-columns: 1fr; }
    .reg-header h1 { font-size: 1.4rem; }
}
</style>
""", unsafe_allow_html=True)

# ========================= HEADER =========================
st.markdown("""
<div class="reg-header">
    <h1>📝 Registro de Informe</h1>
    <p>Registra la actividad mensual de los publicadores del grupo</p>
</div>
""", unsafe_allow_html=True)

# ========================= SUCCESS MSG =========================
if "success_msg" in st.session_state:
    st.markdown(f"""
    <div class="success-premium">
        <span>✅</span>
        <span>{st.session_state.success_msg}</span>
    </div>
    """, unsafe_allow_html=True)
    st.balloons()
    del st.session_state["success_msg"]

# ========================= INIT DATE =========================
if "año_sel" not in st.session_state:
    hoy = datetime.datetime.now()
    primero_mes = hoy.replace(day=1)
    mes_anterior_fecha = primero_mes - datetime.timedelta(days=1)
    st.session_state.año_sel = mes_anterior_fecha.year
    st.session_state.mes_sel = mes_anterior_fecha.month

meses_nombre = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# ========================= LAYOUT 2 COLUMNAS =========================
col_izq, col_der = st.columns([1, 1], gap="large")

with col_izq:
    st.markdown('<div class="section-title-reg">📅 Período y Publicador</div>', unsafe_allow_html=True)

    col_año, col_mes = st.columns(2)
    with col_año:
        rango_años = list(range(st.session_state.año_sel - 2, st.session_state.año_sel + 3))
        try:
            indice_año = rango_años.index(st.session_state.año_sel)
        except ValueError:
            indice_año = 2
        st.session_state.año_sel = st.selectbox("Año", options=rango_años, index=indice_año, key="ano_widget")

    with col_mes:
        st.session_state.mes_sel = st.selectbox(
            "Mes",
            options=list(meses_nombre.keys()),
            format_func=lambda x: meses_nombre[x],
            index=st.session_state.mes_sel - 1,
            key="mes_widget"
        )

    mes_seleccionado = f"{st.session_state.año_sel}-{st.session_state.mes_sel:02d}"

    st.markdown(f'<div class="mes-badge">📆 {meses_nombre[st.session_state.mes_sel]} {st.session_state.año_sel}</div>', unsafe_allow_html=True)

    # Grupos
    db = SessionLocal()
    try:
        grupos = db.query(models.Group).order_by(models.Group.name).all()
        grupo_nombres = ["Todos"] + [g.name for g in grupos]
        grupo_map = {g.name: g.id for g in grupos}
        privileges = db.query(models.Privilege).all()
        privilege_names = [p.name for p in privileges]
    finally:
        db.close()

    grupo_seleccionado = st.selectbox("Grupo", options=grupo_nombres, key="grupo_widget")

    # Publicadores
    db = SessionLocal()
    try:
        ya_informaron_ids = [
            r.publisher_id for r in db.query(models.MonthlyReport.publisher_id)
            .filter(models.MonthlyReport.month == mes_seleccionado).all()
        ]
        pub_query = db.query(models.Publisher).filter(
            models.Publisher.is_inactive == False,
            ~models.Publisher.id.in_(ya_informaron_ids) if ya_informaron_ids else True
        )
        if grupo_seleccionado != "Todos":
            pub_query = pub_query.filter(models.Publisher.group_id == grupo_map[grupo_seleccionado])
        publishers = pub_query.all()

        # Total para mostrar progreso
        total_query = db.query(models.Publisher).filter(models.Publisher.is_inactive == False)
        if grupo_seleccionado != "Todos":
            total_query = total_query.filter(models.Publisher.group_id == grupo_map[grupo_seleccionado])
        total_pubs = total_query.count()
    finally:
        db.close()

    pendientes = len(publishers)
    entregados = total_pubs - pendientes

    # Progress bar
    if total_pubs > 0:
        pct = entregados / total_pubs
        st.markdown(f"""
        <div style="margin: 12px 0 20px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="font-size:0.78rem; color:#64748b; font-weight:500;">PROGRESO DEL MES</span>
                <span style="font-size:0.78rem; color:#14f1b2; font-weight:700; font-family:'JetBrains Mono',monospace;">{entregados}/{total_pubs}</span>
            </div>
            <div style="background:rgba(148,163,184,0.1); border-radius:99px; height:6px; overflow:hidden;">
                <div style="width:{pct*100:.1f}%; height:100%; background:linear-gradient(90deg,#14f1b2,#38bdf8); border-radius:99px; transition:width 0.5s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if not publishers:
        st.markdown(f"""
        <div class="all-done">
            <span class="emoji">🎉</span>
            Todos los publicadores han entregado su informe para <strong>{meses_nombre[st.session_state.mes_sel]} {st.session_state.año_sel}</strong>
        </div>
        """, unsafe_allow_html=True)
        pub_seleccionado = None
        nombre_seleccionado = "Seleccione..."
    else:
        pub_nombres = {"Seleccione...": None}
        for p in publishers:
            pub_nombres[p.name] = p
        nombre_seleccionado = st.selectbox(
            f"Publicador ({pendientes} pendientes)",
            options=list(pub_nombres.keys()),
            key="pub_widget"
        )
        pub_seleccionado = pub_nombres[nombre_seleccionado]

    opciones_privilegio = ["Ninguno"] + privilege_names
    privilegio_seleccionado = st.selectbox("Privilegio del Mes", options=opciones_privilegio, key="priv_widget")

with col_der:
    st.markdown('<div class="section-title-reg">📋 Actividad del Mes</div>', unsafe_allow_html=True)

    es_precursor = "precursor" in privilegio_seleccionado.lower()

    if es_precursor:
        st.info("Al ser precursor, ingresa tus horas y estudios bíblicos.")
        horas = st.number_input("Horas de Servicio", min_value=0, step=1, key="horas_widget")
        informe_servicio = f"{horas} horas"
        cursos_biblicos = st.number_input("Cursos Bíblicos Dirigidos", min_value=0, step=1, key="cursos_widget")
    else:
        st.info("Indica tu participación en el ministerio de forma cualitativa.")
        tipo_informe = st.radio(
            "¿Participaste en el ministerio?",
            ["Sí, participé", "No participé"],
            horizontal=True,
            key="tipo_widget"
        )
        detalles = st.text_input("Detalles adicionales (Ej: facetas)", help="Opcional", key="detalles_widget")
        if tipo_informe == "Sí, participé":
            informe_servicio = "Sí participé" + (f" ({detalles})" if detalles else "")
        else:
            informe_servicio = "No participé" + (f" ({detalles})" if detalles else "")
        cursos_biblicos = st.number_input("Cursos Bíblicos Dirigidos", min_value=0, step=1, key="cursos_widget")

    notas = st.text_area(
        "Notas (Opcional)",
        help="Si no predicó, indique por qué. Ej: 'Enfermo', 'De viaje', etc.",
        height=100,
        key="notas_widget"
    )

# ========================= RESUMEN =========================
st.divider()

if pub_seleccionado and nombre_seleccionado != "Seleccione...":
    st.markdown(f"""
    <div class="resumen-premium">
        <div class="resumen-title">📄 Resumen del Informe</div>
        <div class="resumen-grid">
            <div class="resumen-item">
                <span class="resumen-label">Publicador</span>
                <span class="resumen-value">{pub_seleccionado.name}</span>
            </div>
            <div class="resumen-item">
                <span class="resumen-label">Período</span>
                <span class="resumen-value highlight">{meses_nombre[st.session_state.mes_sel]} {st.session_state.año_sel}</span>
            </div>
            <div class="resumen-item">
                <span class="resumen-label">Privilegio</span>
                <span class="resumen-value">{privilegio_seleccionado}</span>
            </div>
            <div class="resumen-item">
                <span class="resumen-label">Informe</span>
                <span class="resumen-value">{informe_servicio}</span>
            </div>
            <div class="resumen-item">
                <span class="resumen-label">Cursos Bíblicos</span>
                <span class="resumen-value highlight">{cursos_biblicos}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ========================= BOTÓN GUARDAR =========================
deshabilitar = (pub_seleccionado is None) or (nombre_seleccionado == "Seleccione...")
submit = st.button(
    "✅ Guardar Informe",
    disabled=deshabilitar,
    use_container_width=False,
    type="primary"
)

if submit:
    if not pub_seleccionado or nombre_seleccionado == "Seleccione...":
        st.error("Por favor, selecciona un publicador válido.")
    elif es_precursor and horas == 0 and (not notas or "No participé" not in notas):
        st.warning("Has indicado 0 horas siendo precursor. Añade una justificación en 'Notas'.")
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

            st.session_state.success_msg = f"Informe de {meses_nombre[st.session_state.mes_sel]} {st.session_state.año_sel} para {pub_seleccionado.name} guardado exitosamente."

            keys_to_clear = ["pub_widget", "priv_widget", "horas_widget", "cursos_widget",
                             "tipo_widget", "detalles_widget", "notas_widget", "grupo_widget",
                             "ano_widget", "mes_widget"]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]

            st.rerun()
        except Exception as e:
            db2.rollback()
            st.error(f"❌ Error al guardar el informe: {e}")
        finally:
            db2.close()