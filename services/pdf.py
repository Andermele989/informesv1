"""Informe en PDF (A4): indicadores, comparación, análisis de la IA, gráficos y detalle.

Los gráficos se dibujan directamente con fpdf2: no dependen de Chrome ni de kaleido, son
rápidos y se ven igual en cualquier servidor.
"""
import math
import re
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from fpdf import FPDF
from fpdf.fonts import FontFace

from services.metricas import Resumen, numero

NAVY, SLATE, MUTED = (15, 23, 42), (51, 65, 85), (100, 116, 139)
MINT, SKY, VIOLET = (16, 185, 129), (14, 165, 233), (124, 92, 246)
PANEL, LINEA = (241, 245, 249), (226, 232, 240)
VERDE, ROJO = (5, 150, 105), (220, 38, 38)
PALETA = [MINT, SKY, VIOLET, (245, 158, 11), (244, 63, 94), (6, 182, 212), (132, 204, 22), (217, 70, 239)]

ANCHO = 180  # ancho útil (A4 con márgenes de 15 mm)

_REEMPLAZOS = {
    "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "‚": "'",
    "—": "-", "–": "-", "―": "-", "•": "-", "…": "...", "™": "TM",
    "→": "->", "≥": ">=", "≤": "<=", " ": " ",
}


def limpiar(texto) -> str:
    """Deja solo caracteres que la fuente base (latin-1) puede dibujar."""
    t = "" if texto is None else str(texto)
    for k, v in _REEMPLAZOS.items():
        t = t.replace(k, v)
    return t.encode("latin-1", "ignore").decode("latin-1")


def _markdown_inline(texto: str) -> str:
    """Conserva **negrita** (la entiende fpdf2) y quita el resto de la sintaxis markdown."""
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", texto)           # [texto](url) -> texto
    t = re.sub(r"(?<!\*)\*(?!\*)([^*]+)(?<!\*)\*(?!\*)", r"\1", t)  # *cursiva* -> cursiva
    t = t.replace("`", "").replace("__", "")
    return limpiar(t)


@dataclass
class DatosInforme:
    periodo: str
    ambito: str
    modelo_ia: str
    actual: Resumen
    esperados: int
    analisis: str
    anterior: Resumen | None = None
    mes_anterior: str | None = None   # texto legible, p. ej. "Septiembre 2026"
    por_grupo: pd.DataFrame | None = None     # Grupo, Informes, Activos, Horas, Cursos
    serie: pd.DataFrame | None = None         # Mes, Horas
    ranking: pd.DataFrame | None = None       # Publicador, Horas
    precursores: pd.DataFrame | None = None   # Publicador, Horas
    distribucion: pd.DataFrame | None = None  # Publicador, Horas
    detalle: pd.DataFrame | None = None       # Publicador, Grupo, Privilegios, Horas, Cursos Bíblicos, Informe
    titulo: str = "Informe mensual de servicio"
    generado: datetime = field(default_factory=datetime.now)


def _paso_agradable(maximo: float, divisiones: int = 4) -> float:
    """Paso de eje "redondo" (1, 2, 5 x 10^n) para que `divisiones` pasos cubran `maximo`."""
    base = 10 ** (len(str(int(max(maximo, 1)))) - 2) if maximo >= 10 else 1
    for mult in (1, 2, 2.5, 5, 10, 20, 25, 50, 100):
        if base * mult * divisiones >= maximo:
            return base * mult
    return base * 100


def _anillo(cx: float, cy: float, r_ext: float, r_int: float, ang0: float, ang1: float) -> list[tuple[float, float]]:
    """Puntos de un sector de anillo (grados, 0 = derecha, positivo = horario en pantalla)."""
    pasos = max(2, int(abs(ang1 - ang0) / 3))
    angulos = [ang0 + (ang1 - ang0) * k / pasos for k in range(pasos + 1)]
    exterior = [(cx + r_ext * math.cos(math.radians(a)), cy + r_ext * math.sin(math.radians(a))) for a in angulos]
    interior = [(cx + r_int * math.cos(math.radians(a)), cy + r_int * math.sin(math.radians(a))) for a in reversed(angulos)]
    return exterior + interior


def _delta(actual: float, anterior: float | None) -> tuple[str, tuple[int, int, int]] | None:
    if anterior is None or not anterior:
        return None
    cambio = (actual - anterior) / anterior * 100
    if round(cambio) == 0:
        return "= igual", MUTED
    return f"{cambio:+.0f}%", VERDE if cambio > 0 else ROJO


class InformePDF(FPDF):
    def __init__(self, datos: DatosInforme):
        super().__init__(format="A4")
        self.d = datos
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(True, margin=18)
        self.alias_nb_pages()
        self.set_title(limpiar(datos.titulo))
        self.set_author("Sistema de Informes")

    # -- Cabecera y pie ---------------------------------------------------
    def header(self):
        if self.page_no() == 1:
            self.set_fill_color(*NAVY)
            self.rect(0, 0, 210, 36, "F")
            self.set_fill_color(*MINT)
            self.rect(0, 36, 105, 1.4, "F")
            self.set_fill_color(*SKY)
            self.rect(105, 36, 105, 1.4, "F")
            self.set_text_color(255, 255, 255)
            self.set_xy(15, 10)
            self.set_font("Helvetica", "B", 20)
            self.cell(ANCHO, 9, limpiar(self.d.titulo), new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 10.5)
            self.set_text_color(186, 200, 220)
            self.cell(ANCHO, 6, limpiar(f"{self.d.periodo}  |  {self.d.ambito}"), new_x="LMARGIN", new_y="NEXT")
            self.set_y(44)
        else:
            self.set_font("Helvetica", "B", 8.5)
            self.set_text_color(*MUTED)
            self.set_xy(15, 9)
            self.cell(ANCHO / 2, 5, limpiar(self.d.titulo))
            self.set_font("Helvetica", "", 8.5)
            self.cell(ANCHO / 2, 5, limpiar(f"{self.d.periodo}  |  {self.d.ambito}"), align="R")
            self.set_draw_color(*LINEA)
            self.line(15, 15, 195, 15)
            self.set_y(21)

    def footer(self):
        self.set_y(-13)
        self.set_draw_color(*LINEA)
        self.line(15, self.get_y(), 195, self.get_y())
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(ANCHO / 2, 8, f"Generado el {self.d.generado:%d/%m/%Y %H:%M}")
        self.cell(ANCHO / 2, 8, f"Página {self.page_no()}/{{nb}}", align="R")

    # -- Utilidades -------------------------------------------------------
    def _asegurar(self, alto: float) -> None:
        if self.will_page_break(alto):
            self.add_page()

    def _seccion(self, texto: str) -> None:
        self._asegurar(16)
        self.ln(4)
        y = self.get_y()
        self.set_fill_color(*MINT)
        self.rect(15, y + 0.9, 1.6, 5.2, "F")
        self.set_xy(19, y)
        self.set_font("Helvetica", "B", 12.5)
        self.set_text_color(*NAVY)
        self.cell(0, 7, limpiar(texto), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def _recortar(self, texto: str, ancho: float) -> str:
        texto = limpiar(texto)
        while len(texto) > 1 and self.get_string_width(texto) > ancho:
            texto = texto[:-2] + "."
        return texto

    def _tabla(self, encabezados, filas, anchos, alineacion) -> None:
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*SLATE)
        self.set_draw_color(*LINEA)
        self.set_fill_color(255, 255, 255)
        with self.table(
            col_widths=anchos, text_align=alineacion, width=ANCHO, line_height=6, padding=1.2,
            headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=NAVY, size_pt=8.5),
            cell_fill_color=(248, 250, 252), cell_fill_mode="EVEN_ROWS", borders_layout="HORIZONTAL_LINES",
        ) as tabla:
            tabla.row([limpiar(h) for h in encabezados])
            for fila in filas:
                tabla.row([limpiar(c) for c in fila])
        self.ln(2)

    # -- Bloques ----------------------------------------------------------
    def _indicadores(self) -> None:
        a, p = self.d.actual, self.d.anterior
        cobertura = a.informes / self.d.esperados * 100 if self.d.esperados else 0
        tarjetas = [
            ("INFORMES", numero(a.informes), f"de {numero(self.d.esperados)} esperados ({cobertura:.0f}%)",
             _delta(a.informes, p.informes if p else None), MINT),
            ("HORAS", numero(a.horas), f"promedio {numero(a.promedio_horas, 1)} h por informe",
             _delta(a.horas, p.horas if p else None), SKY),
            ("CURSOS BÍBLICOS", numero(a.cursos), f"promedio {numero(a.promedio_cursos, 1)} por informe",
             _delta(a.cursos, p.cursos if p else None), VIOLET),
            ("CON ACTIVIDAD", f"{a.con_actividad_pct:.0f}%", f"{numero(a.sin_actividad)} sin actividad", None, (245, 158, 11)),
        ]
        ancho, hueco, alto = (ANCHO - 3 * 4) / 4, 4, 27
        y = self.get_y()
        for i, (etiqueta, valor, sub, delta, color) in enumerate(tarjetas):
            x = 15 + i * (ancho + hueco)
            self.set_fill_color(*PANEL)
            self.rect(x, y, ancho, alto, "F", round_corners=True, corner_radius=2)
            self.set_fill_color(*color)
            self.rect(x, y + 3, 1.3, alto - 6, "F")
            self.set_xy(x + 4, y + 3)
            self.set_font("Helvetica", "B", 6.8)
            self.set_text_color(*MUTED)
            self.cell(ancho - 6, 4, etiqueta)
            self.set_xy(x + 4, y + 8)
            self.set_font("Helvetica", "B", 19)
            self.set_text_color(*NAVY)
            self.cell(ancho - 20 if delta else ancho - 6, 9, limpiar(valor))
            if delta:
                self.set_xy(x + ancho - 17, y + 10)
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*delta[1])
                self.cell(14, 6, delta[0], align="R")
            self.set_xy(x + 4, y + 19)
            self.set_font("Helvetica", "", 6.8)
            self.set_text_color(*MUTED)
            self.cell(ancho - 6, 4, self._recortar(sub, ancho - 6))
        self.set_y(y + alto + 2)

    def _comparativa(self) -> None:
        p = self.d.anterior
        if not p or not p.informes:
            return
        a = self.d.actual
        self._seccion(f"Comparación con {self.d.mes_anterior}")
        filas = []
        for nombre, ant, act in (("Informes recibidos", p.informes, a.informes), ("Horas de predicación", p.horas, a.horas),
                                 ("Cursos bíblicos", p.cursos, a.cursos)):
            delta = _delta(act, ant)
            filas.append((nombre, numero(ant), numero(act), delta[0] if delta else "-"))
        self._tabla(("Indicador", "Mes anterior", "Mes actual", "Variación"), filas, (66, 38, 38, 38),
                    ("LEFT", "CENTER", "CENTER", "CENTER"))

    def _por_grupo(self) -> None:
        g = self.d.por_grupo
        if g is None or len(g) < 2:
            return
        self._seccion("Resumen por grupo")
        filas = [(r["Grupo"], numero(r["Informes"]), numero(r["Activos"]), numero(r["Horas"]), numero(r["Cursos"]))
                 for r in g.to_dict("records")]
        self._tabla(("Grupo", "Informes", "Con actividad", "Horas", "Cursos"), filas, (54, 28, 38, 30, 30),
                    ("LEFT", "CENTER", "CENTER", "CENTER", "CENTER"))

    def _analisis(self) -> None:
        self._seccion(f"Análisis ({limpiar(self.d.modelo_ia)})")
        for linea in self.d.analisis.splitlines():
            s = linea.strip()
            if not s or set(s) <= {"-", "*", "_"}:
                self.ln(1.5)
                continue
            if s.startswith("#"):
                self._asegurar(30)  # el título nunca queda solo al final de una página
                self.ln(2.5)
                self.set_font("Helvetica", "B", 10.5)
                self.set_text_color(*NAVY)
                self.multi_cell(ANCHO, 5.5, _markdown_inline(s.lstrip("#").strip().replace("**", "")),
                                new_x="LMARGIN", new_y="NEXT")
                self.ln(0.8)
                continue
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*SLATE)
            m = re.match(r"^([-*•]|\d+[.)])\s+(.*)", s)
            if m:
                self._asegurar(8)
                y = self.get_y()
                if m.group(1)[0].isdigit():
                    self.set_font("Helvetica", "B", 9)
                    self.cell(6, 4.8, m.group(1))
                    self.set_font("Helvetica", "", 9)
                else:
                    self.set_fill_color(*MINT)
                    self.circle(18.2, y + 2.4, 1.1, style="F")
                self.set_xy(15 + 6, y)
                self.multi_cell(ANCHO - 6, 4.8, _markdown_inline(m.group(2)), markdown=True,
                                new_x="LMARGIN", new_y="NEXT")
                self.ln(0.6)
            else:
                self.multi_cell(ANCHO, 4.8, _markdown_inline(s), markdown=True, new_x="LMARGIN", new_y="NEXT")
                self.ln(0.6)

    # -- Gráficos nativos -------------------------------------------------
    def _titulo_grafico(self, texto: str) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*NAVY)
        self.cell(ANCHO, 6, limpiar(texto), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def _barras(self, titulo: str, filas: list[tuple[str, float]], color, sufijo: str = " h", max_filas: int = 12) -> None:
        if not filas:
            return
        extra = len(filas) - max_filas
        filas = filas[:max_filas]
        alto_fila = 6.4
        self._asegurar(10 + alto_fila * len(filas) + (6 if extra > 0 else 0))
        self._titulo_grafico(titulo)
        etiqueta_w, barra_w = 52, 100
        maximo = max(v for _, v in filas) or 1
        self.set_font("Helvetica", "", 8.5)
        for nombre, valor in filas:
            y = self.get_y()
            self.set_text_color(*SLATE)
            self.set_xy(15, y)
            self.cell(etiqueta_w, alto_fila, self._recortar(nombre, etiqueta_w - 2))
            self.set_fill_color(*PANEL)
            self.rect(15 + etiqueta_w, y + 1.4, barra_w, 4.2, "F", round_corners=True, corner_radius=1.2)
            self.set_fill_color(*color)
            self.rect(15 + etiqueta_w, y + 1.4, max(1.5, barra_w * valor / maximo), 4.2, "F", round_corners=True, corner_radius=1.2)
            self.set_xy(15 + etiqueta_w + barra_w + 2, y)
            self.set_font("Helvetica", "B", 8.5)
            self.cell(24, alto_fila, f"{numero(valor)}{sufijo}")
            self.set_font("Helvetica", "", 8.5)
            self.set_y(y + alto_fila)
        if extra > 0:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*MUTED)
            self.cell(ANCHO, 5, f"+ {extra} más (ver detalle)", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def _linea(self, titulo: str, puntos: list[tuple[str, float]]) -> None:
        if not puntos:
            return
        alto = 52
        self._asegurar(alto + 16)
        self._titulo_grafico(titulo)
        x0, y0, w, h = 28, self.get_y() + 3, ANCHO - 20, alto - 14
        paso = _paso_agradable(max(v for _, v in puntos) * 1.1)
        maximo = paso * 4
        self.set_draw_color(*LINEA)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        for i in range(5):
            yy = y0 + h - h * i / 4
            self.line(x0, yy, x0 + w, yy)
            self.set_xy(15, yy - 2)
            self.cell(11, 4, numero(paso * i), align="R")
        n = len(puntos)
        xs = [x0 + w / 2 if n == 1 else x0 + 6 + (w - 12) * i / (n - 1) for i in range(n)]
        ys = [y0 + h - h * v / maximo for _, v in puntos]
        if n > 1:
            with self.local_context(fill_opacity=0.14):
                self.set_fill_color(*SKY)
                self.polygon([(xs[0], y0 + h), *zip(xs, ys, strict=True), (xs[-1], y0 + h)], style="F")
            self.set_draw_color(*SKY)
            self.set_line_width(0.8)
            self.polyline(list(zip(xs, ys, strict=True)), style="D")
            self.set_line_width(0.2)
        for (mes, valor), x, y in zip(puntos, xs, ys, strict=True):
            self.set_fill_color(255, 255, 255)
            self.set_draw_color(*SKY)
            self.set_line_width(0.7)
            self.circle(x, y, 1.3, style="DF")
            self.set_line_width(0.2)
            self.set_font("Helvetica", "B", 7.5)
            self.set_text_color(*NAVY)
            self.set_xy(x - 10, y - 6)
            self.cell(20, 4, numero(valor), align="C")
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*MUTED)
            self.set_xy(x - 10, y0 + h + 2)
            self.cell(20, 4, mes, align="C")
        self.set_y(y0 + h + 10)

    def _dona(self, titulo: str, filas: list[tuple[str, float]]) -> None:
        if not filas:
            return
        top = filas[:7]
        if len(filas) > 7:
            top.append(("Otros", sum(v for _, v in filas[7:])))
        total = sum(v for _, v in top) or 1
        alto = 66
        self._asegurar(alto + 12)
        self._titulo_grafico(titulo)
        cx, cy, radio = 15 + 32, self.get_y() + 32, 29
        inicio = -90.0  # las 12 en punto, en sentido horario
        for i, (_, valor) in enumerate(top):
            barrido = 360.0 * valor / total
            self.set_fill_color(*PALETA[i % len(PALETA)])
            self.polygon(_anillo(cx, cy, radio, radio * 0.6, inicio, inicio + min(barrido, 359.9)), style="F")
            inicio += barrido
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*NAVY)
        self.set_xy(cx - 20, cy - 7)
        self.cell(40, 8, numero(total), align="C")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.set_xy(cx - 20, cy + 1)
        self.cell(40, 5, "horas", align="C")
        for i, (nombre, valor) in enumerate(top):
            y = cy - 28 + i * 7.5
            self.set_fill_color(*PALETA[i % len(PALETA)])
            self.rect(85, y + 1.2, 3.6, 3.6, "F", round_corners=True, corner_radius=0.8)
            self.set_xy(91, y)
            self.set_font("Helvetica", "", 8.5)
            self.set_text_color(*SLATE)
            self.cell(62, 6, self._recortar(nombre, 60))
            self.set_font("Helvetica", "B", 8.5)
            self.cell(38, 6, f"{numero(valor)} h  ({valor / total * 100:.0f}%)", align="R")
        self.set_y(cy + radio + 6)

    def _graficos(self) -> None:
        d = self.d
        hay = any(x is not None and len(x) for x in (d.ranking, d.serie, d.precursores, d.distribucion))
        if not hay:
            return
        self._seccion("Gráficos")
        if d.ranking is not None:
            self._barras("Horas por publicador", [(r["Publicador"], r["Horas"]) for r in d.ranking.to_dict("records")], MINT, max_filas=10)
        if d.serie is not None:
            self._linea("Evolución de horas por mes", [(r["Mes"], r["Horas"]) for r in d.serie.to_dict("records")])
        if d.precursores is not None:
            self._barras("Horas de precursores", [(r["Publicador"], r["Horas"]) for r in d.precursores.to_dict("records")], VIOLET)
        if d.distribucion is not None:
            self._dona("Distribución de horas", [(r["Publicador"], r["Horas"]) for r in d.distribucion.to_dict("records")])

    def _detalle(self) -> None:
        det = self.d.detalle
        if det is None or det.empty:
            return
        self._asegurar(60)
        self._seccion("Detalle de informes")
        filas = [(r["Publicador"], r["Grupo"], r["Privilegios"], numero(r["Horas"]) if r["Horas"] else "-",
                  numero(r["Cursos Bíblicos"]) if r["Cursos Bíblicos"] else "-", r["Informe"])
                 for r in det.to_dict("records")]
        self._tabla(("Publicador", "Grupo", "Privilegio", "Horas", "Cursos", "Informe"), filas,
                    (44, 24, 32, 14, 14, 52), ("LEFT", "LEFT", "LEFT", "CENTER", "CENTER", "LEFT"))

    def construir(self) -> None:
        self.add_page()
        self._indicadores()
        self._comparativa()
        self._por_grupo()
        self._analisis()
        self._graficos()
        self._detalle()


def generar_pdf(datos: DatosInforme) -> bytes:
    pdf = InformePDF(datos)
    pdf.construir()
    return bytes(pdf.output())
