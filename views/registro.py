"""Registro del informe mensual de un publicador."""
import datetime as dt
import logging

import streamlit as st
from sqlalchemy.exc import IntegrityError

from core import auth, models, ui
from core.database import sesion
from core.security import limpiar_texto, sanitize_text
from services import datos, ia

log = logging.getLogger("informes.registro")

auth.require_login()
ui.encabezado("Registro de informe", "Registra la actividad mensual de los publicadores del grupo")

# Mes de referencia: el anterior al actual (se informa a mes vencido).
referencia = dt.date.today().replace(day=1) - dt.timedelta(days=1)
anios = list(range(referencia.year - 2, referencia.year + 2))

col_izq, col_der = st.columns(2, gap="large")

# ----------------------------------------------------------------------------
# Izquierda: periodo, grupo y publicador
# ----------------------------------------------------------------------------
with col_izq, st.container(key="card_periodo"):
    ui.titulo_tarjeta("Periodo y publicador")
    c_anio, c_mes = st.columns(2)
    anio = c_anio.selectbox("Año", anios, index=anios.index(referencia.year), key="reg_anio")
    mes = c_mes.selectbox("Mes", range(1, 13), index=referencia.month - 1, key="reg_mes",
                          format_func=lambda m: datos.MESES[m - 1])
    mes_clave = f"{anio}-{mes:02d}"
    etiqueta_mes = f"{datos.MESES[mes - 1]} {anio}"

    with sesion() as db:
        grupos = db.query(models.Group).order_by(models.Group.name).all()
        grupo_id = {g.name: g.id for g in grupos}
        privilegios = [p.name for p in db.query(models.Privilege).order_by(models.Privilege.id).all()]

        grupo_sel = st.selectbox("Grupo", ["Todos", *grupo_id], key="reg_grupo")
        activos = db.query(models.Publisher).filter(models.Publisher.is_inactive.is_(False))
        if grupo_sel != "Todos":
            activos = activos.filter(models.Publisher.group_id == grupo_id[grupo_sel])
        total = activos.count()
        ya_informaron = db.query(models.MonthlyReport.publisher_id).filter(
            models.MonthlyReport.month == mes_clave, models.MonthlyReport.publisher_id.isnot(None))
        pendientes = (activos.filter(~models.Publisher.id.in_(ya_informaron))
                      .order_by(models.Publisher.name).all())
        pendientes = {p.name: (p.id, p.name) for p in pendientes}

    if total:
        entregados = total - len(pendientes)
        ui.html(f"""<div class="progress"><div class="progress-top"><span>Progreso de {sanitize_text(etiqueta_mes)}</span>
            <b>{entregados}/{total}</b></div><div class="meter"><span style="width:{entregados / total * 100:.0f}%"></span></div></div>""")

    if not pendientes:
        st.success(f"Todos los publicadores entregaron su informe de {etiqueta_mes}.", icon=":material/celebration:")
        seleccionado = None
    else:
        nombre = st.selectbox(f"Publicador ({len(pendientes)} pendientes)", ["Seleccione...", *pendientes], key="reg_pub")
        seleccionado = pendientes.get(nombre)

    opciones_priv = ["Ninguno", *privilegios]
    # Sugiere el privilegio del último informe del publicador elegido.
    if st.session_state.get("_reg_pub_previo") != seleccionado:
        st.session_state["_reg_pub_previo"] = seleccionado
        sugerido = "Ninguno"
        if seleccionado:
            with sesion() as db:
                ultimo = (db.query(models.MonthlyReport.assigned_privileges)
                          .filter(models.MonthlyReport.publisher_id == seleccionado[0])
                          .order_by(models.MonthlyReport.month.desc()).first())
            if ultimo and ultimo[0] in opciones_priv:
                sugerido = ultimo[0]
        st.session_state["reg_priv"] = sugerido
    privilegio = st.selectbox("Privilegio del mes", opciones_priv, key="reg_priv")
    if seleccionado:
        with sesion() as db:
            ultimos = (db.query(models.MonthlyReport)
                       .filter(models.MonthlyReport.publisher_id == seleccionado[0])
                       .order_by(models.MonthlyReport.month.desc()).limit(3).all())
        if ultimos:
            horas_rec = [datos.extraer_horas(u.service_report) for u in ultimos]
            prom_h = sum(horas_rec) / len(horas_rec) if horas_rec else 0
            ui.html(f'<div class="hist"><span class="ai-badge">Historial</span>'
                    f'<span>Promedio: <b>{prom_h:.1f} h/mes</b> · {len(ultimos)} informes previos</span></div>')

# ----------------------------------------------------------------------------
# Derecha: actividad del mes
# ----------------------------------------------------------------------------
with col_der, st.container(key="card_actividad"):
    ui.titulo_tarjeta("Actividad del mes")
    es_precursor = "precursor" in privilegio.lower()
    horas = 0
    if es_precursor:
        st.caption("Como precursor, registra las horas y los estudios bíblicos realizados.")
        horas = st.number_input("Horas de servicio", 0, 200, step=1, key="reg_horas")
        informe = f"{horas} horas"
        cursos = st.number_input("Cursos bíblicos dirigidos", 0, 50, step=1, key="reg_cursos")
    else:
        st.caption("Indica la participación en el ministerio de forma cualitativa.")
        participo = st.radio("¿Participó en el ministerio?", ["Sí, participé", "No participé"], horizontal=True, key="reg_tipo")
        detalle = limpiar_texto(st.text_input("Detalles adicionales (opcional)", max_chars=100, key="reg_detalle",
                                              placeholder="Ej: casa en casa, testimonio informal"), 100)
        informe = ("Sí participé" if participo == "Sí, participé" else "No participé") + (f" ({detalle})" if detalle else "")
        if participo == "Sí, participé":
            cursos = st.number_input("Cursos bíblicos dirigidos", 0, 50, step=1, key="reg_cursos")
        else:
            cursos = 0
            st.caption("Al no haber participado, los cursos bíblicos quedan en 0.")

    c_lbl, c_ai = st.columns([1.8, 1.2], vertical_alignment="bottom")
    with c_lbl:
        st.caption("Notas u observaciones (opcional)")
    with c_ai, st.popover("Asistente IA", icon=":material/auto_awesome:"):
        st.caption("Redacta una nota formal. Solo se envía al proveedor de IA la frase corta que escribas aquí: "
                   "evita diagnósticos y datos personales.")
        motivo_ia = st.text_input("Motivo breve", placeholder="Ej: viaje, trabajo, horario", key="ai_reg_motivo", max_chars=80)
        if st.button("Aplicar sugerencia", icon=":material/check:", key="btn_ai_sugerir", type="primary"):
            sug = ia.sugerir_nota(motivo_ia, privilegio)
            st.session_state["reg_notas"] = sug
            st.rerun()

    notas = limpiar_texto(st.text_area("Notas u observaciones", max_chars=500, height=85, key="reg_notas",
                                       label_visibility="collapsed",
                                       help="Si no predicó, indica por qué. Ej: «Enfermo», «De viaje»."), 500, multilinea=True)

# ----------------------------------------------------------------------------
# Resumen y guardado
# ----------------------------------------------------------------------------
if seleccionado:
    ui.html(f"""<div class="summary"><div class="card-head"><b>Resumen del informe</b></div><div class="summary-grid">
        <div><span>Publicador</span><b>{sanitize_text(seleccionado[1])}</b></div>
        <div><span>Periodo</span><b>{sanitize_text(etiqueta_mes)}</b></div>
        <div><span>Privilegio</span><b>{sanitize_text(privilegio)}</b></div>
        <div><span>Informe</span><b>{sanitize_text(informe)}</b></div>
        <div><span>Cursos bíblicos</span><b>{int(cursos)}</b></div></div></div>""")

if st.button("Guardar informe", type="primary", icon=":material/check:", disabled=seleccionado is None):
    if es_precursor and horas == 0 and not notas:
        st.warning("Indicaste 0 horas siendo precursor: añade una justificación en «Notas».")
    else:
        try:
            with sesion() as db:
                db.add(models.MonthlyReport(
                    user_id=st.session_state.user_id, publisher_id=seleccionado[0], full_name=seleccionado[1],
                    month=mes_clave, assigned_privileges=None if privilegio == "Ninguno" else privilegio,
                    service_report=informe, notes=notas, bible_courses=int(cursos)))
                db.commit()
        except IntegrityError:  # otro usuario registró el mismo publicador y mes mientras tanto
            st.error(f"Ya existe un informe de {seleccionado[1]} para {etiqueta_mes}. Recarga la página.")
        except Exception:
            log.exception("Error al guardar el informe")
            st.error("No se pudo guardar el informe. Inténtalo de nuevo.")
        else:
            datos.invalidar_cache()
            # Se conservan año, mes y grupo para registrar al siguiente publicador sin repetir.
            for clave in ("reg_pub", "reg_horas", "reg_cursos", "reg_tipo", "reg_detalle", "reg_notas"):
                st.session_state.pop(clave, None)
            ui.avisar(f"Informe de {seleccionado[1]} ({etiqueta_mes}) guardado.", "🎉")
            st.rerun()
