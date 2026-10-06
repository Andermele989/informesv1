"""Lectura de datos y transformaciones compartidas por las vistas."""
import datetime as dt
import re

import pandas as pd
import streamlit as st

from core import models
from core.database import sesion

MESES = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")

COLUMNAS = ["id", "publisher_id", "Publicador", "Grupo", "Mes", "Privilegios",
            "Cursos Bíblicos", "Informe", "Notas"]

_RE_HORAS = re.compile(r"\b(\d+)\s*(?:horas?|hrs?|h)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Fechas y horas
# ---------------------------------------------------------------------------

def extraer_horas(texto) -> int:
    """Suma las horas escritas en un informe ("50 horas", "12 h")."""
    if not isinstance(texto, str):
        return 0
    return sum(int(n) for n in _RE_HORAS.findall(texto))


def anio_servicio(mes: str) -> str:
    """El año de servicio va de septiembre a agosto: "2026-10" -> "2026-2027"."""
    try:
        anio, numero = (int(p) for p in mes.split("-"))
    except (ValueError, AttributeError):
        return "Desconocido"
    inicio = anio if numero >= 9 else anio - 1
    return f"{inicio}-{inicio + 1}"


def mes_anterior(mes: str) -> str | None:
    try:
        anio, numero = (int(p) for p in mes.split("-"))
    except (ValueError, AttributeError):
        return None
    return f"{anio - 1}-12" if numero == 1 else f"{anio}-{numero - 1:02d}"


def mes_actual() -> str:
    return dt.date.today().strftime("%Y-%m")


def nombre_mes(mes: str) -> str:
    """"2026-09" -> "Septiembre 2026"."""
    try:
        anio, numero = mes.split("-")
        return f"{MESES[int(numero) - 1]} {anio}"
    except (ValueError, IndexError, AttributeError):
        return str(mes)


# ---------------------------------------------------------------------------
# Construcción del DataFrame
# ---------------------------------------------------------------------------

def construir_dataframe(informes, publicadores, grupos) -> pd.DataFrame:
    """Une informes, publicadores y grupos en una tabla lista para filtrar.

    Para cada publicador inactivo añade una fila "Inactivo" en los meses en los que no
    tiene informe, de modo que aparezca en los listados y exportaciones.

    informes:     (id, publisher_id, month, full_name, privilegio, cursos, informe, notas)
    publicadores: (id, name, is_inactive, group_id)
    grupos:       (id, name)
    """
    nombre_grupo = dict(grupos)
    publicador = {p[0]: p for p in publicadores}

    filas = []
    for id_, pub_id, mes, nombre, privilegio, cursos, informe, notas in informes:
        pub = publicador.get(pub_id)
        filas.append((
            id_, pub_id,
            nombre or (pub[1] if pub else "Desconocido"),
            nombre_grupo.get(pub[3], "Sin Grupo") if pub else "Sin Grupo",
            mes, privilegio or "Ninguno", cursos or 0, informe or "", notas or "",
        ))

    meses = sorted({i[2] for i in informes}, reverse=True)
    existentes = {(i[1], i[2]) for i in informes}
    for pub_id, nombre, inactivo, grupo_id in publicadores:
        if not inactivo:
            continue
        for mes in meses:
            if (pub_id, mes) not in existentes:
                filas.append((None, pub_id, nombre, nombre_grupo.get(grupo_id, "Sin Grupo"), mes,
                              "Inactivo", 0, "INACTIVO (No predicó)", "Registrado automático por el sistema"))

    df = pd.DataFrame(filas, columns=COLUMNAS)
    df["Horas"] = df["Informe"].map(extraer_horas)
    df["Año Servicio"] = df["Mes"].map(anio_servicio)
    return df


@st.cache_data(ttl=300, show_spinner="Cargando informes...")
def cargar_datos() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve `(informes, publicadores)`. Se lee de la BD una vez cada 5 min."""
    with sesion() as db:
        informes = [tuple(r) for r in db.query(
            models.MonthlyReport.id, models.MonthlyReport.publisher_id, models.MonthlyReport.month,
            models.MonthlyReport.full_name, models.MonthlyReport.assigned_privileges,
            models.MonthlyReport.bible_courses, models.MonthlyReport.service_report,
            models.MonthlyReport.notes).all()]
        publicadores = [tuple(r) for r in db.query(
            models.Publisher.id, models.Publisher.name, models.Publisher.is_inactive,
            models.Publisher.group_id).all()]
        grupos = [tuple(r) for r in db.query(models.Group.id, models.Group.name).all()]

    df = construir_dataframe(informes, publicadores, grupos)
    nombre_grupo = dict(grupos)
    pubs = pd.DataFrame(publicadores, columns=["id", "Publicador", "Inactivo", "group_id"])
    pubs["Grupo"] = pubs["group_id"].map(nombre_grupo).fillna("Sin Grupo")
    pubs["Inactivo"] = pubs["Inactivo"].fillna(False).astype(bool)
    return df, pubs


def invalidar_cache() -> None:
    """Llamar tras crear, editar o borrar informes, publicadores o grupos."""
    cargar_datos.clear()
    resumen_inicio.clear()


def directorio(informes: pd.DataFrame, publicadores: pd.DataFrame) -> pd.DataFrame:
    """Un renglón por informe, más uno por cada publicador que aún no tiene informes."""
    reales = informes[informes["id"].notna()]
    inactivos = dict(zip(publicadores["id"], publicadores["Inactivo"], strict=False))
    filas = [{
        "Publicador": r["Publicador"], "Grupo": r["Grupo"], "Mes del Informe": r["Mes"],
        "Privilegio": r["Privilegios"] if r["Privilegios"] != "Ninguno" else "—",
        "Cursos Bíblicos": r["Cursos Bíblicos"], "Informe": r["Informe"] or "Sin detalles",
        "Estado": "Inactivo" if inactivos.get(r["publisher_id"]) else "Activo",
    } for r in reales.sort_values("Mes", ascending=False).to_dict("records")]

    con_informe = set(reales["publisher_id"].dropna().astype(int))
    for p in publicadores.to_dict("records"):
        if p["id"] not in con_informe:
            filas.append({"Publicador": p["Publicador"], "Grupo": p["Grupo"], "Mes del Informe": "Sin Informes",
                          "Privilegio": "—", "Cursos Bíblicos": 0, "Informe": "Sin datos",
                          "Estado": "Inactivo" if p["Inactivo"] else "Activo"})
    return pd.DataFrame(filas, columns=["Publicador", "Grupo", "Mes del Informe", "Privilegio",
                                        "Cursos Bíblicos", "Informe", "Estado"])


@st.cache_data(ttl=60, show_spinner=False)
def resumen_inicio() -> dict:
    """Cifras de la página de inicio para administradores (cacheadas por 60s)."""
    mes = mes_actual()
    with sesion() as db:
        activos = db.query(models.Publisher).filter(models.Publisher.is_inactive.is_(False))
        total = activos.count()
        recibidos = (db.query(models.MonthlyReport)
                     .join(models.Publisher, models.MonthlyReport.publisher_id == models.Publisher.id)
                     .filter(models.MonthlyReport.month == mes, models.Publisher.is_inactive.is_(False))
                     .count())
        grupos = db.query(models.Group).count()
    return {"mes": mes, "publicadores": total, "grupos": grupos, "recibidos": recibidos,
            "pendientes": max(0, total - recibidos),
            "porcentaje": (recibidos / total * 100) if total else 0}
