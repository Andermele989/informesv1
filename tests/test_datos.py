import pandas as pd
import pytest

from services import datos, metricas


@pytest.mark.parametrize("texto, esperado", [
    ("50 horas", 50), ("12 h", 12), ("1 hora", 1), ("10 horas y 3 h", 13), ("Sí participé", 0),
    ("Sí participé (2 hogares)", 0), ("participó 3 horarios", 0), (None, 0), ("", 0),
])
def test_extraer_horas(texto, esperado):
    assert datos.extraer_horas(texto) == esperado


def test_anio_de_servicio_va_de_septiembre_a_agosto():
    assert datos.anio_servicio("2026-08") == "2025-2026"
    assert datos.anio_servicio("2026-09") == "2026-2027"
    assert datos.anio_servicio("2027-01") == "2026-2027"
    assert datos.anio_servicio("basura") == "Desconocido"


def test_mes_anterior_y_nombre():
    assert datos.mes_anterior("2026-10") == "2026-09"
    assert datos.mes_anterior("2026-01") == "2025-12"
    assert datos.mes_anterior("x") is None
    assert datos.nombre_mes("2026-09") == "Septiembre 2026"


def test_dataframe_incluye_inactivos_sin_informe(datos_ejemplo):
    from core import models
    from core.database import sesion
    with sesion() as db:
        informes = [tuple(r) for r in db.query(
            models.MonthlyReport.id, models.MonthlyReport.publisher_id, models.MonthlyReport.month,
            models.MonthlyReport.full_name, models.MonthlyReport.assigned_privileges, models.MonthlyReport.bible_courses,
            models.MonthlyReport.service_report, models.MonthlyReport.notes)]
        pubs = [tuple(r) for r in db.query(
            models.Publisher.id, models.Publisher.name, models.Publisher.is_inactive, models.Publisher.group_id)]
        grupos = [tuple(r) for r in db.query(models.Group.id, models.Group.name)]
    df = datos.construir_dataframe(informes, pubs, grupos)
    assert len(df) == 5 + 2  # 5 informes + Nico inactivo en 2 meses
    assert (df["Privilegios"] == "Inactivo").sum() == 2
    assert df.loc[df["Publicador"] == "Ana", "Horas"].tolist() == [60, 50]
    assert set(df["Grupo"]) == {"Grupo 1", "Grupo 2"}
    # el directorio muestra a cada publicador; los inactivos sintéticos no cuentan como informes
    pub_df = pd.DataFrame(pubs, columns=["id", "Publicador", "Inactivo", "group_id"])
    pub_df["Grupo"] = pub_df["group_id"].map(dict(grupos))
    directorio = datos.directorio(df, pub_df)
    assert len(directorio) == 5 + 1  # 5 informes + Nico sin informes
    assert "Sin Informes" in directorio["Mes del Informe"].tolist()


def test_sin_actividad_no_castiga_a_quien_participo_sin_horas():
    df = pd.DataFrame({
        "Informe": ["Sí participé", "No participé", "0 horas", "50 horas", "No participé (enfermo)"],
        "Privilegios": ["Publicador", "Publicador", "Precursor Regular", "Precursor Regular", "Publicador"],
        "Horas": [0, 0, 0, 50, 0],
    })
    assert metricas.sin_actividad(df).tolist() == [False, True, True, False, True]


def test_variacion_y_formato_numerico():
    assert metricas.variacion(110, 100) == ("▲ 10%", "delta-up")
    assert metricas.variacion(80, 100) == ("▼ 20%", "delta-down")
    assert metricas.variacion(5, 0) == ("▲ nuevo", "delta-up")
    assert metricas.variacion(0, 0) == ("", "")
    assert metricas.numero(1234) == "1.234"
    assert metricas.numero(12.5, 1) == "12,5"
    assert metricas.numero(1234.5, 1) == "1.234,5"
