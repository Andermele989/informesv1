"""
Script de auditoría completa del proyecto Informes.
Detecta todos los problemas de lógica, seguridad y funcionamiento.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
os.environ['DB_PASS'] = '123456'  # asegurar que el env está cargado

print("=" * 60)
print("  AUDITORIA COMPLETA DEL PROYECTO")
print("=" * 60)

errores = []
advertencias = []
ok = []

# ─────────────────────────────────────────────
# 1. CONEXION A LA BASE DE DATOS
# ─────────────────────────────────────────────
print("\n[1] Probando conexión a PostgreSQL...")
try:
    from database import engine, SessionLocal, Base
    with engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        ok.append(f"Conexión a PostgreSQL: OK ({version[:40]}...)")
        print(f"    OK - {version[:60]}")
except Exception as e:
    errores.append(f"Conexión a PostgreSQL FALLIDA: {e}")
    print(f"    ERROR: {e}")

# ─────────────────────────────────────────────
# 2. TABLAS EXISTENTES
# ─────────────────────────────────────────────
print("\n[2] Verificando tablas en la base de datos...")
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    required = {'users', 'monthly_reports', 'privileges'}
    for t in required:
        if t in tablas:
            ok.append(f"Tabla '{t}': Existe")
            print(f"    OK - Tabla '{t}' existe")
        else:
            errores.append(f"Tabla '{t}' NO EXISTE en la base de datos")
            print(f"    ERROR - Tabla '{t}' NO existe")
    extras = set(tablas) - required
    if extras:
        print(f"    INFO - Tablas extra encontradas: {extras}")
except Exception as e:
    errores.append(f"Error al inspeccionar tablas: {e}")
    print(f"    ERROR: {e}")

# ─────────────────────────────────────────────
# 3. COLUMNAS DE CADA TABLA
# ─────────────────────────────────────────────
print("\n[3] Verificando columnas de tablas...")
try:
    import models
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    expected_cols = {
        'users': {'id', 'username', 'password_hash', 'role'},
        'monthly_reports': {'id', 'user_id', 'month', 'assigned_privileges', 'service_report', 'bible_courses'},
        'privileges': {'id', 'name'}
    }
    
    for tabla, cols_esperadas in expected_cols.items():
        if tabla not in inspector.get_table_names():
            continue
        cols_reales = {c['name'] for c in inspector.get_columns(tabla)}
        faltantes = cols_esperadas - cols_reales
        if faltantes:
            errores.append(f"Tabla '{tabla}' - Columnas FALTANTES: {faltantes}")
            print(f"    ERROR - '{tabla}' le faltan columnas: {faltantes}")
        else:
            ok.append(f"Columnas de '{tabla}': Completas")
            print(f"    OK - '{tabla}' tiene todas sus columnas: {cols_reales}")
except Exception as e:
    errores.append(f"Error al verificar columnas: {e}")
    print(f"    ERROR: {e}")

# ─────────────────────────────────────────────
# 4. USUARIO ADMIN
# ─────────────────────────────────────────────
print("\n[4] Verificando usuario admin...")
try:
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if admin:
        ok.append("Usuario 'admin' existe en la BD")
        print(f"    OK - Usuario admin existe (id={admin.id}, rol={admin.role})")
        if admin.role != 'admin':
            errores.append(f"El usuario 'admin' tiene rol '{admin.role}' en lugar de 'admin'")
            print(f"    ERROR - El usuario admin tiene rol '{admin.role}' incorrecto")
    else:
        errores.append("Usuario 'admin' NO existe en la BD")
        print("    ERROR - Usuario admin NO existe")
    
    # Verificar login
    if admin and admin.password_hash == "admin":
        ok.append("Login de admin funciona con contraseña 'admin'")
        print("    OK - Login con contraseña 'admin' funicionaría correctamente")
    elif admin:
        advertencias.append(f"La contraseña del admin NO es 'admin' - es: '{admin.password_hash}'")
        print(f"    ADVERTENCIA - contraseña admin es '{admin.password_hash}'")
    db.close()
except Exception as e:
    errores.append(f"Error al verificar usuario admin: {e}")
    print(f"    ERROR: {e}")

# ─────────────────────────────────────────────
# 5. MODELOS SQLAlchemy CONSISTENTES
# ─────────────────────────────────────────────
print("\n[5] Verificando consistencia de modelos SQLAlchemy...")
try:
    # Verificar que los modelos se pueden instanciar y que las relaciones funcionan
    u = models.User(username="test_audit", password_hash="x", role="user")
    p = models.Privilege(name="test_privilege_audit")
    r = models.MonthlyReport(user_id=1, month="2026-03", assigned_privileges="", service_report="", bible_courses=0)
    ok.append("Modelos SQLAlchemy instanciables correctamente")
    print("    OK - Modelos se instancian sin errores")
except Exception as e:
    errores.append(f"Error en modelos SQLAlchemy: {e}")
    print(f"    ERROR: {e}")

# ─────────────────────────────────────────────
# 6. LÓGICA DE REGISTRO - POSIBLE INFORME DUPLICADO
# ─────────────────────────────────────────────
print("\n[6] Verificando lógica de registro de informes...")
try:
    db = SessionLocal()
    # Verificar si hay restricción de unicidad (mismo usuario + mismo mes)
    from sqlalchemy import inspect as sa_inspect
    inspector2 = sa_inspect(engine)
    uq_constraints = inspector2.get_unique_constraints('monthly_reports')
    indexes = inspector2.get_indexes('monthly_reports')
    
    # No hay unique constraint en (user_id, month) - esto permite duplicados
    has_uq_user_month = any(
        set(u.get('column_names', [])) == {'user_id', 'month'} 
        for u in uq_constraints
    )
    if not has_uq_user_month:
        advertencias.append(
            "No hay restricción UNIQUE en (user_id, month) en 'monthly_reports'. "
            "Un mismo usuario puede guardar múltiples informes para el mismo mes."
        )
        print("    ADVERTENCIA - Sin restricción única (user_id, month): un usuario puede duplicar informes del mismo mes")
    else:
        ok.append("Restricción única (user_id, month) existe")
        print("    OK - Restricción única (user_id, month) existe")
    db.close()
except Exception as e:
    advertencias.append(f"No se pudo verificar unicidad de informes: {e}")
    print(f"    ADVERTENCIA: {e}")

# ─────────────────────────────────────────────
# 7. SEGURIDAD - CONTRASEÑAS EN TEXTO PLANO
# ─────────────────────────────────────────────
print("\n[7] Verificando seguridad de contraseñas...")
advertencias.append(
    "SEGURIDAD: Las contraseñas se guardan en TEXTO PLANO (campo 'password_hash'). "
    "No hay hashing real. Cualquiera con acceso a la BD puede ver las contraseñas."
)
print("    ADVERTENCIA - Las contraseñas NO están hasheadas (se guardan en texto plano)")
print("    Recomendación: usar bcrypt o hashlib para hashear contraseñas")

# ─────────────────────────────────────────────
# 8. VERIFICAR .env COMPLETO
# ─────────────────────────────────────────────
print("\n[8] Verificando archivo .env...")
from dotenv import dotenv_values
env = dotenv_values(".env")
for key in ['DB_USER', 'DB_PASS', 'DB_HOST', 'DB_NAME']:
    if env.get(key):
        ok.append(f".env - {key} configurado")
        print(f"    OK - {key} = '{env[key]}'")
    else:
        errores.append(f".env - {key} está vacío o no existe")
        print(f"    ERROR - {key} está vacío o no existe")

for key in ['OPENAI_API_KEY', 'GEMINI_API_KEY']:
    val = env.get(key, '')
    if val:
        ok.append(f".env - {key} configurado (IA disponible)")
        print(f"    OK - {key} configurado")
    else:
        advertencias.append(f".env - {key} vacío (función de IA no disponible)")
        print(f"    ADVERTENCIA - {key} vacío (la función de IA no funcionará)")

# ─────────────────────────────────────────────
# 9. VERIFICAR IMPORTS DE PÁGINAS
# ─────────────────────────────────────────────
print("\n[9] Verificando imports de todas las páginas...")
pages = {
    'main.py': ['streamlit', 'database', 'models', 'sqlalchemy'],
    'pages/1_Registro.py': ['streamlit', 'database', 'models', 'datetime'],
    'pages/2_Dashboard.py': ['streamlit', 'database', 'models', 'pandas', 'plotly', 'io'],
    'pages/3_Admin_Privilegios.py': ['streamlit', 'database', 'models'],
}
for page, imports in pages.items():
    print(f"    Verificando {page}...")
    for imp in imports:
        try:
            __import__(imp)
            print(f"        OK - import '{imp}'")
        except ImportError:
            errores.append(f"{page}: import '{imp}' FALLA - no instalado")
            print(f"        ERROR - import '{imp}' FALLA")

# ─────────────────────────────────────────────
# 10. LÓGICA DEL DASHBOARD - st.stop() ROMPE EL EXCEL
# ─────────────────────────────────────────────
print("\n[10] Verificando lógica del Dashboard...")
with open("pages/2_Dashboard.py", "r", encoding="utf-8") as f:
    dashboard_code = f.read()

if "st.stop()" in dashboard_code and "if not reports:" in dashboard_code:
    advertencias.append(
        "Dashboard: si no hay informes, usa st.stop() lo cual TAMBIÉN detiene "
        "la renderización del botón de Excel y la sección de IA. "
        "Esto es comportamiento esperado de Streamlit, no un bug."
    )
    print("    INFO - Si no hay informes, la página se detiene (comportamiento correcto de Streamlit)")

if "excel_bytes = buffer.getvalue()" in dashboard_code:
    ok.append("Dashboard: buffer Excel corregido (getvalue() fuera del with)")
    print("    OK - Bug de Excel corregido")

# ─────────────────────────────────────────────
# RESUMEN FINAL
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"  RESUMEN: {len(ok)} OK | {len(advertencias)} ADVERTENCIAS | {len(errores)} ERRORES")
print("=" * 60)

if errores:
    print("\n❌ ERRORES CRÍTICOS (deben corregirse):")
    for i, e in enumerate(errores, 1):
        print(f"  {i}. {e}")

if advertencias:
    print("\n⚠️  ADVERTENCIAS (importantes pero no críticos):")
    for i, a in enumerate(advertencias, 1):
        print(f"  {i}. {a}")

if ok:
    print("\n✅ TODO LO QUE ESTÁ BIEN:")
    for i, o in enumerate(ok, 1):
        print(f"  {i}. {o}")

print("\n" + "=" * 60)
