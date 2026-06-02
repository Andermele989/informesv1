import os
# pyrefly: ignore [missing-import]
import streamlit as st

def cargar_estilos_responsivos(es_login=False):
    """
    Carga e inyecta de forma centralizada el archivo responsive.css en la página actual.
    
    Parámetros:
    - es_login (bool): Si es True, añade la clase helper de Login y estilos específicos del login.
    """
    # Obtener la ruta absoluta de responsive.css relativa a este archivo
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_css = os.path.join(directorio_actual, "responsive.css")
    
    try:
        with open(ruta_css, "r", encoding="utf-8") as f:
            css_content = f.read()
            
        # Inyectar el CSS
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        
        # Si es página de Login, aplicar configuraciones extras para ocultar elementos de navegación nativos
        if es_login:
            st.markdown("""
            <style>
            /* Ocultar barra lateral en login */
            section[data-testid="stSidebar"] { display: none !important; }
            button[kind="header"] { display: none !important; }
            header[data-testid="stHeader"] { background: transparent !important; }
            </style>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        # Fallback silencioso o advertencia discreta si no encuentra el archivo durante el arranque
        st.error(f"⚠️ Error al cargar los estilos responsivos: {e}")
