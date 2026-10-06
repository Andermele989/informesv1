"""Dashboard: indicadores, gráficos, exportación a Excel/PDF y análisis con IA."""
import logging
import time

import pandas as pd
import streamlit as st

from core import auth, ui
from core.security import sanitize_text
from services import datos, excel, graficos, ia, metricas, pdf

log = logging.getLogger("informes.dashboard")
PAUSA_IA_SEGUNDOS = 15

auth.require_login()

informes, publicadores = datos.cargar_datos()
cabecera = st.empty()  # se rellena al final, cuando ya se conocen los filtros
if informes.empty:
    ui.encabezado("Dashboard", "Aún no hay informes registrados")
    st.info("Ve a «Registro» para añadir el primer informe.")
    st.stop()

# ----------------------------------------------------------------------------
# Filtros: año de servicio -> meses -> grupo -> publicadores
# ----------------------------------------------------------------------------
anios = sorted(informes["Año Servicio"].unique(), reverse=True)
anio_actual = datos.anio_servicio(datos.mes_actual())

with st.container(key="card_filtros"):
    c_anio, c_mes, c_grupo, c_pub, c_refrescar = st.columns([1.1, 1.7, 1.1, 1.7, 0.45], vertical_alignment="bottom")
    anio_sel = c_anio.selectbox("Año de servicio", ["Todos", *anios],
                                index=(anios.index(anio_actual) + 1) if anio_actual in anios else 1)
    df_anio = informes if anio_sel == "Todos" else informes[informes["Año Servicio"] == anio_sel]

    meses_disponibles = sorted(df_anio["Mes"].unique(), reverse=True)
    por_defecto = [datos.mes_actual()] if datos.mes_actual() in meses_disponibles else meses_disponibles[:1]
    meses_sel = c_mes.multiselect("Mes(es)", meses_disponibles, default=por_defecto)
    df_mes = df_anio[df_anio["Mes"].isin(meses_sel)] if meses_sel else df_anio

    grupo_sel = c_grupo.selectbox("Grupo", ["Todos", *sorted(df_mes["Grupo"].unique())])
    df_grupo = df_mes if grupo_sel == "Todos" else df_mes[df_mes["Grupo"] == grupo_sel]

    pubs_sel = c_pub.multiselect("Publicador", sorted(df_grupo["Publicador"].unique()), placeholder="Todos")
    df = df_grupo if not pubs_sel else df_grupo[df_grupo["Publicador"].isin(pubs_sel)]
    df = df.sort_values(["Grupo", "Publicador"])

    if c_refrescar.button("", icon=":material/refresh:", help="Actualizar datos", width="stretch"):
        datos.invalidar_cache()
        st.rerun()


def filtrar_ambito(frame: pd.DataFrame) -> pd.DataFrame:
    """Aplica el grupo y los publicadores elegidos (no el periodo)."""
    if grupo_sel != "Todos":
        frame = frame[frame["Grupo"] == grupo_sel]
    if pubs_sel:
        frame = frame[frame["Publicador"].isin(pubs_sel)]
    return frame


# ----------------------------------------------------------------------------
# Indicadores
# ----------------------------------------------------------------------------
activos = metricas.solo_activos(df)
actual = metricas.resumir(activos)
resumen_anio = metricas.resumir(metricas.solo_activos(df_anio))

etiqueta_periodo = (meses_sel[0] if len(meses_sel) == 1 else f"{len(meses_sel)} meses") if meses_sel else "Todos los meses"
meses_contexto = meses_sel or meses_disponibles

mes_ant = datos.mes_anterior(meses_sel[0]) if len(meses_sel) == 1 else None
anterior = None
if mes_ant:
    anterior = metricas.resumir(metricas.solo_activos(filtrar_ambito(informes[informes["Mes"] == mes_ant])))

en_ambito = publicadores[~publicadores["Inactivo"]]
if grupo_sel != "Todos":
    en_ambito = en_ambito[en_ambito["Grupo"] == grupo_sel]
if pubs_sel:
    en_ambito = en_ambito[en_ambito["Publicador"].isin(pubs_sel)]
esperados = len(en_ambito) * max(len(meses_contexto), 1)
cobertura = actual.informes / esperados * 100 if esperados else 0


def delta(campo: str) -> tuple[str, str]:
    return metricas.variacion(getattr(actual, campo), getattr(anterior, campo)) if anterior else ("", "")


cabecera.empty()
with cabecera.container():
    ui.encabezado("Dashboard de rendimiento", "Análisis estadístico del servicio del grupo", insignias=(
        ("Periodo", etiqueta_periodo), ("Grupo", grupo_sel), ("Informes", str(actual.informes)),
        ("Año de servicio", f"{anio_sel} · {metricas.numero(resumen_anio.horas)} h" if anio_sel != "Todos" else "Histórico"),
    ))

evolucion_base = metricas.solo_activos(filtrar_ambito(informes))
historial = metricas.serie_mensual(evolucion_base)  # últimos 6 meses, para las mini-barras

ui.html(
    '<div class="kpi-grid">'
    + ui.tarjeta_metrica("Informes recibidos", metricas.numero(actual.informes), "amber", "description", delta=delta("informes"),
                         nota=f"{metricas.numero(esperados)} esperados · {metricas.porcentaje(cobertura)}",
                         serie=historial["informes"].tolist())
    + ui.tarjeta_metrica("Horas reportadas", metricas.numero(actual.horas), "orange", "schedule", delta=delta("horas"),
                         nota=f"Promedio {metricas.numero(actual.promedio_horas, 1)} h por informe",
                         serie=historial["horas"].tolist())
    + ui.tarjeta_metrica("Cursos bíblicos", metricas.numero(actual.cursos), "gold", "menu_book", delta=delta("cursos"),
                         nota=f"Promedio {metricas.numero(actual.promedio_cursos, 1)} por informe",
                         serie=historial["cursos"].tolist())
    + ui.tarjeta_metrica("Sin actividad", metricas.numero(actual.sin_actividad), "flame", "pause_circle",
                         nota=f"{metricas.porcentaje(actual.con_actividad_pct)} con actividad",
                         serie=historial["sin_actividad"].tolist())
    + "</div>"
)

# ----------------------------------------------------------------------------
# Gráficos
# ----------------------------------------------------------------------------
fig_horas = graficos.horas_por_publicador(activos)
filas_dona = graficos.distribucion_filas(activos)
fig_evolucion = graficos.evolucion_mensual(evolucion_base)


def tarjeta_grafico(clave: str, titulo: str, figura, vacio: str, detalle: str = "") -> None:
    with st.container(key=f"card_{clave}"):
        ui.titulo_tarjeta(titulo, detalle)
        if figura is None:
            st.caption(vacio)
        else:
            st.plotly_chart(figura, width="stretch", config=graficos.CONFIG)


fila1 = st.columns([3, 2], gap="medium")
with fila1[0]:
    tarjeta_grafico("horas", "Horas por publicador", fig_horas, "Sin horas reportadas en este periodo.",
                    "Solo quienes reportan horas")
with fila1[1], st.container(key="card_dona"):
    ui.titulo_tarjeta("Distribución de horas", "Participación de cada publicador")
    if not filas_dona:
        st.caption("Sin horas reportadas en este periodo.")
    else:
        c_anillo, c_leyenda = st.columns([1.35, 1], vertical_alignment="center", gap="small")
        c_anillo.plotly_chart(graficos.distribucion(filas_dona), width="stretch", config=graficos.CONFIG)
        c_leyenda.markdown(
            '<ul class="legend">' + "".join(
                f'<li><i style="background:{color}"></i><span>{sanitize_text(graficos.nombre_corto(nombre, 15))}</span>'
                f"<b>{pct:.0f}% <em>({horas})</em></b></li>"
                for nombre, horas, pct, color in filas_dona) + "</ul>",
            unsafe_allow_html=True)

fila2 = st.columns([3, 2], gap="medium")
with fila2[0]:
    tarjeta_grafico("evolucion", "Evolución mensual de horas", fig_evolucion, "No hay suficientes datos.",
                    "Horas reportadas cada mes")
with fila2[1], st.container(key="card_precursores"):
    c_titulo, c_tipo = st.columns([1, 1.2], vertical_alignment="center")
    with c_titulo:
        ui.titulo_tarjeta("Precursores", "Horas del periodo")
    tipo = c_tipo.selectbox("Tipo", ["Todos", "Regulares", "Auxiliares"], label_visibility="collapsed")
    precursores = activos[activos["Privilegios"].str.contains("precursor", case=False, na=False)]
    if tipo != "Todos":
        precursores = precursores[precursores["Privilegios"].str.contains(tipo[:-2], case=False, na=False)]
    figura = graficos.precursores(precursores)
    if figura is None:
        st.caption("No hay precursores en este periodo.")
    else:
        st.plotly_chart(figura, width="stretch", config=graficos.CONFIG)
        st.caption(f"{metricas.numero(int(precursores['Horas'].sum()))} h · "
                   f"{metricas.numero(int(precursores['Cursos Bíblicos'].sum()))} cursos bíblicos")

# ----------------------------------------------------------------------------
# Tabla de datos
# ----------------------------------------------------------------------------
with st.container(key="card_tabla"):
    ui.titulo_tarjeta("Datos del periodo", f"{len(df)} filas")
    st.dataframe(df[["Publicador", "Grupo", "Mes", "Privilegios", "Cursos Bíblicos", "Informe", "Notas"]],
                 hide_index=True, width="stretch", height=min(520, 38 + 35 * max(len(df), 1)))

# ----------------------------------------------------------------------------
# Exportar a Excel
# ----------------------------------------------------------------------------
titulo_excel = f"Grupo {grupo_sel}" if grupo_sel != "Todos" else "Reporte general"
titulo_excel += f" · {etiqueta_periodo}"
nombre_archivo = f"Reporte_{etiqueta_periodo.replace(' ', '_')}"

col_excel, col_ia = st.columns(2, gap="medium")
with col_excel, st.container(key="card_excel"):
    ui.titulo_tarjeta("Exportar a Excel", "Tabla con filtros y totales")
    st.caption("Incluye una hoja filtrable por grupo, mes, privilegio y publicador, con totales que se "
               "recalculan al filtrar, y un resumen por grupo.")
    st.download_button(
        "Descargar Excel", icon=":material/download:", type="primary", width="stretch",
        data=lambda: excel.generar_excel(excel.preparar_exportacion(df), titulo_excel),  # se genera al pulsar
        file_name=f"{nombre_archivo}.xlsx", on_click="ignore",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ----------------------------------------------------------------------------
# Análisis con IA + PDF
# ----------------------------------------------------------------------------
firma = (anio_sel, tuple(meses_sel), grupo_sel, tuple(pubs_sel))


def generar_informe(motor: str) -> dict:
    """Pide el análisis a la IA y arma el PDF. Devuelve lo que se guarda en sesión."""
    por_grupo = (activos.assign(Activo=~metricas.sin_actividad(activos)).groupby("Grupo")
                 .agg(Informes=("Publicador", "count"), Activos=("Activo", "sum"), Horas=("Horas", "sum"),
                      Cursos=("Cursos Bíblicos", "sum")).reset_index())
    serie = (evolucion_base.groupby("Mes").agg(Horas=("Horas", "sum"), Informes=("Publicador", "count"))
             .reset_index().sort_values("Mes").tail(6))
    todos_precursores = activos[activos["Privilegios"].str.contains("precursor", case=False, na=False)]
    prec_ia = todos_precursores.rename(columns={"Cursos Bíblicos": "Cursos"})[["Publicador", "Privilegios", "Horas", "Cursos"]]
    contexto = ia.ContextoAnalisis(
        periodo=etiqueta_periodo, ambito=grupo_sel if grupo_sel != "Todos" else "Todos los grupos",
        anio_servicio=anio_sel, actual=actual, esperados=esperados, anterior=anterior, mes_anterior=mes_ant,
        tendencia=serie, por_grupo=por_grupo, precursores=prec_ia,
        sin_actividad=sorted(activos[metricas.sin_actividad(activos)]["Publicador"].unique()),
        inactivos=sorted(df[df["Privilegios"] == "Inactivo"]["Publicador"].unique()),
        pendientes=sorted(set(en_ambito["Publicador"]) - set(activos["Publicador"])),
    )
    texto, modelo = ia.generar_analisis(motor, ia.construir_prompt(contexto))

    con_horas = (activos[activos["Horas"] > 0].groupby("Publicador", as_index=False)["Horas"].sum()
                 .sort_values("Horas", ascending=False))
    datos_pdf = pdf.DatosInforme(
        periodo=datos.nombre_mes(meses_sel[0]) if len(meses_sel) == 1 else etiqueta_periodo,
        ambito=contexto.ambito, modelo_ia=modelo, actual=actual, esperados=esperados, analisis=texto,
        anterior=anterior, mes_anterior=datos.nombre_mes(mes_ant) if mes_ant else None,
        por_grupo=por_grupo, serie=serie[["Mes", "Horas"]], ranking=con_horas,
        precursores=todos_precursores.groupby("Publicador", as_index=False)["Horas"].sum().sort_values("Horas", ascending=False),
        distribucion=con_horas,
        detalle=df[["Publicador", "Grupo", "Privilegios", "Horas", "Cursos Bíblicos", "Informe"]],
    )
    return {"firma": firma, "motor": motor, "texto": texto, "modelo": modelo, "pdf": pdf.generar_pdf(datos_pdf),
            "archivo": f"Informe_{etiqueta_periodo.replace(' ', '_')}.pdf"}


with col_ia, st.container(key="card_ia"):
    ui.titulo_tarjeta("Análisis con IA", "Informe en PDF incluido")
    motor = st.radio("Motor", ia.MOTORES, horizontal=True, label_visibility="collapsed")
    st.caption(f"Modelo: `{ia.modelo_de(motor)}`. Se envían cifras agregadas y nombres; las notas nunca se envían.")
    generar = st.button("Generar análisis", icon=":material/auto_awesome:", type="primary", width="stretch",
                        disabled=actual.informes == 0)
    espera = PAUSA_IA_SEGUNDOS - (time.time() - st.session_state.get("ia_ultimo", 0))
    if generar and espera > 0:  # evita lanzar llamadas de pago en ráfaga
        st.warning(f"Espera {espera:.0f} s antes de generar otro análisis.")
    elif generar:
        st.session_state["ia_ultimo"] = time.time()
        try:
            with st.spinner("Analizando datos y preparando el PDF…"):
                st.session_state["ia_resultado"] = generar_informe(motor)
        except ia.ErrorIA as error:
            st.session_state.pop("ia_resultado", None)
            st.error(str(error))
        except Exception:
            log.exception("Error al generar el informe con IA")
            st.session_state.pop("ia_resultado", None)
            st.error("No se pudo generar el informe. Inténtalo de nuevo.")

# El resultado se guarda en sesión: sobrevive a las recargas del script (p. ej. al pulsar «Descargar»).
resultado = st.session_state.get("ia_resultado")
if resultado:
    with st.container(key="card_resultado"):
        if resultado["firma"] != firma:
            st.warning("Cambiaste los filtros después de generar este análisis. Genera uno nuevo para que coincida.")
        cabecera_r, descarga = st.columns([3, 1], vertical_alignment="center")
        with cabecera_r:
            ui.titulo_tarjeta("Análisis generado", resultado["modelo"])
        descarga.download_button("Descargar PDF", icon=":material/picture_as_pdf:", type="primary", width="stretch",
                                 data=resultado["pdf"], file_name=resultado["archivo"], mime="application/pdf",
                                 on_click="ignore")
        st.markdown(resultado["texto"])  # nunca HTML: la respuesta de un proveedor externo no es de confianza
