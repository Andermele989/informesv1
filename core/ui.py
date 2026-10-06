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


def icono(nombre: str) -> str:
    """HTML de un icono Material (la fuente ya la carga Streamlit)."""
    return f'<i class="mi">{sanitize_text(nombre)}</i>'


def encabezado(
    titulo: str,
    subtitulo: str = "",
    insignias: tuple[tuple[str, str], ...] = (),
    etiqueta: str = "",
) -> None:
    """Cabecera de página: título y subtítulo a la izquierda, datos del filtro a la derecha."""
    lista_chips = list(insignias)
    if etiqueta:
        lista_chips.insert(0, ("", etiqueta))
    chips = "".join(
        f'<span class="chip">{"<b>" + sanitize_text(rotulo) + "</b> " if rotulo else ""}{sanitize_text(valor)}</span>'
        for rotulo, valor in lista_chips
    )
    html(
        f'''<div class="page-head"><div>
        <h1>{sanitize_text(titulo)}</h1>
        {f'<p>{sanitize_text(subtitulo)}</p>' if subtitulo else ''}
        </div>{f'<div class="chips">{chips}</div>' if chips else ''}</div>'''
    )


def titulo_tarjeta(titulo: str, detalle: str = "") -> None:
    """Título de una tarjeta con su subtítulo debajo."""
    html(f'<div class="card-head"><b>{sanitize_text(titulo)}</b>'
         f'{f"<span>{sanitize_text(detalle)}</span>" if detalle else ""}</div>')


def _barras(serie: list[float]) -> str:
    """Mini gráfico de barras (la última barra, la del periodo actual, resalta)."""
    if not serie:
        return ""
    maximo = max(serie) or 1
    ultima = len(serie) - 1
    barras = "".join(
        '<span{} style="height:{:.0f}%"></span>'.format(' class="on"' if i == ultima else "", max(10, v / maximo * 100))
        for i, v in enumerate(serie)
    )
    return f'<div class="spark" aria-hidden="true">{barras}</div>'


def tarjeta_metrica(etiqueta: str, valor: str, color: str, icono_material: str, nota: str = "",
                    delta: tuple[str, str] = ("", ""), serie: list[float] | None = None) -> str:
    """HTML de un indicador. `color`: amber | orange | gold | flame. `serie`: valores recientes para las mini-barras."""
    texto_delta, clase_delta = delta
    linea_delta = (f'<span class="kpi-delta"><b class="{clase_delta}">{sanitize_text(texto_delta)}</b> vs mes anterior</span>'
                   if texto_delta else "")
    return (
        f'<div class="kpi tone-{color}"><div class="kpi-label">{sanitize_text(etiqueta)}</div>'
        f'<div class="kpi-main"><span class="chip-icon">{icono(icono_material)}</span>'
        f'<span class="kpi-value">{sanitize_text(valor)}</span></div>{_barras(serie or [])}'
        f'<div class="kpi-foot">{linea_delta}<span class="kpi-note">{sanitize_text(nota)}</span></div></div>'
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
