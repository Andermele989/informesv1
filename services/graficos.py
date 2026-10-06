"""Gráficos Plotly del dashboard (tema oscuro translúcido sobre las tarjetas de cristal)."""
import pandas as pd
import plotly.graph_objects as go

CONFIG = {"displayModeBar": False, "responsive": True}

PALETA = ["#14f1b2", "#38bdf8", "#a78bfa", "#fbbf24", "#fb7185", "#22d3ee", "#34d399",
          "#818cf8", "#f472b6", "#2dd4bf", "#c084fc", "#67e8f9", "#a3e635", "#f0abfc", "#fdba74"]

_FUENTE = "-apple-system, 'SF Pro Display', 'Segoe UI Variable', 'Segoe UI', Inter, system-ui, sans-serif"
_TEXTO, _TENUE, _REJILLA = "#eef2ff", "#94a3b8", "rgba(148,163,184,0.12)"


def nombre_corto(nombre, limite: int = 16) -> str:
    nombre = str(nombre or "")
    return nombre if len(nombre) <= limite else f"{nombre[:limite - 1]}…"


def _tema(fig: go.Figure, alto: int, margen: dict | None = None) -> go.Figure:
    fig.update_layout(
        height=alto, showlegend=False, bargap=0.28,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FUENTE, size=12, color=_TEXTO),
        margin=margen or dict(t=16, b=40, l=44, r=16),
        hoverlabel=dict(bgcolor="#0f172a", bordercolor="rgba(255,255,255,0.18)",
                        font=dict(family=_FUENTE, color=_TEXTO)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=11, color=_TENUE), title="")
    fig.update_yaxes(gridcolor=_REJILLA, zeroline=False, tickfont=dict(size=11, color=_TENUE), title="")
    return fig


def _degradado(n: int, inicio=(20, 241, 178), fin=(56, 189, 248)) -> list[str]:
    """Colores de `inicio` a `fin` (menta -> cielo por defecto) para n barras."""
    def mezcla(i):
        t = i / max(n - 1, 1)
        return "rgb({},{},{})".format(*(round(a + (b - a) * t) for a, b in zip(inicio, fin, strict=True)))
    return [mezcla(i) for i in range(n)]


def horas_por_publicador(df_activos: pd.DataFrame) -> go.Figure | None:
    datos = (df_activos[df_activos["Horas"] > 0].groupby("Publicador", as_index=False)["Horas"].sum()
             .sort_values("Horas", ascending=False))
    if datos.empty:
        return None
    fig = go.Figure(go.Bar(
        x=datos["Publicador"].map(nombre_corto), y=datos["Horas"], customdata=datos["Publicador"],
        marker=dict(color=_degradado(len(datos)), line=dict(width=0)),
        text=datos["Horas"], textposition="outside", textfont=dict(size=12, color=_TEXTO),
        hovertemplate="<b>%{customdata}</b><br>%{y} horas<extra></extra>",
    ))
    fig.update_xaxes(tickangle=-30 if len(datos) > 6 else 0)
    fig.update_yaxes(range=[0, datos["Horas"].max() * 1.18])
    return _tema(fig, 340, dict(t=16, b=70, l=40, r=12))


def evolucion_mensual(df_activos: pd.DataFrame) -> go.Figure | None:
    if df_activos.empty:
        return None
    serie = df_activos.groupby("Mes", as_index=False)["Horas"].sum().sort_values("Mes")
    fig = go.Figure(go.Scatter(
        x=serie["Mes"], y=serie["Horas"], mode="lines+markers+text",
        text=serie["Horas"], textposition="top center", textfont=dict(size=12, color="#bae6fd"),
        line=dict(color="#38bdf8", width=3, shape="spline"), fill="tozeroy", fillcolor="rgba(56,189,248,0.10)",
        marker=dict(size=9, color="#38bdf8", line=dict(width=2, color="#0b1224")),
        hovertemplate="<b>%{x}</b><br>%{y} horas<extra></extra>",
    ))
    fig.update_xaxes(type="category", range=[-0.4, len(serie) - 0.6])
    fig.update_yaxes(range=[0, max(serie["Horas"].max(), 1) * 1.25])
    return _tema(fig, 340)


def precursores(df_precursores: pd.DataFrame) -> go.Figure | None:
    if df_precursores.empty:
        return None
    datos = (df_precursores.groupby("Publicador", as_index=False)["Horas"].sum().sort_values("Horas"))
    fig = go.Figure(go.Bar(
        y=datos["Publicador"].map(lambda n: nombre_corto(n, 20)), x=datos["Horas"], orientation="h",
        customdata=datos["Publicador"], marker=dict(color=_degradado(len(datos), (124, 92, 246), (167, 139, 250)),
                                                    line=dict(width=0)),
        text=[f"{h} h" for h in datos["Horas"]], textposition="outside", textfont=dict(size=12, color="#ddd6fe"),
        hovertemplate="<b>%{customdata}</b><br>%{x} horas<extra></extra>",
    ))
    fig.update_xaxes(range=[0, max(datos["Horas"].max(), 1) * 1.2], showgrid=True, gridcolor=_REJILLA)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=12, color=_TEXTO))
    return _tema(fig, max(240, len(datos) * 40 + 60), dict(t=8, b=30, l=8, r=30))


def distribucion(df_activos: pd.DataFrame) -> go.Figure | None:
    datos = (df_activos[df_activos["Horas"] > 0].groupby("Publicador", as_index=False)["Horas"].sum()
             .sort_values("Horas", ascending=False))
    if datos.empty:
        return None
    fig = go.Figure(go.Pie(
        labels=datos["Publicador"].map(nombre_corto), values=datos["Horas"], customdata=datos["Publicador"],
        hole=0.64, sort=False, rotation=90, direction="clockwise",
        marker=dict(colors=(PALETA * 4)[:len(datos)], line=dict(color="rgba(7,11,22,0.9)", width=2)),
        textinfo="percent", textposition="inside", textfont=dict(size=11, color="#06101f"),
        hovertemplate="<b>%{customdata}</b><br>%{value} horas · %{percent}<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{int(datos['Horas'].sum())}</b><br><span style='font-size:12px;color:{_TENUE}'>horas</span>",
                       x=0.5, y=0.5, showarrow=False, font=dict(size=28, color=_TEXTO))
    fig.update_layout(showlegend=True, legend=dict(font=dict(size=11, color=_TENUE), orientation="h",
                                                  yanchor="top", y=-0.02, x=0.5, xanchor="center"))
    return _tema(fig, 340, dict(t=8, b=60, l=8, r=8)).update_layout(showlegend=True)
