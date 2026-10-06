# Sistema de Informes

Aplicación web (Streamlit + PostgreSQL) para registrar los informes mensuales de servicio de los
publicadores de un grupo, consultar indicadores, exportar a Excel/PDF y generar un análisis con IA.

**Versión 2.0.0** · ver [CHANGELOG.md](CHANGELOG.md)

## Estructura

```
main.py                 Punto de entrada: configuración, sesión y navegación
core/                   Núcleo
  database.py             Conexión SQLAlchemy y `sesion()`
  models.py               Tablas (usuarios, privilegios, grupos, publicadores, informes, intentos de acceso)
  security.py             Contraseñas (bcrypt), token de sesión firmado, saneamiento de texto
  auth.py                 Login con bloqueo, sesión por cookie, guardias `require_login/admin`
  arranque.py             Tablas, migraciones idempotentes y cuenta admin inicial
  formularios.py          Pantalla de login y cambio de contraseña
  ui.py                   Estilos y componentes visuales compartidos
services/               Lógica de negocio sin interfaz
  datos.py                Lectura de la BD y DataFrame de informes
  metricas.py             Indicadores y variaciones
  graficos.py             Gráficos Plotly del dashboard
  excel.py                Exportación a Excel (tabla filtrable + resumen)
  pdf.py                  Informe PDF con gráficos dibujados en nativo
  ia.py                   Prompt y llamadas a Gemini / OpenAI
views/                  Páginas (inicio, registro, dashboard, administracion, publicadores, informes, cuenta)
assets/styles.css       Única hoja de estilos ("cristal sobre aurora")
scripts/                Utilidades de mantenimiento (ver scripts/README.md)
tests/                  Pruebas automáticas
.streamlit/config.toml  Tema y endurecimiento de Streamlit
```

## Instalación

Requiere Python 3.12 o superior y PostgreSQL.

```bash
python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # Linux/macOS: cp .env.example .env   (y completa los valores)
python -m scripts.setup_db       # crea la base de datos, las tablas y el usuario admin
streamlit run main.py
```

### Primer acceso

La cuenta `admin` se crea en el primer arranque. Si no definiste `ADMIN_INITIAL_PASSWORD` en `.env`, la
contraseña se genera al azar y **se muestra una sola vez en la consola del servidor**. Si una cuenta tiene
una contraseña débil o predeterminada (por ejemplo `admin`), la app obliga a cambiarla antes de continuar.

## Configuración (`.env`)

| Variable | Para qué sirve |
|---|---|
| `DATABASE_URL` o `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT`, `DB_NAME` | Conexión a PostgreSQL |
| `SECRET_KEY` | Firma de las cookies de sesión (obligatoria en producción) |
| `SESSION_TTL_DAYS` | Duración de la sesión guardada en el navegador (7 por defecto) |
| `ADMIN_INITIAL_PASSWORD` | Contraseña inicial de `admin` (opcional) |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Análisis con Google Gemini |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Análisis con OpenAI |

## Seguridad

- Contraseñas con bcrypt y política mínima; las heredadas en texto plano se migran solas en el siguiente login.
- Bloqueo temporal de la cuenta tras 5 intentos fallidos (tabla `login_attempts`); el mensaje de error no revela si el usuario existe.
- Sesión por cookie firmada con HMAC que **no contiene usuario ni rol** y deja de valer al cambiar la contraseña.
- Con sesión inválida el contenido de las páginas ni se ejecuta; las páginas de administración solo se registran para administradores.
- El rol y el estado del usuario se revalidan en cada ejecución.
- Todo texto incrustado en HTML se escapa; los textos del usuario se limpian y limitan; el Excel neutraliza fórmulas (`=...`).
- Las notas de los informes nunca se envían a la IA; los errores de proveedores no se muestran al usuario.
- Streamlit sin trazas de error ni menú de desarrollo (`.streamlit/config.toml`); XSRF activado.
- Eliminar publicadores, grupos o informes requiere confirmación y rol de administrador.

Gestión de usuarios y recuperación de acceso desde la terminal: `python -m scripts.usuarios` (ver `scripts/README.md`).

## Pruebas y calidad

```bash
pip install -r requirements-dev.txt
python -m pytest          # pruebas (usan SQLite temporal; no tocan tu base ni llaman a la IA)
python -m ruff check .    # análisis estático
python -m scripts.audit   # revisa tu base de datos y configuración real (solo lectura)
```

La integración continua (`.github/workflows/ci.yml`) ejecuta ambas en cada push y pull request.

## Despliegue (Render u otro servidor)

- Comando de inicio: `streamlit run main.py --server.port $PORT --server.address 0.0.0.0`
- Variables de entorno: `DATABASE_URL`, `SECRET_KEY` y, si usas IA, las claves correspondientes.
- Sirve la app por HTTPS: la cookie de sesión se marca `Secure` automáticamente cuando detecta HTTPS.

## Flujo de trabajo con Git

```bash
git switch -c mi-cambio            # trabaja en una rama
git add -A && git commit -m "mensaje"
git push -u origin mi-cambio       # sube la rama y abre un Pull Request en GitHub
```

Las versiones se marcan con etiquetas: `git tag -a v2.0.0 -m "Versión 2.0.0" && git push origin v2.0.0`.

## Pendientes conocidos

- `google-generativeai` está en desuso; el reemplazo oficial es `google-genai`. Funciona hoy, pero conviene
  migrar (solo cambia la función `_generar_gemini` de `services/ia.py`, sin cambiar de modelo).
