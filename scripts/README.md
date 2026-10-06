# scripts/

Utilidades de mantenimiento. **No forman parte de la app en ejecución.** Se lanzan desde la raíz del
proyecto con el entorno virtual activo y leen la configuración del `.env`.

| Comando | Para qué sirve |
|---|---|
| `python -m scripts.setup_db` | Instalación inicial: crea la base de datos, las tablas y el usuario `admin` |
| `python -m scripts.audit` | Auditoría de solo lectura: conexión, tablas, índices, integridad, contraseñas débiles, claves y rendimiento |
| `python -m scripts.usuarios listar` | Lista los usuarios |
| `python -m scripts.usuarios crear <usuario> [--admin]` | Crea un usuario (la contraseña se pide por teclado) |
| `python -m scripts.usuarios password <usuario>` | Restablece una contraseña y cierra sus sesiones activas |
| `python -m scripts.usuarios desbloquear <usuario>` | Quita el bloqueo por intentos fallidos |
| `python -m scripts.usuarios activar\|desactivar <usuario>` | Habilita o inhabilita una cuenta |

Las migraciones de esquema ya no son scripts aparte: `core/arranque.py` aplica al iniciar la app los
pasos pendientes de forma idempotente.
