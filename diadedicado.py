import csv
import os
import tempfile
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import teradatasql
from datetime import date, timedelta

APP_VERSION = "1.0.16"

# --- Date Calculation Logic ---
# Today's date reference
TODAY = date.today()

# Start Date: First day of the previous month
first_day_current_month = TODAY.replace(day=1)
last_day_previous_month = first_day_current_month - timedelta(days=1)
DEFAULT_START_DATE = last_day_previous_month.replace(day=1)

# End Date: Yesterday
DEFAULT_END_DATE = TODAY - timedelta(days=1)


# --- Teradata Brand Palette (Tokens) ---
TD_NAVY = "#00233C"
TD_ORANGE = "#FF5F02"
TD_WHITE = "#FFFFFF"
TD_BLUE = "#3053F4"
TD_GREEN = "#04CE7E"
TD_LAVENDER = "#C4B7F1"
TD_MID_BLUE_GRAY = "#667B8A"
TD_STEEL = "#99A7B1"
TD_DEEP_TEAL = "#334F63"
TD_OFF_WHITE = "#F5F7FA"
TD_BORDER = "#E2E8F0"
TD_MUTED = "#64748B"
TD_DARK_TEXT = "#001A2C"

# Dark Theme Specific Variants
TD_NAVY_DEEP = "#071A2E"
TD_NAVY_MID = "#0A3354"
TD_DARK_BORDER = "#1E3A52"

# Categorical sequence according to Teradata design rules
TD_SEQUENCE = [
    TD_NAVY,
    TD_ORANGE,
    TD_BLUE,
    TD_GREEN,
    TD_LAVENDER,
    TD_DEEP_TEAL,
    TD_MID_BLUE_GRAY,
    TD_STEEL,
]

TD_DARK_SEQUENCE = [
    TD_ORANGE,
    TD_BLUE,
    TD_GREEN,
    TD_LAVENDER,
    TD_STEEL,
    TD_MID_BLUE_GRAY,
]

# Configure Streamlit page layout
st.set_page_config(page_title="Teradata Management & Analysis", layout="wide")


# --- Helpers for the local connections file ---
CONNECTIONS_FILE = "conexiones.conf"
DEFAULT_TD_PORT = 1025
CONNECTION_FIELDS = (
    "sistema",
    "ip_address",
    "port",
    "username",
    "userpassword",
)
LEGACY_CONNECTION_FIELDS = ("ip_address", "username", "userpassword")


def load_connections(file_path: str = CONNECTIONS_FILE) -> list[dict[str, str]]:
    """Load connection records from a comma-separated local file."""
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as connections_file:
        reader = csv.DictReader(connections_file)
        if reader.fieldnames is None or not set(LEGACY_CONNECTION_FIELDS).issubset(
            reader.fieldnames
        ):
            raise ValueError(
                "La cabecera debe incluir: sistema,ip_address,username,userpassword."
            )

        connections = []
        for line_number, row in enumerate(reader, start=2):
            connection = {field: row.get(field) or "" for field in CONNECTION_FIELDS}
            connection["sistema"] = connection["sistema"].strip()
            connection["ip_address"] = connection["ip_address"].strip()
            connection["username"] = connection["username"].strip()
            connection["port"] = connection["port"].strip() or str(DEFAULT_TD_PORT)
            if not all(
                connection[field].strip() for field in LEGACY_CONNECTION_FIELDS
            ):
                raise ValueError(
                    f"La fila {line_number} debe incluir dirección, usuario y contraseña."
                )
            try:
                port = int(connection["port"])
            except ValueError as exc:
                raise ValueError(
                    f"El puerto de la fila {line_number} debe ser un entero entre 1 y 65535."
                ) from exc
            if not 1 <= port <= 65535:
                raise ValueError(
                    f"El puerto de la fila {line_number} debe estar entre 1 y 65535."
                )
            connection["port"] = str(port)
            connections.append(connection)
    return connections


def save_connections(
    connections: list[dict[str, str]],
    file_path: str = CONNECTIONS_FILE,
) -> None:
    """Write connection records atomically to the local CSV file."""
    directory = os.path.dirname(os.path.abspath(file_path))
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=directory,
            prefix=".conexiones-",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            writer = csv.DictWriter(
                temporary_file,
                fieldnames=CONNECTION_FIELDS,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(connections)
        os.replace(temporary_path, file_path)
    except OSError:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise


try:
    CONNECTIONS = load_connections()
    CONNECTIONS_ERROR = None
except (OSError, ValueError, csv.Error) as exc:
    CONNECTIONS = []
    CONNECTIONS_ERROR = str(exc)

# --- Theme Preference Setup (Bottom Control) ---
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "Dark"

theme_mode = st.session_state.get("theme_mode", "Dark")

if theme_mode == "Dark":
    bg_app = TD_NAVY_DEEP
    bg_card = TD_NAVY_MID
    text_color = "#E6EDF3"
    header_color = "#E6EDF3"
    border_color = TD_DARK_BORDER
    chart_bg = TD_NAVY_MID
    chart_grid = TD_DARK_BORDER
    chart_text = "#C4D0DA"
    active_sequence = TD_DARK_SEQUENCE
    logo_color = "#FFFFFF"
else:
    bg_app = TD_OFF_WHITE
    bg_card = TD_WHITE
    text_color = TD_DARK_TEXT
    header_color = TD_NAVY
    border_color = TD_BORDER
    chart_bg = TD_WHITE
    chart_grid = TD_BORDER
    chart_text = TD_MUTED
    active_sequence = TD_SEQUENCE
    logo_color = "#001A2C"

dark_text_styles = ""
if theme_mode == "Dark":
    dark_text_styles = f"""
        [data-testid="stAppViewContainer"] :is(
            p, label, small, li, summary,
            [data-testid="stMarkdownContainer"],
            [data-testid="stCaptionContainer"],
            [data-testid="stWidgetLabel"],
            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"],
            [data-testid="stAlert"]
        ),
        [data-testid="stSidebar"] :is(
            p, label, small, li, summary,
            [data-testid="stMarkdownContainer"],
            [data-testid="stCaptionContainer"],
            [data-testid="stWidgetLabel"]
        ),
        [data-testid="stAppViewContainer"] [data-baseweb="select"] *,
        [data-testid="stAppViewContainer"] [role="option"],
        [data-testid="stAppViewContainer"] [role="listbox"],
        .stButton button:not([kind="primary"]) {{
            color: {text_color} !important;
        }}

        [data-testid="stAppViewContainer"] [data-testid="stDataFrame"],
        [data-testid="stSidebar"] [data-testid="stDataFrame"] {{
            color: {text_color} !important;
        }}
    """

# --- Sidebar: Top Logo ---
st.sidebar.caption(f"Versión {APP_VERSION}")

logo_html = f"""
<div style="padding: 10px 0px 15px 0px; text-align: left;">
    <svg width="160" height="32" viewBox="0 0 300 60" fill="none" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="42" font-family="'Inter', sans-serif" font-weight="800" font-size="46" fill="{logo_color}" letter-spacing="-1.5">teradata<tspan fill="#FF5F02">.</tspan></text>
    </svg>
</div>
"""
st.sidebar.markdown(logo_html, unsafe_allow_html=True)

# --- Sidebar: Page Selector ---
selected_page = st.sidebar.radio(
    "Navigation",
    options=[
        "📊 Graficas dia dedicado",
        "🔍 Revisiones",
        "📦 Revisión de espacio",
        "⚙️ Configuraciones",
    ],
    index=0,
    key="page_selector",
)

st.sidebar.markdown("---")

# --- Sidebar: Database Credentials ---
st.sidebar.header("Connection settings")

CUSTOM_HOST_OPTION = "Custom host..."
connection_labels = []
connections_by_label = {}
connection_indexes_by_label = {}
for connection_index, connection in enumerate(CONNECTIONS):
    system_label = connection["sistema"] or "Sin sistema"
    label = (
        f"{system_label} — {connection['ip_address']}:{connection['port']} — "
        f"{connection['username']}"
    )
    if label in connections_by_label:
        suffix = 2
        while f"{label} ({suffix})" in connections_by_label:
            suffix += 1
        label = f"{label} ({suffix})"
    connection_labels.append(label)
    connections_by_label[label] = connection
    connection_indexes_by_label[label] = connection_index

host_options = [*connection_labels, CUSTOM_HOST_OPTION]
default_host_option = host_options[0] if connection_labels else CUSTOM_HOST_OPTION
if st.session_state.get("connection_selector") not in host_options:
    st.session_state["connection_selector"] = default_host_option

current_selection = st.session_state["connection_selector"]
if st.session_state.get("_credential_selection") != current_selection:
    selected_connection = connections_by_label.get(current_selection)
    st.session_state["connection_username"] = (
        selected_connection["username"] if selected_connection else ""
    )
    st.session_state["connection_password"] = (
        selected_connection["userpassword"] if selected_connection else ""
    )
    st.session_state["_credential_selection"] = current_selection

selected_host_option = st.sidebar.selectbox(
    "Conexión (IP o dirección)",
    options=host_options,
    key="connection_selector",
)

selected_connection = connections_by_label.get(selected_host_option)
if selected_connection:
    host = selected_connection["ip_address"]
    port = int(selected_connection["port"])
else:
    host = st.sidebar.text_input("Enter custom host / IP", value="")
    port = st.sidebar.number_input(
        "Puerto Teradata",
        min_value=1,
        max_value=65535,
        value=DEFAULT_TD_PORT,
        step=1,
        key="custom_connection_port",
    )

user = st.sidebar.text_input("Username", key="connection_username")
password = st.sidebar.text_input(
    "Password",
    type="password",
    key="connection_password",
)

if CONNECTIONS_ERROR:
    st.sidebar.error(f"No se pudo leer {CONNECTIONS_FILE}: {CONNECTIONS_ERROR}")


# Connection Helper Function
def execute_teradata_query(sql_query: str):
    started_at = time.perf_counter()
    try:
        connection_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
        with teradatasql.connect(
            host=f"{connection_host}:{port}",
            user=user,
            password=password,
        ) as conn:
            result = pd.read_sql(sql_query, conn)
    finally:
        st.session_state["last_query_duration_seconds"] = (
            time.perf_counter() - started_at
        )
    return result


def query_duration_text() -> str:
    duration = st.session_state.get("last_query_duration_seconds")
    if duration is None:
        return "Tiempo de ejecución: no disponible"
    return f"Tiempo de ejecución: {duration:.2f} s"


# Sidebar Test Connection Button
if st.sidebar.button("🔌 Test connection", key="btn_test_conn", use_container_width=True):
    if not host or not user or not password:
        st.sidebar.error("Please provide Host, Username, and Password.")
    else:
        try:
            with st.sidebar.spinner("Testing connection..."):
                execute_teradata_query("SELECT 1;")
            st.sidebar.success(
                f"Connection successful! {query_duration_text()}"
            )
        except Exception as e:
            st.sidebar.error(f"Connection failed: {str(e)}")

# Sidebar Divider
st.sidebar.markdown("---")

# --- Theme Control Selector (At the Bottom) ---
selected_theme = st.sidebar.radio(
    "Appearance Mode",
    options=["Light", "Dark"],
    index=1 if theme_mode == "Dark" else 0,
    key="theme_radio",
)

if selected_theme != theme_mode:
    st.session_state["theme_mode"] = selected_theme
    st.rerun()

# --- Custom Teradata Brand CSS Injection ---
st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            color: {text_color};
        }}
        
        /* App background */
        .stApp {{
            background-color: {bg_app};
        }}

        [data-testid="stSidebar"] {{
            background-color: {bg_app};
        }}

        {dark_text_styles}
        
        /* Headers & Subheaders styling */
        h1, h2, h3, .stSubheader {{
            color: {header_color} !important;
            font-weight: 300 !important;
        }}
        
        /* Tabs Text Color Fix for Light/Dark Theme */
        button[data-baseweb="tab"] p {{
            color: {text_color} !important;
            font-weight: 500;
        }}
        
        /* Active Tab Color Highlight */
        button[data-baseweb="tab"][aria-selected="true"] p {{
            color: {TD_ORANGE if theme_mode == "Dark" else TD_NAVY} !important;
            font-weight: 700;
        }}

        @keyframes incremental-restore-pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.25; }}
        }}
        .incremental-restore-running {{
            animation: incremental-restore-pulse 1s ease-in-out infinite;
            font-weight: 600;
            color: {text_color};
            padding: 0.5rem 0;
        }}
        
        /* Primary Buttons */
        .stButton>button[kind="primary"] {{
            background-color: {TD_ORANGE if theme_mode == "Dark" else TD_NAVY};
            color: {TD_WHITE};
            border-radius: 4px;
            border: none;
            font-weight: 600;
        }}
        .stButton>button[kind="primary"]:hover {{
            background-color: {TD_DEEP_TEAL};
            color: {TD_WHITE};
        }}
        
        /* Inputs styling for dark mode readability */
        .stTextArea textarea, .stTextInput input, .stSelectbox select {{
            background-color: {bg_card} !important;
            color: {text_color} !important;
            border-color: {border_color} !important;
        }}
        
        /* Accent elements & borders */
        .td-accent-bar {{
            width: 64px;
            height: 4px;
            background-color: {TD_ORANGE};
            margin-bottom: 16px;
        }}
        
        /* Footer styling */
        .td-footer {{
            border-top: 1px solid {border_color};
            padding-top: 16px;
            margin-top: 48px;
            font-size: 12px;
            color: {chart_text};
        }}
        .td-tagline {{
            font-size: 18px;
            color: {header_color};
            font-weight: 300;
            margin-bottom: 4px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# Teradata Plotly Theme Applicator
def apply_td_layout(fig, title_text: str, y_label: str = ""):
    fig.update_layout(
        title=dict(
            text=f"<b>{title_text}</b>",
            font=dict(family="Inter", size=18, color=header_color),
        ),
        paper_bgcolor=chart_bg,
        plot_bgcolor=chart_bg,
        hovermode="x unified",
        xaxis=dict(
            title="",
            gridcolor=chart_grid,
            linecolor=chart_grid,
            tickfont=dict(color=chart_text, size=10),
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text=y_label, font=dict(color=text_color, size=11)),
            gridcolor=chart_grid,
            linecolor=chart_grid,
            tickfont=dict(color=chart_text, size=10),
            showgrid=True,
            zeroline=True,
            zerolinecolor=chart_grid,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=text_color),
        ),
        margin=dict(l=50, r=40, t=80, b=80),
    )
    return fig


# --- Helper SQL Generator Functions ---
def get_backup_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT 
    A.BACKUP AS "Nombre Job",
    A.F_INICIO AS "Fecha",
    A.H_INICIO AS "Hora Inicio",
    A.H_FIN AS "Hora Fin",
    (EXTRACT(HOUR FROM B.DURACION) * 3600 
     + EXTRACT(MINUTE FROM B.DURACION) * 60 
     + EXTRACT(SECOND FROM B.DURACION)) AS "Duración segundos",
    CASE LOWER(A.ESTADO)
        WHEN 'completed_successfully' THEN '4'
        WHEN 'completed_errors' THEN '3'
        WHEN 'warning' THEN '2'
        WHEN 'failed' THEN '1'
        ELSE '0'
    END AS estado_numerico,
    A.ESTADO AS "Estado",
    A.OCUPA || ' ' || A.UNIDADES AS "Tamaño",
    B.TASA || ' ' || B.UNIDADES AS "Velocidad",
    COUNT(*) OVER (PARTITION BY A.BACKUP) AS historico
FROM soporte_td.BACKUPS_SETS A
LEFT JOIN soporte_td.COMPROBACION_BACKUPS B
    ON A.SAVESET = B.SAVESET
   AND A.BACKUP = B.BACKUP
WHERE A.F_INICIO BETWEEN '{start_str}' AND '{end_str}'
QUALIFY ROW_NUMBER() OVER (PARTITION BY A.BACKUP ORDER BY A.F_INICIO DESC) = 1;""".strip()


def get_phantom_spool_sql():
    return """SELECT DatabaseName,
       ROUND(SUM(CurrentSpool)/(1024*1024*1024)) AS TOTAL_GB
FROM DBC.Diskspacev
WHERE DatabaseName NOT IN (
    SELECT Username
    FROM DBC.SessionInfo
)
AND CurrentSpool > 0
GROUP BY DatabaseName
ORDER BY 2 DESC;""".strip()


def get_space_review_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT
    EXTRACT(MONTH FROM cal.calendar_date) AS TheMonth,
    EXTRACT(YEAR FROM cal.calendar_date) AS TheYear,
    db.LogDate,
    db.DatabaseName,
    db.Current_Perm_DB_GB,
    db.Max_Perm_DB_GB,
    53500 AS Max_User_Perm_GB,
    cap.Max_Perm_SYS_GB
FROM (
    SELECT
        LogDate,
        DatabaseName,
        CAST(SUM(CurrentPerm) / (1024 ** 3) AS INTEGER) AS Current_Perm_DB_GB,
        CAST(SUM(MaxPerm) / (1024 ** 3) AS INTEGER) AS Max_Perm_DB_GB
    FROM PDCRINFO.DatabaseSpace_Hst
    WHERE LogDate BETWEEN DATE '{start_str}' AND DATE '{end_str}'
    GROUP BY LogDate, DatabaseName
) db
INNER JOIN SYS_CALENDAR.CALENDAR cal
    ON db.LogDate = cal.calendar_date
CROSS JOIN (
    SELECT CAST(SUM(MaxPerm) / (1000 ** 3) AS INTEGER) AS Max_Perm_SYS_GB
    FROM DBC.DiskSpaceV
) cap
WHERE db.Current_Perm_DB_GB > 0
ORDER BY TheYear, TheMonth, db.LogDate;""".strip()


def get_table_space_sql():
    return """SELECT
    DatabaseName,
    TableName,
    SUM(CurrentPerm) / (1000 ** 3) AS Current_Perm_GB
FROM DBC.TableSizeV
GROUP BY DatabaseName, TableName
ORDER BY Current_Perm_GB DESC;""".strip()


def get_skew_review_sql():
    return """SELECT
    xa.DatabaseName,
    xa.TableName,
    CAST(xa.espacio_ocupado_GB / (1000 ** 3) AS DECIMAL(8,2)) AS Espacio_Ocupado_GB,
    CAST(xa.espacio_real_GB / (1000 ** 3) AS DECIMAL(8,2)) AS Espacio_Real_GB,
    xa.ratio AS Ratio
FROM (
    SELECT
        DatabaseName,
        TableName,
        SUM(CurrentPerm) AS espacio_ocupado_GB,
        MAX(CurrentPerm) * (SEL HASHAMP() + 1) AS espacio_real_GB,
        100 * espacio_real_GB / espacio_ocupado_GB AS ratio
    FROM DBC.TableSizeV
    WHERE DatabaseName NOT IN ('DBC')
    GROUP BY 1, 2
    HAVING
        (espacio_ocupado_GB > 1000 ** 3 AND ratio > 150)
        OR (espacio_real_GB - espacio_ocupado_GB > 10 * (1000 ** 3))
) xa
ORDER BY 3 DESC;""".strip()


def get_incremental_restore_sql():
    return """SELECT
    tables.DatabaseName,
    tables.TableName,
    tables.TableKind,
    tables.IncrementalRestoreEnabled,
    COALESCE(table_space.CurrentPerm, 0) / (1000 ** 3) AS Current_Perm_GB
FROM DBC.TablesV AS tables
LEFT JOIN (
    SELECT
        DatabaseName,
        TableName,
        SUM(CurrentPerm) AS CurrentPerm
    FROM DBC.TableSizeV
    GROUP BY DatabaseName, TableName
) AS table_space
    ON tables.DatabaseName = table_space.DatabaseName
   AND tables.TableName = table_space.TableName
WHERE tables.IncrementalRestoreEnabled IS NOT NULL
ORDER BY tables.IncrementalRestoreEnabled, Current_Perm_GB DESC;""".strip()


def get_incremental_restore_history_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT
    space_hist.LogDate,
    space_hist.DatabaseName,
    space_hist.TableName,
    tables.TableKind,
    tables.IncrementalRestoreEnabled,
    SUM(space_hist.CurrentPerm) / (1000 ** 3) AS Current_Perm_GB
FROM PDCRINFO.TableSpace_Hst AS space_hist
INNER JOIN DBC.TablesV AS tables
    ON space_hist.DatabaseName = tables.DatabaseName
   AND space_hist.TableName = tables.TableName
WHERE space_hist.LogDate BETWEEN DATE '{start_str}' AND DATE '{end_str}'
  AND tables.IncrementalRestoreEnabled IS NOT NULL
GROUP BY
    space_hist.LogDate,
    space_hist.DatabaseName,
    space_hist.TableName,
    tables.TableKind,
    tables.IncrementalRestoreEnabled
ORDER BY
    space_hist.LogDate,
    tables.IncrementalRestoreEnabled,
    space_hist.DatabaseName,
    space_hist.TableName;""".strip()


def find_column_case_insensitive(dataframe: pd.DataFrame, column_name: str):
    return next(
        (
            column
            for column in dataframe.columns
            if str(column).casefold() == column_name.casefold()
        ),
        None,
    )


def get_workload_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT 
    LogDate,
    WDNAME AS WORKLOAD,
    SUM(AMPCPUTIME) AS TiempoCPU,
    SUM(TotalIOCount) AS IO,
    SUM(SPOOLUSAGE) AS "SPOOL",
    SUM(DELAYTIME) AS DELAY,
    COUNT(*) AS CONCURRENCIA
FROM PDCRINFO.DBQLogTbl_hst
WHERE LogDate BETWEEN '{start_str}' AND '{end_str}'
GROUP BY 1, 2;""".strip()


def get_memory_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT     
    TheDate (FORMAT 'YYYY-MM-DD') AS TheDate,    
    EXTRACT (YEAR FROM TheDate) AS año,    
    EXTRACT (MONTH FROM TheDate) AS mes,    
    EXTRACT (DAY FROM TheDate) AS dia,    
    CAST((TheTime (FORMAT '99:99:99')) AS CHAR(8)) AS TheTime,    
    EXTRACT(HOUR FROM TheTime) AS hr,    
    EXTRACT(MINUTE FROM TheTime) AS mn,    
    SUM(MemFreeKB/(1024.0*1024.0)) AS FreeMemGB                        
FROM DBC.ResUsageSpma    
WHERE TheDate BETWEEN '{start_str}' AND '{end_str}'    
  AND vproctype1='AMP' 
  AND vproc1 > 0    
GROUP BY TheDate, año, mes, dia, TheTime, hr, mn
ORDER BY TheDate, TheTime;""".strip()


def get_swap_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT
    TheYear,
    TheMonth,
    a.TheDate,
    DayOfWeek,
    TheTime,
    CAST(a.TheDate AS FORMAT 'YYYY-MM-DDB') || CAST(CAST(EXTRACT(HOUR FROM TheTime) AS FORMAT '99') AS CHAR(2)) ||':'|| CAST(CAST(EXTRACT(MINUTE FROM TheTime) AS FORMAT '99') AS CHAR(2)) || ':00' AS TheDateTime,
    NodeType,
    SUM(Secs) AS Secs,
    SUM(NCPUs) AS NCPUs,
    SUM(( MemTextPageReads + MemCtxtPageReads + MemCtxtPageWrites )*4) AS PageOrSwapIOKB,
    SUM(( MemCtxtPageWrites+MemCtxtPageReads)/NULLIFZERO(Secs)) AS SwapPerSeconds,
    SUM(MemTextPageReads) AS SegIOReads,
    SUM(MemCtxtPageWrites) AS MemCtxtPageWrites,
    SUM(MemCtxtPageReads) AS MemCtxtPageReads
FROM PDCRDATA.ResUsageSpma_HST AS a
INNER JOIN
(
    SELECT 
        calendar_date AS TheDate, 
        EXTRACT(YEAR FROM calendar_date) AS TheYear,
        EXTRACT(MONTH FROM calendar_date) AS TheMonth,
        CASE
            WHEN day_of_week = 1 THEN 'Domingo'
            WHEN day_of_week = 2 THEN 'Lunes'
            WHEN day_of_week = 3 THEN 'Martes'
            WHEN day_of_week = 4 THEN 'Miércoles'
            WHEN day_of_week = 5 THEN 'Jueves'
            WHEN day_of_week = 6 THEN 'Viernes'
            WHEN day_of_week = 7 THEN 'Sábado'
        END DayOfWeek
    FROM sys_calendar.CALENDAR
) AS b
ON a.TheDate = b.TheDate
WHERE a.TheDate BETWEEN '{start_str}' AND '{end_str}'
  AND Vproc1 > 0
GROUP BY TheYear, TheMonth, a.TheDate, DayOfWeek, TheTime, TheDateTime, NodeType
ORDER BY TheDateTime;""".strip()


def get_flow_control_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT
    TheYear,
    TheMonth,
    a.TheDate,
    NodeID,
    DayOfWeek,
    TheTime,
    CAST((CAST(a.TheDate AS FORMAT 'YYYY-MM-DDB') || CAST(CAST(EXTRACT(HOUR FROM TheTime) AS FORMAT '99') AS CHAR(2)) ||':'|| CAST(CAST(EXTRACT(MINUTE FROM TheTime) AS FORMAT '99') AS CHAR(2)) || ':00') AS TIMESTAMP(0)) AS TheDateTime,
    HASHAMP()+1 AS AMPs,
    MAX(Secs) AS Secs,
    MAX(120) AS AWTs,
    
    -- FlowControl
    AVG(MailboxDepth) (FORMAT 'ZZZZZ9') AS AVG_MailBoxDepth,
    MAX(MailboxDepth) (FORMAT 'ZZZZZ9') AS MAX_MailBoxDepth,
    
    SUM(CASE WHEN FlowCtlTime > 0 THEN 1 ELSE 0 END) (FORMAT 'ZZ9.99') AS Number_AMP_in_FlowCtl,
    
    AVG(FlowCtlCnt) (FORMAT 'ZZ9.9') AS AVG_AMP_Time_Enter_in_FlowCtl, 
    MAX(FlowCtlCnt) (FORMAT 'ZZ9.99') AS MAX_AMP_Time_Enter_in_FlowCtl, 
    
    AVG(FlowCtlTime/1000) (FORMAT 'ZZ9.99') AS AVG_Segs_In_FlowCtl,
    MAX(FlowCtlTime/1000) (FORMAT 'ZZ9.99') AS MAX_Segs_In_FlowCtl,
    
    -- AWTs in Use and by type
    AVG(InUseMax) (FORMAT 'ZZ9.99') AS AVG_InUseMax,
    MIN(InUseMax) (FORMAT 'ZZ9.99') AS MIN_InUseMax,
    MAX(InUseMax) (FORMAT 'ZZ9.99') AS MAX_InUseMax,
    
    AVG(WorkTypeInUse00+WorkTypeInUse01) (FORMAT 'ZZ9') AS AVG_New_One_AWTs,
    MAX(WorkTypeMax00+WorkTypeMax01) (FORMAT 'ZZ9') AS MAX_New_One_AWTs,
    
    AVG(WorkTypeInUse00) (FORMAT 'ZZ9') AS Work_New_AWTs,
    AVG(WorkTypeInUse01) (FORMAT 'ZZ9') AS Work_One_AWTs,
    AVG(WorkTypeInUse02) (FORMAT 'ZZ9') AS Work_Two_AWTs,
    AVG(WorkTypeInUse03) (FORMAT 'ZZ9') AS Work_3_AWTs,
    AVG(WorkTypeInUse12) (FORMAT 'ZZ9') AS Work_Abrt_AWTs,
    AVG(WorkTypeInUse13) (FORMAT 'ZZ9') AS Work_Spwn_AWTs,
    AVG(WorkTypeInUse14) (FORMAT 'ZZ9') AS Work_Norm_AWTs,
    AVG(WorkTypeInUse15) (FORMAT 'ZZ9') AS Work_Ctl_AWTs,
    AVG(WorkTypeInUse08) (FORMAT 'ZZ9') AS Work_Exp_AWTs,
    MAX(WorkTypeMax00) (FORMAT 'ZZ9') AS MAX_Work_New_AWTs,
    MAX(WorkTypeMax01) (FORMAT 'ZZ9') AS MAX_Work_One_AWTs,
    MAX(WorkTypeMax02) (FORMAT 'ZZ9') AS MAX_Work_Two_AWTs,
    MAX(WorkTypeMax03) (FORMAT 'ZZ9') AS MAX_Work_3_AWTs,
    MAX(WorkTypeMax12) (FORMAT 'ZZ9') AS MAX_Work_Abrt_AWTs,
    MAX(WorkTypeMax13) (FORMAT 'ZZ9') AS MAX_Work_Spwn_AWTs,
    MAX(WorkTypeMax14) (FORMAT 'ZZ9') AS MAX_Work_Norm_AWTs,
    MAX(WorkTypeMax15) (FORMAT 'ZZ9') AS MAX_Work_Ctl_AWTs,
    MAX(WorkTypeMax08) (FORMAT 'ZZ9') AS MAX_Work_Exp_AWTs

FROM
    dbc.ResUsageSAWT AS a
    INNER JOIN
    (
            SELECT 
                    calendar_date AS TheDate,
                    EXTRACT(YEAR FROM calendar_date) AS TheYear,
                    EXTRACT(MONTH FROM calendar_date) AS TheMonth,
                    CASE
                            WHEN day_of_week = 1 THEN 'Domingo'
                            WHEN day_of_week = 2 THEN 'Lunes'
                            WHEN day_of_week = 3 THEN 'Martes'
                            WHEN day_of_week = 4 THEN 'Miercoles'
                            WHEN day_of_week = 5 THEN 'Jueves'
                            WHEN day_of_week = 6 THEN 'Viernes'
                            WHEN day_of_week = 7 THEN 'Sabado'
                    END DayOfWeek
            FROM sys_calendar.CALENDAR
    ) AS b
    ON a.TheDate = b.TheDate
WHERE a.TheDate BETWEEN '{start_str}' AND '{end_str}'
GROUP BY 1,2,3,4,5,6;""".strip()


def get_single_line_inserts_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT
    CAST(LogDate AS DATE) AS LogDate,
    SessionID,
    UserName,
    COUNT(*) AS InsertCount
FROM PDCRDATA.DBQLogTbl_Hst
WHERE
    StmtDMLRowCount = '{{\"Insert\":1}}'
    AND QueryText LIKE 'INSERT%'
    AND LogDate BETWEEN DATE '{start_str}' AND DATE '{end_str}'
    AND StartTime >= TIMESTAMP '{start_str} 00:00:00'
    AND StartTime <= TIMESTAMP '{end_str} 23:59:59'
GROUP BY 1,2,3
HAVING COUNT(*) > 1000
ORDER BY InsertCount DESC;""".strip()


def get_error_espacio_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""Select logdate, right(trim(ErrorText),20) as basededatos,
 count(*) as cnt
from PDCRInfo.DBQLogTbl_hst
where LogDate BETWEEN DATE '{start_str}' AND DATE '{end_str}'
and ErrorText like 'No more room%'
group by 1,2;""".strip()


def get_error_spool_sql(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return f"""SELECT
    LogDate,
    UPPER(
        TRIM(TRAILING '.' FROM 
            REGEXP_REPLACE(
                ErrorText, 
                '^.*IN\\s+([A-Z0-9_$.]+).*$', 
                '\\1', 
                1, 
                1, 
                'i'
            )
        )
    ) AS username,
    COUNT(*) AS cnt
FROM PDCRInfo.DBQLogTbl_hst
WHERE LogDate BETWEEN DATE '{start_str}' AND DATE '{end_str}'
  AND ErrorCode IN (2646, 2647)
GROUP BY 1, 2
ORDER BY cnt DESC;""".strip()


# =========================================================
# PAGE 1: GRAFICAS DIA DEDICADO
# =========================================================
if selected_page == "📊 Graficas dia dedicated" or selected_page == "📊 Graficas dia dedicado":
    st.title("Teradata management & export tool")
    st.markdown('<div class="td-accent-bar"></div>', unsafe_allow_html=True)

    (
        tab_adhoc,
        tab_backups,
        tab_workload,
        tab_io,
        tab_concurrencia,
        tab_memory,
        tab_swap,
        tab_flow,
    ) = st.tabs(
        [
            "🔍 Ad-hoc query runner",
            "📊 Backup status report",
            "📈 Workload CPU analysis",
            "💾 Workload I/O analysis",
            "⚡ Workload concurrencia",
            "🧠 Memory status",
            "🔄 Swap analysis",
            "⚡ FlowControl Analysis",
        ]
    )

    # ---------------------------------------------------------
    # TAB 1: Ad-hoc Query Runner
    # ---------------------------------------------------------
    with tab_adhoc:
        st.subheader("Ad-hoc SQL execution")
        query = st.text_area(
            "Enter SQL query",
            value="SELECT * FROM DBC.TablesV SAMPLE 10;",
            height=150,
            key="adhoc_sql",
        )

        if st.button("Execute query", type="primary", key="btn_adhoc"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not query.strip():
                st.warning("Please enter a SQL query.")
            else:
                try:
                    with st.spinner("Connecting to Teradata and executing query..."):
                        df = execute_teradata_query(query)

                    st.success(
                        f"Query returned {len(df)} rows. {query_duration_text()}"
                    )
                    st.dataframe(df, use_container_width=True)

                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name="teradata_export.csv",
                        mime="text/csv",
                        type="secondary",
                        key="dl_adhoc",
                    )
                except Exception as e:
                    st.error(f"Error executing query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 2: Backup Status Report
    # ---------------------------------------------------------
    with tab_backups:
        st.subheader("Última ejecución - Análisis de jobs de backup")

        if "backup_start_date" not in st.session_state:
            st.session_state["backup_start_date"] = DEFAULT_START_DATE
        if "backup_end_date" not in st.session_state:
            st.session_state["backup_end_date"] = DEFAULT_END_DATE
        if "backup_sql_area" not in st.session_state:
            st.session_state["backup_sql_area"] = get_backup_sql(
                st.session_state["backup_start_date"],
                st.session_state["backup_end_date"],
            )

        col_bk_date1, col_bk_date2 = st.columns(2)
        with col_bk_date1:
            start_date_bk = st.date_input(
                "Start date",
                value=st.session_state["backup_start_date"],
                key="input_backup_start_date",
            )
        with col_bk_date2:
            end_date_bk = st.date_input(
                "End date",
                value=st.session_state["backup_end_date"],
                key="input_backup_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_backup_dates"):
            st.session_state["backup_start_date"] = start_date_bk
            st.session_state["backup_end_date"] = end_date_bk
            st.session_state["backup_sql_area"] = get_backup_sql(start_date_bk, end_date_bk)
            st.rerun()

        sql_backup_input = st.text_area(
            "Backup query definition",
            height=300,
            key="backup_sql_area",
        )

        if st.button("Execute backup report", type="primary", key="btn_backup"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_backup_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Fetching backup metrics from Teradata..."):
                        df_backup = execute_teradata_query(sql_backup_input)

                    st.success(
                        f"Retrieved {len(df_backup)} backup job execution records. "
                        f"{query_duration_text()}"
                    )

                    if not df_backup.empty:
                        status_icon_map = {
                            "4": "🟢",
                            "3": "🟠",
                            "2": "🟡",
                            "1": "🔴",
                            "0": "⚪",
                        }
                        if "estado_numerico" in df_backup.columns:
                            df_backup["Finalización"] = df_backup["estado_numerico"].astype(str).map(status_icon_map)

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Total jobs executed", len(df_backup))
                        c2.metric(
                            "Successful (Status 4)",
                            len(df_backup[df_backup["estado_numerico"] == "4"]) if "estado_numerico" in df_backup.columns else 0,
                        )
                        c3.metric(
                            "Warnings / errors (Status 2-3)",
                            len(df_backup[df_backup["estado_numerico"].isin(["2", "3"])]) if "estado_numerico" in df_backup.columns else 0,
                        )
                        c4.metric(
                            "Failures (Status 1)",
                            len(df_backup[df_backup["estado_numerico"] == "1"]) if "estado_numerico" in df_backup.columns else 0,
                        )

                        column_order = [
                            "Nombre Job",
                            "Fecha",
                            "Hora Inicio",
                            "Hora Fin",
                            "Duración segundos",
                            "Finalización",
                            "Estado",
                            "Tamaño",
                            "Velocidad",
                            "historico",
                        ]
                        
                        display_cols = [c for c in column_order if c in df_backup.columns]

                        st.dataframe(
                            df_backup[display_cols],
                            column_config={
                                "Duración segundos": st.column_config.ProgressColumn(
                                    "Duración segundos",
                                    help="Execution time in seconds",
                                    format="%d",
                                    min_value=0,
                                    max_value=int(df_backup["Duración segundos"].max()) if "Duración segundos" in df_backup.columns and not df_backup["Duración segundos"].isnull().all() else 100,
                                ),
                                "Finalización": st.column_config.TextColumn("Finalización", width="small"),
                            },
                            use_container_width=True,
                            hide_index=True,
                        )

                        csv_backup = df_backup.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Download backup report as CSV",
                            data=csv_backup,
                            file_name="backup_jobs_execution_analysis.csv",
                            mime="text/csv",
                            type="secondary",
                            key="dl_backup",
                        )

                except Exception as e:
                    st.error(f"Error executing backup query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 3: Workload CPU Analysis
    # ---------------------------------------------------------
    with tab_workload:
        st.subheader("CPU por workload analysis")

        if "workload_start_date" not in st.session_state:
            st.session_state["workload_start_date"] = DEFAULT_START_DATE
        if "workload_end_date" not in st.session_state:
            st.session_state["workload_end_date"] = DEFAULT_END_DATE
        if "workload_sql_area" not in st.session_state:
            st.session_state["workload_sql_area"] = get_workload_sql(
                st.session_state["workload_start_date"],
                st.session_state["workload_end_date"],
            )

        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input(
                "Start date",
                value=st.session_state["workload_start_date"],
                key="input_workload_start_date",
            )
        with col_date2:
            end_date = st.date_input(
                "End date",
                value=st.session_state["workload_end_date"],
                key="input_workload_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_workload_dates"):
            st.session_state["workload_start_date"] = start_date
            st.session_state["workload_end_date"] = end_date
            st.session_state["workload_sql_area"] = get_workload_sql(start_date, end_date)
            st.rerun()

        sql_workload_input = st.text_area(
            "Workload history query definition",
            height=240,
            key="workload_sql_area",
        )

        if st.button("Generate workload graph", type="primary", key="btn_workload"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_workload_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Extracting workload history from PDCRINFO..."):
                        df_workload = execute_teradata_query(sql_workload_input)

                    st.success(
                        f"Retrieved {len(df_workload)} workload entries. "
                        f"{query_duration_text()}"
                    )

                    if not df_workload.empty:
                        df_workload["LogDate"] = pd.to_datetime(df_workload["LogDate"])
                        df_workload = df_workload.sort_values("LogDate")
                        df_workload["TiempoCPU_Millones"] = df_workload["TiempoCPU"] / 1_000_000

                        fig = px.line(
                            df_workload,
                            x="LogDate",
                            y="TiempoCPU_Millones",
                            color="WORKLOAD",
                            color_discrete_sequence=active_sequence,
                        )
                        fig = apply_td_layout(
                            fig,
                            title_text="CPU por workload",
                            y_label="CPU (Millones de segundos)",
                        )

                        st.plotly_chart(fig, use_container_width=True)

                        with st.expander("View raw data & export"):
                            st.dataframe(df_workload, use_container_width=True)
                            csv_workload = df_workload.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download workload data as CSV",
                                data=csv_workload,
                                file_name="workload_cpu_report.csv",
                                mime="text/csv",
                                type="secondary",
                                key="dl_workload",
                            )

                except Exception as e:
                    st.error(f"Error executing workload query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 4: Workload I/O Analysis
    # ---------------------------------------------------------
    with tab_io:
        st.subheader("I/O por workload analysis")

        if "workload_io_start_date" not in st.session_state:
            st.session_state["workload_io_start_date"] = DEFAULT_START_DATE
        if "workload_io_end_date" not in st.session_state:
            st.session_state["workload_io_end_date"] = DEFAULT_END_DATE
        if "workload_io_sql_area" not in st.session_state:
            st.session_state["workload_io_sql_area"] = get_workload_sql(
                st.session_state["workload_io_start_date"],
                st.session_state["workload_io_end_date"],
            )

        col_io_date1, col_io_date2 = st.columns(2)
        with col_io_date1:
            start_date_io = st.date_input(
                "Start date",
                value=st.session_state["workload_io_start_date"],
                key="input_workload_io_start_date",
            )
        with col_io_date2:
            end_date_io = st.date_input(
                "End date",
                value=st.session_state["workload_io_end_date"],
                key="input_workload_io_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_workload_io_dates"):
            st.session_state["workload_io_start_date"] = start_date_io
            st.session_state["workload_io_end_date"] = end_date_io
            st.session_state["workload_io_sql_area"] = get_workload_sql(start_date_io, end_date_io)
            st.rerun()

        sql_workload_io_input = st.text_area(
            "Workload history query definition",
            height=240,
            key="workload_io_sql_area",
        )

        if st.button("Generate workload graph", type="primary", key="btn_workload_io"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_workload_io_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Extracting workload history from PDCRINFO..."):
                        df_workload_io = execute_teradata_query(sql_workload_io_input)

                    st.success(
                        f"Retrieved {len(df_workload_io)} workload entries. "
                        f"{query_duration_text()}"
                    )

                    if not df_workload_io.empty:
                        df_workload_io["LogDate"] = pd.to_datetime(df_workload_io["LogDate"])
                        df_workload_io = df_workload_io.sort_values("LogDate")

                        fig_io = px.line(
                            df_workload_io,
                            x="LogDate",
                            y="IO",
                            color="WORKLOAD",
                            color_discrete_sequence=active_sequence,
                        )
                        fig_io = apply_td_layout(
                            fig_io,
                            title_text="I/O por workload",
                            y_label="Total I/O count",
                        )

                        st.plotly_chart(fig_io, use_container_width=True)

                        with st.expander("View raw data & export"):
                            st.dataframe(df_workload_io, use_container_width=True)
                            csv_workload_io = df_workload_io.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download workload data as CSV",
                                data=csv_workload_io,
                                file_name="workload_io_report.csv",
                                mime="text/csv",
                                type="secondary",
                                key="dl_workload_io",
                            )

                except Exception as e:
                    st.error(f"Error executing workload query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 5: Workload Concurrencia
    # ---------------------------------------------------------
    with tab_concurrencia:
        st.subheader("Concurrencia por workload analysis")

        if "workload_conc_start_date" not in st.session_state:
            st.session_state["workload_conc_start_date"] = DEFAULT_START_DATE
        if "workload_conc_end_date" not in st.session_state:
            st.session_state["workload_conc_end_date"] = DEFAULT_END_DATE
        if "workload_conc_sql_area" not in st.session_state:
            st.session_state["workload_conc_sql_area"] = get_workload_sql(
                st.session_state["workload_conc_start_date"],
                st.session_state["workload_conc_end_date"],
            )

        col_conc_date1, col_conc_date2 = st.columns(2)
        with col_conc_date1:
            start_date_conc = st.date_input(
                "Start date",
                value=st.session_state["workload_conc_start_date"],
                key="input_workload_conc_start_date",
            )
        with col_conc_date2:
            end_date_conc = st.date_input(
                "End date",
                value=st.session_state["workload_conc_end_date"],
                key="input_workload_conc_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_workload_conc_dates"):
            st.session_state["workload_conc_start_date"] = start_date_conc
            st.session_state["workload_conc_end_date"] = end_date_conc
            st.session_state["workload_conc_sql_area"] = get_workload_sql(start_date_conc, end_date_conc)
            st.rerun()

        sql_workload_conc_input = st.text_area(
            "Workload history query definition",
            height=240,
            key="workload_conc_sql_area",
        )

        if st.button("Generate workload graph", type="primary", key="btn_workload_conc"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_workload_conc_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Extracting workload history from PDCRINFO..."):
                        df_workload_conc = execute_teradata_query(sql_workload_conc_input)

                    st.success(
                        f"Retrieved {len(df_workload_conc)} workload entries. "
                        f"{query_duration_text()}"
                    )

                    if not df_workload_conc.empty:
                        df_workload_conc["LogDate"] = pd.to_datetime(df_workload_conc["LogDate"])
                        df_workload_conc = df_workload_conc.sort_values("LogDate")

                        fig_conc = px.line(
                            df_workload_conc,
                            x="LogDate",
                            y="CONCURRENCIA",
                            color="WORKLOAD",
                            color_discrete_sequence=active_sequence,
                        )
                        fig_conc = apply_td_layout(
                            fig_conc,
                            title_text="Concurrencia por workload",
                            y_label="Número de consultas (Concurrencia)",
                        )

                        st.plotly_chart(fig_conc, use_container_width=True)

                        with st.expander("View raw data & export"):
                            st.dataframe(df_workload_conc, use_container_width=True)
                            csv_workload_conc = df_workload_conc.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download workload data as CSV",
                                data=csv_workload_conc,
                                file_name="workload_concurrencia_report.csv",
                                mime="text/csv",
                                type="secondary",
                                key="dl_workload_conc",
                            )

                except Exception as e:
                    st.error(f"Error executing workload query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 6: Memory Status
    # ---------------------------------------------------------
    with tab_memory:
        st.subheader("System memory status (FreeMemGB)")

        if "mem_start_date" not in st.session_state:
            st.session_state["mem_start_date"] = DEFAULT_START_DATE
        if "mem_end_date" not in st.session_state:
            st.session_state["mem_end_date"] = DEFAULT_END_DATE
        if "memory_sql_area" not in st.session_state:
            st.session_state["memory_sql_area"] = get_memory_sql(
                st.session_state["mem_start_date"],
                st.session_state["mem_end_date"],
            )

        col_mem_date1, col_mem_date2 = st.columns(2)
        with col_mem_date1:
            start_date_mem = st.date_input(
                "Start date",
                value=st.session_state["mem_start_date"],
                key="input_mem_start_date",
            )
        with col_mem_date2:
            end_date_mem = st.date_input(
                "End date",
                value=st.session_state["mem_end_date"],
                key="input_mem_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_memory_dates"):
            st.session_state["mem_start_date"] = start_date_mem
            st.session_state["mem_end_date"] = end_date_mem
            st.session_state["memory_sql_area"] = get_memory_sql(start_date_mem, end_date_mem)
            st.rerun()

        sql_memory_input = st.text_area(
            "Memory query definition",
            height=240,
            key="memory_sql_area",
        )

        if st.button("Execute memory check", type="primary", key="btn_memory"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_memory_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Extracting memory usage from DBC.ResUsageSpma..."):
                        df_mem = execute_teradata_query(sql_memory_input)

                    st.success(
                        f"Retrieved {len(df_mem)} memory usage records. "
                        f"{query_duration_text()}"
                    )

                    if not df_mem.empty:
                        df_mem["Timestamp"] = pd.to_datetime(
                            df_mem["TheDate"].astype(str) + " " + df_mem["TheTime"].astype(str)
                        )

                        fig_mem = px.line(
                            df_mem,
                            x="Timestamp",
                            y="FreeMemGB",
                            color_discrete_sequence=[TD_ORANGE],
                        )
                        fig_mem = apply_td_layout(
                            fig_mem,
                            title_text="Total system free memory (GB)",
                            y_label="Free Memory (GB)",
                        )

                        st.plotly_chart(fig_mem, use_container_width=True)

                        with st.expander("View raw memory data & export"):
                            st.dataframe(df_mem, use_container_width=True)
                            csv_mem = df_mem.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download memory report as CSV",
                                data=csv_mem,
                                file_name="memory_status_report.csv",
                                mime="text/csv",
                                type="secondary",
                                key="dl_mem",
                            )

                except Exception as e:
                    st.error(f"Error executing memory query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 7: Swap Analysis
    # ---------------------------------------------------------
    with tab_swap:
        st.subheader("System swap & paging I/O analysis")

        if "swap_start_date" not in st.session_state:
            st.session_state["swap_start_date"] = DEFAULT_START_DATE
        if "swap_end_date" not in st.session_state:
            st.session_state["swap_end_date"] = DEFAULT_END_DATE
        if "swap_sql_area" not in st.session_state:
            st.session_state["swap_sql_area"] = get_swap_sql(
                st.session_state["swap_start_date"],
                st.session_state["swap_end_date"],
            )

        col_swap_date1, col_swap_date2 = st.columns(2)
        with col_swap_date1:
            start_date_swap = st.date_input(
                "Start date",
                value=st.session_state["swap_start_date"],
                key="input_swap_start_date",
            )
        with col_swap_date2:
            end_date_swap = st.date_input(
                "End date",
                value=st.session_state["swap_end_date"],
                key="input_swap_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_swap_dates"):
            st.session_state["swap_start_date"] = start_date_swap
            st.session_state["swap_end_date"] = end_date_swap
            st.session_state["swap_sql_area"] = get_swap_sql(start_date_swap, end_date_swap)
            st.rerun()

        sql_swap_input = st.text_area(
            "Swap history query definition",
            height=280,
            key="swap_sql_area",
        )

        if st.button("Execute swap report", type="primary", key="btn_swap"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_swap_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Extracting swap metrics from PDCRDATA.ResUsageSpma_HST..."):
                        df_swap = execute_teradata_query(sql_swap_input)

                    st.success(
                        f"Retrieved {len(df_swap)} swap metrics records. "
                        f"{query_duration_text()}"
                    )

                    if not df_swap.empty:
                        # Dual axis Plotly figure enabling/disabling metrics via legend click
                        fig_swap = go.Figure()

                        if "PageOrSwapIOKB" in df_swap.columns:
                            fig_swap.add_trace(
                                go.Scatter(
                                    x=df_swap["TheDateTime"],
                                    y=df_swap["PageOrSwapIOKB"],
                                    mode="lines",
                                    name="Page / Swap I/O (KB)",
                                    line=dict(color=TD_BLUE, width=2),
                                    yaxis="y1",
                                )
                            )

                        if "SwapPerSeconds" in df_swap.columns:
                            fig_swap.add_trace(
                                go.Scatter(
                                    x=df_swap["TheDateTime"],
                                    y=df_swap["SwapPerSeconds"],
                                    mode="lines",
                                    name="Swap / Second",
                                    line=dict(color=TD_ORANGE, width=2),
                                    yaxis="y2",
                                )
                            )

                        fig_swap = apply_td_layout(
                            fig_swap,
                            title_text="Total system page / swap metrics (Click legend items to show/hide)",
                        )

                        # Dual y-axis layout configuration
                        fig_swap.update_layout(
                            yaxis=dict(
                                title=dict(text="Page / Swap I/O (KB)", font=dict(color=TD_BLUE, size=11)),
                                gridcolor=chart_grid,
                                linecolor=chart_grid,
                                tickfont=dict(color=chart_text, size=10),
                                showgrid=True,
                                zeroline=False,
                            ),
                            yaxis2=dict(
                                title=dict(text="Swap / Second", font=dict(color=TD_ORANGE, size=11)),
                                tickfont=dict(color=chart_text, size=10),
                                overlaying="y",
                                side="right",
                                showgrid=False,
                                zeroline=False,
                            ),
                        )

                        st.plotly_chart(fig_swap, use_container_width=True)

                        with st.expander("View raw swap data & export"):
                            st.dataframe(df_swap, use_container_width=True)
                            csv_swap = df_swap.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download swap report as CSV",
                                data=csv_swap,
                                file_name="swap_analytics_report.csv",
                                mime="text/csv",
                                type="secondary",
                                key="dl_swap",
                            )

                except Exception as e:
                    st.error(f"Error executing swap query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 8: FlowControl Analysis
    # ---------------------------------------------------------
    with tab_flow:
        st.subheader("FlowControl & AWT Analysis")
        st.markdown("Monitoring AMP mailbox depths, flow control entries, and execution delays from `dbc.ResUsageSAWT`.")

        if "flow_start_date" not in st.session_state:
            st.session_state["flow_start_date"] = DEFAULT_START_DATE
        if "flow_end_date" not in st.session_state:
            st.session_state["flow_end_date"] = DEFAULT_END_DATE
        if "flow_sql_area" not in st.session_state:
            st.session_state["flow_sql_area"] = get_flow_control_sql(
                st.session_state["flow_start_date"],
                st.session_state["flow_end_date"],
            )

        col_flow_date1, col_flow_date2 = st.columns(2)
        with col_flow_date1:
            start_date_flow = st.date_input(
                "Start date",
                value=st.session_state["flow_start_date"],
                key="input_flow_start_date",
            )
        with col_flow_date2:
            end_date_flow = st.date_input(
                "End date",
                value=st.session_state["flow_end_date"],
                key="input_flow_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_flow_dates"):
            st.session_state["flow_start_date"] = start_date_flow
            st.session_state["flow_end_date"] = end_date_flow
            st.session_state["flow_sql_area"] = get_flow_control_sql(start_date_flow, end_date_flow)
            st.rerun()

        sql_flow_input = st.text_area(
            "FlowControl query definition",
            height=280,
            key="flow_sql_area",
        )

        if st.button("Execute FlowControl report", type="primary", key="btn_flow"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_flow_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Extracting FlowControl metrics from dbc.ResUsageSAWT..."):
                        df_flow = execute_teradata_query(sql_flow_input)

                    st.success(
                        f"Retrieved {len(df_flow)} FlowControl metric records. "
                        f"{query_duration_text()}"
                    )

                    if not df_flow.empty:
                        fig_flow = px.line(
                            df_flow, 
                            x='TheDateTime', 
                            y=['Number_AMP_in_FlowCtl', 'AVG_Segs_In_FlowCtl'],
                            labels={
                                'value': 'Metric Measurement', 
                                'TheDateTime': 'Timeline', 
                                'variable': 'FlowControl Indicator'
                            },
                            title='AMPs in FlowControl vs. Average Seconds in FlowControl',
                            color_discrete_sequence=active_sequence
                        )
                        fig_flow = apply_td_layout(
                            fig_flow,
                            title_text="AMPs in FlowControl vs. Average Seconds in FlowControl",
                            y_label="Metric Measurement"
                        )
                        st.plotly_chart(fig_flow, use_container_width=True)

                        with st.expander("View raw FlowControl data & export"):
                            st.dataframe(df_flow, use_container_width=True)
                            csv_flow = df_flow.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download FlowControl report as CSV",
                                data=csv_flow,
                                file_name="flow_control_analytics_report.csv",
                                mime="text/csv",
                                type="secondary",
                                key="dl_flow",
                            )

                except Exception as e:
                    st.error(f"Error executing FlowControl query: {str(e)}")

# =========================================================
# PAGE 2: REVISIONES
# =========================================================
elif selected_page == "🔍 Revisiones":
    st.title("Revisiones")
    st.markdown('<div class="td-accent-bar"></div>', unsafe_allow_html=True)

    # Sub-navigation for Revisiones
    (
        tab_spool_rev,
        tab_inserts_rev,
        tab_espacio_rev,
        tab_spool_err_rev,
    ) = st.tabs(
        [
            "👻 Phantom spool checker",
            "📥 Inserciones línea a línea",
            "📦 Error de espacio",
            "🧵 Error de spool",
        ]
    )

    # ---------------------------------------------------------
    # TAB 1: Phantom Spool Checker
    # ---------------------------------------------------------
    with tab_spool_rev:
        st.subheader("Phantom spool detection")

        if "spool_sql_page2" not in st.session_state:
            st.session_state["spool_sql_page2"] = get_phantom_spool_sql()

        if not st.session_state.get("phantom_spool_date_filter_removed"):
            st.session_state["spool_sql_page2"] = "\n".join(
                line
                for line in st.session_state["spool_sql_page2"].splitlines()
                if not line.strip().upper().startswith("AND LOGDATE BETWEEN")
            )
            st.session_state["phantom_spool_date_filter_removed"] = True

        sql_spool_input = st.text_area(
            "Phantom spool query definition",
            height=200,
            key="spool_sql_page2",
        )

        if st.button("Check phantom spool", type="primary", key="btn_spool_page2"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_spool_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Scanning system for phantom spool space..."):
                        df_spool = execute_teradata_query(sql_spool_input)

                    st.success(
                        f"Scan complete. Found {len(df_spool)} database(s) holding spool. "
                        f"{query_duration_text()}"
                    )

                    if not df_spool.empty and "TOTAL_GB" in df_spool.columns:
                        c1, c2 = st.columns(2)
                        c1.metric("Impacted databases", len(df_spool))
                        c2.metric("Total phantom spool (GB)", int(df_spool["TOTAL_GB"].sum()))

                    st.dataframe(df_spool, use_container_width=True)

                    csv_spool = df_spool.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="Download spool report as CSV",
                        data=csv_spool,
                        file_name="phantom_spool_report.csv",
                        mime="text/csv",
                        type="secondary",
                        key="dl_spool_page2",
                    )

                    if "DatabaseName" in df_spool.columns:
                        fix_commands = "\n".join(
                            [
                                f"call SYSLIB.FixCurrentSpace('S', 'N', 'N', '{db}', cnt, err);"
                                for db in df_spool["DatabaseName"]
                            ]
                        )

                        st.subheader("Generated FixCurrentSpace commands")
                        st.code(fix_commands, language="sql")

                        st.download_button(
                            label="Download FixCurrentSpace script",
                            data=fix_commands,
                            file_name="fixcurrentspace.sql",
                            mime="text/plain",
                            key="dl_fixcurrentspace_page2",
                        )

                except Exception as e:
                    st.error(f"Error executing phantom spool query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 2: Inserciones línea a línea
    # ---------------------------------------------------------
    with tab_inserts_rev:
        st.subheader("Análisis de inserciones línea a línea (Single line inserts)")

        if "inserts_start_date" not in st.session_state:
            st.session_state["inserts_start_date"] = DEFAULT_START_DATE
        if "inserts_end_date" not in st.session_state:
            st.session_state["inserts_end_date"] = DEFAULT_END_DATE
        if "inserts_sql_area" not in st.session_state:
            st.session_state["inserts_sql_area"] = get_single_line_inserts_sql(
                st.session_state["inserts_start_date"],
                st.session_state["inserts_end_date"],
            )

        col_ins_date1, col_ins_date2 = st.columns(2)
        with col_ins_date1:
            start_date_ins = st.date_input(
                "Start date (LogDate)",
                value=st.session_state["inserts_start_date"],
                key="input_inserts_start_date",
            )
        with col_ins_date2:
            end_date_ins = st.date_input(
                "End date (LogDate)",
                value=st.session_state["inserts_end_date"],
                key="input_inserts_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_inserts_dates"):
            st.session_state["inserts_start_date"] = start_date_ins
            st.session_state["inserts_end_date"] = end_date_ins
            st.session_state["inserts_sql_area"] = get_single_line_inserts_sql(
                start_date_ins, end_date_ins
            )
            st.rerun()

        sql_inserts_input = st.text_area(
            "Query definition",
            height=280,
            key="inserts_sql_area",
        )

        if st.button("Execute single line inserts analysis", type="primary", key="btn_inserts_exec"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_inserts_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Analyzing DBQLogTbl_Hst for line-by-line inserts..."):
                        df_inserts = execute_teradata_query(sql_inserts_input)

                    st.success(
                        f"Retrieved {len(df_inserts)} sessions exceeding 1,000 "
                        f"single line inserts. {query_duration_text()}"
                    )

                    if not df_inserts.empty:
                        st.dataframe(df_inserts, use_container_width=True)

                        if "UserName" in df_inserts.columns and "InsertCount" in df_inserts.columns:
                            fig_inserts = px.bar(
                                df_inserts,
                                x="UserName",
                                y="InsertCount",
                                color="SessionID",
                                color_discrete_sequence=active_sequence,
                            )
                            fig_inserts = apply_td_layout(
                                fig_inserts,
                                title_text="Total single line inserts by user & session",
                                y_label="Insert count",
                            )
                            st.plotly_chart(fig_inserts, use_container_width=True)

                        csv_inserts = df_inserts.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Download inserts analysis as CSV",
                            data=csv_inserts,
                            file_name="single_line_inserts_report.csv",
                            mime="text/csv",
                            type="secondary",
                            key="dl_inserts",
                        )

                except Exception as e:
                    st.error(f"Error executing inserts query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 3: Error de espacio
    # ---------------------------------------------------------
    with tab_espacio_rev:
        st.subheader("Análisis de errores de espacio ('No more room')")

        if "espacio_start_date" not in st.session_state:
            st.session_state["espacio_start_date"] = DEFAULT_START_DATE
        if "espacio_end_date" not in st.session_state:
            st.session_state["espacio_end_date"] = DEFAULT_END_DATE
        if "espacio_sql_area" not in st.session_state:
            st.session_state["espacio_sql_area"] = get_error_espacio_sql(
                st.session_state["espacio_start_date"],
                st.session_state["espacio_end_date"],
            )

        col_esp_date1, col_esp_date2 = st.columns(2)
        with col_esp_date1:
            start_date_esp = st.date_input(
                "Start date (LogDate)",
                value=st.session_state["espacio_start_date"],
                key="input_espacio_start_date",
            )
        with col_esp_date2:
            end_date_esp = st.date_input(
                "End date (LogDate)",
                value=st.session_state["espacio_end_date"],
                key="input_espacio_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_espacio_dates"):
            st.session_state["espacio_start_date"] = start_date_esp
            st.session_state["espacio_end_date"] = end_date_esp
            st.session_state["espacio_sql_area"] = get_error_espacio_sql(
                start_date_esp, end_date_esp
            )
            st.rerun()

        sql_espacio_input = st.text_area(
            "Query definition",
            height=200,
            key="espacio_sql_area",
        )

        if st.button("Execute error de espacio analysis", type="primary", key="btn_espacio_exec"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_espacio_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Analyzing DBQLogTbl_hst for space errors..."):
                        df_espacio = execute_teradata_query(sql_espacio_input)

                    st.success(
                        f"Retrieved {len(df_espacio)} space error records. "
                        f"{query_duration_text()}"
                    )

                    if not df_espacio.empty:
                        st.dataframe(df_espacio, use_container_width=True)

                        count_col = "cnt" if "cnt" in df_espacio.columns else [c for c in df_espacio.columns if "count" in c.lower()][0]
                        db_col = "basededatos" if "basededatos" in df_espacio.columns else df_espacio.columns[1]

                        fig_espacio = px.bar(
                            df_espacio,
                            x=db_col,
                            y=count_col,
                            color="LogDate" if "LogDate" in df_espacio.columns else None,
                            color_discrete_sequence=active_sequence,
                        )
                        fig_espacio = apply_td_layout(
                            fig_espacio,
                            title_text="Space error count by database",
                            y_label="Error count",
                        )
                        st.plotly_chart(fig_espacio, use_container_width=True)

                        csv_espacio = df_espacio.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Download space error analysis as CSV",
                            data=csv_espacio,
                            file_name="error_espacio_report.csv",
                            mime="text/csv",
                            type="secondary",
                            key="dl_espacio",
                        )

                except Exception as e:
                    st.error(f"Error executing space error query: {str(e)}")

    # ---------------------------------------------------------
    # TAB 4: Error de spool
    # ---------------------------------------------------------
    with tab_spool_err_rev:
        st.subheader("Análisis de errores de spool (Error Codes 2646, 2647)")

        if "spool_err_start_date" not in st.session_state:
            st.session_state["spool_err_start_date"] = DEFAULT_START_DATE
        if "spool_err_end_date" not in st.session_state:
            st.session_state["spool_err_end_date"] = DEFAULT_END_DATE
        if "spool_err_sql_area" not in st.session_state:
            st.session_state["spool_err_sql_area"] = get_error_spool_sql(
                st.session_state["spool_err_start_date"],
                st.session_state["spool_err_end_date"],
            )

        col_spl_date1, col_spl_date2 = st.columns(2)
        with col_spl_date1:
            start_date_spl = st.date_input(
                "Start date (LogDate)",
                value=st.session_state["spool_err_start_date"],
                key="input_spool_err_start_date",
            )
        with col_spl_date2:
            end_date_spl = st.date_input(
                "End date (LogDate)",
                value=st.session_state["spool_err_end_date"],
                key="input_spool_err_end_date",
            )

        if st.button("🔄 Update query dates", key="btn_update_spool_err_dates"):
            st.session_state["spool_err_start_date"] = start_date_spl
            st.session_state["spool_err_end_date"] = end_date_spl
            st.session_state["spool_err_sql_area"] = get_error_spool_sql(
                start_date_spl, end_date_spl
            )
            st.rerun()

        sql_spool_err_input = st.text_area(
            "Query definition",
            height=280,
            key="spool_err_sql_area",
        )

        if st.button("Execute error de spool analysis", type="primary", key="btn_spool_err_exec"):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_spool_err_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Analyzing DBQLogTbl_hst for spool errors (2646/2647)..."):
                        df_spool_err = execute_teradata_query(sql_spool_err_input)

                    st.success(
                        f"Retrieved {len(df_spool_err)} spool error records. "
                        f"{query_duration_text()}"
                    )

                    if not df_spool_err.empty:
                        st.dataframe(df_spool_err, use_container_width=True)

                        if "username" in df_spool_err.columns and "cnt" in df_spool_err.columns:
                            fig_spool_err = px.bar(
                                df_spool_err,
                                x="username",
                                y="cnt",
                                color="LogDate" if "LogDate" in df_spool_err.columns else None,
                                color_discrete_sequence=active_sequence,
                            )
                            fig_spool_err = apply_td_layout(
                                fig_spool_err,
                                title_text="Spool error count by user/database",
                                y_label="Error count",
                            )
                            st.plotly_chart(fig_spool_err, use_container_width=True)

                        csv_spool_err = df_spool_err.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Download spool error analysis as CSV",
                            data=csv_spool_err,
                            file_name="error_spool_report.csv",
                            mime="text/csv",
                            type="secondary",
                            key="dl_spool_err",
                        )

                except Exception as e:
                    st.error(f"Error executing spool error query: {str(e)}")

# =========================================================
# PAGE 3: REVISION DE ESPACIO
# =========================================================
elif selected_page == "📦 Revisión de espacio":
    st.title("Revisión de espacio")
    st.markdown('<div class="td-accent-bar"></div>', unsafe_allow_html=True)
    st.markdown(
        "Consulta la evolución del espacio utilizado, agregada para todo el "
        "sistema o desglosada por base de datos."
    )

    (
        tab_space_history,
        tab_table_space,
        tab_skew_review,
        tab_incremental_restore,
        tab_incremental_restore_history,
    ) = st.tabs(
        [
            "Evolución del espacio",
            "Revisión a nivel de tablas",
            "Revisión de skew",
            "Incremental restore",
            "Incremental restore análisis",
        ]
    )
    with tab_space_history:
        if "space_review_start_date" not in st.session_state:
            st.session_state["space_review_start_date"] = TODAY - timedelta(days=365)
        if "space_review_end_date" not in st.session_state:
            st.session_state["space_review_end_date"] = DEFAULT_END_DATE
        if "space_review_sql" not in st.session_state:
            st.session_state["space_review_sql"] = get_space_review_sql(
                st.session_state["space_review_start_date"],
                st.session_state["space_review_end_date"],
            )

        col_space_date1, col_space_date2 = st.columns(2)
        with col_space_date1:
            start_date_space = st.date_input(
                "Fecha inicial",
                value=st.session_state["space_review_start_date"],
                key="input_space_review_start_date",
            )
        with col_space_date2:
            end_date_space = st.date_input(
                "Fecha final",
                value=st.session_state["space_review_end_date"],
                key="input_space_review_end_date",
            )

        if st.button("Actualizar fechas de la consulta", key="btn_update_space_review_dates"):
            if start_date_space > end_date_space:
                st.error("La fecha inicial no puede ser posterior a la fecha final.")
            else:
                st.session_state["space_review_start_date"] = start_date_space
                st.session_state["space_review_end_date"] = end_date_space
                st.session_state["space_review_sql"] = get_space_review_sql(
                    start_date_space, end_date_space
                )
                st.rerun()

        st.caption(
            "La consulta predeterminada incluye todas las bases de datos con espacio "
            "actual mayor que 0, para no omitir bases pequeñas del total del sistema. "
            "Al actualizar las fechas se regenera el SQL; puedes editarlo antes de ejecutarlo."
        )
        sql_space_review_input = st.text_area(
            "Consulta de revisión de espacio",
            height=320,
            key="space_review_sql",
        )
        space_review_chart_mode = st.selectbox(
            "Nivel del gráfico",
            options=["Sistema completo", "Por base de datos"],
            key="space_review_chart_mode",
        )

        if st.button(
            "Ejecutar revisión de espacio",
            type="primary",
            key="btn_space_review_exec",
        ):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_space_review_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Consultando el histórico de espacio..."):
                        df_space_review = execute_teradata_query(sql_space_review_input)

                    st.success(
                        f"Consulta completada. Se obtuvieron {len(df_space_review)} "
                        f"registros. {query_duration_text()}"
                    )
                    if df_space_review.empty:
                        st.info("La consulta no devolvió registros para el intervalo seleccionado.")
                    else:
                        st.dataframe(df_space_review)

                        date_col = find_column_case_insensitive(df_space_review, "LogDate")
                        database_col = find_column_case_insensitive(
                            df_space_review, "DatabaseName"
                        )
                        current_space_col = find_column_case_insensitive(
                            df_space_review, "Current_Perm_DB_GB"
                        )
                        system_capacity_col = find_column_case_insensitive(
                            df_space_review, "Max_Perm_SYS_GB"
                        )
                        user_capacity_col = find_column_case_insensitive(
                            df_space_review, "Max_User_Perm_GB"
                        )

                        if not date_col or not database_col or not current_space_col:
                            st.warning(
                                "No se puede generar el gráfico. La consulta debe devolver "
                                "las columnas LogDate, DatabaseName y Current_Perm_DB_GB."
                            )
                        else:
                            chart_data = df_space_review.copy()
                            chart_data["_space_review_date"] = pd.to_datetime(
                                chart_data[date_col], errors="coerce"
                            )
                            chart_data["_space_review_gb"] = pd.to_numeric(
                                chart_data[current_space_col], errors="coerce"
                            )
                            chart_data = chart_data.dropna(
                                subset=["_space_review_date", "_space_review_gb"]
                            )

                            if chart_data.empty:
                                st.warning(
                                    "La consulta no contiene fechas o valores de espacio "
                                    "válidos para graficar."
                                )
                            else:
                                latest_date = chart_data["_space_review_date"].max()
                                latest_data = chart_data[
                                    chart_data["_space_review_date"] == latest_date
                                ]
                                latest_total_gb = latest_data["_space_review_gb"].sum()
                                database_count = latest_data[database_col].nunique()

                                system_capacity_gb = None
                                if system_capacity_col:
                                    capacity_values = pd.to_numeric(
                                        latest_data[system_capacity_col], errors="coerce"
                                    ).dropna()
                                    if not capacity_values.empty:
                                        system_capacity_gb = capacity_values.max()

                                user_capacity_gb = None
                                if user_capacity_col:
                                    capacity_values = pd.to_numeric(
                                        latest_data[user_capacity_col], errors="coerce"
                                    ).dropna()
                                    if not capacity_values.empty:
                                        user_capacity_gb = capacity_values.max()

                                metric_columns = st.columns(4)
                                metric_columns[0].metric(
                                    "Espacio actual (GB)", f"{latest_total_gb:,.0f}"
                                )
                                metric_columns[1].metric(
                                    "Capacidad actual del sistema (GB)",
                                    f"{system_capacity_gb:,.0f}"
                                    if system_capacity_gb is not None
                                    else "—",
                                )
                                metric_columns[2].metric(
                                    "Máximo de usuario (GB)",
                                    f"{user_capacity_gb:,.0f}"
                                    if user_capacity_gb is not None
                                    else "—",
                                )
                                metric_columns[3].metric(
                                    "Bases de datos", f"{database_count:,}"
                                )

                                if space_review_chart_mode == "Sistema completo":
                                    plot_data = (
                                        chart_data.groupby(
                                            "_space_review_date", as_index=False
                                        )["_space_review_gb"]
                                        .sum()
                                        .sort_values("_space_review_date")
                                    )
                                    fig_space_review = px.line(
                                        plot_data,
                                        x="_space_review_date",
                                        y="_space_review_gb",
                                        color_discrete_sequence=active_sequence,
                                    )
                                    chart_title = "Evolución del espacio utilizado — sistema completo"
                                else:
                                    chart_data["_space_review_database"] = (
                                        chart_data[database_col]
                                        .astype("string")
                                        .fillna("Sin base de datos")
                                    )
                                    plot_data = (
                                        chart_data.groupby(
                                            [
                                                "_space_review_date",
                                                "_space_review_database",
                                            ],
                                            as_index=False,
                                        )["_space_review_gb"]
                                        .sum()
                                        .sort_values("_space_review_date")
                                    )
                                    fig_space_review = px.line(
                                        plot_data,
                                        x="_space_review_date",
                                        y="_space_review_gb",
                                        color="_space_review_database",
                                        color_discrete_sequence=active_sequence,
                                    )
                                    chart_title = "Evolución del espacio utilizado por base de datos"

                                fig_space_review = apply_td_layout(
                                    fig_space_review,
                                    title_text=chart_title,
                                    y_label="Espacio actual (GB)",
                                )
                                fig_space_review.update_layout(
                                    xaxis_title="Fecha",
                                    yaxis_title="Espacio actual (GB)",
                                )
                                st.plotly_chart(fig_space_review, width="stretch")

                        csv_space_review = df_space_review.to_csv(index=False).encode(
                            "utf-8"
                        )
                        st.download_button(
                            label="Descargar resultados en CSV",
                            data=csv_space_review,
                            file_name="revision_espacio.csv",
                            mime="text/csv",
                            key="dl_space_review",
                        )
                except Exception as e:
                    st.error(f"Error al ejecutar la consulta de revisión de espacio: {str(e)}")

    with tab_table_space:
        st.subheader("Espacio utilizado por tabla")
        st.markdown(
            "Consulta el espacio actual de cada tabla a partir de `DBC.TableSizeV`. "
            "El gráfico muestra las tablas con mayor ocupación."
        )

        if "table_space_sql" not in st.session_state:
            st.session_state["table_space_sql"] = get_table_space_sql()

        sql_table_space_input = st.text_area(
            "Consulta de espacio por tabla",
            height=220,
            key="table_space_sql",
        )
        table_chart_limit = st.number_input(
            "Número de tablas en el gráfico",
            min_value=1,
            max_value=100,
            value=20,
            step=5,
            key="table_space_chart_limit",
        )

        if st.button(
            "Ejecutar revisión por tabla",
            type="primary",
            key="btn_table_space_exec",
        ):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_table_space_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Consultando el espacio utilizado por tabla..."):
                        df_table_space = execute_teradata_query(sql_table_space_input)

                    st.success(
                        f"Consulta completada. Se obtuvieron {len(df_table_space)} "
                        f"registros. {query_duration_text()}"
                    )
                    if df_table_space.empty:
                        st.info("La consulta no devolvió registros.")
                    else:
                        st.dataframe(df_table_space)

                        database_col = find_column_case_insensitive(
                            df_table_space, "DatabaseName"
                        )
                        table_col = find_column_case_insensitive(
                            df_table_space, "TableName"
                        )
                        table_space_col = find_column_case_insensitive(
                            df_table_space, "Current_Perm_GB"
                        )

                        if not database_col or not table_col or not table_space_col:
                            st.warning(
                                "No se puede generar el gráfico. La consulta debe devolver "
                                "DatabaseName, TableName y Current_Perm_GB."
                            )
                        else:
                            chart_data = df_table_space[
                                [database_col, table_col, table_space_col]
                            ].copy()
                            chart_data["_table_space_gb"] = pd.to_numeric(
                                chart_data[table_space_col], errors="coerce"
                            )
                            chart_data = chart_data.dropna(
                                subset=["_table_space_gb"]
                            )

                            if chart_data.empty:
                                st.warning(
                                    "La consulta no contiene valores de espacio válidos "
                                    "para graficar."
                                )
                            else:
                                chart_data["_database_label"] = (
                                    chart_data[database_col]
                                    .astype("string")
                                    .fillna("Sin base de datos")
                                )
                                chart_data["_table_label"] = (
                                    chart_data[table_col]
                                    .astype("string")
                                    .fillna("Sin nombre")
                                )
                                chart_data = (
                                    chart_data.groupby(
                                        ["_database_label", "_table_label"],
                                        as_index=False,
                                    )["_table_space_gb"]
                                    .sum()
                                    .sort_values("_table_space_gb", ascending=False)
                                    .head(int(table_chart_limit))
                                )
                                chart_data["_full_table_name"] = (
                                    chart_data["_database_label"]
                                    + "."
                                    + chart_data["_table_label"]
                                )
                                chart_data = chart_data.sort_values(
                                    "_table_space_gb", ascending=True
                                )

                                fig_table_space = px.bar(
                                    chart_data,
                                    x="_table_space_gb",
                                    y="_full_table_name",
                                    orientation="h",
                                    hover_data={
                                        "_database_label": True,
                                        "_table_label": True,
                                        "_table_space_gb": ":,.2f",
                                    },
                                    color_discrete_sequence=active_sequence,
                                )
                                fig_table_space = apply_td_layout(
                                    fig_table_space,
                                    title_text=(
                                        "Tablas con mayor consumo de espacio "
                                        f"(top {int(table_chart_limit)})"
                                    ),
                                    y_label="",
                                )
                                fig_table_space.update_layout(
                                    xaxis_title="Espacio actual (GB)",
                                    yaxis_title="Base de datos y tabla",
                                )
                                st.plotly_chart(
                                    fig_table_space,
                                    width="stretch",
                                )

                        csv_table_space = df_table_space.to_csv(
                            index=False
                        ).encode("utf-8")
                        st.download_button(
                            label="Descargar resultados en CSV",
                            data=csv_table_space,
                            file_name="revision_espacio_tablas.csv",
                            mime="text/csv",
                            key="dl_table_space",
                        )
                except Exception as e:
                    st.error(
                        f"Error al ejecutar la consulta de espacio por tabla: {str(e)}"
                    )

    with tab_skew_review:
        st.subheader("Revisión de skew por tabla")
        st.markdown(
            "El ratio representa el nivel de skew: cuanto mayor sea, mayor es la "
            "desigualdad de distribución del espacio entre los AMP."
        )

        if "skew_review_sql" not in st.session_state:
            st.session_state["skew_review_sql"] = get_skew_review_sql()

        sql_skew_review_input = st.text_area(
            "Consulta de revisión de skew",
            height=300,
            key="skew_review_sql",
        )
        skew_chart_limit = st.number_input(
            "Número de tablas en el gráfico de skew",
            min_value=1,
            max_value=100,
            value=20,
            step=5,
            key="skew_review_chart_limit",
        )

        if st.button(
            "Ejecutar revisión de skew",
            type="primary",
            key="btn_skew_review_exec",
        ):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_skew_review_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner("Analizando la distribución de espacio entre AMP..."):
                        df_skew_review = execute_teradata_query(sql_skew_review_input)

                    st.success(
                        f"Consulta completada. Se obtuvieron {len(df_skew_review)} "
                        f"tablas. {query_duration_text()}"
                    )
                    if df_skew_review.empty:
                        st.info("No se encontraron tablas que cumplan los criterios de skew.")
                    else:
                        st.dataframe(df_skew_review)

                        database_col = find_column_case_insensitive(
                            df_skew_review, "DatabaseName"
                        )
                        table_col = find_column_case_insensitive(
                            df_skew_review, "TableName"
                        )
                        ratio_col = find_column_case_insensitive(
                            df_skew_review, "Ratio"
                        )

                        if not database_col or not table_col or not ratio_col:
                            st.warning(
                                "No se puede generar el gráfico. La consulta debe devolver "
                                "DatabaseName, TableName y Ratio."
                            )
                        else:
                            chart_data = df_skew_review[
                                [database_col, table_col, ratio_col]
                            ].copy()
                            chart_data["_skew_ratio"] = pd.to_numeric(
                                chart_data[ratio_col], errors="coerce"
                            )
                            chart_data = chart_data.dropna(subset=["_skew_ratio"])

                            if chart_data.empty:
                                st.warning(
                                    "La consulta no contiene ratios válidos para graficar."
                                )
                            else:
                                chart_data["_database_label"] = (
                                    chart_data[database_col]
                                    .astype("string")
                                    .fillna("Sin base de datos")
                                )
                                chart_data["_table_label"] = (
                                    chart_data[table_col]
                                    .astype("string")
                                    .fillna("Sin nombre")
                                )
                                chart_data["_full_table_name"] = (
                                    chart_data["_database_label"]
                                    + "."
                                    + chart_data["_table_label"]
                                )
                                chart_data = (
                                    chart_data.sort_values(
                                        "_skew_ratio", ascending=False
                                    )
                                    .head(int(skew_chart_limit))
                                    .sort_values("_skew_ratio", ascending=True)
                                )

                                metric_columns = st.columns(2)
                                metric_columns[0].metric(
                                    "Ratio máximo de skew",
                                    f"{chart_data['_skew_ratio'].max():,.2f}%",
                                )
                                metric_columns[1].metric(
                                    "Tablas en el gráfico",
                                    f"{len(chart_data):,}",
                                )

                                fig_skew_review = px.bar(
                                    chart_data,
                                    x="_skew_ratio",
                                    y="_full_table_name",
                                    orientation="h",
                                    hover_data={
                                        "_database_label": True,
                                        "_table_label": True,
                                        "_skew_ratio": ":,.2f",
                                    },
                                    color_discrete_sequence=active_sequence,
                                )
                                fig_skew_review = apply_td_layout(
                                    fig_skew_review,
                                    title_text=(
                                        "Tablas con mayor nivel de skew "
                                        f"(top {int(skew_chart_limit)})"
                                    ),
                                )
                                fig_skew_review.update_layout(
                                    xaxis_title="Ratio de skew (%)",
                                    yaxis_title="Base de datos y tabla",
                                )
                                st.plotly_chart(
                                    fig_skew_review,
                                    width="stretch",
                                )

                        csv_skew_review = df_skew_review.to_csv(
                            index=False
                        ).encode("utf-8")
                        st.download_button(
                            label="Descargar resultados de skew en CSV",
                            data=csv_skew_review,
                            file_name="revision_skew.csv",
                            mime="text/csv",
                            key="dl_skew_review",
                        )
                except Exception as e:
                    st.error(f"Error al ejecutar la consulta de revisión de skew: {str(e)}")

    with tab_incremental_restore:
        st.subheader("Espacio por configuración de incremental restore")
        st.markdown(
            "Consulta las tablas con `IncrementalRestoreEnabled` informado y "
            "agrega su espacio actual según el valor de esa marca."
        )

        if "incremental_restore_sql" not in st.session_state:
            st.session_state["incremental_restore_sql"] = (
                get_incremental_restore_sql()
            )

        sql_incremental_restore_input = st.text_area(
            "Consulta de incremental restore",
            height=260,
            key="incremental_restore_sql",
        )

        if st.button(
            "Ejecutar revisión de incremental restore",
            type="primary",
            key="btn_incremental_restore_exec",
        ):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_incremental_restore_input.strip():
                st.warning("Please enter a valid query.")
            else:
                try:
                    with st.spinner(
                        "Consultando tablas y espacio de incremental restore..."
                    ):
                        df_incremental_restore = execute_teradata_query(
                            sql_incremental_restore_input
                        )

                    st.success(
                        "Consulta completada. Se obtuvieron "
                        f"{len(df_incremental_restore)} tablas. "
                        f"{query_duration_text()}"
                    )
                    if df_incremental_restore.empty:
                        st.info(
                            "No se encontraron tablas con "
                            "IncrementalRestoreEnabled informado."
                        )
                    else:
                        st.dataframe(df_incremental_restore)

                        restore_flag_col = find_column_case_insensitive(
                            df_incremental_restore, "IncrementalRestoreEnabled"
                        )
                        table_space_col = find_column_case_insensitive(
                            df_incremental_restore, "Current_Perm_GB"
                        )

                        if not restore_flag_col or not table_space_col:
                            st.warning(
                                "No se puede agregar el espacio. La consulta debe devolver "
                                "IncrementalRestoreEnabled y Current_Perm_GB."
                            )
                        else:
                            chart_data = df_incremental_restore[
                                [restore_flag_col, table_space_col]
                            ].copy()
                            chart_data["_incremental_restore_flag"] = (
                                chart_data[restore_flag_col]
                                .astype("string")
                                .fillna("Sin valor")
                            )
                            chart_data["_incremental_restore_space_gb"] = pd.to_numeric(
                                chart_data[table_space_col], errors="coerce"
                            )
                            chart_data = chart_data.dropna(
                                subset=["_incremental_restore_space_gb"]
                            )
                            summary = (
                                chart_data.groupby(
                                    "_incremental_restore_flag", as_index=False
                                )
                                .agg(
                                    Current_Perm_GB=(
                                        "_incremental_restore_space_gb",
                                        "sum",
                                    ),
                                    Table_Count=(
                                        "_incremental_restore_space_gb",
                                        "size",
                                    ),
                                )
                                .sort_values("Current_Perm_GB", ascending=False)
                            )

                            if summary.empty:
                                st.warning(
                                    "La consulta no contiene valores de espacio "
                                    "válidos para agregar."
                                )
                            else:
                                st.subheader("Espacio agregado por marca")
                                st.dataframe(summary, hide_index=True)

                                fig_incremental_restore = px.bar(
                                    summary,
                                    x="_incremental_restore_flag",
                                    y="Current_Perm_GB",
                                    color="_incremental_restore_flag",
                                    color_discrete_sequence=active_sequence,
                                )
                                fig_incremental_restore = apply_td_layout(
                                    fig_incremental_restore,
                                    title_text=(
                                        "Espacio agregado por "
                                        "IncrementalRestoreEnabled"
                                    ),
                                    y_label="Espacio actual (GB)",
                                )
                                fig_incremental_restore.update_layout(
                                    xaxis_title="IncrementalRestoreEnabled",
                                    yaxis_title="Espacio actual (GB)",
                                    showlegend=False,
                                )
                                st.plotly_chart(
                                    fig_incremental_restore,
                                    width="stretch",
                                )

                        csv_incremental_restore = (
                            df_incremental_restore.to_csv(index=False).encode("utf-8")
                        )
                        st.download_button(
                            label="Descargar resultados en CSV",
                            data=csv_incremental_restore,
                            file_name="revision_incremental_restore.csv",
                            mime="text/csv",
                            key="dl_incremental_restore",
                        )
                except Exception as e:
                    st.error(
                        "Error al ejecutar la consulta de incremental restore: "
                        f"{str(e)}"
                    )

    with tab_incremental_restore_history:
        st.subheader("Análisis histórico de incremental restore")
        st.markdown(
            "Consulta el histórico de espacio de `PDCRINFO.TableSpace_Hst` para "
            "tablas cuyo valor actual de `IncrementalRestoreEnabled` está informado."
        )

        if "incremental_restore_history_start_date" not in st.session_state:
            st.session_state["incremental_restore_history_start_date"] = (
                TODAY - timedelta(days=365)
            )
        if "incremental_restore_history_end_date" not in st.session_state:
            st.session_state["incremental_restore_history_end_date"] = DEFAULT_END_DATE
        if "incremental_restore_history_sql" not in st.session_state:
            st.session_state["incremental_restore_history_sql"] = (
                get_incremental_restore_history_sql(
                    st.session_state["incremental_restore_history_start_date"],
                    st.session_state["incremental_restore_history_end_date"],
                )
            )

        col_restore_start_date, col_restore_end_date = st.columns(2)
        with col_restore_start_date:
            restore_history_start_date = st.date_input(
                "Fecha inicial",
                value=st.session_state["incremental_restore_history_start_date"],
                key="input_incremental_restore_history_start_date",
            )
        with col_restore_end_date:
            restore_history_end_date = st.date_input(
                "Fecha final",
                value=st.session_state["incremental_restore_history_end_date"],
                key="input_incremental_restore_history_end_date",
            )

        if st.button(
            "Actualizar fechas de la consulta",
            key="btn_update_incremental_restore_history_dates",
        ):
            if restore_history_start_date > restore_history_end_date:
                st.error("La fecha inicial no puede ser posterior a la fecha final.")
            else:
                st.session_state["incremental_restore_history_start_date"] = (
                    restore_history_start_date
                )
                st.session_state["incremental_restore_history_end_date"] = (
                    restore_history_end_date
                )
                st.session_state["incremental_restore_history_sql"] = (
                    get_incremental_restore_history_sql(
                        restore_history_start_date,
                        restore_history_end_date,
                    )
                )
                st.rerun()

        st.caption(
            "Al actualizar las fechas se regenera la consulta predeterminada. "
            "El SQL se puede modificar antes de ejecutarlo."
        )
        sql_incremental_restore_history_input = st.text_area(
            "Consulta histórica de incremental restore",
            height=300,
            key="incremental_restore_history_sql",
        )

        if st.button(
            "Ejecutar análisis histórico",
            type="primary",
            key="btn_incremental_restore_history_exec",
        ):
            if not host or not user or not password:
                st.error("Please fill in all connection details in the sidebar.")
            elif not sql_incremental_restore_history_input.strip():
                st.warning("Please enter a valid query.")
            else:
                running_message = st.empty()
                try:
                    running_message.markdown(
                        '<div class="incremental-restore-running">'
                        "Consultando el histórico de espacio de incremental restore..."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    try:
                        df_incremental_restore_history = execute_teradata_query(
                            sql_incremental_restore_history_input
                        )
                    finally:
                        running_message.empty()

                    st.success(
                        f"Consulta completada. Se obtuvieron "
                        f"{len(df_incremental_restore_history)} registros. "
                        f"{query_duration_text()}"
                    )
                    if df_incremental_restore_history.empty:
                        st.info(
                            "No se encontraron registros para las fechas seleccionadas."
                        )
                    else:
                        st.dataframe(df_incremental_restore_history)

                        date_col = find_column_case_insensitive(
                            df_incremental_restore_history, "LogDate"
                        )
                        restore_flag_col = find_column_case_insensitive(
                            df_incremental_restore_history,
                            "IncrementalRestoreEnabled",
                        )
                        table_space_col = find_column_case_insensitive(
                            df_incremental_restore_history, "Current_Perm_GB"
                        )

                        if not date_col or not restore_flag_col or not table_space_col:
                            st.warning(
                                "No se puede generar el análisis. La consulta debe devolver "
                                "LogDate, IncrementalRestoreEnabled y Current_Perm_GB."
                            )
                        else:
                            chart_data = df_incremental_restore_history[
                                [date_col, restore_flag_col, table_space_col]
                            ].copy()
                            chart_data["_restore_history_date"] = pd.to_datetime(
                                chart_data[date_col], errors="coerce"
                            )
                            chart_data["_restore_history_flag"] = (
                                chart_data[restore_flag_col]
                                .astype("string")
                                .fillna("Sin valor")
                            )
                            chart_data["_restore_history_space_gb"] = pd.to_numeric(
                                chart_data[table_space_col], errors="coerce"
                            )
                            chart_data = chart_data.dropna(
                                subset=[
                                    "_restore_history_date",
                                    "_restore_history_space_gb",
                                ]
                            )

                            if chart_data.empty:
                                st.warning(
                                    "La consulta no contiene fechas o valores de espacio "
                                    "válidos para analizar."
                                )
                            else:
                                daily_summary = (
                                    chart_data.groupby(
                                        [
                                            "_restore_history_date",
                                            "_restore_history_flag",
                                        ],
                                        as_index=False,
                                    )
                                    .agg(
                                        Current_Perm_GB=(
                                            "_restore_history_space_gb",
                                            "sum",
                                        ),
                                        Table_Count=(
                                            "_restore_history_space_gb",
                                            "size",
                                        ),
                                    )
                                    .sort_values("_restore_history_date")
                                )
                                latest_date = daily_summary[
                                    "_restore_history_date"
                                ].max()
                                latest_summary = daily_summary[
                                    daily_summary["_restore_history_date"] == latest_date
                                ].drop(columns="_restore_history_date")

                                st.subheader(
                                    "Espacio agregado por marca en la última fecha"
                                )
                                st.caption(
                                    f"Última fecha con datos: {latest_date:%Y-%m-%d}"
                                )
                                st.dataframe(latest_summary, hide_index=True)

                                fig_restore_history = px.line(
                                    daily_summary,
                                    x="_restore_history_date",
                                    y="Current_Perm_GB",
                                    color="_restore_history_flag",
                                    color_discrete_sequence=active_sequence,
                                )
                                fig_restore_history = apply_td_layout(
                                    fig_restore_history,
                                    title_text=(
                                        "Evolución del espacio por "
                                        "IncrementalRestoreEnabled"
                                    ),
                                    y_label="Espacio actual (GB)",
                                )
                                fig_restore_history.update_layout(
                                    xaxis_title="Fecha",
                                    yaxis_title="Espacio actual (GB)",
                                    legend_title_text="IncrementalRestoreEnabled",
                                )
                                st.plotly_chart(
                                    fig_restore_history,
                                    width="stretch",
                                )

                        csv_incremental_restore_history = (
                            df_incremental_restore_history.to_csv(
                                index=False
                            ).encode("utf-8")
                        )
                        st.download_button(
                            label="Descargar histórico en CSV",
                            data=csv_incremental_restore_history,
                            file_name="analisis_historico_incremental_restore.csv",
                            mime="text/csv",
                            key="dl_incremental_restore_history",
                        )
                except Exception as e:
                    st.error(
                        "Error al ejecutar el análisis histórico de incremental restore: "
                        f"{str(e)}"
                    )


# =========================================================
# PAGE 4: CONFIGURACIONES
# =========================================================
elif selected_page == "⚙️ Configuraciones":
    st.title("Configuraciones")
    st.markdown('<div class="td-accent-bar"></div>', unsafe_allow_html=True)
    st.warning(
        "Esta aplicación no autentica usuarios. Limita el acceso a este panel "
        "a tu equipo local o a una red de confianza. Las contraseñas se guardan "
        "en texto plano en `conexiones.conf`."
    )

    if "connections_notice" in st.session_state:
        st.success(st.session_state.pop("connections_notice"))

    if CONNECTIONS_ERROR:
        st.error(
            f"No se puede gestionar {CONNECTIONS_FILE}: {CONNECTIONS_ERROR} "
            "Corrige el fichero y vuelve a cargar la aplicación."
        )
    else:
        st.subheader("Conexiones guardadas")
        if CONNECTIONS:
            st.caption(
                f"{len(CONNECTIONS)} conexión(es) guardada(s). "
                "Las contraseñas no se muestran."
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Sistema": connection["sistema"] or "Sin sistema",
                            "IP o dirección": connection["ip_address"],
                            "Puerto": connection["port"],
                            "Usuario": connection["username"],
                        }
                        for connection in CONNECTIONS
                    ]
                ),
                hide_index=True,
            )

            st.subheader("Modificar conexión")
            connection_to_edit = st.selectbox(
                "Conexión que quieres modificar",
                options=connection_labels,
                key="edit_connection_selection",
            )
            edit_index = connection_indexes_by_label[connection_to_edit]
            connection_to_update = CONNECTIONS[edit_index]
            edit_keys = {
                "sistema": f"edit_connection_system_{edit_index}",
                "ip_address": f"edit_connection_ip_{edit_index}",
                "port": f"edit_connection_port_{edit_index}",
                "username": f"edit_connection_username_{edit_index}",
                "userpassword": f"edit_connection_password_{edit_index}",
            }

            with st.form("edit_connection_form"):
                updated_system = st.text_input(
                    "Sistema",
                    value=connection_to_update["sistema"],
                    key=edit_keys["sistema"],
                )
                updated_ip_address = st.text_input(
                    "IP o dirección",
                    value=connection_to_update["ip_address"],
                    key=edit_keys["ip_address"],
                )
                updated_port = st.number_input(
                    "Puerto Teradata",
                    min_value=1,
                    max_value=65535,
                    value=int(connection_to_update["port"]),
                    step=1,
                    key=edit_keys["port"],
                )
                updated_username = st.text_input(
                    "Usuario",
                    value=connection_to_update["username"],
                    key=edit_keys["username"],
                )
                updated_password = st.text_input(
                    "Contraseña (vacío para conservar la actual)",
                    type="password",
                    placeholder="Dejar vacío para conservarla",
                    key=edit_keys["userpassword"],
                )
                update_connection = st.form_submit_button(
                    "Guardar cambios",
                    type="primary",
                )

            if update_connection:
                updated_connection = {
                    "sistema": updated_system.strip(),
                    "ip_address": updated_ip_address.strip(),
                    "port": str(updated_port),
                    "username": updated_username.strip(),
                    "userpassword": (
                        updated_password
                        if updated_password
                        else connection_to_update["userpassword"]
                    ),
                }
                if not all(
                    updated_connection[field].strip()
                    for field in (
                        "sistema",
                        "ip_address",
                        "port",
                        "username",
                        "userpassword",
                    )
                ):
                    st.error(
                        "Sistema, dirección, puerto, usuario y contraseña son obligatorios."
                    )
                elif any(
                    char in updated_connection["sistema"]
                    + updated_connection["ip_address"]
                    + updated_connection["username"]
                    for char in "\r\n"
                ):
                    st.error(
                        "Sistema, dirección y usuario no pueden contener saltos de línea."
                    )
                elif any(char in updated_connection["userpassword"] for char in "\r\n"):
                    st.error("La contraseña no puede contener saltos de línea.")
                elif any(
                    index != edit_index
                    and connection["ip_address"] == updated_connection["ip_address"]
                    and connection["port"] == updated_connection["port"]
                    and connection["username"] == updated_connection["username"]
                    for index, connection in enumerate(CONNECTIONS)
                ):
                    st.error(
                        "Ya existe una conexión con esa dirección, puerto y usuario."
                    )
                else:
                    updated_connections = CONNECTIONS.copy()
                    updated_connections[edit_index] = updated_connection
                    try:
                        save_connections(updated_connections)
                    except OSError as exc:
                        st.error(f"No se pudo actualizar {CONNECTIONS_FILE}: {exc}")
                    else:
                        st.session_state["connections_notice"] = (
                            f"Se modificó la conexión de «{connection_to_edit}»."
                        )
                        for key in edit_keys.values():
                            st.session_state.pop(key, None)
                        st.rerun()

            with st.form("remove_connection_form"):
                connection_to_remove = st.selectbox(
                    "Conexión que quieres quitar",
                    options=connection_labels,
                    key="remove_connection",
                )
                remove_connection = st.form_submit_button(
                    "Quitar conexión",
                    type="secondary",
                )

            if remove_connection:
                remove_index = connection_indexes_by_label[connection_to_remove]
                updated_connections = [
                    connection
                    for index, connection in enumerate(CONNECTIONS)
                    if index != remove_index
                ]
                try:
                    save_connections(updated_connections)
                except OSError as exc:
                    st.error(f"No se pudo actualizar {CONNECTIONS_FILE}: {exc}")
                else:
                    st.session_state["connections_notice"] = (
                        f"Se quitó la conexión «{connection_to_remove}»."
                    )
                    st.rerun()
        else:
            st.info(f"No hay conexiones guardadas en {CONNECTIONS_FILE}.")

        st.subheader("Añadir conexión")
        with st.form("add_connection_form", clear_on_submit=True):
            new_system = st.text_input("Sistema", key="new_connection_system")
            new_ip_address = st.text_input(
                "IP o dirección",
                key="new_connection_ip_address",
            )
            new_port = st.number_input(
                "Puerto Teradata",
                min_value=1,
                max_value=65535,
                value=DEFAULT_TD_PORT,
                step=1,
                key="new_connection_port",
            )
            new_username = st.text_input("Usuario", key="new_connection_username")
            new_password = st.text_input(
                "Contraseña",
                type="password",
                key="new_connection_password",
            )
            add_connection = st.form_submit_button(
                "Añadir conexión",
                type="primary",
            )

        if add_connection:
            new_connection = {
                "sistema": new_system.strip(),
                "ip_address": new_ip_address.strip(),
                "port": str(new_port),
                "username": new_username.strip(),
                "userpassword": new_password,
            }
            if (
                not new_connection["sistema"]
                or not new_connection["ip_address"]
                or not new_connection["port"]
                or not new_connection["username"]
                or not new_password.strip()
            ):
                st.error(
                    "Introduce un sistema, una dirección, un puerto, un usuario "
                    "y una contraseña."
                )
            elif any(
                char
                in new_connection["sistema"]
                + new_connection["ip_address"]
                + new_connection["username"]
                for char in "\r\n"
            ):
                st.error(
                    "Sistema, dirección y usuario no pueden contener saltos de línea."
                )
            elif any(char in new_password for char in "\r\n"):
                st.error("La contraseña no puede contener saltos de línea.")
            elif any(
                connection["ip_address"] == new_connection["ip_address"]
                and connection["port"] == new_connection["port"]
                and connection["username"] == new_connection["username"]
                for connection in CONNECTIONS
            ):
                st.error(
                    "Ya existe una conexión con esa dirección, puerto y usuario."
                )
            else:
                try:
                    save_connections([*CONNECTIONS, new_connection])
                except OSError as exc:
                    st.error(f"No se pudo actualizar {CONNECTIONS_FILE}: {exc}")
                else:
                    st.session_state["connections_notice"] = (
                        f"Se añadió la conexión «{new_connection['sistema']} — "
                        f"{new_connection['ip_address']}:{new_connection['port']} — "
                        f"{new_connection['username']}»."
                    )
                    st.rerun()

# --- Footer: Teradata Corporate Identity ---
st.markdown(
    """
    <footer class="td-footer">
        <div class="td-tagline">Be business confident.</div>
        <p>© 2026 Teradata. All rights reserved.</p>
    </footer>
    """,
    unsafe_allow_html=True,
)