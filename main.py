import streamlit as st
st.set_page_config(
    page_title="Sistema de Informes",
    page_icon="📋",
    layout="wide"
)
from database import SessionLocal, Base, engine
import models
from sqlalchemy import text
import datetime



# 🔥 Crear tablas SOLO UNA VEZ a nivel global del proceso
if not getattr(st, "_db_initialized_global", False):
    try:
        from models import User, Publisher, MonthlyReport, Privilege, Group
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            new_admin = User(username="admin", password_hash="admin", role="admin")
            db.add(new_admin)
            db.commit()
        db.close()
        st._db_initialized_global = True
    except Exception as e:
        st.error(f"❌ Error inicializando BD: {e}")
        st.stop()

# ========================= SESSION =========================
from auth_helper import check_session_cookie_or_localstorage
check_session_cookie_or_localstorage()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None
    st.session_state.logged_out = False

def check_db_connection():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False

# ========================= CARGAR ESTILOS RESPONSIVOS =========================
from styles_loader import cargar_estilos_responsivos


def login():
    if not check_db_connection():
        st.error("🚨 No se pudo conectar a la base de datos PostgreSQL.")
        st.info("Ejecuta `python setup_db.py` para configurar la base de datos.")
        return

    st.markdown('<div class="login-form-wrapper">', unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        # Cabecera de la ventana con los tres puntos estilo macOS
        st.markdown("""
        <div class="window-header">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
        </div>
        """, unsafe_allow_html=True)
        
        # Avatar redondo estilo la imagen del usuario
        st.markdown("""
        <div class="login-avatar-container">
            <div class="login-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="login-title">LOGIN</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-line"></div>', unsafe_allow_html=True)
        
        username = st.text_input("Usuario", placeholder="Ingresa tu usuario", label_visibility="collapsed")
        password = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña", label_visibility="collapsed")
        
        submit = st.form_submit_button("LOGIN", use_container_width=True)

        if submit:
            db = SessionLocal()
            user = db.query(models.User).filter(models.User.username == username).first()
            db.close()

            if user and user.password_hash == password:
                st.session_state.logged_in = True
                st.session_state.username = user.username
                st.session_state.role = user.role
                st.session_state.user_id = user.id
                st.session_state.logged_out = False
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    st.markdown('</div>', unsafe_allow_html=True)


def logout():
    st.session_state.logged_out = True
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None
    st.query_params.clear()
    st.rerun()

def show_home():
    st.title("Sistema Automático de Informes Mensuales 📊")

    # Show quick summary for admin
    if st.session_state.role == "admin":
        db = SessionLocal()
        try:
            mes_actual = datetime.datetime.now().strftime("%Y-%m")
            total_pubs = db.query(models.Publisher).filter(models.Publisher.is_inactive == False).count()
            informes_mes = db.query(models.MonthlyReport).filter(models.MonthlyReport.month == mes_actual).count()
            pendientes = max(0, total_pubs - informes_mes)
        finally:
            db.close()

        st.markdown(f"""
        <div class="summary-row">
            <div class="summary-metric">
                <div class="metric-val">{total_pubs}</div>
                <div class="metric-label">Publicadores Activos</div>
            </div>
            <div class="summary-metric">
                <div class="metric-val">{informes_mes}</div>
                <div class="metric-label">Informes {mes_actual}</div>
            </div>
            <div class="summary-metric">
                <div class="metric-val">{pendientes}</div>
                <div class="metric-label">Pendientes</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    import urllib.parse
    q_dict = {k: st.query_params[k] for k in st.query_params}
    query_str = "?" + urllib.parse.urlencode(q_dict) if q_dict else ""

    st.markdown(f"""
    <div class="welcome-grid">
        <a class="welcome-card nav-card" href="/Registro{query_str}" target="_self" style="text-decoration: none; color: inherit; display: block;">
            <div class="card-emoji">📝</div>
            <h3>Registro de Informe</h3>
            <p>Registra el informe mensual de los publicadores del grupo. Selecciona el mes, el publicador y su actividad del mes.</p>
            <div class="nav-hint">Haz clic para abrir →</div>
        </a>
        <a class="welcome-card nav-card" href="/Dashboard{query_str}" target="_self" style="text-decoration: none; color: inherit; display: block;">
            <div class="card-emoji">📈</div>
            <h3>Dashboard y Análisis</h3>
            <p>Visualiza estadísticas, gráficos de rendimiento, exporta a Excel y utiliza la IA para generar insights automáticos.</p>
            <div class="nav-hint">Haz clic para abrir →</div>
        </a>
        <a class="welcome-card nav-card" href="/Admin_Privilegios{query_str}" target="_self" style="text-decoration: none; color: inherit; display: block;">
            <div class="card-emoji">🛡️</div>
            <h3>Administración</h3>
            <p>Gestiona los privilegios disponibles, añade o elimina publicadores y controla los estados activo/inactivo.</p>
            <div class="nav-hint">Haz clic para abrir →</div>
        </a>
        <a class="welcome-card nav-card" href="/Lista_Publicadores{query_str}" target="_self" style="text-decoration: none; color: inherit; display: block;">
            <div class="card-emoji">👥</div>
            <h3>Lista de Publicadores</h3>
            <p>Consulta el directorio completo de publicadores con su historial de informes y privilegios asignados.</p>
            <div class="nav-hint">Haz clic para abrir →</div>
        </a>
    </div>
    """, unsafe_allow_html=True)


# Renderizado condicional del CSS según el estado de sesión
if not st.session_state.logged_in:
    cargar_estilos_responsivos(es_login=True)
    login()
else:
    cargar_estilos_responsivos(es_login=False)
    show_home()
