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



# 🔥 Crear tablas SOLO UNA VEZ
if "db_initialized" not in st.session_state:
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
        st.session_state.db_initialized = True
    except Exception as e:
        st.error(f"❌ Error inicializando BD: {e}")
        st.stop()

# ========================= SESSION =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None

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
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    st.markdown('</div>', unsafe_allow_html=True)


def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None
    st.rerun()

def show_home():
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.caption(f"Rol: {'Administrador' if st.session_state.role == 'admin' else 'Usuario'}")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        logout()

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

    st.markdown("""
    <div class="welcome-grid">
        <div class="welcome-card nav-card" data-href="/1_Registro">
            <div class="card-emoji">📝</div>
            <h3>Registro de Informe</h3>
            <p>Registra el informe mensual de los publicadores del grupo. Selecciona el mes, el publicador y su actividad del mes.</p>
            <div class="nav-hint">Doble toque para abrir →</div>
        </div>
        <div class="welcome-card nav-card" data-href="/2_Dashboard">
            <div class="card-emoji">📈</div>
            <h3>Dashboard y Análisis</h3>
            <p>Visualiza estadísticas, gráficos de rendimiento, exporta a Excel y utiliza la IA para generar insights automáticos.</p>
            <div class="nav-hint">Doble toque para abrir →</div>
        </div>
        <div class="welcome-card nav-card" data-href="/3_Admin_Privilegios">
            <div class="card-emoji">🛡️</div>
            <h3>Administración</h3>
            <p>Gestiona los privilegios disponibles, añade o elimina publicadores y controla los estados activo/inactivo.</p>
            <div class="nav-hint">Doble toque para abrir →</div>
        </div>
        <div class="welcome-card nav-card" data-href="/4_Lista_Publicadores">
            <div class="card-emoji">👥</div>
            <h3>Lista de Publicadores</h3>
            <p>Consulta el directorio completo de publicadores con su historial de informes y privilegios asignados.</p>
            <div class="nav-hint">Doble toque para abrir →</div>
        </div>
    </div>
    <script>
    (function() {
        // Esperar a que el DOM esté completamente cargado
        function initNavCards() {
            var cards = document.querySelectorAll('.nav-card');
            if (cards.length === 0) {
                setTimeout(initNavCards, 200);
                return;
            }
            cards.forEach(function(card) {
                var href = card.getAttribute('data-href');
                var lastTap = 0;
                card.setAttribute('role', 'button');
                card.setAttribute('tabindex', '0');

                // Double-click (PC / laptop)
                card.addEventListener('dblclick', function(e) {
                    e.preventDefault();
                    window.location.href = href;
                });

                // Double-tap (móvil / tableta)
                card.addEventListener('touchend', function(e) {
                    var now = Date.now();
                    var gap = now - lastTap;
                    if (gap > 0 && gap < 400) {
                        e.preventDefault();
                        window.location.href = href;
                    }
                    lastTap = now;
                });

                // Pointer double-tap for modern phones/tablets and hybrid devices
                card.addEventListener('pointerup', function(e) {
                    if (e.pointerType === 'mouse') return;
                    var now = Date.now();
                    var gap = now - lastTap;
                    if (gap > 0 && gap < 420) {
                        e.preventDefault();
                        window.location.href = href;
                    }
                    lastTap = now;
                });

                card.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        window.location.href = href;
                    }
                });

                // Hover visual feedback
                card.addEventListener('mouseenter', function() {
                    card.style.cursor = 'pointer';
                });
            });
        }
        setTimeout(initNavCards, 300);
    </script>
    """, unsafe_allow_html=True)


# Renderizado condicional del CSS según el estado de sesión
if not st.session_state.logged_in:
    cargar_estilos_responsivos(es_login=True)
    login()
else:
    cargar_estilos_responsivos(es_login=False)
    show_home()
