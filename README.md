# Dia Dedicado

Aplicación web construida con Streamlit para consultar y analizar métricas operativas de entornos Teradata. Incluye informes interactivos, visualizaciones y descarga de resultados en CSV.

**Versión actual: 1.0.4.** Incrementa el último número (`X`) en cada cambio de la aplicación.

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

### Configuraciones

- Añadir, modificar y quitar conexiones Teradata guardadas localmente en `conexiones.conf`.
- Consultar sistema, dirección y usuario; las contraseñas no se muestran.

Los análisis que trabajan con fechas permiten seleccionar un intervalo. Por defecto, la aplicación propone desde el primer día del mes anterior hasta ayer. Los resultados pueden incluir tablas y gráficos; los informes que ofrecen exportación se pueden descargar en formato CSV.

El análisis de phantom spool utiliza por defecto el intervalo desde el primer día del mes anterior hasta ayer. La consulta generada sigue siendo editable.

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
2. Introduce el usuario y la contraseña de Teradata.
3. Usa **Test connection** para comprobar la conexión.
4. Selecciona un análisis, ajusta las fechas o la consulta cuando corresponda y ejecútalo.

La página **Configuraciones** gestiona `conexiones.conf`, un CSV separado por comas con esta cabecera y una conexión por fila:

```csv
sistema,ip_address,username,userpassword
Produccion,teradata.example.com,mi_usuario,mi_contraseña
```

Configuraciones permite añadir, modificar o quitar registros. Al modificar una conexión, deja la contraseña vacía para conservar la guardada. Los ficheros CSV creados con la cabecera anterior (`ip_address,username,userpassword`) siguen siendo compatibles; al guardar cambios, se añade la columna `sistema`, inicialmente vacía para las conexiones anteriores.

Al seleccionar una conexión en la barra lateral, la aplicación completa la dirección, el usuario y la contraseña. También se puede elegir un host personalizado e introducir las credenciales manualmente. El fichero guarda contraseñas en texto plano y la aplicación no autentica a sus usuarios: limita el acceso a la aplicación a tu equipo local o a una red de confianza, o sustituye el almacenamiento por un gestor de secretos. **No publiques `conexiones.conf`, `passwords.txt` ni credenciales en GitHub.** Las entradas antiguas de `passwords.txt` no se migran automáticamente porque no incluyen la dirección del servidor.

## Uso responsable

Las consultas ad hoc y los análisis se ejecutan con los permisos del usuario Teradata conectado. Revisa las consultas antes de ejecutarlas y utiliza únicamente sistemas y datos para los que tengas autorización.
