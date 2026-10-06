# Cambios

## 2.0.0

### Diseño
- Nuevo sistema visual "cristal sobre aurora": una sola hoja de estilos (`assets/styles.css`) con tarjetas
  translúcidas, desenfoque, bordes de luz y fondo de aurora animado con bajo costo.
- Se eliminó el diseño duplicado: cabeceras recortadas, iconos del menú superpuestos y textos que se pisaban en el login.
- Navegación nativa con `st.navigation` (Inicio / Gestión / Cuenta) y navegación interna sin recargar la página.
- Dashboard simplificado: filtros en una barra superior, 4 indicadores, 4 gráficos en rejilla y tarjetas de exportación e IA.

### Seguridad
- Bloqueo por intentos fallidos, mensajes de error que no revelan usuarios y verificación en tiempo constante.
- Cookie de sesión firmada sin usuario ni rol, invalidada al cambiar la contraseña; revalidación del usuario en cada ejecución.
- Política de contraseñas, cambio de contraseña desde "Mi cuenta" y cambio obligatorio si es débil o predeterminada.
- La cuenta `admin` ya no se crea con la contraseña `admin`: se usa `ADMIN_INITIAL_PASSWORD` o una clave aleatoria.
- Páginas de administración solo para administradores; borrar informes solo para administradores; confirmación al eliminar.
- Neutralización de fórmulas en Excel; las notas no se envían a la IA; errores internos no se muestran al usuario.
- Streamlit sin trazas ni menú de desarrollo; pausa mínima entre análisis de IA.

### Funciones
- PDF rediseñado: indicadores, comparación con el mes anterior, resumen por grupo, análisis de la IA con formato,
  gráficos propios y tabla de detalle. Ya no depende de Chrome/kaleido y se genera mucho más rápido.
- Análisis con IA mejorado (más datos: tendencia, grupos, pendientes, estructura fija de secciones). Los modelos no cambian.
- Excel con tabla filtrable, totales que respetan el filtro, hoja de resumen por grupo y diseño sobrio.
- El análisis generado ya no desaparece al pulsar "Descargar".

### Correcciones
- "Sin actividad" ya no cuenta como inactivos a quienes sí participaron sin reportar horas.
- La extracción de horas ya no confunde palabras como "2 hogares" con horas.
- Editar publicadores y renombrar grupos guardaba siempre el primer elemento de la lista.
- Registro: la lista de pendientes quedaba vacía si había informes antiguos sin publicador.
- El orden de los privilegios y de los informes ya es estable.

### Estructura y mantenimiento
- Código reorganizado en `core/`, `services/`, `views/` y `assets/`; sin código duplicado ni archivos muertos.
- Migraciones idempotentes al arrancar (índices y unicidad publicador+mes).
- Scripts de un solo uso ya aplicados eliminados; nuevos `scripts/audit.py` (auditoría de solo lectura) y `scripts/usuarios.py`.
- Pruebas automáticas, `ruff` y CI en GitHub Actions.
