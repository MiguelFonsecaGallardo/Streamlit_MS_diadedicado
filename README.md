# Dia Dedicado

Aplicación web construida con Streamlit para consultar y analizar métricas operativas de entornos Teradata. Incluye informes interactivos, visualizaciones y descarga de resultados en CSV.

**Versión actual: 1.0.20.** Incrementa el último número (`X`) en cada cambio de la aplicación.

## Funcionalidades

### Gráficas dia dedicado

- Ejecución de consultas SQL ad hoc.
- Informes de ejecuciones de jobs de backup.
- Análisis de CPU, I/O y concurrencia por workload.
- Consulta del estado de memoria del sistema.
- Análisis de swap y paginación.
- Análisis de Flow Control y AWT.

### Revisiones

- Detección de phantom spool.
- Análisis de inserciones línea a línea.
- Análisis de errores de espacio («No more room»).
- Análisis de errores de spool (códigos Teradata 2646 y 2647).

### Revisión de espacio

- Consulta editable del histórico de `PDCRINFO.DatabaseSpace_Hst`.
- Filtro por fechas para consultar la evolución del espacio utilizado.
- Gráfico agregado para el sistema completo o desglosado por base de datos.
- Indicadores de espacio actual y capacidades incluidas en la consulta.
- La consulta inicial incluye todas las bases de datos con espacio actual mayor que cero.
- Revisión del espacio actual por base de datos y tabla desde `DBC.TableSizeV`, con gráfico de las tablas de mayor consumo.
- Revisión editable del skew por tabla, mostrando el ratio y un gráfico de las tablas con mayor skew.
- Revisión de `IncrementalRestoreEnabled` de `DBC.TablesV`, con espacio agregado por valor de la marca.
- Análisis histórico del espacio de tablas con `IncrementalRestoreEnabled`, filtro de fechas, consulta modificable y gráfico de evolución.

### Configuraciones

- Ordenar, añadir, modificar y quitar conexiones Teradata guardadas localmente en `conexiones.conf`.
- Consultar sistema, dirección, puerto y usuario; las contraseñas no se muestran.

Los análisis que trabajan con fechas permiten seleccionar un intervalo. Por defecto, la aplicación propone desde el primer día del mes anterior hasta ayer. Los resultados pueden incluir tablas y gráficos; los informes que ofrecen exportación se pueden descargar en formato CSV.

Al finalizar la ejecución de una consulta, la aplicación muestra el número de registros y el tiempo empleado en conectar, ejecutar y recuperar sus resultados.

El análisis de phantom spool no limita los resultados por fecha en su consulta predeterminada. La consulta generada sigue siendo editable.

## Requisitos

- Python 3.
- Acceso de red a un sistema Teradata.
- Un usuario Teradata con permisos para ejecutar las consultas y leer las vistas utilizadas por los análisis.

El proyecto utiliza Streamlit, pandas, Plotly y el controlador `teradatasql` (declarados en `requirements.txt`).

## Instalación y ejecución

Desde la carpeta del proyecto, crea y activa un entorno virtual e instala las dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

En Windows, activa el entorno con:

```powershell
.venv\Scripts\Activate.ps1
```

Inicia la aplicación con:

```bash
streamlit run diadedicado.py
```

Streamlit mostrará en la terminal la dirección local para abrir la aplicación en el navegador.

## Conexión a Teradata

1. En la barra lateral, selecciona una conexión guardada o introduce un host personalizado.
2. Introduce el usuario y, si la conexión lo requiere, la contraseña de Teradata.
3. Usa **Test connection** para comprobar la conexión.
4. Selecciona un análisis, ajusta las fechas o la consulta cuando corresponda y ejecútalo.

La página **Configuraciones** gestiona `conexiones.conf`, un CSV separado por comas con esta cabecera y una conexión por fila:

```csv
sistema,ip_address,port,logmech,username,userpassword,save_password
Produccion,teradata.example.com,1025,TDNEGO,mi_usuario,mi_contraseña,true
```

Configuraciones permite ordenar, añadir, modificar o quitar registros, incluido el puerto Teradata (por defecto `1025`), el mecanismo de autenticación (`TD2`, `TDNEGO` o `LDAP`) y si se guarda la contraseña. El orden guardado determina también el orden del selector de conexiones en la barra lateral. La aplicación pasa la dirección y el puerto al controlador Teradata por separado. `TD2` mantiene el comportamiento predeterminado anterior. Al activar **No guardar la contraseña**, se guarda `save_password=false` y el campo `userpassword` queda vacío; se puede introducir una contraseña temporalmente en la barra lateral para usarla durante esa sesión. Al desactivar la opción, la contraseña vuelve a ser obligatoria para guardar la conexión. Al modificar una conexión con la opción desactivada, deja la contraseña vacía para conservar la guardada. Los ficheros CSV anteriores que no tengan las columnas `sistema`, `port`, `logmech` o `save_password` siguen siendo compatibles; se asignan el puerto `1025`, el mecanismo `TD2` y guardar la contraseña hasta que se guarden cambios.

Al seleccionar una conexión en la barra lateral, la aplicación completa la dirección, el puerto, el mecanismo de autenticación, el usuario y, si está guardada, la contraseña. Para un host personalizado se conserva el mecanismo `TD2`. Las contraseñas que sí se guardan están en texto plano y la aplicación no autentica a sus usuarios: limita el acceso a la aplicación a tu equipo local o a una red de confianza, o sustituye el almacenamiento por un gestor de secretos. **No publiques `conexiones.conf`, `passwords.txt` ni credenciales en GitHub.** Las entradas antiguas de `passwords.txt` no se migran automáticamente porque no incluyen la dirección del servidor.

## Uso responsable

Las consultas ad hoc y los análisis se ejecutan con los permisos del usuario Teradata conectado. Revisa las consultas antes de ejecutarlas y utiliza únicamente sistemas y datos para los que tengas autorización.
