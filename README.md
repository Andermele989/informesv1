# Sistema de Informes

Aplicación web (Streamlit + PostgreSQL) para registrar los informes mensuales de servicio de los
publicadores de un grupo, consultar indicadores, exportar a Excel/PDF y generar un análisis con IA.

**Versión 2.1.1** · ver [CHANGELOG.md](CHANGELOG.md)

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
- El rol y el estado del usuario se revalidan contra la base cada 30 segundos (una cuenta desactivada pierde el acceso casi al instante).
- Todo texto incrustado en HTML se escapa; los textos del usuario se limpian y limitan; el Excel neutraliza fórmulas (`=...`).
- El análisis del dashboard nunca envía las notas de los informes. El asistente de notas solo envía a la IA la frase corta
  (máx. 80 caracteres) que el usuario escribe en él, con aviso en pantalla; los errores de los proveedores no se muestran.
- Los usuarios son únicos sin importar mayúsculas y la base de datos impone integridad (campos obligatorios, roles válidos,
  cursos no negativos, un informe por publicador y mes). Si al arrancar hay datos que lo impiden, la app no inicia y el
  registro del servidor indica qué corregir (`python -m scripts.audit` muestra el detalle).
- Streamlit sin trazas de error ni menú de desarrollo (`.streamlit/config.toml`); XSRF activado.
- Eliminar publicadores, grupos o informes requiere confirmación y rol de administrador.

Gestión de usuarios y recuperación de acceso desde la terminal: `python -m scripts.usuarios` (ver `scripts/README.md`).

## Pruebas y calidad

```bash
pip install -r requirements-dev.txt
python -m pytest          # pruebas (usan SQLite temporal; no tocan tu base ni llaman a la IA)
python -m ruff check .    # análisis estático
python -m scripts.audit   # auditoría de tu base de datos y configuración real (solo lectura)
```

La integración continua (`.github/workflows/ci.yml`) ejecuta ambas en cada push y pull request.

## Despliegue en Render (u otro servidor)

| Ajuste | Valor |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `streamlit run main.py --server.port $PORT --server.address 0.0.0.0` |
| Health Check Path | `/_stcore/health` |
| Python | 3.12 o superior (en Render: variable `PYTHON_VERSION`, p. ej. `3.13.5`) |

Variables de entorno (en Render no existe el `.env`: se definen en *Environment*):

| Variable | Valor |
|---|---|
| `DATABASE_URL` | La *Internal Database URL* de tu PostgreSQL de Render (acepta `postgres://` y `postgresql://`) |
| `SECRET_KEY` | Clave aleatoria de 32+ caracteres (puedes dejar que Render la genere). Si falta, las sesiones se pierden al reiniciar |
| `ADMIN_INITIAL_PASSWORD` | Opcional: contraseña de `admin` solo si aún no existe |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `OPENAI_API_KEY`, `OPENAI_MODEL` | Solo si usas el análisis con IA |

La app sirve por HTTPS y la cookie de sesión se marca `Secure` sola. El archivo `render.yaml` es una referencia
con estos mismos ajustes por si prefieres crear el servicio como *Blueprint*.

### Bases de datos antiguas

Al arrancar, la app pone al día sola una base creada con versiones anteriores: añade las columnas que falten,
rellena vacíos con el valor normal (publicadores sin estado pasan a activos, usuarios sin rol a `user`, cursos
vacíos a 0), vincula por nombre los informes antiguos que no tenían publicador y crea los índices. **Nunca borra datos
y nunca impide el arranque por datos antiguos**: lo que no se pueda arreglar sin adivinar se deja tal cual y se
registra una advertencia.

### Si ves «No se pudo conectar…» o «No se pudo preparar la base de datos»

1. Abre **Logs** del servicio en Render y busca `ARRANQUE FALLIDO`: la línea siguiente da la causa exacta.
2. «No se pudo conectar»: revisa `DATABASE_URL` (usa la *Internal* si el servicio y la base están en la misma
   región), que la base esté activa y que no esté vacía la variable.
3. Otro motivo: abre la *Shell* del servicio y ejecuta `python -m scripts.audit` para ver el estado de la base.
4. Las líneas `WARNING informes.arranque` no son errores: indican qué se reparó o qué quedó pendiente de revisar.

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
