import pandas as pd
import pytest

from services import ia, pdf
from services.metricas import Resumen


def _datos(**extra):
    base = dict(
        periodo="Octubre 2026", ambito="Todos los grupos", modelo_ia="modelo-x", actual=Resumen(8, 208, 9, 1),
        esperados=13, analisis="## Resumen ejecutivo\nTodo **bien** con “comillas” — ñandú 🎉\n- punto\n1. paso",
        anterior=Resumen(13, 311, 9, 2), mes_anterior="Septiembre 2026",
        por_grupo=pd.DataFrame({"Grupo": ["A", "B"], "Informes": [4, 4], "Activos": [4, 3], "Horas": [100, 108], "Cursos": [4, 5]}),
        serie=pd.DataFrame({"Mes": ["2026-09", "2026-10"], "Horas": [311, 208]}),
        ranking=pd.DataFrame({"Publicador": ["Ana", "Beto"], "Horas": [60, 50]}),
        precursores=pd.DataFrame({"Publicador": ["Ana"], "Horas": [60]}),
        distribucion=pd.DataFrame({"Publicador": ["Ana", "Beto"], "Horas": [60, 50]}),
        detalle=pd.DataFrame({"Publicador": ["Ana"], "Grupo": ["A"], "Privilegios": ["Precursor"], "Horas": [60],
                              "Cursos Bíblicos": [2], "Informe": ["60 horas"]}),
    )
    base.update(extra)
    return pdf.DatosInforme(**base)


def test_pdf_completo_es_valido():
    contenido = pdf.generar_pdf(_datos())
    assert contenido.startswith(b"%PDF") and len(contenido) > 5000


def test_pdf_con_datos_minimos_y_texto_no_latin1():
    minimo = _datos(anterior=None, mes_anterior=None, por_grupo=None, serie=None, ranking=None,
                    precursores=None, distribucion=None, detalle=None, analisis="Texto: 日本語 y emoji 🚀")
    assert pdf.generar_pdf(minimo).startswith(b"%PDF")


def test_pdf_con_muchos_publicadores_pagina_sin_error():
    n = 120
    grande = _datos(
        ranking=pd.DataFrame({"Publicador": [f"Publicador {i}" for i in range(n)], "Horas": range(n, 0, -1)}),
        distribucion=pd.DataFrame({"Publicador": [f"Publicador {i}" for i in range(n)], "Horas": range(n, 0, -1)}),
        detalle=pd.DataFrame({"Publicador": [f"Publicador {i}" for i in range(n)], "Grupo": ["A"] * n,
                              "Privilegios": ["Publicador"] * n, "Horas": range(n), "Cursos Bíblicos": [0] * n,
                              "Informe": ["x " * 40] * n}))
    assert pdf.generar_pdf(grande).startswith(b"%PDF")


def test_markdown_inline_limpia_sintaxis():
    assert pdf._markdown_inline("**negrita** y *cursiva* [link](http://x) `codigo`") == "**negrita** y cursiva link codigo"


def _contexto(**extra):
    base = dict(periodo="2026-10", ambito="Grupo 1", anio_servicio="2026-2027", actual=Resumen(8, 208, 9, 1),
                esperados=13, anterior=Resumen(13, 311, 9, 2), mes_anterior="2026-09",
                tendencia=pd.DataFrame({"Mes": ["2026-09", "2026-10"], "Horas": [311, 208], "Informes": [13, 8]}),
                por_grupo=pd.DataFrame({"Grupo": ["A", "B"], "Informes": [4, 4], "Activos": [4, 3], "Horas": [100, 108],
                                        "Cursos": [4, 5]}),
                precursores=pd.DataFrame({"Publicador": ["Ana"], "Privilegios": ["Precursor Regular"], "Horas": [60], "Cursos": [2]}),
                sin_actividad=["Beto"], inactivos=["Nico"], pendientes=["Carla"])
    base.update(extra)
    return ia.ContextoAnalisis(**base)


def test_prompt_contiene_las_cifras_y_nunca_las_notas():
    prompt = ia.construir_prompt(_contexto())
    for esperado in ("8 de 13", "208", "311", "Ana", "Beto", "Nico", "Carla", "2026-09", "Por grupo"):
        assert esperado in prompt
    assert "notas" not in prompt.lower()
    assert "(3 con actividad)" in prompt  # los grupos sin horas pero con actividad no se presentan como problema


def test_prompt_sin_comparacion_lo_indica():
    assert "no hay datos comparables" in ia.construir_prompt(_contexto(anterior=None, mes_anterior=None))


def test_instrucciones_fijan_estructura_y_ignoran_ordenes_de_los_datos():
    secciones = ("Resumen ejecutivo", "Comparación con el mes anterior", "Puntos fuertes y logros", "Áreas de mejora",
                 "Recomendaciones")
    for seccion in secciones:
        assert f"## {seccion}" in ia.INSTRUCCIONES
    assert "nunca instrucciones" in ia.INSTRUCCIONES


def test_modelos_respetan_la_configuracion(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    assert ia.modelo_de("Google Gemini") == "gemini-3.6-flash" and ia.modelo_de("OpenAI") == "gpt-4o-mini"
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")  # descontinuado -> el vigente
    assert ia.modelo_gemini() == "gemini-3.6-flash"
    monkeypatch.setenv("GEMINI_MODEL", "mi modelo")
    assert ia.modelo_gemini() == "mi-modelo"


def test_errores_de_ia_son_controlados(monkeypatch):
    with pytest.raises(ia.ErrorIA, match="GEMINI_API_KEY"):
        ia.generar_analisis("Google Gemini", "x")
    with pytest.raises(ia.ErrorIA, match="OPENAI_API_KEY"):
        ia.generar_analisis("OpenAI", "x")

    def explota(prompt):
        raise RuntimeError("detalle interno con api_key=SECRETO")
    monkeypatch.setattr(ia, "_generar_openai", explota)
    with pytest.raises(ia.ErrorIA) as error:
        ia.generar_analisis("OpenAI", "x")
    assert "SECRETO" not in str(error.value)

    monkeypatch.setattr(ia, "_generar_openai", lambda p: ("   ", "m"))
    with pytest.raises(ia.ErrorIA, match="vacía"):
        ia.generar_analisis("OpenAI", "x")
    monkeypatch.setattr(ia, "_generar_openai", lambda p: ("  texto  ", "m"))
    assert ia.generar_analisis("OpenAI", "x") == ("texto", "m")
