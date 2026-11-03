# Dia Dedicado

Aplicación web construida con Streamlit para consultar y analizar métricas operativas de entornos Teradata. Incluye informes interactivos, visualizaciones y descarga de resultados en CSV.

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

Los análisis que trabajan con fechas permiten seleccionar un intervalo. Por defecto, la aplicación propone desde el primer día del mes anterior hasta ayer. Los resultados pueden incluir tablas y gráficos; los informes que ofrecen exportación se pueden descargar en formato CSV.

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

1. En la barra lateral, selecciona un host configurado o introduce uno personalizado.
2. Introduce el usuario y la contraseña de Teradata.
3. Usa **Test connection** para comprobar la conexión.
4. Selecciona un análisis, ajusta las fechas o la consulta cuando corresponda y ejecútalo.

La aplicación puede precargar contraseñas desde un archivo local `passwords.txt`, con una entrada por línea en el formato `usuario:contraseña`. Este mecanismo guarda credenciales en texto plano: es preferible introducirlas en la aplicación o sustituirlo por un gestor de secretos. **No publiques `passwords.txt` ni credenciales en GitHub.**

## Uso responsable

Las consultas ad hoc y los análisis se ejecutan con los permisos del usuario Teradata conectado. Revisa las consultas antes de ejecutarlas y utiliza únicamente sistemas y datos para los que tengas autorización.
