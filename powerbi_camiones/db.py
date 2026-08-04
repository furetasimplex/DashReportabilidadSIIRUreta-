"""
Capa de acceso a datos para la carga del Export de PowerBI camiones.

Todo el SQL vive aqui, mismo patron que reclamo/db.py. La tabla destino es
inventar_SpcHidr.mov_cam_powerbi (ver crear_tabla_mov_cam_powerbi.sql).

Estrategia de carga (ajustada 2026-08-03, a pedido del usuario): una fecha
sola no identifica "el mismo registro" -- un dia trae varias filas (turno,
fase, banco, excavadora, destino, tipo de camion distintos), y ni siquiera
esas 8 columnas alcanzan: un mismo turno/fase/banco/excavadora/destino/
flota puede traer varios carguios distintos en el dia, diferenciados por
'grade' (codigo de lote/carguio, ej. STA-1708-010/TAL). Se confirmo contra
el Export real que fecha+turno+tipo_movimiento+fase+banco+excavadora+
destino_descarga+flota_cex_tc+grade no tiene duplicados. Se usa esa LLAVE
COMPUESTA de 9 columnas (COLUMNAS_CLAVE) y, dentro del rango de fechas del
archivo, se hace un MERGE contra una tabla de aterrizaje (staging):
    - llave existente con algun valor distinto -> ACTUALIZA
    - llave nueva -> INSERTA
    - llave que ya no aparece en el archivo nuevo -> ELIMINA
Mismo espiritu de "reemplazar el rango, pero registro a registro" que
reclamo.sp_sincronizar_desde_etl.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from db_connection import get_engine as _app_get_engine

log = logging.getLogger(__name__)

TABLA_DESTINO = "inventar_SpcHidr.mov_cam_powerbi"
TABLA_STAGING = "inventar_SpcHidr.mov_cam_powerbi_staging"
HOJA_ESPERADA = "Export"

# Llave compuesta que identifica "el mismo registro" entre cargas. Debe
# calzar con el indice unico ux_mov_cam_powerbi_clave de la tabla destino.
COLUMNAS_CLAVE = [
    "fecha", "turno", "tipo_movimiento", "fase", "banco",
    "excavadora", "destino_descarga", "flota_cex_tc", "grade",
]

# Mapeo columna del Excel -> columna de la tabla SQL. El orden es el mismo
# que trae el archivo. Las claves deben calzar EXACTO con el encabezado del
# Excel (incluye el espacio final en 'Fase ' y el '#' en '#100 Ponderado').
COLUMNAS = {
    "fecha": "fecha",
    "Turno": "turno",
    "Expit o Remanejo": "tipo_movimiento",
    "Fase ": "fase",
    "Banco": "banco",
    "excav": "excavadora",
    "Destino descarga": "destino_descarga",
    "ton descarga": "ton_descarga",
    "tonelaje descarga TMS": "tonelaje_descarga_tms",
    "grade": "grade",
    "CuT Ponderado": "cut_ponderado",
    "CuS Ponderado": "cus_ponderado",
    "Razon Solubilidad": "razon_solubilidad",
    "CO3 Ponderado": "co3_ponderado",
    "Rec_Cu_Lix Ponderado": "rec_cu_lix_ponderado",
    "SPI Ponderado": "spi_ponderado",
    "BWI Ponderado": "bwi_ponderado",
    "Py Ponderado": "py_ponderado",
    "#100 Ponderado": "malla100_ponderado",
    "grade08": "grade08",
    "Rec_Mass_10 Ponderado": "rec_mass_10_ponderado",
    "ClayB Ponderado": "clayb_ponderado",
    "Mo Ponderado": "mo_ponderado",
    "As Ponderado": "as_ponderado",
    "Ag Ponderado": "ag_ponderado",
    "Au Ponderado": "au_ponderado",
    "csrCC Ponderado": "csrcc_ponderado",
    "csrCV Ponderado": "csrcv_ponderado",
    "csrCPY Ponderado": "csrcpy_ponderado",
    "UGG Ponderado": "ugg_ponderado",
    "Sericita Ponderado": "sericita_ponderado",
    "Flota_CEX tc": "flota_cex_tc",
    "N_Break": "n_break",
}

# Columnas que deben existir si o si en el archivo. El resto se acepta
# aunque falte (queda NULL), para no romper la carga por una columna de
# ley que a veces no viene.
COLUMNAS_OBLIGATORIAS = [
    "fecha", "Turno", "Fase ", "Destino descarga",
    "ton descarga", "tonelaje descarga TMS",
]

COLUMNAS_NUMERICAS = [
    v for k, v in COLUMNAS.items()
    if k not in (
        "fecha", "Turno", "Expit o Remanejo", "Fase ", "Banco", "excav",
        "Destino descarga", "grade", "grade08", "Flota_CEX tc", "N_Break",
    )
]

# Columnas de texto que forman parte de la llave (menos fecha, que es date
# no texto). Se normalizan a '' en vez de NULL antes de cargar a staging,
# porque la tabla destino tiene estas columnas NOT NULL DEFAULT '' -- asi
# el indice unico de la llave compuesta funciona de forma predecible aunque
# el Excel traiga alguna celda vacia.
COLUMNAS_CLAVE_TEXTO = [c for c in COLUMNAS_CLAVE if c != "fecha"]

# Columnas de valor: todo lo que no es parte de la llave compuesta.
COLUMNAS_VALOR = [v for v in COLUMNAS.values() if v not in COLUMNAS_CLAVE]

# Ancho maximo de las columnas de texto en la tabla SQL (ver
# crear_tabla_mov_cam_powerbi.sql). Se valida ACA, antes de tocar la base,
# para mostrar un mensaje entendible en vez del error crudo de SQL Server
# "String or binary data would be truncated" (8152). Detectado en la carga
# de mes.xlsx: 'STOCK_PARRILLADO-OXIDO BAJA LEY' (31) supero el varchar(30)
# que tenian fase/banco en ese momento -- la tabla se amplio a varchar(50).
LONGITUDES_MAXIMAS = {
    "turno": 10,
    "tipo_movimiento": 30,
    "fase": 50,
    "banco": 50,
    "excavadora": 30,
    "destino_descarga": 30,
    "flota_cex_tc": 50,
    "grade": 100,
    "grade08": 50,
    "n_break": 50,
}


def get_engine() -> Engine:
    """Motor SQLAlchemy compartido con el resto de la app (db_connection)."""
    engine = _app_get_engine()
    if engine is None:
        raise RuntimeError(
            "No se pudo crear el engine SQL Server. "
            "Revise SQLSERVER_* y ENTORNO en .env (ver .env.example)."
        )
    return engine


class ArchivoInvalidoError(Exception):
    """El archivo subido no tiene la forma esperada del Export de PowerBI."""


def leer_excel(contents: str, filename: str) -> pd.DataFrame:
    """Decodifica el contenido de dcc.Upload y devuelve un DataFrame listo
    para cargar, con las columnas ya renombradas a los nombres de la tabla.

    No toca la base de datos. Lanza ArchivoInvalidoError con un mensaje
    entendible si falta alguna columna obligatoria o el formato no calza.
    """
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise ArchivoInvalidoError(
            f"'{filename}' no es un Excel (.xlsx/.xls). Verifique el archivo."
        )

    try:
        _, contenido_b64 = contents.split(",", 1)
        crudo = base64.b64decode(contenido_b64)
    except Exception as exc:
        raise ArchivoInvalidoError(
            f"No se pudo leer el contenido del archivo: {exc}"
        ) from exc

    try:
        libro = pd.ExcelFile(io.BytesIO(crudo))
    except Exception as exc:
        raise ArchivoInvalidoError(
            f"El archivo no es un Excel valido: {exc}"
        ) from exc

    hoja = HOJA_ESPERADA if HOJA_ESPERADA in libro.sheet_names else libro.sheet_names[0]
    df = libro.parse(hoja)

    faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in df.columns]
    if faltantes:
        raise ArchivoInvalidoError(
            "El archivo no tiene la forma esperada del Export de PowerBI. "
            f"Faltan columnas obligatorias: {', '.join(faltantes)}. "
            f"Hoja leida: '{hoja}'."
        )

    # Solo se toman las columnas conocidas; el resto del archivo se ignora.
    columnas_presentes = [c for c in COLUMNAS if c in df.columns]
    df = df[columnas_presentes].rename(columns=COLUMNAS)

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
    filas_sin_fecha = int(df["fecha"].isna().sum())
    if filas_sin_fecha:
        df = df[df["fecha"].notna()].copy()

    for col in COLUMNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if df.empty:
        raise ArchivoInvalidoError(
            "El archivo no tiene filas con fecha valida despues de la limpieza."
        )

    df.attrs["filas_sin_fecha_descartadas"] = filas_sin_fecha
    df.attrs["hoja_leida"] = hoja

    _validar_longitudes(df)
    _validar_llave_sin_duplicados(df)
    return df


def _validar_longitudes(df: pd.DataFrame) -> None:
    """Corta la carga ANTES de tocar la base si alguna columna de texto
    trae valores mas largos de lo que soporta la tabla destino -- evita
    el error crudo de SQL Server "String or binary data would be
    truncated" y en vez de eso muestra que fila y que valor se pasa.

    Validador temporal mientras se sigue afinando la tabla con datos
    reales de PowerBI (ver historial: fase/banco se ampliaron de
    varchar(30) a varchar(50) tras un caso real en mes.xlsx).
    """
    errores = []
    for col, limite in LONGITUDES_MAXIMAS.items():
        if col not in df.columns:
            continue
        s = df[col].dropna().astype(str)
        largos = s.str.len()
        excede = s[largos > limite]
        if excede.empty:
            continue
        ejemplo = excede.iloc[0]
        errores.append(
            f"{col} (maximo {limite}): {len(excede)} fila(s), ej. "
            f"'{ejemplo}' ({len(ejemplo)} caracteres)"
        )

    if not errores:
        return

    log.warning("Archivo con valores que exceden el ancho de columna: %s", "; ".join(errores))
    raise ArchivoInvalidoError(
        "El archivo trae valores mas largos de lo que soporta la tabla. "
        + " | ".join(errores)
        + ". Si es un valor real (no un error de tipeo), avise para "
        "ampliar la columna en la base antes de volver a cargar."
    )


def _validar_llave_sin_duplicados(df: pd.DataFrame) -> None:
    """Corta la carga ANTES de tocar la base si el archivo trae filas
    duplicadas bajo COLUMNAS_CLAVE -- evita que el usuario vea un error
    crudo de SQL Server (duplicate key / IntegrityError) y en vez de eso
    muestra cuales filas chocan, para que se puedan revisar en el Excel.

    Validador temporal mientras se sigue afinando la llave compuesta con
    datos reales de PowerBI (ver historial: se agrego flota_cex_tc y
    luego grade tras encontrar duplicados en cargas anteriores).
    """
    columnas_llave_presentes = [c for c in COLUMNAS_CLAVE if c in df.columns]
    conteo = df.groupby(columnas_llave_presentes, dropna=False).size()
    duplicadas = conteo[conteo > 1]
    if duplicadas.empty:
        return

    ejemplos = []
    for llave, n in duplicadas.head(5).items():
        if not isinstance(llave, tuple):
            llave = (llave,)
        descripcion = ", ".join(f"{c}={v}" for c, v in zip(columnas_llave_presentes, llave))
        ejemplos.append(f"[{descripcion}] -> {n} filas")

    total_grupos = len(duplicadas)
    total_filas = int(duplicadas.sum())
    log.warning(
        "Archivo con %d combinacion(es) de llave duplicada(s) (%d filas): %s",
        total_grupos, total_filas, "; ".join(ejemplos),
    )
    raise ArchivoInvalidoError(
        f"El archivo trae {total_grupos} combinacion(es) de "
        f"{'+'.join(columnas_llave_presentes)} repetida(s) ({total_filas} filas en total). "
        "Cada combinacion deberia identificar un unico movimiento. Ejemplos: "
        + " | ".join(ejemplos)
        + ". Revise esas filas en el Excel antes de volver a subirlo."
    )


def resumen(df: pd.DataFrame) -> dict:
    """Resumen del DataFrame ya parseado, para mostrar antes de confirmar
    la carga: rango de fechas, filas, y filas descartadas por fecha invalida.
    """
    return {
        "filas": int(len(df)),
        "fecha_min": df["fecha"].min(),
        "fecha_max": df["fecha"].max(),
        "filas_sin_fecha_descartadas": int(df.attrs.get("filas_sin_fecha_descartadas", 0)),
        "hoja_leida": df.attrs.get("hoja_leida", HOJA_ESPERADA),
    }


def _sql_merge(desde_param: str = "desde", hasta_param: str = "hasta") -> str:
    """Arma el MERGE staging -> destino, comparando por la llave compuesta.

    NOT MATCHED BY SOURCE solo borra dentro del rango de fechas del propio
    archivo (:desde/:hasta): una carga de julio nunca borra registros de
    otro mes que ya estaban en la tabla.
    """
    on_clause = " AND ".join(f"tgt.{c} = src.{c}" for c in COLUMNAS_CLAVE)
    set_clause = ",\n            ".join(f"{c} = src.{c}" for c in COLUMNAS_VALOR)
    insert_cols = COLUMNAS_CLAVE + COLUMNAS_VALOR + ["archivo_origen", "usuario_carga", "fecha_carga"]
    insert_vals = [f"src.{c}" for c in COLUMNAS_CLAVE + COLUMNAS_VALOR + ["archivo_origen", "usuario_carga"]]
    insert_vals.append("SYSDATETIME()")

    # SET NOCOUNT ON es obligatorio aca: sin el, SQL Server intercala
    # mensajes "(N row(s) affected)" del propio MERGE como si fueran un
    # result set mas, y pyodbc/SQLAlchemy terminan devolviendo ESE result
    # set vacio en vez del SELECT final -> ResourceClosedError al hacer
    # fetchall() en Python aunque el MERGE se haya ejecutado bien.
    return f"""
        SET NOCOUNT ON;

        DECLARE @Resumen TABLE (accion nvarchar(10));

        MERGE {TABLA_DESTINO} AS tgt
        USING {TABLA_STAGING} AS src
            ON {on_clause}
        WHEN MATCHED THEN UPDATE SET
            {set_clause},
            archivo_origen = src.archivo_origen,
            usuario_carga = src.usuario_carga,
            fecha_carga = SYSDATETIME()
        WHEN NOT MATCHED BY TARGET THEN INSERT
            ({", ".join(insert_cols)})
            VALUES ({", ".join(insert_vals)})
        WHEN NOT MATCHED BY SOURCE
             AND tgt.fecha BETWEEN :{desde_param} AND :{hasta_param}
            THEN DELETE
        OUTPUT $action INTO @Resumen;

        SELECT accion, COUNT(*) AS n FROM @Resumen GROUP BY accion;
    """


def cargar(df: pd.DataFrame, usuario: str, archivo_origen: str) -> str:
    """Carga el DataFrame en inventar_SpcHidr.mov_cam_powerbi comparando por
    la llave compuesta (COLUMNAS_CLAVE), no solo por fecha:
        - llave existente con valores distintos -> ACTUALIZA
        - llave nueva -> INSERTA
        - llave que ya no aparece en el archivo, dentro del mismo rango
          de fechas que trae el archivo -> ELIMINA
    Todo en una sola transaccion, via una tabla de staging (se vacia y se
    vuelve a llenar en cada carga).
    """
    if df.empty:
        raise ArchivoInvalidoError("No hay filas para cargar.")

    fecha_min = df["fecha"].min()
    fecha_max = df["fecha"].max()

    df = df.copy()
    for col in COLUMNAS_CLAVE_TEXTO:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["archivo_origen"] = archivo_origen
    df["usuario_carga"] = usuario

    log.info(
        "cargar(): %d fila(s) validas, periodo %s a %s, archivo=%s, usuario=%s",
        len(df), fecha_min, fecha_max, archivo_origen, usuario,
    )

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {TABLA_STAGING}"))
        df.to_sql(
            "mov_cam_powerbi_staging",
            con=conn,
            schema="inventar_SpcHidr",
            if_exists="append",
            index=False,
        )
        filas_staging = conn.execute(text(f"SELECT COUNT(*) FROM {TABLA_STAGING}")).scalar()
        log.info("cargar(): %s filas en staging antes del MERGE", filas_staging)

        resultado = conn.execute(
            text(_sql_merge()), {"desde": fecha_min, "hasta": fecha_max}
        )
        filas_resultado = resultado.fetchall()
        log.info("cargar(): resultado crudo del MERGE = %s", filas_resultado)
        conteo = {fila[0]: fila[1] for fila in filas_resultado}

    insertados = conteo.get("INSERT", 0)
    actualizados = conteo.get("UPDATE", 0)
    eliminados = conteo.get("DELETE", 0)
    return (
        f"Carga completa para el periodo {fecha_min} a {fecha_max}: "
        f"{insertados} fila(s) nueva(s), {actualizados} actualizada(s), "
        f"{eliminados} eliminada(s) (ya no estaban en el archivo)."
    )


def historial(limite: int = 15) -> pd.DataFrame:
    """Ultimas cargas realizadas, agrupadas por archivo, para mostrar en el
    panel como bitacora simple."""
    sql = f"""
        SELECT TOP (:limite)
            archivo_origen,
            usuario_carga,
            MIN(fecha) AS fecha_desde,
            MAX(fecha) AS fecha_hasta,
            COUNT(*) AS filas,
            MAX(fecha_carga) AS fecha_carga
        FROM {TABLA_DESTINO}
        GROUP BY archivo_origen, usuario_carga
        ORDER BY MAX(fecha_carga) DESC
    """
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params={"limite": limite})
