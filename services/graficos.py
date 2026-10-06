"""Gráficos Plotly del dashboard: paleta ejecutiva Ámbar / Oro / Naranja estilo Learnio."""
import pandas as pd
import plotly.graph_objects as go

CONFIG = {"displayModeBar": False, "responsive": True}

# Paleta Cálida Ejecutiva (Ámbar, Oro, Naranja, Fuego, Caramelo, Slate)
AMBAR = "#ff9500"
ORO = "#fbbf24"
NARANJA = "#f97316"
FUEGO = "#ea580c"
PALETA = [AMBAR, ORO, NARANJA, FUEGO, "#d97706", "#b45309", "#9a3412", "#c2410c", "#78350f"]
COLOR_OTROS = "#334155"

_FUENTE = "-apple-system, 'SF Pro Display', 'Segoe UI Variable', Inter, system-ui, sans-serif"
_TEXTO, _TENUE, _REJILLA = "#ffffff", "#8492a6", "rgba(255,255,255,0.07)"


def nombre_corto(nombre, limite: int = 16) -> str:
    nombre = str(nombre or "")
    return nombre if len(nombre) <= limite else f"{nombre[:limite - 1]}…"


def _tema(fig: go.Figure, alto: int, margen: dict | None = None) -> go.Figure:
    fig.update_layout(
        height=alto, showlegend=False, bargap=0.36,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FUENTE, size=12, color=_TEXTO),
        margin=margen or dict(t=12, b=36, l=40, r=12),
        hoverlabel=dict(bgcolor="#161822", bordercolor="rgba(255,149,0,0.35)", font=dict(family=_FUENTE, color="#ffffff")),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, tickfont=dict(size=11, color=_TENUE), title="")
    fig.update_yaxes(gridcolor=_REJILLA, griddash="dot", zeroline=False, showline=False,
                     tickfont=dict(size=11, color=_TENUE), title="")
    return fig


def _degradado(n: int, inicio: tuple[int, int, int] = (255, 149, 0), fin: tuple[int, int, int] = (234, 88, 12)) -> list[str]:
    """`n` colores desde `inicio` hasta `fin` (RGB)."""
    def mezcla(i: int) -> str:
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
        marker=dict(
            color=_degradado(len(datos), (255, 149, 0), (234, 88, 12)),
            cornerradius=8,
            line=dict(width=0),
        ),
        text=datos["Horas"], textposition="outside", textfont=dict(size=12, color=_TEXTO, family=_FUENTE), cliponaxis=False,
        hovertemplate="<b>%{customdata}</b><br>%{y} horas<extra></extra>",
    ))
    fig.update_xaxes(tickangle=-30 if len(datos) > 6 else 0)
    fig.update_yaxes(range=[0, datos["Horas"].max() * 1.2])
    return _tema(fig, 320, dict(t=24, b=64, l=36, r=8))


def evolucion_mensual(df_activos: pd.DataFrame) -> go.Figure | None:
    """Gráfico de evolución con spline suave y relleno de gradiente dorado (estilo Enrolment Activity)."""
    if df_activos.empty:
        return None
    serie = df_activos.groupby("Mes", as_index=False)["Horas"].sum().sort_values("Mes")
    fig = go.Figure(go.Scatter(
        x=serie["Mes"], y=serie["Horas"], mode="lines+markers+text",
        text=serie["Horas"], textposition="top center", textfont=dict(size=11, color=_TEXTO, family=_FUENTE),
        line=dict(color=AMBAR, width=3, shape="spline", smoothing=0.65),
        fill="tozeroy",
        fillgradient=dict(type="vertical", colorscale=[[0, "rgba(255,149,0,0)"], [1, "rgba(255,149,0,0.38)"]]),
        marker=dict(size=8, color="#0b0c10", line=dict(width=2.5, color=AMBAR)),
        hovertemplate="<b>%{x}</b><br>%{y} horas<extra></extra>",
    ))
    fig.update_xaxes(type="category", range=[-0.35, len(serie) - 0.65])
    fig.update_yaxes(range=[0, max(serie["Horas"].max(), 1) * 1.25])
    return _tema(fig, 320)


def precursores(df_precursores: pd.DataFrame) -> go.Figure | None:
    if df_precursores.empty:
        return None
    datos = df_precursores.groupby("Publicador", as_index=False)["Horas"].sum().sort_values("Horas")
    fig = go.Figure(go.Bar(
        y=datos["Publicador"].map(lambda n: nombre_corto(n, 20)), x=datos["Horas"], orientation="h",
        customdata=datos["Publicador"],
        marker=dict(
            color=_degradado(len(datos), (251, 191, 36), (249, 115, 22)),
            cornerradius=8,
            line=dict(width=0),
        ),
        text=[f"{h} h" for h in datos["Horas"]], textposition="outside", textfont=dict(size=12, color=_TEXTO, family=_FUENTE),
        cliponaxis=False, hovertemplate="<b>%{customdata}</b><br>%{x} horas<extra></extra>",
    ))
    fig.update_xaxes(range=[0, max(datos["Horas"].max(), 1) * 1.22], showgrid=True, gridcolor=_REJILLA, griddash="dot")
    fig.update_yaxes(showgrid=False, tickfont=dict(size=12, color=_TEXTO))
    return _tema(fig, max(300, len(datos) * 40 + 54), dict(t=6, b=28, l=8, r=34))


def distribucion_filas(df_activos: pd.DataFrame, maximo: int = 6) -> list[tuple[str, int, float, str]]:
    """`(nombre, horas, porcentaje, color)` de los que más horas aportan; el resto se agrupa en «Otros»."""
    datos = (df_activos[df_activos["Horas"] > 0].groupby("Publicador", as_index=False)["Horas"].sum()
             .sort_values("Horas", ascending=False))
    total = datos["Horas"].sum()
    if not total:
        return []
    filas = [(r["Publicador"], int(r["Horas"])) for r in datos.head(maximo).to_dict("records")]
    resto = int(datos["Horas"].iloc[maximo:].sum())
    if resto:
        filas.append(("Otros", resto))
    return [(n, h, h / total * 100, COLOR_OTROS if n == "Otros" else PALETA[i % len(PALETA)])
            for i, (n, h) in enumerate(filas)]


def distribucion(filas: list[tuple[str, int, float, str]]) -> go.Figure | None:
    """Dona estilo Learnio con el total en el centro y borde elegante."""
    if not filas:
        return None
    total = sum(h for _, h, _, _ in filas)
    fig = go.Figure(go.Pie(
        labels=[f[0] for f in filas], values=[f[1] for f in filas], hole=0.64, sort=False, rotation=90,
        direction="clockwise", textinfo="none",
        marker=dict(colors=[f[3] for f in filas], line=dict(color="#090a0f", width=3)),
        hovertemplate="<b>%{label}</b><br>%{value} horas · %{percent}<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{total}</b>", x=0.5, y=0.55, showarrow=False, font=dict(size=30, color="#ffffff", family=_FUENTE))
    fig.add_annotation(text="horas", x=0.5, y=0.40, showarrow=False, font=dict(size=12, color=_TENUE, family=_FUENTE))
    return _tema(fig, 300, dict(t=4, b=4, l=4, r=4))
