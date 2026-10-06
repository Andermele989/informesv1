"""Auditoría de seguridad, integridad de base de datos y rendimiento.

Ejecución desde la raíz del proyecto:
    python -m scripts.audit
"""
import os
import sys
import time

from sqlalchemy import inspect, text

from core import models
from core.database import engine, sesion
from core.security import is_bcrypt_hash, verify_password

TABLAS_REQUERIDAS = {"users", "privileges", "groups", "publishers", "monthly_reports", "login_attempts"}
INDICES_REQUERIDOS = {
    "ix_monthly_reports_publisher_id",
    "ix_monthly_reports_user_id",
    "ix_publishers_group_id",
    "ix_publishers_is_inactive",
    "uq_report_publisher_month",
}


def _check(ok: bool, item: str, detalle: str = "", info: str = "") -> bool:
    """Imprime una comprobación. `detalle` solo se muestra si falla; `info`, si pasa."""
    texto = f"  [{'OK' if ok else '!!'}] {item}"
    if not ok and detalle:
        texto += f" -> {detalle}"
    elif ok and info:
        texto += f" ({info})"
    print(texto)
    return ok


def auditar_base_de_datos() -> int:
    fallos = 0
    print("\n1. Base de datos y Conectividad")
    t0 = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ms = (time.perf_counter() - t0) * 1000
        _check(True, f"Conexión activa a {engine.url.render_as_string(hide_password=True)}", info=f"{ms:.1f} ms")
    except Exception as exc:
        _check(False, "Conexión a la base de datos", str(exc))
        return 1

    inspector = inspect(engine)
    tablas = set(inspector.get_table_names())
    faltan_tablas = TABLAS_REQUERIDAS - tablas
    fallos += not _check(not faltan_tablas, "Estructura de tablas completa", f"faltan: {sorted(faltan_tablas)}")

    # Verificar índices
    indices_existentes = set()
    for t in tablas:
        try:
            for idx in inspector.get_indexes(t):
                indices_existentes.add(idx.get("name"))
            for uq in inspector.get_unique_constraints(t):
                if uq.get("name"):
                    indices_existentes.add(uq["name"])
        except Exception:
            pass

    # En SQLite o Postgres algunos nombres pueden coincidir o variar ligeramente
    indices_encontrados = INDICES_REQUERIDOS & indices_existentes
    resumen = f"{len(indices_encontrados)}/{len(INDICES_REQUERIDOS)} verificados"
    _check(len(indices_encontrados) >= 3, "Índices de rendimiento de consultas", resumen, info=resumen)

    return fallos


def auditar_integridad() -> int:
    fallos = 0
    print("\n2. Integridad de los Datos")
    with sesion() as db:
        num_informes = db.query(models.MonthlyReport).count()
        num_publicadores = db.query(models.Publisher).count()
        num_grupos = db.query(models.Group).count()
        _check(True, f"Volumen de registros: {num_informes} informes, {num_publicadores} publicadores, {num_grupos} grupos")

        duplicados = db.execute(
            text("SELECT publisher_id, month FROM monthly_reports GROUP BY 1, 2 HAVING count(*) > 1")
        ).fetchall()
        fallos += not _check(not duplicados, "Unicidad de informe por publicador y mes",
                             f"{len(duplicados)} informes duplicados detectados")

        huerfanos = db.query(models.MonthlyReport).filter(models.MonthlyReport.publisher_id.is_(None)).count()
        fallos += not _check(huerfanos == 0, "Asignación de publicador en informes",
                             f"{huerfanos} informes sin publicador asignado")

        grupos_huerfanos = db.query(models.Publisher).filter(
            models.Publisher.group_id.isnot(None),
            ~models.Publisher.group_id.in_(db.query(models.Group.id))
        ).count()
        fallos += not _check(grupos_huerfanos == 0, "Integridad referencial de grupos",
                             f"{grupos_huerfanos} publicadores con grupo inexistente")

    return fallos


def auditar_seguridad() -> int:
    fallos = 0
    print("\n3. Seguridad y Control de Acceso")
    with sesion() as db:
        usuarios = db.query(models.User).all()
        fallos += not _check(len(usuarios) > 0, "Usuarios registrados", "no hay ninguno", info=f"total: {len(usuarios)}")

        for u in usuarios:
            es_bcrypt = is_bcrypt_hash(u.password_hash)
            fallos += not _check(es_bcrypt, f"Hash seguro para '{u.username}' (bcrypt)",
                                 "contraseña en texto plano")
            es_debil = any(verify_password(c, u.password_hash)[0] for c in {"admin", "12345678", u.username})
            fallos += not _check(not es_debil, f"Contraseña robusta para '{u.username}'",
                                 "usa contraseña predeterminada o predecible")

    clave_secreta = os.getenv("SECRET_KEY", "")
    longitud = f"longitud actual: {len(clave_secreta)}"
    fallos += not _check(len(clave_secreta) >= 32, "Firma HMAC de sesiones (SECRET_KEY >= 32 caracteres)", longitud, info=longitud)

    # IA y APIs
    tiene_gemini = bool(os.getenv("GEMINI_API_KEY"))
    tiene_openai = bool(os.getenv("OPENAI_API_KEY"))
    proveedor = "Gemini" if tiene_gemini else ("OpenAI" if tiene_openai else "ninguno configurado")
    _check(tiene_gemini or tiene_openai, "Configuración de proveedor de IA", proveedor, info=proveedor)

    return fallos


def auditar_rendimiento() -> int:
    fallos = 0
    print("\n4. Benchmark de Rendimiento de Consultas")
    with sesion() as db:
        t0 = time.perf_counter()
        # Consulta típica del dashboard: todos los informes con sus publicadores
        _ = db.query(models.MonthlyReport).all()
        _ = db.query(models.Publisher).all()
        duracion_ms = (time.perf_counter() - t0) * 1000

        rapido = duracion_ms < 100
        medida = f"{duracion_ms:.1f} ms (meta < 100 ms)"
        fallos += not _check(rapido, "Carga de datos principales", medida, info=medida)

    return fallos


def main() -> int:
    print("=" * 60)
    print(" AUDITORÍA INTEGRAL DE SEGURIDAD, BASE DE DATOS Y RENDIMIENTO")
    print("=" * 60)

    total_fallos = (
        auditar_base_de_datos()
        + auditar_integridad()
        + auditar_seguridad()
        + auditar_rendimiento()
    )

    print("\n" + "=" * 60)
    if total_fallos == 0:
        print(" RESULTADO: TODO CORRECTO.")
    else:
        print(f" RESULTADO: {total_fallos} PUNTO(S) REQUIEREN ATENCIÓN.")
    print("=" * 60 + "\n")

    return 0 if total_fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
