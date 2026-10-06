# Cambios

## 2.1.1

### Corrección: la app no arrancaba con una base de datos antigua (Render)
- Con la 2.1.0, una base creada por versiones anteriores (informes sin publicador, usuarios sin rol, columnas
  que faltan…) hacía que el arranque se detuviera con «No se pudo preparar la base de datos».
- Ahora el arranque **nunca se detiene por datos antiguos**: añade las columnas que falten, rellena vacíos con el
  valor normal, vincula por nombre los informes antiguos sin publicador (solo si no crea duplicados) y crea los
  índices y restricciones que los datos permitan. Lo demás se conserva y se registra como advertencia.
- Los publicadores con estado vacío (columna añadida a mano años atrás) ya cuentan como activos.
- Mensajes de error distintos para «no hay conexión» y «error al preparar», que apuntan al registro del servidor.
- Guía de despliegue en Render (comandos, variables, comprobación de salud y diagnóstico) y `render.yaml` de referencia.

## 2.1.0

### Diseño
- Nueva identidad visual negro + naranja/ámbar inspirada en la referencia: superficies sólidas y sobrias (se eliminó el
  efecto cristal, el desenfoque y el brillo animado de fondo, que además costaban rendimiento).
- Cabecera de página plana, menú lateral con chips de icono y marca, y el tema de Streamlit alineado con la paleta.
- Indicadores con chip de icono, variación frente al mes anterior y mini-barras con los últimos 6 meses reales.
- Mismos gráficos con nuevo acabado: barras redondeadas, relleno degradado, rejilla punteada y dona con leyenda en lista.
- Tarjetas de Inicio alineadas en filas y gráficos de una misma fila con la misma altura.

### Seguridad e integridad
- Usuarios únicos sin distinguir mayúsculas; restricciones en PostgreSQL (campos obligatorios, rol válido, cursos >= 0).
- El arranque se detiene con un mensaje claro si hay datos que impiden aplicar esas restricciones, en vez de seguir a medias.
- Una `SECRET_KEY` copiada de los archivos de ejemplo se rechaza y no firma sesiones.
- Asistente de notas con IA: solo se envía una frase corta, limpia y limitada, con aviso al usuario.

### Corrección
- La pantalla de cambio obligatorio de contraseña no se rompe al estrenar la cabecera nueva.

## 2.0.0

### Diseño
- Nuevo sistema visual "cristal sobre aurora": una sola hoja de estilos (`assets/styles.css`) con tarjetas
  translúcidas, desenfoque, bordes de luz y fondo de aurora animado con bajo costo.
- Se eliminó el diseño duplicado: cabeceras recortadas, iconos del menú superpuestos y textos que se pisaban en el login.
- Navegación nativa con `st.navigation` (Inicio / Gestión / Cuenta) y navegación interna sin recargar la página.
- Dashboard simplificado: filtros en una barra superior, 4 indicadores, 4 gráficos en rejilla y tarjetas de exportación e IA.

### Seguridad
- Bloqueo por intentos fallidos, mensajes de error que no revelan usuarios y verificación en tiempo constante.
- Cookie de sesión firmada sin usuario ni rol, invalidada al cambiar la contraseña; revalidación del usuario cada 30 segundos.
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
