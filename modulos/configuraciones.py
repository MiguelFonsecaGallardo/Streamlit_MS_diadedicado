import csv
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

CONNECTIONS_FILE = Path(__file__).resolve().parents[1] / "conexiones.conf"
CONNECTION_FIELDS = (
    "sistema",
    "ip_address",
    "port",
    "logmech",
    "username",
    "userpassword",
    "save_password",
)
DEFAULT_TD_PORT = 1025
DEFAULT_TD_LOGMECH = "TD2"
TD_LOGMECH_OPTIONS = ("TD2", "TDNEGO", "LDAP")


def load_connections(
    file_path: str | os.PathLike[str] = CONNECTIONS_FILE,
) -> list[dict[str, str]]:
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as connections_file:
        reader = csv.DictReader(connections_file)
        required_fields = {"ip_address", "username", "userpassword"}
        if reader.fieldnames is None or not required_fields.issubset(reader.fieldnames):
            raise ValueError(
                "La cabecera debe incluir: ip_address, username y userpassword."
            )

        connections = []
        for line_number, row in enumerate(reader, start=2):
            connection = {
                field: row.get(field) or "" for field in CONNECTION_FIELDS
            }
            for field in ("sistema", "ip_address", "port", "logmech", "username"):
                connection[field] = connection[field].strip()

            save_password_value = (row.get("save_password") or "true").strip().lower()
            if save_password_value in ("true", "1", "yes"):
                connection["save_password"] = "true"
            elif save_password_value in ("false", "0", "no"):
                connection["save_password"] = "false"
            else:
                raise ValueError(
                    f"La opción de guardar contraseña de la fila {line_number} "
                    "debe ser true o false."
                )

            connection["port"] = connection["port"] or str(DEFAULT_TD_PORT)
            connection["logmech"] = (
                connection["logmech"].upper() or DEFAULT_TD_LOGMECH
            )
            if not connection["sistema"]:
                connection["sistema"] = "Sin sistema"
            if not connection["ip_address"] or not connection["username"]:
                raise ValueError(
                    f"La fila {line_number} debe incluir dirección y usuario."
                )
            if connection["save_password"] == "false":
                connection["userpassword"] = ""
            elif not connection["userpassword"]:
                raise ValueError(
                    f"La fila {line_number} debe incluir contraseña o indicar "
                    "save_password=false."
                )

            try:
                port = int(connection["port"])
            except ValueError as exc:
                raise ValueError(
                    f"El puerto de la fila {line_number} debe ser un entero "
                    "entre 1 y 65535."
                ) from exc
            if not 1 <= port <= 65535:
                raise ValueError(
                    f"El puerto de la fila {line_number} debe estar entre 1 y 65535."
                )
            if connection["logmech"] not in TD_LOGMECH_OPTIONS:
                raise ValueError(
                    f"El mecanismo de autenticación de la fila {line_number} "
                    f"debe ser uno de: {', '.join(TD_LOGMECH_OPTIONS)}."
                )

            connection["port"] = str(port)
            connections.append(connection)
    return connections


def save_connections(
    connections: list[dict[str, str]],
    file_path: str | os.PathLike[str] = CONNECTIONS_FILE,
) -> None:
    destination = Path(file_path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
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
            for connection in connections:
                save_password = str(
                    connection.get("save_password", "true")
                ).strip().lower() not in ("false", "0", "no")
                serialized = {
                    field: connection.get(field, "") for field in CONNECTION_FIELDS
                }
                serialized["save_password"] = "true" if save_password else "false"
                if not save_password:
                    serialized["userpassword"] = ""
                writer.writerow(serialized)
        os.replace(temporary_path, destination)
    except OSError:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise


def move_connection(
    connections: list[dict[str, str]],
    index: int,
    direction: int,
) -> list[dict[str, str]]:
    if direction not in (-1, 1):
        raise ValueError("La dirección debe ser -1 (arriba) o 1 (abajo).")
    target_index = index + direction
    if not 0 <= index < len(connections) or not 0 <= target_index < len(connections):
        raise ValueError("La conexión no se puede mover más allá de los límites.")

    reordered = connections.copy()
    reordered[index], reordered[target_index] = (
        reordered[target_index],
        reordered[index],
    )
    return reordered


def connection_labels(
    connections: list[dict[str, str]],
) -> tuple[list[str], dict[str, int]]:
    labels = []
    indexes = {}
    for index, connection in enumerate(connections):
        label = (
            f"{connection['sistema']} — {connection['ip_address']}:"
            f"{connection['port']} — {connection['username']} "
            f"[{connection['logmech']}]"
        )
        base_label = label
        suffix = 2
        while label in indexes:
            label = f"{base_label} ({suffix})"
            suffix += 1
        labels.append(label)
        indexes[label] = index
    return labels, indexes


def _validate_connection(
    connection: dict[str, str],
    existing: list[dict[str, str]],
    ignore_index: int | None = None,
) -> str | None:
    if not all(
        connection[field].strip()
        for field in ("sistema", "ip_address", "port", "username")
    ):
        return "Sistema, dirección, puerto y usuario son obligatorios."
    if (
        connection["save_password"] == "true"
        and not connection["userpassword"].strip()
    ):
        return "Introduce una contraseña o activa la opción para no guardarla."
    if any(
        char
        in connection["sistema"]
        + connection["ip_address"]
        + connection["username"]
        for char in "\r\n"
    ):
        return "Sistema, dirección y usuario no pueden contener saltos de línea."
    if connection["save_password"] == "true" and any(
        char in connection["userpassword"] for char in "\r\n"
    ):
        return "La contraseña no puede contener saltos de línea."
    if any(
        index != ignore_index
        and candidate["ip_address"] == connection["ip_address"]
        and candidate["port"] == connection["port"]
        and candidate["logmech"] == connection["logmech"]
        and candidate["username"] == connection["username"]
        for index, candidate in enumerate(existing)
    ):
        return (
            "Ya existe una conexión con esa dirección, puerto, mecanismo "
            "de autenticación y usuario."
        )
    return None


def _save_and_rerun(
    connections_to_save: list[dict[str, str]],
    notice: str,
) -> None:
    try:
        save_connections(connections_to_save)
    except OSError as exc:
        st.error(f"No se pudo actualizar {CONNECTIONS_FILE.name}: {exc}")
        return
    st.session_state["connections_notice"] = notice
    st.rerun()


st.title("Configuraciones")
st.warning(
    "Las contraseñas que se decida guardar se almacenan en texto claro en "
    f"`{CONNECTIONS_FILE.name}`. Restringe el acceso al fichero."
)

if notice := st.session_state.pop("connections_notice", None):
    st.success(notice)

try:
    connections = load_connections()
except (OSError, ValueError, csv.Error) as exc:
    st.error(f"No se puede gestionar {CONNECTIONS_FILE.name}: {exc}")
    st.stop()

labels, indexes = connection_labels(connections)
if connections:
    st.subheader("Orden de las conexiones")
    st.caption(
        "El orden guardado aquí también determina el orden del selector "
        "de conexiones en la barra lateral."
    )
    order_label = st.selectbox(
        "Conexión que quieres reordenar",
        options=labels,
        key="order_connection_selection",
    )
    order_index = indexes[order_label]
    move_up_column, move_down_column = st.columns(2)
    if move_up_column.button(
        "Mover arriba",
        disabled=order_index == 0,
        key="move_connection_up",
    ):
        reordered_connections = move_connection(connections, order_index, -1)
        _save_and_rerun(
            reordered_connections,
            f"Se movió arriba la conexión «{connections[order_index]['sistema']}».",
        )
    if move_down_column.button(
        "Mover abajo",
        disabled=order_index == len(connections) - 1,
        key="move_connection_down",
    ):
        reordered_connections = move_connection(connections, order_index, 1)
        _save_and_rerun(
            reordered_connections,
            f"Se movió abajo la conexión «{connections[order_index]['sistema']}».",
        )

    st.subheader("Conexiones guardadas")
    st.caption(
        f"{len(connections)} conexión(es). Las contraseñas no se muestran."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Sistema": connection["sistema"],
                    "IP o dirección": connection["ip_address"],
                    "Puerto": connection["port"],
                    "Autenticación": connection["logmech"],
                    "Usuario": connection["username"],
                    "Contraseña guardada": (
                        "Sí" if connection["save_password"] == "true" else "No"
                    ),
                }
                for connection in connections
            ]
        ),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Modificar o quitar conexión")
    selected_label = st.selectbox(
        "Conexión que quieres modificar o quitar",
        options=labels,
        key="edit_connection_selection",
    )
    edit_index = indexes[selected_label]
    original = connections[edit_index]
    key_suffix = str(edit_index)

    with st.form("edit_connection_form"):
        system = st.text_input(
            "Sistema", value=original["sistema"], key=f"edit_system_{key_suffix}"
        )
        host = st.text_input(
            "IP o dirección",
            value=original["ip_address"],
            key=f"edit_host_{key_suffix}",
        )
        port = st.number_input(
            "Puerto Teradata",
            min_value=1,
            max_value=65535,
            value=int(original["port"]),
            step=1,
            key=f"edit_port_{key_suffix}",
        )
        logmech = st.selectbox(
            "Mecanismo de autenticación",
            options=TD_LOGMECH_OPTIONS,
            index=TD_LOGMECH_OPTIONS.index(original["logmech"]),
            key=f"edit_logmech_{key_suffix}",
        )
        username = st.text_input(
            "Usuario",
            value=original["username"],
            key=f"edit_username_{key_suffix}",
        )
        do_not_save_password = st.checkbox(
            "No guardar la contraseña en conexiones.conf",
            value=original["save_password"] == "false",
            key=f"edit_no_save_password_{key_suffix}",
        )
        new_password = st.text_input(
            "Nueva contraseña (vacío para conservar la actual)",
            type="password",
            key=f"edit_password_{key_suffix}",
        )
        update = st.form_submit_button("Guardar cambios", type="primary")

    if update:
        updated = {
            "sistema": system.strip(),
            "ip_address": host.strip(),
            "port": str(port),
            "logmech": logmech,
            "username": username.strip(),
            "save_password": "false" if do_not_save_password else "true",
            "userpassword": (
                ""
                if do_not_save_password
                else new_password or original["userpassword"]
            ),
        }
        error = _validate_connection(updated, connections, edit_index)
        if error:
            st.error(error)
        else:
            changed_connections = connections.copy()
            changed_connections[edit_index] = updated
            _save_and_rerun(
                changed_connections,
                f"Se modificó la conexión «{updated['sistema']}».",
            )

    with st.form("remove_connection_form"):
        confirm_remove = st.checkbox(
            "Confirmo que quiero quitar esta conexión",
            key=f"confirm_remove_{key_suffix}",
        )
        remove = st.form_submit_button("Quitar conexión", type="secondary")
    if remove:
        if not confirm_remove:
            st.error("Confirma la eliminación antes de continuar.")
        else:
            changed_connections = [
                connection
                for index, connection in enumerate(connections)
                if index != edit_index
            ]
            _save_and_rerun(
                changed_connections,
                f"Se quitó la conexión «{original['sistema']}».",
            )
else:
    st.info(f"No hay conexiones guardadas en {CONNECTIONS_FILE.name}.")

st.subheader("Añadir conexión")
with st.form("add_connection_form", clear_on_submit=True):
    new_system = st.text_input("Sistema", key="new_system")
    new_host = st.text_input("IP o dirección", key="new_host")
    new_port = st.number_input(
        "Puerto Teradata",
        min_value=1,
        max_value=65535,
        value=DEFAULT_TD_PORT,
        step=1,
        key="new_port",
    )
    new_logmech = st.selectbox(
        "Mecanismo de autenticación",
        options=TD_LOGMECH_OPTIONS,
        index=TD_LOGMECH_OPTIONS.index(DEFAULT_TD_LOGMECH),
        key="new_logmech",
    )
    new_username = st.text_input("Usuario", key="new_username")
    no_save_password = st.checkbox(
        "No guardar la contraseña en conexiones.conf",
        key="new_no_save_password",
    )
    new_password = st.text_input(
        "Contraseña (opcional si no se guarda)",
        type="password",
        key="new_password",
    )
    add = st.form_submit_button("Añadir conexión", type="primary")

if add:
    new_connection = {
        "sistema": new_system.strip(),
        "ip_address": new_host.strip(),
        "port": str(new_port),
        "logmech": new_logmech,
        "username": new_username.strip(),
        "save_password": "false" if no_save_password else "true",
        "userpassword": "" if no_save_password else new_password,
    }
    error = _validate_connection(new_connection, connections)
    if error:
        st.error(error)
    else:
        _save_and_rerun(
            [*connections, new_connection],
            f"Se añadió la conexión «{new_connection['sistema']}».",
        )
