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
        
        # Aplicar estilos premium de la barra lateral
        aplicar_estilos(es_login=es_login)
        
        # Renderizar el perfil del usuario al final de la barra lateral si está logueado y no es la pantalla de login
        if not es_login and st.session_state.get("logged_in", False):
            mostrar_perfil_sidebar()
            
    except Exception as e:
        # Fallback silencioso o advertencia discreta si no encuentra el archivo durante el arranque
        st.error(f"⚠️ Error al cargar los estilos responsivos: {e}")

def mostrar_perfil_sidebar():
    """Dibuja el perfil del usuario en la parte inferior de la barra lateral."""
    username = st.session_state.get("username", "Usuario")
    role = st.session_state.get("role", "user")
    iniciales = (username[:2]).upper() if username else "US"
    rol_display = "Administrador" if role == "admin" else "Usuario"
    
    st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)
    st.sidebar.markdown(f"""
    <div class="user-profile-container">
        <div class="user-avatar">{iniciales}</div>
        <div class="user-info">
            <div class="user-name">{username}</div>
            <div class="user-role">{rol_display}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Botón de cerrar sesión unificado para todas las páginas
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, key="sidebar_logout_btn"):
        st.session_state.logged_out = True
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.user_id = None
        st.query_params.clear()
        st.rerun()

def aplicar_estilos(es_login: bool = False):
    """Inyecta estilos premium para la barra lateral y la app."""
    
    sidebar_styles = """
    <style>
    /* ─── FUENTE ─────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&display=swap');

    /* ─── VARIABLES GLOBALES ─────────────────────────────── */
    :root {
        --sb-accent:        #00e8a2;
        --sb-accent-dark:   #00c896;
        --sb-active-bg:     rgba(0, 232, 162, 0.09);
        --sb-hover-bg:      rgba(0, 232, 162, 0.04);
        --sb-radius:        10px;
        --sb-transition:    0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ─── RESET FONT EN SIDEBAR (EVITANDO ROMPER ICONOS DE STREAMLIT) ─── */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] a,
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] span:not([class*="Icon"]):not([data-testid="stSidebarNavLinkIcon"]):not(.material-symbols-rounded):not([data-testid="collapsedControl"] *):not([class*="collapsedControl"] *):not([data-testid="stSidebarCollapseButton"] *):not([class*="SidebarCollapseButton"] *) {
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ─── PROTECCIÓN DE ICONOS DE STREAMLIT (EVITA TEXTOS COMO keyboard_double_arrow_right) ─── */
    .material-symbols-rounded,
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stSidebarCollapseButton"] *,
    button[data-testid="collapse-button"],
    button[data-testid="collapse-button"] *,
    [data-testid="collapsedControl"] button,
    [data-testid="collapsedControl"] span,
    button[data-testid="collapsedControl"],
    button[data-testid="collapsedControl"] *,
    html body [data-testid="stAppViewContainer"] [data-testid="collapsedControl"] button,
    html body [data-testid="stAppViewContainer"] [data-testid="collapsedControl"] span,
    html body [data-testid="stAppViewContainer"] button[data-testid="collapsedControl"],
    html body [data-testid="stAppViewContainer"] button[data-testid="collapsedControl"] *,
    html body [data-testid="stAppViewContainer"] [data-testid="stSidebarCollapseButton"] button,
    html body [data-testid="stAppViewContainer"] [data-testid="stSidebarCollapseButton"] span,
    html body [data-testid="stAppViewContainer"] [data-testid="stSidebarCollapseButton"] *,
    section[data-testid="stSidebar"] [data-testid="collapsedControl"] *,
    section[data-testid="stSidebar"] button[data-testid="collapsedControl"] *,
    section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] *,
    [class*="Icon"], 
    [data-testid="stSidebarNavLinkIcon"] {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined" !important;
    }

    /* ─── BARRA LATERAL CONTENEDOR ───────────────────────── */
    section[data-testid="stSidebar"] {
        background: rgba(10, 12, 22, 0.97) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 0.5px solid rgba(255, 255, 255, 0.06) !important;
        box-shadow: 4px 0 30px rgba(0, 0, 0, 0.4) !important;
        position: relative !important;
    }

    /* Esfera de luz ambiental en la esquina superior de la sidebar */
    section[data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: -60px;
        left: -60px;
        width: 220px;
        height: 220px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(0, 232, 162, 0.07) 0%, transparent 65%);
        pointer-events: none;
        z-index: 0;
    }

    /* ─── LOGO HEADER EN NAVEGACIÓN ──────────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"]::before {
        content: "";
        display: block;
        height: 70px;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60"><rect x="15" y="12" width="36" height="36" rx="10" fill="url(%23grad)"/><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="%2300e8a2"/><stop offset="100%" stop-color="%2338bdf8"/></linearGradient></defs><path d="M28 30l4 4 8-8" stroke="%230b1020" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/><text x="64" y="36" fill="%23ffffff" font-family="Outfit, sans-serif" font-size="20" font-weight="700" letter-spacing="0.5">Informes</text></svg>');
        background-repeat: no-repeat;
        background-position: left center;
        margin-bottom: 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* ─── CONTENIDO INTERIOR DE LA SIDEBAR ───────────────── */
    section[data-testid="stSidebar"] > div:first-child {
        padding: 1.25rem 0rem !important;
    }

    /* ─── CABECERAS DE SECCIONES (CATEGORÍAS) ────────────── */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li:nth-child(1)::before {
        content: "PRINCIPAL";
        display: block;
        font-size: 11.5px;
        font-weight: 700;
        color: #64748b;
        letter-spacing: 1.8px;
        margin: 15px 0 10px 16px;
        text-transform: uppercase;
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li:nth-child(4)::before {
        content: "GESTIÓN";
        display: block;
        font-size: 11.5px;
        font-weight: 700;
        color: #64748b;
        letter-spacing: 1.8px;
        margin: 25px 0 10px 16px;
        text-transform: uppercase;
    }

    /* ─── ELEMENTOS DE NAVEGACIÓN ────────────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a {
        display: flex !important;
        align-items: center !important;
        padding: 10px 16px !important;
        margin: 4px 12px !important;
        border-radius: 8px !important;
        color: #cbd5e1 !important;
        text-decoration: none !important;
        font-weight: 500 !important;
        font-size: 16.5px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border-left: 2.5px solid transparent !important;
    }

    /* Ocultar icono nativo de Streamlit */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a [data-testid="stSidebarNavLinkIcon"] {
        display: none !important;
    }

    /* Agregar icono personalizado */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a::before {
        font-size: 16px;
        margin-right: 12px;
        display: inline-block;
        vertical-align: middle;
    }

    /* Iconos dinámicos */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[href="/"]::before,
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[href*="/?"]::before,
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[href*="/main"]::before {
        content: "⚡";
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[href*="/Registro"]::before {
        content: "📝";
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[href*="/Dashboard"]::before {
        content: "📈";
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[href*="/Admin_Privilegios"]::before {
        content: "🛡️";
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[href*="/Lista_Publicadores"]::before {
        content: "👥";
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[href*="/Editar_Informes"]::before {
        content: "✏️";
    }

    /* Hover */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a:hover {
        background-color: var(--sb-hover-bg) !important;
        color: #ffffff !important;
    }

    /* Activo */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[aria-current="page"],
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a.st-emotion-cache-hs3y9a {
        border-left: 2.5px solid var(--sb-accent) !important;
        background: var(--sb-active-bg) !important;
        color: var(--sb-accent) !important;
        font-weight: 600 !important;
    }

    /* ─── SOPORTE PARA st.radio (MÉTODO ALTERNATIVO) ─────── */
    section[data-testid="stSidebar"] .stRadio label {
        border-left: 2.5px solid transparent !important;
        transition: all 0.18s ease !important;
    }
    section[data-testid="stSidebar"] [aria-checked="true"] + label {
        border-left: 2.5px solid var(--sb-accent) !important;
        background: var(--sb-active-bg) !important;
        color: var(--sb-accent) !important;
    }

    /* ─── SEPARADORES ────────────────────────────────────── */
    section[data-testid="stSidebar"] hr.sidebar-divider {
        border: none !important;
        border-top: 1px solid rgba(255, 255, 255, 0.05) !important;
        margin: 15px 12px 10px 12px !important;
    }

    /* ─── PERFIL DE USUARIO ──────────────────────────────── */
    .user-profile-container {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        padding: 12px 16px !important;
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        margin: 10px 12px 5px 12px !important;
    }
    .user-avatar {
        width: 42px !important;
        height: 42px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #00e8a2 0%, #38bdf8 100%) !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        color: #0b1020 !important;
        font-weight: 700 !important;
        font-size: 15.5px !important;
        box-shadow: 0 4px 10px rgba(20, 241, 178, 0.15) !important;
    }
    .user-info {
        display: flex !important;
        flex-direction: column !important;
        flex-grow: 1 !important;
        overflow: hidden !important;
    }
    .user-name {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 15.5px !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .user-role {
        color: #94a3b8 !important;
        font-size: 13px !important;
        margin-top: 2px !important;
    }

    /* ─── BOTONES EN SIDEBAR (CERRAR SESIÓN) ──────────────── */
    section[data-testid="stSidebar"] .stButton > button {
        width: calc(100% - 24px) !important;
        margin: 5px 12px !important;
        background: rgba(255, 118, 118, 0.03) !important;
        border: 1px solid rgba(255, 118, 118, 0.1) !important;
        border-radius: 10px !important;
        color: #ff7676 !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        padding: 10px 14px !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 118, 118, 0.1) !important;
        border-color: rgba(255, 118, 118, 0.3) !important;
        box-shadow: 0 4px 15px rgba(255, 118, 118, 0.1) !important;
    }
    section[data-testid="stSidebar"] .stButton > button:active {
        transform: scale(0.98) !important;
    }

    /* ─── ESTILOS PARA INPUTS Y SELECTBOXES EN SIDEBAR ───── */
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stMultiSelect > div > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label p,
    section[data-testid="stSidebar"] .stMultiSelect label p {
        color: #cbd5e1 !important;
        font-size: 14.5px !important;
        font-weight: 600 !important;
    }
    </style>
    """

    login_styles = """
    <style>
    /* Ocultar barra lateral en login */
    section[data-testid="stSidebar"] { display: none !important; }
    button[kind="header"] { display: none !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    </style>
    """

    try:
        st.markdown(sidebar_styles, unsafe_allow_html=True)
        if es_login:
            st.markdown(login_styles, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar los estilos: {e}")
