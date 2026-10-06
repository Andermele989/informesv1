"""Componentes de interfaz compartidos: estilos, cabeceras, tarjetas y perfil lateral."""
import os

import streamlit as st

from core import VERSION, auth
from core.database import RAIZ_PROYECTO
from core.security import sanitize_text

_RUTA_CSS = os.path.join(RAIZ_PROYECTO, "assets", "styles.css")


@st.cache_data(show_spinner=False)
def _leer_css(modificado: float) -> str:  # `modificado` solo sirve como clave de caché
    with open(_RUTA_CSS, encoding="utf-8") as f:
        return f.read()


def inyectar_estilos() -> None:
    """Inyecta `assets/styles.css`, la única hoja de estilos de la app."""
    st.markdown(f"<style>{_leer_css(os.path.getmtime(_RUTA_CSS))}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Avisos que sobreviven a un `st.rerun()`
# ---------------------------------------------------------------------------

def avisar(mensaje: str, icono: str = "✅") -> None:
    """Programa un aviso para la siguiente ejecución (un mensaje antes de `st.rerun()` se pierde)."""
    st.session_state["_aviso"] = (mensaje, icono)


def mostrar_aviso() -> None:
    aviso = st.session_state.pop("_aviso", None)
    if aviso:
        st.toast(aviso[0], icon=aviso[1])


# ---------------------------------------------------------------------------
# Bloques visuales
# ---------------------------------------------------------------------------

def html(texto: str) -> None:
    """Renderiza HTML propio. Markdown corta los bloques HTML en las líneas en blanco y trata
    como código lo indentado, así que el texto se compacta en una sola línea."""
    st.markdown(" ".join(linea.strip() for linea in texto.splitlines() if linea.strip()), unsafe_allow_html=True)


def encabezado(titulo: str, subtitulo: str = "", etiqueta: str = "", insignias: tuple[tuple[str, str], ...] = ()) -> None:
    """Cabecera de página. `insignias` es una serie de `(icono_texto, valor)`."""
    chips = "".join(
        f'<span class="chip">{sanitize_text(rotulo)} <b>{sanitize_text(valor)}</b></span>' for rotulo, valor in insignias
    )
    html(
        f'''<div class="app-header">
        {f'<span class="eyebrow">{sanitize_text(etiqueta)}</span>' if etiqueta else ''}
        <h1>{sanitize_text(titulo)}</h1>
        {f'<p>{sanitize_text(subtitulo)}</p>' if subtitulo else ''}
        {f'<div class="chips">{chips}</div>' if chips else ''}
        </div>'''
    )


def titulo_tarjeta(titulo: str, detalle: str = "") -> None:
    st.markdown(
        f'<div class="card-title">{sanitize_text(titulo)}'
        f'{f"<span>{sanitize_text(detalle)}</span>" if detalle else ""}</div>',
        unsafe_allow_html=True,
    )


def tarjeta_metrica(etiqueta: str, valor: str, color: str, pie: str = "", delta: tuple[str, str] = ("", ""),
                    progreso: float | None = None) -> str:
    """HTML de una tarjeta de indicador. `color`: mint | sky | violet | amber | rose."""
    barra = ""
    if progreso is not None:
        barra = f'<div class="meter"><span style="width:{max(0, min(100, progreso)):.0f}%"></span></div>'
    texto_delta, clase_delta = delta
    chip_delta = f'<span class="delta {clase_delta}">{sanitize_text(texto_delta)}</span>' if texto_delta else ""
    return (
        f'<div class="metric-card tone-{color}"><div class="metric-top"><span class="metric-label">'
        f'{sanitize_text(etiqueta)}</span>{chip_delta}</div><div class="metric-value">{sanitize_text(valor)}</div>'
        f'{barra}<div class="metric-foot">{sanitize_text(pie)}</div></div>'
    )


def perfil_sidebar() -> None:
    """Perfil del usuario y botón de cerrar sesión, bajo el menú de navegación."""
    usuario = st.session_state.get("username") or "Usuario"
    rol = "Administrador" if st.session_state.get("role") == "admin" else "Usuario"
    st.sidebar.markdown(
        f'<div class="profile"><div class="avatar">{sanitize_text(usuario[:2].upper())}</div>'
        f'<div class="profile-text"><b>{sanitize_text(usuario)}</b><span>{rol}</span></div></div>',
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Cerrar sesión", icon=":material/logout:", key="btn_logout", width="stretch"):
        auth.cerrar_sesion()
    st.sidebar.caption(f"Sistema de Informes · v{VERSION}")
