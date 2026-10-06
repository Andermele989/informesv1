"""Indicadores del dashboard: totales, actividad y variación frente al mes anterior."""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Resumen:
    informes: int = 0
    horas: int = 0
    cursos: int = 0
    sin_actividad: int = 0

    @property
    def promedio_horas(self) -> float:
        return self.horas / self.informes if self.informes else 0.0

    @property
    def promedio_cursos(self) -> float:
        return self.cursos / self.informes if self.informes else 0.0

    @property
    def con_actividad_pct(self) -> float:
        return (self.informes - self.sin_actividad) / self.informes * 100 if self.informes else 0.0


def solo_activos(df: pd.DataFrame) -> pd.DataFrame:
    """Quita las filas sintéticas de publicadores inactivos."""
    return df[df["Privilegios"] != "Inactivo"]


def sin_actividad(df: pd.DataFrame) -> pd.Series:
    """Informes de quien no participó, o de un precursor/auxiliar con 0 horas.

    Un publicador que sí participó pero no reporta horas NO cuenta como inactivo.
    """
    no_participo = df["Informe"].str.contains(r"no\s+(?:particip|predic)", case=False, regex=True, na=False)
    precursor_sin_horas = df["Privilegios"].str.contains("precursor", case=False, na=False) & (df["Horas"] == 0)
    return no_participo | precursor_sin_horas


def resumir(df_activos: pd.DataFrame) -> Resumen:
    if df_activos.empty:
        return Resumen()
    return Resumen(
        informes=len(df_activos),
        horas=int(df_activos["Horas"].sum()),
        cursos=int(df_activos["Cursos Bíblicos"].sum()),
        sin_actividad=int(sin_actividad(df_activos).sum()),
    )


def variacion(actual: float, anterior: float) -> tuple[str, str]:
    """Texto y clase CSS de la variación: `("▲ 12%", "delta-up")`. Vacío si no hay base."""
    if not anterior:
        return ("▲ nuevo", "delta-up") if actual > 0 else ("", "")
    cambio = (actual - anterior) / anterior * 100
    if round(cambio) == 0:
        return "= igual", ""
    return (f"▲ {cambio:.0f}%", "delta-up") if cambio > 0 else (f"▼ {abs(cambio):.0f}%", "delta-down")


def porcentaje(valor: float) -> str:
    return f"{max(0, min(100, valor)):.0f}%"


def numero(valor: float, decimales: int = 0) -> str:
    """Formato español: 1.234 y 12,5."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def serie_mensual(df_activos: pd.DataFrame, meses: int = 6) -> pd.DataFrame:
    """Informes, horas, cursos y casos sin actividad por mes (últimos `meses`), para las mini-barras."""
    columnas = ["Mes", "informes", "horas", "cursos", "sin_actividad"]
    if df_activos.empty:
        return pd.DataFrame(columns=columnas)
    marcado = df_activos.assign(_sin=sin_actividad(df_activos))
    serie = marcado.groupby("Mes").agg(
        informes=("Mes", "size"), horas=("Horas", "sum"), cursos=("Cursos Bíblicos", "sum"), sin_actividad=("_sin", "sum"),
    ).reset_index().sort_values("Mes").tail(meses)
    return serie[columnas].reset_index(drop=True)
