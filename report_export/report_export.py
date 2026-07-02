import os
import pandas as pd
import numpy as np
from datetime import date
try:
    from db_connection import get_engine
except Exception as e:
    raise RuntimeError("No se pudo importar get_engine desde db_connection.py") from e

from sqlalchemy import text as _sa_text


def _get_engine():
    engine = get_engine()
    if engine is None:
        raise RuntimeError("get_engine() devolvio None: revisar configuracion de DB.")
    return engine

# Nombre completo de la tabla (ajusta si cambia)
TABLE_FQN = "[inventar_SpcHidr].[Datos_conciliados_of]"
TABLE_DATOS_CONCILIADOS = "[inventar_SpcHidr].[Datos_conciliados_of]"
# Ruta del logo BHP
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

BHP_LOGO_PATH = os.path.join(PROJECT_DIR, "assets", "logoBHP.png")
# Columnas exactas para el reporte "Producción Diaria" / plantilla Datos conciliados
COLUMNAS_DATOS_CONCILIADOS = [
    "Fecha", "Chancado_TMS_Real", "Humedad_Turno_A", "Humedad_Turno_B", "Humedad_promedio_dia",
    "Sal_turno_A", "Sal_Turno_B", "Sal_promedio_dia",
    "Apilado_TMH_turno_A", "Apilado_TMH_turno_B", "Apilado_TMH_promedio_dia",
    "Apilado_TMS_Real", "Apilado_TMS_Plan", "Campana_apilado", "Modulo_apilado", "Avance_apilado",
    "Ley_CuT_Real", "Ley_CuT_Plan", "Cobre_fino_Apilado_Real", "Cobre_fino_Apilado_Plan",
    "TMS_Rotopala_1_Real", "TMS_Rotopala_1_Plan", "Campana_reclamo_oxidos", "Modulo_reclamo_oxidos", "Avance_reclamo_oxidos",
    "TMS_Rotopala_2_Real", "TMS_Rotopala_2_Plan", "Campana_reclamo_sulfuros", "modulo_reclamo_sulfuros", "Avance_reclamo_sulfuros",
    "Camiones_TMS_Reclamo_Oxidos", "Camiones_TMS_Reclamo_Sulfuros", "Movido", "Extraido",
    "Camiones_TMS_total", "Camiones_TMS_plan", "Campana_reclamo_camiones", "Modulo_reclamo_camiones",
    "Total_Ripios_Incluye_Camiones_Real", "Total_Ripios_Incluye_Camiones_Plan",
    "Produccion_Catodos_Real", "Produccion_Catodos_Plan","Estado"
]


def first_day_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def fetch_report_data(end_date: date) -> pd.DataFrame:
    """
    Trae datos desde el día 1 del mes de end_date hasta end_date (inclusive)
    y añade/normaliza la columna 'es_preliminar'.
    """
    start_date = first_day_of_month(end_date)
    engine = _get_engine()

    sql = f"""
    SELECT *
    FROM {TABLE_FQN}
    WHERE [Fecha] BETWEEN :start AND :end
    ORDER BY [Fecha] ASC
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql(_sa_text(sql), conn, params={"start": start_date, "end": end_date})
    except Exception as e:
        raise RuntimeError(f"Error al leer SQL Server en fetch_report_data: {e}") from e

    # ===== Manejar columna es_preliminar =====
    prelim = None
    for candidate in ["es_preliminar", "preliminar", "estado"]:
        if candidate in df.columns:
            prelim = candidate
            break

    if prelim is None:
        df["es_preliminar"] = False
    else:
        if df[prelim].dtype == bool:
            df["es_preliminar"] = df[prelim]
        else:
            df["es_preliminar"] = df[prelim].astype(str).str.lower().isin(
                ["1", "true", "sí", "si", "preliminar", "preliminary", "pre"]
            )

    # Dejamos Fecha y es_preliminar al inicio
    cols = list(df.columns)
    ordered = []
    for c in ["Fecha", "es_preliminar"]:
        if c in cols:
            ordered.append(c)
            cols.remove(c)
    ordered.extend(cols)

    return df[ordered]


def fetch_datos_conciliados_report(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Consulta exacta para el reporte de Producción Diaria / plantilla Datos conciliados.
    """
    engine = _get_engine()
    cols = ", ".join(f"[{c}]" for c in COLUMNAS_DATOS_CONCILIADOS)
    sql = f"""
    SELECT {cols}
    FROM {TABLE_DATOS_CONCILIADOS}
    WHERE [Fecha] BETWEEN :start AND :end
    ORDER BY [Fecha] ASC
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(_sa_text(sql), conn, params={"start": start_date, "end": end_date})
    except Exception as e:
        raise RuntimeError(f"Error al leer Datos_conciliados_of: {e}") from e

    df = df[[c for c in COLUMNAS_DATOS_CONCILIADOS if c in df.columns]]
    return df

def fetch_representatividad_torres_report(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Consulta representatividad de torres via sp_reporte_representatividad_torres.
    """
    engine = _get_engine()
    sql = """
    EXEC inventar_SpcHidr.sp_reporte_representatividad_torres
        @fecha_inicio = :start,
        @fecha_fin = :end
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(_sa_text(sql), conn, params={"start": start_date, "end": end_date})
    except Exception as e:
        raise RuntimeError(f"Error al leer representatividad de torres: {e}") from e
    return df
def fetch_bd_ton_report(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Consulta la capa histórica persistente de BD Ton.

    El rango de fechas es inclusivo:
        Fecha >= start_date
        Fecha <= end_date
    """
    conn_or_engine = _get_engine()

    if conn_or_engine is None:
        raise RuntimeError(
            "get_engine() devolvió None: revisar conexión a la base de datos."
        )

    sql = """
    SELECT
        [Fecha],
        [Apilado_TMH_CV08_TA] AS [Apilado TMH CV-08 TA],
        [Apilado_TMH_CV08_TB] AS [Apilado TMH CV-08 TB],
        [Apilado_TMH_CV108_TA] AS [Apilado TMH CV-108 TA],
        [Apilado_TMH_CV108_TB] AS [Apilado TMH CV-108 TB],
        [Rep_TM1_TA_Qui] AS [Rep. TM1 TA Qui.],
        [Rep_TM1_TA_Fis] AS [Rep. TM1 TA Fis.],
        [Rep_TM1_TB_Qui] AS [Rep. TM1 TB Qui.],
        [Rep_TM1_TB_Fis] AS [Rep. TM1 TB Fis.],
        [Rep_TM2_TA_Qui] AS [Rep. TM2 TA Qui.],
        [Rep_TM2_TA_Fis] AS [Rep. TM2 TA Fis.],
        [Rep_TM2_TB_Qui] AS [Rep. TM2 TB Qui.],
        [Rep_TM2_TB_Fis] AS [Rep. TM2 TB Fis.],
        [Muestra_representativa_TM1_TA]
            AS [Muestra representativa TM1 TA],
        [Muestra_representativa_TM1_TB]
            AS [Muestra representativa TM1 TB],
        [Muestra_representativa_TM2_TA]
            AS [Muestra representativa TM2 TA],
        [Muestra_representativa_TM2_TB]
            AS [Muestra representativa TM2 TB],
        [FISICO_TM1_TA] AS [FISICO TM1 TA],
        [FISICO_TM1_TB] AS [FISICO TM1 TB],
        [FISICO_TM2_TA] AS [FISICO TM2 TA],
        [FISICO_TM2_TB] AS [FISICO TM2 TB],
        [Evaluable_TM1_TA],
        [Evaluable_TM1_TB],
        [Evaluable_TM2_TA],
        [Evaluable_TM2_TB],
        [Evaluable_Combinado_TA],
        [Evaluable_Combinado_TB],
        [Fuente_Evaluabilidad]
    FROM inventar_SpcHidr.v_bd_ton_reportabilidad
    WHERE [Fecha] >= ?
      AND [Fecha] <= ?
    ORDER BY [Fecha] ASC;
    """

    sql_sa = """
    SELECT
        [Fecha],
        [Apilado_TMH_CV08_TA] AS [Apilado TMH CV-08 TA],
        [Apilado_TMH_CV08_TB] AS [Apilado TMH CV-08 TB],
        [Apilado_TMH_CV108_TA] AS [Apilado TMH CV-108 TA],
        [Apilado_TMH_CV108_TB] AS [Apilado TMH CV-108 TB],
        [Rep_TM1_TA_Qui] AS [Rep. TM1 TA Qui.],
        [Rep_TM1_TA_Fis] AS [Rep. TM1 TA Fis.],
        [Rep_TM1_TB_Qui] AS [Rep. TM1 TB Qui.],
        [Rep_TM1_TB_Fis] AS [Rep. TM1 TB Fis.],
        [Rep_TM2_TA_Qui] AS [Rep. TM2 TA Qui.],
        [Rep_TM2_TA_Fis] AS [Rep. TM2 TA Fis.],
        [Rep_TM2_TB_Qui] AS [Rep. TM2 TB Qui.],
        [Rep_TM2_TB_Fis] AS [Rep. TM2 TB Fis.],
        [Muestra_representativa_TM1_TA]
            AS [Muestra representativa TM1 TA],
        [Muestra_representativa_TM1_TB]
            AS [Muestra representativa TM1 TB],
        [Muestra_representativa_TM2_TA]
            AS [Muestra representativa TM2 TA],
        [Muestra_representativa_TM2_TB]
            AS [Muestra representativa TM2 TB],
        [FISICO_TM1_TA] AS [FISICO TM1 TA],
        [FISICO_TM1_TB] AS [FISICO TM1 TB],
        [FISICO_TM2_TA] AS [FISICO TM2 TA],
        [FISICO_TM2_TB] AS [FISICO TM2 TB],
        [Evaluable_TM1_TA],
        [Evaluable_TM1_TB],
        [Evaluable_TM2_TA],
        [Evaluable_TM2_TB],
        [Evaluable_Combinado_TA],
        [Evaluable_Combinado_TB],
        [Fuente_Evaluabilidad]
    FROM inventar_SpcHidr.v_bd_ton_reportabilidad
    WHERE [Fecha] >= :start
      AND [Fecha] <= :end
    ORDER BY [Fecha] ASC;
    """

    try:
        # Conexión DBAPI, por ejemplo pyodbc
        if hasattr(conn_or_engine, "cursor"):
            df = pd.read_sql_query(
                sql,
                conn_or_engine,
                params=(start_date, end_date),
            )

        # Engine SQLAlchemy
        else:
            with conn_or_engine.connect() as conn:
                df = pd.read_sql_query(
                    _sa_text(sql_sa),
                    conn,
                    params={
                        "start": start_date,
                        "end": end_date,
                    },
                )

    except Exception as exc:
        raise RuntimeError(
            "Error al leer "
            f"inventar_SpcHidr.v_bd_ton_reportabilidad: {exc}"
        ) from exc

    if "Fecha" not in df.columns:
        raise RuntimeError(
            "La vista v_bd_ton_reportabilidad no entregó la columna Fecha. "
            f"Columnas recibidas: {list(df.columns)}"
        )

    df["Fecha"] = pd.to_datetime(
        df["Fecha"],
        errors="coerce",
    )
    df = (
        df[df["Fecha"].notna()]
        .sort_values("Fecha", kind="stable")
        .drop_duplicates(subset=["Fecha"], keep="last")
        .reset_index(drop=True)
    )

    return df


def fetch_gestion_representatividad_fy(
    anio_fiscal: int,
    tipo: str,
    alcance: str = "COMBINADO",
    objetivo: float = 0.85,
    fecha_corte: date | None = None,
) -> pd.DataFrame:
    """Consulta los indicadores de gestión de representatividad del FY."""
    tipo = str(tipo).strip().upper()
    alcance = str(alcance).strip().upper()

    if tipo not in {"QUIMICO", "FISICO"}:
        raise ValueError(
            "tipo debe ser QUIMICO o FISICO. "
            f"Valor recibido: {tipo!r}"
        )
    if alcance not in {"TM1", "TM2", "COMBINADO"}:
        raise ValueError(
            "alcance debe ser TM1, TM2 o COMBINADO. "
            f"Valor recibido: {alcance!r}"
        )
    if not 0 <= float(objetivo) <= 1:
        raise ValueError(
            "objetivo debe estar entre 0 y 1. "
            f"Valor recibido: {objetivo!r}"
        )

    conn_or_engine = _get_engine()

    if conn_or_engine is None:
        raise RuntimeError("get_engine() devolvió None.")

    sql_dbapi = """
        SET NOCOUNT ON;
        EXEC inventar_SpcHidr.sp_gestion_representatividad_fy
            @anio_fiscal = ?,
            @tipo = ?,
            @alcance = ?,
            @objetivo = ?,
            @fecha_corte = ?;
    """

    sql_sa = """
        SET NOCOUNT ON;
        EXEC inventar_SpcHidr.sp_gestion_representatividad_fy
            @anio_fiscal = :anio_fiscal,
            @tipo = :tipo,
            @alcance = :alcance,
            @objetivo = :objetivo,
            @fecha_corte = :fecha_corte;
    """

    parametros = {
        "anio_fiscal": anio_fiscal,
        "tipo": tipo,
        "alcance": alcance,
        "objetivo": objetivo,
        "fecha_corte": fecha_corte,
    }

    try:
        if hasattr(conn_or_engine, "cursor"):
            return pd.read_sql(
                sql_dbapi,
                conn_or_engine,
                params=(
                    anio_fiscal,
                    tipo,
                    alcance,
                    objetivo,
                    fecha_corte,
                ),
            )

        with conn_or_engine.connect() as conn:
            return pd.read_sql(
                _sa_text(sql_sa),
                conn,
                params=parametros,
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al ejecutar "
            "inventar_SpcHidr.sp_gestion_representatividad_fy: "
            f"{exc}"
        ) from exc


def fetch_estado_apilado_turno_representatividad(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Obtiene la evaluabilidad oficial de cada Fecha + Turno para el
    Reporte de Representatividad.

    Fuente principal:
        inventar_SpcHidr.v_estado_apilado_turno_representatividad

    Material:
        inventar_SpcHidr.v_reporte_turno_campania_modulo_test

    El rango utiliza fecha final exclusiva:
        Fecha >= start_date
        Fecha <  end_date

    La columna Apilado_TMS_Real se conserva como alias interno de
    compatibilidad con la preparación actual de las hojas mensuales.
    Para Representatividad solo se utiliza su condición mayor que cero.
    """

    from sqlalchemy import text
    from db_connection import get_engine

    engine = get_engine()

    if engine is None:
        raise RuntimeError(
            "No se pudo obtener conexión a la base de datos."
        )

    query = text("""
        SELECT
            e.Fecha,
            e.Turno,

            COALESCE(
                cm.Material,
                'Sin clasificar'
            ) AS Material,

            e.Apilado_TMH_Base AS Apilado_TMS_Real,
            e.Flag_Apilado_Valido,

            CONVERT(
                int,
                e.Turno_Evaluable
            ) AS Turno_Evaluable

        FROM
            [inventar_SpcHidr].[v_estado_apilado_turno_representatividad] AS e

        OUTER APPLY
        (
            SELECT TOP (1)
                c.Material
            FROM
                [inventar_SpcHidr].[v_reporte_turno_campania_modulo_test] AS c
            WHERE
                CAST(c.Fecha AS date) = e.Fecha
            ORDER BY
                CASE
                    WHEN c.Material IS NULL THEN 1
                    ELSE 0
                END,
                COALESCE(c.Volumen_Diario_Modulo_m3, 0) DESC,
                COALESCE(c.Avance, 0) DESC,
                c.Material,
                c.Modulo
        ) AS cm

        WHERE
            e.Fecha >= :start_date
            AND e.Fecha < :end_date

        ORDER BY
            e.Fecha,
            e.Turno;
    """)

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                query,
                conn,
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )

    except Exception as exc:
        raise RuntimeError(
            "Error al consultar el estado de apilado por turno "
            "para Representatividad."
        ) from exc

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce",
        )

    if "Turno" in df.columns:
        df["Turno"] = (
            df["Turno"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # La fuente debe entregar una sola fila por Fecha + Turno.
    duplicados = df[
        df.duplicated(
            subset=["Fecha", "Turno"],
            keep=False,
        )
    ]

    if not duplicados.empty:
        detalle = (
            duplicados[
                ["Fecha", "Turno", "Material"]
            ]
            .sort_values(["Fecha", "Turno"])
            .to_string(index=False)
        )

        raise RuntimeError(
            "La fuente de evaluabilidad entregó más de una fila "
            "para una misma Fecha + Turno.\n"
            f"{detalle}"
        )

    return df

def fetch_reporte_turno_report(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Consulta el reporte por turno via sp_reporte_turno_test.
    Fecha >= start_date AND Fecha < end_date (end_date exclusivo).
    """
    engine = _get_engine()
    sql = """
    EXEC inventar_SpcHidr.sp_reporte_turno_test
        @fecha_inicio = :start,
        @fecha_fin = :end
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(_sa_text(sql), conn, params={"start": start_date, "end": end_date})
    except Exception as e:
        raise RuntimeError(f"Error al leer reporte por turno: {e}") from e
    return df


def fetch_reporte_turno_cache(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Consulta el reporte por turno desde la tabla cache inventar_SpcHidr.reporte_turno_cache.
    Fecha >= start_date AND Fecha < end_date (end_date exclusivo).
    """
    engine = _get_engine()

    sql = """
    SELECT
        Fecha,
        Campania,
        Material,
        Modulo,
        Avance,
        Turno,
        Apilado_TMS_Real,
        Apilado_TMS_Plan_Mensual,
        STOCK,
        MINA,
        SRR,
        CuT_Real,
        CuT_Plan_Mensual,
        CuT_Plan_Semanal,
        CuS_Real,
        CuS_Plan_Mensual,
        CuS_Plan_Semanal,
        Solubilidad_Real,
        Solubilidad_Plan_Mensual,
        Solubilidad_Plan_Semanal,
        CO3_Real,
        CO3_Plan_Mensual,
        CO3_Plan_Semanal,
        CuFe_Real,
        CuFe_Plan_Mensual,
        CuFe_Plan_Semanal,
        FeT_Real,
        FeS_Real,
        ConsH_Real,
        Malla_Menos_1_2_Real,
        Malla_Menos_1_2_Plan_Semanal,
        Malla_Menos_100_Real,
        Malla_Menos_100_Plan_Mensual,
        Malla_Menos_100_Plan_Semanal,
        CaolBeta_Real,
        CaolBeta_Plan_Mensual,
        CaolBeta_Plan_Semanal,
        Dosis_Acido_Ideal_TM,
        Dosis_Acido_Programa_Semanal,
        Fuente_Info_Quimica,
        Fuente_Info_Fisica,
        Muestra_Quimica,
        Muestra_Fisica
    FROM inventar_SpcHidr.reporte_turno_cache
    WHERE Fecha >= :start
      AND Fecha < :end
    ORDER BY Fecha, Turno;
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql(_sa_text(sql), conn, params={"start": start_date, "end": end_date})
    except Exception as e:
        raise RuntimeError(f"Error al leer reporte por turno desde cache: {e}") from e

    return df

def fetch_generador_reporte_diario(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Ejecuta sp_generador_reporte_diario (consolida turnos A y B en una fila diaria).
    Fecha >= start_date AND Fecha < end_date (end_date exclusivo).
    """
    engine = _get_engine()
    sql = """
    EXEC inventar_SpcHidr.sp_generador_reporte_diario
        @fecha_inicio = :start,
        @fecha_fin = :end
    """
    try:
        with engine.connect() as conn:
            return pd.read_sql(_sa_text(sql), conn, params={"start": start_date, "end": end_date})
    except Exception as exc:
        raise RuntimeError(f"Error al ejecutar sp_generador_reporte_diario: {exc}") from exc
def preparar_df_reporte_turno_excel(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    if "Turno" in df.columns:
        df["Turno"] = df["Turno"].astype(str).str.upper().str.strip()
        df["Turno_excel"] = df["Turno"].map({"A": "TA", "B": "TB"}).fillna(df["Turno"])
    else:
        df["Turno_excel"] = ""

    if "Fecha" in df.columns:
        df["Fecha_Turno"] = df["Fecha"].dt.strftime("%d-%m-%Y") + " " + df["Turno_excel"]
        df["Semana"] = "Semana " + (((df["Fecha"].dt.day - 1) // 7) + 1).astype(str)
    else:
        df["Fecha_Turno"] = ""
        df["Semana"] = ""

    # Avance viene desde SQL/cache en escala 0-1.
    # Para el reporte se muestra en escala 0-100.
    if "Avance" in df.columns:
        df["Avance"] = pd.to_numeric(df["Avance"], errors="coerce") * 100

    # STOCK, MINA y SRR ya vienen en escala 0-100 desde SQL/cache.
    # No multiplicar ni dividir.
    for col in ["STOCK", "MINA", "SRR"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Solubilidad es razón CuS/CuT, no porcentaje.
    # No multiplicar por 100 ni agregar símbolo %.
    for col in ["Solubilidad_Real", "Solubilidad_Plan_Semanal", "Solubilidad_Plan_Mensual"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Estandarizar objetivo granulométrico: unidad en encabezado, no en celda.
    # Ejemplo: <75% -> <75
    if "Malla_Menos_1_2_Plan_Semanal" in df.columns:
        df["Malla_Menos_1_2_Plan_Semanal"] = (
            df["Malla_Menos_1_2_Plan_Semanal"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .replace({"nan": np.nan, "None": np.nan, "NULL": np.nan})
        )

    # Normalización visual de material.
    if "Material" in df.columns:
        df["Material"] = (
            df["Material"]
            .astype(str)
            .str.upper()
            .str.strip()
            .replace({
                "SULFUROS": "Sulfuro",
                "SULFURO": "Sulfuro",
                "OXIDOS": "Óxido",
                "OXIDO": "Óxido",
                "ÓXIDOS": "Óxido",
                "ÓXIDO": "Óxido",
            })
        )

    # ------------------------------------------------------------
    # PRESENTACIÓN EN EXCEL: CEROS SIN INFORMACIÓN -> CELDAS VACÍAS
    #
    # No se ocultan ceros válidos. Por ejemplo, MINA = 0 se conserva
    # cuando sí existe apilado real. Solo se limpian bloques sin datos.
    # ------------------------------------------------------------
    columnas_reales = [
        "Apilado_TMS_Real",
        "STOCK",
        "MINA",
        "SRR",
        "CuT_Real",
        "CuS_Real",
        "Solubilidad_Real",
        "CO3_Real",
        "CuFe_Real",
        "FeT_Real",
        "FeS_Real",
        "ConsH_Real",
        "Malla_Menos_1_2_Real",
        "Malla_Menos_100_Real",
        "CaolBeta_Real",
        "Dosis_Acido_Ideal_TM",
    ]

    if "Apilado_TMS_Real" in df.columns:
        apilado_real = pd.to_numeric(
            df["Apilado_TMS_Real"],
            errors="coerce",
        )
        sin_apilado_real = apilado_real.fillna(0).eq(0)

        for col in columnas_reales:
            if col in df.columns:
                df.loc[sin_apilado_real, col] = np.nan

    columnas_plan_mensual = [
        "Apilado_TMS_Plan_Mensual",
        "CuT_Plan_Mensual",
        "CuS_Plan_Mensual",
        "Solubilidad_Plan_Mensual",
        "CO3_Plan_Mensual",
        "CuFe_Plan_Mensual",
        "Malla_Menos_100_Plan_Mensual",
        "CaolBeta_Plan_Mensual",
    ]

    if "Apilado_TMS_Plan_Mensual" in df.columns:
        apilado_plan = pd.to_numeric(
            df["Apilado_TMS_Plan_Mensual"],
            errors="coerce",
        )
        sin_plan_mensual = apilado_plan.fillna(0).eq(0)

        for col in columnas_plan_mensual:
            if col in df.columns:
                df.loc[sin_plan_mensual, col] = np.nan

    # Las variables de programa químico/granulométrico en cero
    # representan ausencia de programa en la fuente.
    columnas_programa = [
        "CuT_Plan_Semanal",
        "CuS_Plan_Semanal",
        "Solubilidad_Plan_Semanal",
        "CO3_Plan_Semanal",
        "CuFe_Plan_Semanal",
        "Malla_Menos_100_Plan_Semanal",
        "CaolBeta_Plan_Semanal",
        "Dosis_Acido_Programa_Semanal",
    ]

    for col in columnas_programa:
        if col in df.columns:
            valores = pd.to_numeric(df[col], errors="coerce")
            df.loc[valores.eq(0), col] = np.nan

    # ------------------------------------------------------------
    # PRESENTACIÓN FINAL EN EXCEL:
    # toda celda numérica vacía se muestra como 0.
    # Los campos descriptivos permanecen como texto.
    # ------------------------------------------------------------
    columnas_texto_export = {
        "Fecha",
        "Turno",
        "Turno_excel",
        "Fecha_Turno",
        "Material",
        "Fuente_Info_Quimica",
        "Fuente_Info_Fisica",
        "Muestra_Quimica",
        "Muestra_Fisica",
        "Malla_Menos_1_2_Plan_Semanal",
    }

    for col in df.columns:
        if col not in columnas_texto_export:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Malla_Menos_1_2_Plan_Semanal" in df.columns:
        df["Malla_Menos_1_2_Plan_Semanal"] = (
            df["Malla_Menos_1_2_Plan_Semanal"]
            .replace({"": "0", "nan": "0", "None": "0", "NULL": "0"})
            .fillna("0")
        )

    return df
def preparar_df_generador_reporte_excel(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepara la capa diaria para exportación.

    Importante:
    - Los valores numéricos sin información se muestran como 0 en Excel.
    - La base de datos y el SP no se modifican.
    - Avance pasa de escala 0-1 a escala 0-100.
    - STOCK, MINA y SRR ya vienen en escala 0-100.
    - Solubilidad permanece como razón 0-1.
    """

    df = df.copy()

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce",
        )

    if "Avance" in df.columns:
        df["Avance"] = (
            pd.to_numeric(df["Avance"], errors="coerce") * 100
        )

    if "Material_Operacion" in df.columns:
        df["Material_Operacion"] = (
            df["Material_Operacion"]
            .astype(str)
            .str.upper()
            .str.strip()
            .replace(
                {
                    "SULFUROS": "Sulfuro",
                    "SULFURO": "Sulfuro",
                    "OXIDOS": "Óxido",
                    "OXIDO": "Óxido",
                    "ÓXIDOS": "Óxido",
                    "ÓXIDO": "Óxido",
                    "NAN": "",
                    "NONE": "",
                }
            )
        )

    if "Clasificacion_Solubilidad" in df.columns:
        df["Clasificacion_Solubilidad"] = (
            df["Clasificacion_Solubilidad"]
            .astype(str)
            .str.capitalize()
            .replace(
                {
                    "Nan": "",
                    "None": "",
                }
            )
        )

    # Mapeo visual según la hoja original "Generador Reporte":
    # - Campaña mantiene el número de campaña (por ejemplo, 11).
    # - Material mantiene el material operacional (Sulfuro/Óxido).
    # - La clasificación por solubilidad no se muestra como columna.
    df["Campaña"] = (
        df["Campania"]
        if "Campania" in df.columns
        else 0
    )
    df["Material"] = (
        df["Material_Operacion"]
        if "Material_Operacion" in df.columns
        else ""
    )

    if "Malla_Menos_1_2_Programa" in df.columns:
        df["Malla_Menos_1_2_Programa"] = (
            df["Malla_Menos_1_2_Programa"]
            .astype(str)
            .replace(
                {
                    "nan": "",
                    "None": "",
                    "NULL": "",
                }
            )
        )

    columnas = [
        "Fecha",
        "Campaña",
        "Material",
        "Modulo",
        "Avance",

        "Apilado_TMS_Real_Dia",
        "Apilado_TMS_Programa",
        "Apilado_TMS_Plan",

        "STOCK_Dia",
        "MINA_Dia",
        "SRR_Dia",

        "CuT_Real_Dia",
        "CuT_Programa",
        "CuT_Plan",

        "CuS_Real_Dia",
        "CuS_Programa",
        "CuS_Plan",

        "Solubilidad_Real_Dia",
        "Solubilidad_Programa",
        "Solubilidad_Plan",

        "CO3_Real_Dia",
        "CO3_Programa",
        "CO3_Plan",

        "CuFe_Real_Dia",
        "CuFe_Programa",
        "CuFe_Plan",

        "FeT_Real_Dia",
        "FeS_Real_Dia",
        "ConsH_Real_Dia",

        "Malla_Menos_1_2_Real_Dia",
        "Malla_Menos_1_2_Programa",

        "Malla_Menos_100_Real_Dia",
        "Malla_Menos_100_Programa",
        "Malla_Menos_100_Plan",

        "CaolBeta_Real_Dia",
        "CaolBeta_Programa",
        "CaolBeta_Plan",

        "Dosis_Acido_Ideal_Dia",
        "Dosis_Acido_Programa_Semanal",
    ]

    columnas = [col for col in columnas if col in df.columns]

    # ------------------------------------------------------------
    # PRESENTACIÓN EN EXCEL: BLOQUES SIN DATOS -> CELDAS VACÍAS
    # ------------------------------------------------------------
    columnas_reales = [
        "Apilado_TMS_Real_Dia",
        "STOCK_Dia",
        "MINA_Dia",
        "SRR_Dia",
        "CuT_Real_Dia",
        "CuS_Real_Dia",
        "Solubilidad_Real_Dia",
        "CO3_Real_Dia",
        "CuFe_Real_Dia",
        "FeT_Real_Dia",
        "FeS_Real_Dia",
        "ConsH_Real_Dia",
        "Malla_Menos_1_2_Real_Dia",
        "Malla_Menos_100_Real_Dia",
        "CaolBeta_Real_Dia",
        "Dosis_Acido_Ideal_Dia",
    ]

    if "Apilado_TMS_Real_Dia" in df.columns:
        apilado_real = pd.to_numeric(
            df["Apilado_TMS_Real_Dia"],
            errors="coerce",
        )
        sin_apilado_real = apilado_real.fillna(0).eq(0)

        for col in columnas_reales:
            if col in df.columns:
                df.loc[sin_apilado_real, col] = np.nan

    columnas_programa = [
        "Apilado_TMS_Programa",
        "CuT_Programa",
        "CuS_Programa",
        "Solubilidad_Programa",
        "CO3_Programa",
        "CuFe_Programa",
        "Malla_Menos_100_Programa",
        "CaolBeta_Programa",
        "Dosis_Acido_Programa_Semanal",
    ]

    if "Apilado_TMS_Programa" in df.columns:
        apilado_programa = pd.to_numeric(
            df["Apilado_TMS_Programa"],
            errors="coerce",
        )
        sin_programa = apilado_programa.fillna(0).eq(0)

        for col in columnas_programa:
            if col in df.columns:
                df.loc[sin_programa, col] = np.nan

    columnas_plan = [
        "Apilado_TMS_Plan",
        "CuT_Plan",
        "CuS_Plan",
        "Solubilidad_Plan",
        "CO3_Plan",
        "CuFe_Plan",
        "Malla_Menos_100_Plan",
        "CaolBeta_Plan",
    ]

    if "Apilado_TMS_Plan" in df.columns:
        apilado_plan = pd.to_numeric(
            df["Apilado_TMS_Plan"],
            errors="coerce",
        )
        sin_plan = apilado_plan.fillna(0).eq(0)

        for col in columnas_plan:
            if col in df.columns:
                df.loc[sin_plan, col] = np.nan

    # ------------------------------------------------------------
    # PRESENTACIÓN FINAL EN EXCEL:
    # toda celda numérica vacía se muestra como 0.
    # Los campos descriptivos permanecen vacíos cuando no hay texto.
    # ------------------------------------------------------------
    columnas_texto_export = {
        "Fecha",
        "Material",
        "Malla_Menos_1_2_Programa",
    }

    for col in columnas:
        if col not in columnas_texto_export:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Malla_Menos_1_2_Programa" in df.columns:
        df["Malla_Menos_1_2_Programa"] = (
            df["Malla_Menos_1_2_Programa"]
            .replace({"": "0", "nan": "0", "None": "0", "NULL": "0"})
            .fillna("0")
        )

    return df[columnas]

def agregar_hoja_generador_reporte(
    writer: pd.ExcelWriter,
    df_diario: pd.DataFrame,
) -> None:
    """
    Agrega la hoja diaria "Generador Reporte" al mismo archivo Excel
    que ya contiene la hoja "Reporte por Turno".

    No modifica el DataFrame ni el diseño de la hoja por turno.
    """

    df_export = preparar_df_generador_reporte_excel(df_diario)

    sheet_name = "Generador Reporte"
    workbook = writer.book
    worksheet = workbook.add_worksheet(sheet_name)
    writer.sheets[sheet_name] = worksheet

    # Mantener la misma lógica visual de la hoja por turno.
    col_offset = 2  # la tabla comienza en la columna C
    fila_data = 21  # Excel fila 22, igual a la plantilla original

    # ============================================================
    # FORMATOS
    # ============================================================
    fmt_titulo = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "align": "left",
        "valign": "vcenter",
    })

    fmt_subtitulo = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "align": "left",
        "valign": "vcenter",
    })

    fmt_grupo = workbook.add_format({
        "bold": True,
        "align": "center",
        "valign": "vcenter",
        "bg_color": "#D9EAF7",
        "border": 1,
        "text_wrap": True,
    })

    fmt_header = workbook.add_format({
        "bold": True,
        "align": "center",
        "valign": "vcenter",
        "bg_color": "#9DC3E6",
        "font_color": "#1F4E79",
        "border": 1,
        "text_wrap": True,
    })

    fmt_header_claro = workbook.add_format({
        "bold": True,
        "align": "center",
        "valign": "vcenter",
        "bg_color": "#D9EAF7",
        "font_color": "#1F4E79",
        "border": 1,
        "text_wrap": True,
    })

    fmt_texto = workbook.add_format({
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })

    fmt_texto_gris = workbook.add_format({
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "bg_color": "#F2F2F2",
        "text_wrap": True,
    })

    fmt_fecha = workbook.add_format({
        "num_format": "dd-mm-yyyy",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_numero = workbook.add_format({
        "num_format": "#,##0",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_decimal_2 = workbook.add_format({
        "num_format": "0.00",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_decimal_3 = workbook.add_format({
        "num_format": "0.000",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_decimal_gris = workbook.add_format({
        "num_format": "0.00",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "bg_color": "#F2F2F2",
    })

    # ============================================================
    # LOGO Y ENCABEZADO INSTITUCIONAL
    # ============================================================
    if os.path.exists(BHP_LOGO_PATH):
        worksheet.insert_image(
            "B1",
            BHP_LOGO_PATH,
            {
                "x_scale": 1.15,
                "y_scale": 1.15,
                "x_offset": 5,
                "y_offset": 3,
                "object_position": 1,
            },
        )

    worksheet.merge_range(
        "G2:AO2",
        "Superintendencia de Medición y Reconciliación",
        fmt_titulo,
    )
    worksheet.merge_range(
        "G3:AO3",
        "Gerencia de Planificación de la Producción",
        fmt_subtitulo,
    )
    worksheet.merge_range(
        "G4:AO4",
        "Minerals Americas / Pampa Norte / Spence",
        fmt_subtitulo,
    )

    # ============================================================
    # ENCABEZADOS SEGÚN LA HOJA ORIGINAL "GENERADOR REPORTE"
    #
    # Se elimina únicamente la columna Semana.
    # No se agrega una columna visible llamada
    # "Clasificación Solubilidad".
    # ============================================================

    # Grupos superiores
    worksheet.merge_range("N18:AE19", "Analisis Quimicos", fmt_grupo)
    worksheet.merge_range("AF18:AJ19", "Granulometrias", fmt_grupo)
    worksheet.merge_range("AK18:AM19", "NIR", fmt_grupo)
    worksheet.merge_range("AN18:AO20", "Dosis de ácido\n(kg/ton)", fmt_grupo)

    # Información general
    worksheet.merge_range("C20:C21", "Fecha", fmt_header_claro)
    worksheet.merge_range("D20:D21", "Campaña", fmt_header_claro)
    worksheet.merge_range("E20:E21", "Material", fmt_header_claro)
    worksheet.merge_range("F20:F21", "Módulo", fmt_header_claro)
    worksheet.merge_range("G20:G21", "Avance", fmt_header_claro)

    # Apilado
    worksheet.merge_range("H20:J20", "Apilado TMS", fmt_header)
    worksheet.write("H21", "TMS", fmt_header)
    worksheet.write("I21", "Programa", fmt_header)
    worksheet.write("J21", "Plan", fmt_header)

    # Distribución de origen
    worksheet.write("K20", "STOCK", fmt_header)
    worksheet.write("L20", "MINA", fmt_header)
    worksheet.write("M20", "SRR", fmt_header)
    worksheet.write("K21", "%", fmt_header)
    worksheet.write("L21", "%", fmt_header)
    worksheet.write("M21", "%", fmt_header)

    # CuT
    worksheet.merge_range("N20:P20", "CuT %", fmt_header)
    worksheet.write("N21", "Real", fmt_header)
    worksheet.write("O21", "Programa", fmt_header)
    worksheet.write("P21", "Plan", fmt_header)

    # CuS
    worksheet.merge_range("Q20:S20", "CuS %", fmt_header)
    worksheet.write("Q21", "Real", fmt_header)
    worksheet.write("R21", "Programa", fmt_header)
    worksheet.write("S21", "Plan", fmt_header)

    # Solubilidad: razón adimensional, sin unidad %
    worksheet.merge_range("T20:V20", "Solubilidad", fmt_header)
    worksheet.write("T21", "Real", fmt_header)
    worksheet.write("U21", "Programa", fmt_header)
    worksheet.write("V21", "Plan", fmt_header)

    # CO3
    worksheet.merge_range("W20:Y20", "CO3 %", fmt_header)
    worksheet.write("W21", "Real", fmt_header)
    worksheet.write("X21", "Programa", fmt_header)
    worksheet.write("Y21", "Plan", fmt_header)

    # CuFe
    worksheet.merge_range("Z20:AB20", "CuFe %", fmt_header)
    worksheet.write("Z21", "Real", fmt_header)
    worksheet.write("AA21", "Programa", fmt_header)
    worksheet.write("AB21", "Plan", fmt_header)

    # Otros análisis
    worksheet.write("AC20", "FeT %", fmt_header)
    worksheet.write("AD20", "FeS %", fmt_header)
    worksheet.write("AE20", "Consumo de Acido kg/ton", fmt_header)
    worksheet.write("AC21", "Real", fmt_header)
    worksheet.write("AD21", "Real", fmt_header)
    worksheet.write("AE21", "Real", fmt_header)

    # Granulometrías
    worksheet.merge_range("AF20:AG20", "-1/2´", fmt_header)
    worksheet.write("AF21", "Real", fmt_header)
    worksheet.write("AG21", "Plan", fmt_header)

    worksheet.merge_range("AH20:AJ20", "-100#Ty", fmt_header)
    worksheet.write("AH21", "Real", fmt_header)
    worksheet.write("AI21", "Programa", fmt_header)
    worksheet.write("AJ21", "Plan", fmt_header)

    # NIR
    worksheet.merge_range("AK20:AM20", "CaolBeta%", fmt_header)
    worksheet.write("AK21", "Real", fmt_header)
    worksheet.write("AL21", "Programa", fmt_header)
    worksheet.write("AM21", "Plan", fmt_header)

    # Dosis de ácido
    # El encabezado ocupa tres filas, igual que en "Reporte por Turno".
    worksheet.write("AN21", "Ideal TM", fmt_header)
    worksheet.write("AO21", "Programa semanal", fmt_header)

    if df_export.empty:
        worksheet.write(fila_data, col_offset, "Sin datos para el rango seleccionado.", fmt_texto)
        worksheet.hide_gridlines(2)
        return

    columnas_numero_entero = {
        "Campaña",
        "Modulo",
        "Apilado_TMS_Real_Dia",
        "Apilado_TMS_Programa",
        "Apilado_TMS_Plan",
    }

    columnas_texto = {
        "Campaña",
        "Material",
        "Malla_Menos_1_2_Programa",
    }

    columnas_grises = {
        "Fecha",
        "Material",
        "Modulo",
        "Avance",
    }

    columnas_2_decimales = {
        "Avance",
        "STOCK_Dia",
        "MINA_Dia",
        "SRR_Dia",
        "Dosis_Acido_Ideal_Dia",
        "Dosis_Acido_Programa_Semanal",
    }

    def es_numero_valido(value) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, (int, float, np.integer, np.floating)):
            return bool(np.isfinite(value))
        return False

    # ============================================================
    # DATOS
    # ============================================================
    for row_idx, (_, row) in enumerate(df_export.iterrows()):
        excel_row = fila_data + row_idx

        for col_idx, col_name in enumerate(df_export.columns):
            excel_col = col_offset + col_idx
            value = row[col_name]

            if pd.isna(value):
                formato_vacio = fmt_texto_gris if col_name in columnas_grises else fmt_texto
                worksheet.write_blank(excel_row, excel_col, None, formato_vacio)
                continue

            if col_name == "Fecha":
                fecha = pd.to_datetime(value, errors="coerce")
                if pd.isna(fecha):
                    worksheet.write_blank(excel_row, excel_col, None, fmt_texto_gris)
                else:
                    worksheet.write_datetime(
                        excel_row,
                        excel_col,
                        fecha.to_pydatetime(),
                        fmt_fecha,
                    )
                continue

            if col_name in columnas_texto:
                formato = fmt_texto_gris if col_name in columnas_grises else fmt_texto
                worksheet.write(excel_row, excel_col, str(value), formato)
                continue

            if col_name in columnas_numero_entero and es_numero_valido(value):
                worksheet.write_number(excel_row, excel_col, float(value), fmt_numero)
                continue

            if es_numero_valido(value):
                formato = fmt_decimal_gris if col_name == "Avance" else fmt_decimal_2
                worksheet.write_number(excel_row, excel_col, float(value), formato)
                continue

            formato = fmt_texto_gris if col_name in columnas_grises else fmt_texto
            worksheet.write(excel_row, excel_col, str(value), formato)

    # ============================================================
    # ANCHOS Y PRESENTACIÓN
    # ============================================================
    worksheet.set_column("A:A", 4)
    worksheet.set_column("B:B", 4)
    worksheet.set_column("C:C", 13)
    worksheet.set_column("D:E", 16)
    worksheet.set_column("F:F", 11)
    worksheet.set_column("G:G", 12)
    worksheet.set_column("H:J", 15)
    worksheet.set_column("K:M", 10)
    worksheet.set_column("N:AB", 12)
    worksheet.set_column("AC:AE", 16)
    worksheet.set_column("AF:AM", 13)
    worksheet.set_column("AN:AO", 16)
    worksheet.set_column("AP:AP", 3)

    worksheet.set_row(0, 42)
    worksheet.set_row(1, 42)
    worksheet.set_row(2, 28)
    worksheet.set_row(3, 24)
    worksheet.set_row(17, 22)
    worksheet.set_row(18, 22)
    worksheet.set_row(19, 28)
    worksheet.set_row(20, 38)

    for row_num in range(fila_data, fila_data + len(df_export)):
        worksheet.set_row(row_num, 20)

    last_row = fila_data + len(df_export) - 1
    last_col = col_offset + len(df_export.columns) - 1

    # Sin paneles congelados ni autofiltro, para mantener
    # el mismo comportamiento visual de la hoja "Reporte por Turno".

    worksheet.set_margins(left=0.35, right=0.35, top=0.35, bottom=0.35)
    worksheet.center_horizontally()
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)
    worksheet.print_area(0, 0, last_row + 2, last_col + 1)
    worksheet.hide_gridlines(2)


def export_reporte_turno_estilo_leyes_finos(
    df: pd.DataFrame,
    output,
    df_generador: pd.DataFrame = None,
):
    """
    Exporta el reporte por turno con formato visual similar al archivo:
    'Actual Reporte Leyes y Finos - Reporte por Turno'.

    Esta versión mejora:
    - Encabezados combinados tipo plantilla.
    - Grupos superiores en filas 19-22.
    - Tabla desde fila 23.
    - Celdas verticales combinadas entre TA/TB para variables comunes del día.
    """

    df = preparar_df_reporte_turno_excel(df)

    columnas = [
        "Fecha",
        "Campania",
        "Material",
        "Modulo",
        "Avance",
        "Turno_excel",

        "Apilado_TMS_Real",
        "Apilado_TMS_Plan_Mensual",

        "STOCK",
        "MINA",
        "SRR",

        "CuT_Real",
        "CuT_Plan_Semanal",
        "CuT_Plan_Mensual",

        "CuS_Real",
        "CuS_Plan_Semanal",
        "CuS_Plan_Mensual",

        "Solubilidad_Real",
        "Solubilidad_Plan_Semanal",
        "Solubilidad_Plan_Mensual",

        "CO3_Real",
        "CO3_Plan_Semanal",
        "CO3_Plan_Mensual",

        "CuFe_Real",
        "FeT_Real",
        "FeS_Real",
        "ConsH_Real",

        "Malla_Menos_1_2_Real",
        "Malla_Menos_1_2_Plan_Semanal",

        "Malla_Menos_100_Real",
        "Malla_Menos_100_Plan_Semanal",
        "Malla_Menos_100_Plan_Mensual",

        "CaolBeta_Real",
        "CaolBeta_Plan_Semanal",
        "CaolBeta_Plan_Mensual",

        "Dosis_Acido_Ideal_TM",
        "Dosis_Acido_Programa_Semanal",

        "Fuente_Info_Quimica",
        "Fuente_Info_Fisica",
    ]

    columnas_finales = [c for c in columnas if c in df.columns]
    df_export = df[columnas_finales].copy()
    col_offset = 2  # deja columnas A:B como margen visual
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        sheet_name = "Reporte por Turno"
        worksheet = workbook.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet
        # ============================================================
        # LOGO BHP
        # ============================================================
        if os.path.exists(BHP_LOGO_PATH):
            worksheet.insert_image(
                "B1",
                BHP_LOGO_PATH,
                {
                    "x_scale": 1.15,
                    "y_scale": 1.15,
                    "x_offset": 5,
                    "y_offset": 3,
                    "object_position": 1,
                }
            )

        # ============================================================
        # FORMATOS
        # ============================================================
        fmt_titulo = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "align": "left",
            "valign": "vcenter"
        })

        fmt_subtitulo = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "align": "left",
        "valign": "vcenter"
        })

        fmt_grupo = workbook.add_format({
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#D9EAF7",
            "border": 1,
            "text_wrap": True
        })

        fmt_header = workbook.add_format({
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#9DC3E6",
            "font_color": "#1F4E79",
            "border": 1,
            "text_wrap": True
        })

        fmt_header_claro = workbook.add_format({
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#D9EAF7",
            "font_color": "#1F4E79",
            "border": 1,
            "text_wrap": True
        })

        fmt_texto = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True
        })

        fmt_texto_gris = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#F2F2F2",
            "text_wrap": True
        })

        fmt_fecha = workbook.add_format({
            "num_format": "dd-mm-yyyy",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_numero = workbook.add_format({
            "num_format": "#,##0",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_num_2 = workbook.add_format({
            "num_format": "0.00",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })

        fmt_decimal = workbook.add_format({
            "num_format": "0.00",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_decimal_gris = workbook.add_format({
            "num_format": "0.00",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#F2F2F2",
        })

        fmt_porcentaje = workbook.add_format({
            "num_format": "0.00",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_blanco = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#FFFFFF"
        })

        # ============================================================
        # ENCABEZADO INSTITUCIONAL
        # ============================================================
        worksheet.merge_range("G2:AM2", "Superintendencia de Medición y Reconciliación", fmt_titulo)
        worksheet.merge_range("G3:AM3", "Gerencia de Planificación de la Producción", fmt_subtitulo)
        worksheet.merge_range("G4:AM4", "Minerals Americas / Pampa Norte / Spence", fmt_subtitulo)

        # ============================================================
        # ENCABEZADOS TIPO PLANTILLA
        # Excel:
        # fila 19 -> índice 18
        # fila 20 -> índice 19
        # fila 21 -> índice 20
        # fila 22 -> índice 21
        # fila 23 datos -> índice 22
        # ============================================================

        worksheet.merge_range("N19:AC20", "Análisis Químicos", fmt_grupo)
        worksheet.merge_range("AD19:AH20", "Granulometrías", fmt_grupo)
        worksheet.merge_range("AI19:AK20", "NIR", fmt_grupo)
        worksheet.merge_range("AL19:AM21", "Dosis de ácido\n(kg/ton)", fmt_grupo)
        worksheet.merge_range("AN19:AO21", "Fuentes de información", fmt_grupo)

        worksheet.merge_range("C21:C22", "Fecha", fmt_header_claro)
        worksheet.merge_range("D21:D22", "Campaña", fmt_header_claro)
        worksheet.merge_range("E21:E22", "Material", fmt_header_claro)
        worksheet.merge_range("F21:F22", "Módulo", fmt_header_claro)
        worksheet.merge_range("G21:G22", "Avance (%)", fmt_header_claro)
        worksheet.merge_range("H21:H22", "Turno", fmt_header_claro)

        worksheet.merge_range("I21:J21", "Apilado TMS", fmt_header)
        worksheet.write("I22", "TMS", fmt_header)
        worksheet.write("J22", "Plan", fmt_header)

        worksheet.write("K21", "Stock", fmt_header)
        worksheet.write("L21", "Mina", fmt_header)
        worksheet.write("M21", "SRR", fmt_header)
        worksheet.write("K22", "%", fmt_header)
        worksheet.write("L22", "%", fmt_header)
        worksheet.write("M22", "%", fmt_header)

        worksheet.merge_range("N21:P21", "CuT (%)", fmt_header)
        worksheet.write("N22", "Real", fmt_header)
        worksheet.write("O22", "Programa", fmt_header)
        worksheet.write("P22", "Plan", fmt_header)

        worksheet.merge_range("Q21:S21", "CuS (%)", fmt_header)
        worksheet.write("Q22", "Real", fmt_header)
        worksheet.write("R22", "Programa", fmt_header)
        worksheet.write("S22", "Plan", fmt_header)

        worksheet.merge_range("T21:V21", "Solubilidad", fmt_header)
        worksheet.write("T22", "Real", fmt_header)
        worksheet.write("U22", "Programa", fmt_header)
        worksheet.write("V22", "Plan", fmt_header)

        worksheet.merge_range("W21:Y21", "CO3 (%)", fmt_header)
        worksheet.write("W22", "Real", fmt_header)
        worksheet.write("X22", "Programa", fmt_header)
        worksheet.write("Y22", "Plan", fmt_header)

        worksheet.write("Z21", "CuFe (%)", fmt_header)
        worksheet.write("AA21", "FeT (%)", fmt_header)
        worksheet.write("AB21", "FeS (%)", fmt_header)
        worksheet.write("AC21", "Consumo de Ácido (kg/ton)", fmt_header)

        worksheet.write("Z22", "Real", fmt_header)
        worksheet.write("AA22", "Real", fmt_header)
        worksheet.write("AB22", "Real", fmt_header)
        worksheet.write("AC22", "Real", fmt_header)

        worksheet.merge_range("AD21:AE21", "-1/2´ (%)", fmt_header)
        worksheet.write("AD22", "Real", fmt_header)
        worksheet.write("AE22", "Plan", fmt_header)

        worksheet.merge_range("AF21:AH21", "-100#Ty (%)", fmt_header)
        worksheet.write("AF22", "Real", fmt_header)
        worksheet.write("AG22", "Programa", fmt_header)
        worksheet.write("AH22", "Plan", fmt_header)

        worksheet.merge_range("AI21:AK21", "CaolBeta (%)", fmt_header)
        worksheet.write("AI22", "Real", fmt_header)
        worksheet.write("AJ22", "Programa", fmt_header)
        worksheet.write("AK22", "Plan", fmt_header)

        worksheet.write("AL22", "Ideal TM", fmt_header)
        worksheet.write("AM22", "Programa", fmt_header)

        worksheet.write("AN22", "Muestra química", fmt_header)
        worksheet.write("AO22", "Muestra física", fmt_header)
        # ============================================================
        # MAPEO DE FORMATOS POR COLUMNA
        # ============================================================
        columnas_numero_0 = [
            "Apilado_TMS_Real",
            "Apilado_TMS_Plan_Mensual",
        ]

        columnas_porcentaje = [
            "STOCK",
            "MINA",
            "SRR",
        ]

        columnas_grises = [
            "Semana",
            "Fecha",
            "Campania",
            "Material",
            "Modulo",
            "Avance",
        ]

        def formato_columna(col_name):
            if col_name == "Fecha":
                return fmt_fecha
            if col_name == "Avance":
                return fmt_decimal_gris
            if col_name in columnas_numero_0:
                return fmt_numero
            if col_name in columnas_porcentaje:
                return fmt_porcentaje
            if col_name in columnas_grises:
                return fmt_texto_gris
            return fmt_decimal

        def es_numero_invalido(value):
            """
            Detecta NaN, inf y -inf antes de escribir en Excel.
            """
            if pd.isna(value):
                return True

            if isinstance(value, (int, float, np.integer, np.floating)):
                return not np.isfinite(value)

            return False


        def escribir_valor(row_idx, excel_col, col_name, value, formato=None):
            if formato is None:
                formato = formato_columna(col_name)

            # Controla NaN, inf, -inf
            if es_numero_invalido(value):
                worksheet.write(row_idx, excel_col, "", fmt_texto)
                return

            if col_name == "Fecha":
                value_fecha = pd.to_datetime(value, errors="coerce")
                if pd.isna(value_fecha):
                    worksheet.write(row_idx, excel_col, "", fmt_texto)
                else:
                    worksheet.write_datetime(row_idx, excel_col, value_fecha.to_pydatetime(), fmt_fecha)
                return

            if col_name in columnas_numero_0:
                worksheet.write_number(row_idx, excel_col, float(value), fmt_numero)
                return

            if col_name in columnas_porcentaje:
                worksheet.write_number(row_idx, excel_col, float(value), fmt_porcentaje)
                return

            if isinstance(value, (int, float, np.integer, np.floating)):
                worksheet.write_number(row_idx, excel_col, float(value), formato)
                return

            worksheet.write(row_idx, excel_col, value, formato if formato is not None else fmt_texto)

        def valor_limpio(value):
            if es_numero_invalido(value):
                return ""
            return value

        # ============================================================
        # DATOS DESDE FILA 23
        # ============================================================
        fila_data = 22

        # Columnas que se deben combinar verticalmente entre TA/TB
        # Solo estética. No cambia datos.
        columnas_merge_vertical = [
            "Fecha",
            "Campania",
            "Material",
            "Modulo",
            "Avance",

            "Apilado_TMS_Plan_Mensual",

            "CuT_Plan_Mensual",
            "CuT_Plan_Semanal",
            "CuS_Plan_Mensual",
            "CuS_Plan_Semanal",
            "Solubilidad_Plan_Mensual",
            "Solubilidad_Plan_Semanal",
            "CO3_Plan_Mensual",
            "CO3_Plan_Semanal",

            "Malla_Menos_1_2_Plan_Semanal",
            "Malla_Menos_100_Plan_Mensual",
            "Malla_Menos_100_Plan_Semanal",

            "CaolBeta_Plan_Mensual",
            "CaolBeta_Plan_Semanal",
            "Dosis_Acido_Ideal_TM",
            "Dosis_Acido_Programa_Semanal",
        ]

        columnas_merge_vertical = [c for c in columnas_merge_vertical if c in df_export.columns]

        celdas_saltadas = set()

        for i, (_, row) in enumerate(df_export.iterrows()):
            excel_row = fila_data + i

            for col_idx, col_name in enumerate(columnas_finales):
                excel_col = col_idx + col_offset
                if (excel_row, excel_col) in celdas_saltadas:
                    continue

                value = row[col_name]

                # Intento de merge vertical con fila siguiente
                puede_merge = (
                    col_name in columnas_merge_vertical
                    and i + 1 < len(df_export)
                )

                if puede_merge:
                    row_next = df_export.iloc[i + 1]

                    misma_fecha = False
                    if "Fecha" in df_export.columns:
                        f1 = pd.to_datetime(row.get("Fecha"), errors="coerce")
                        f2 = pd.to_datetime(row_next.get("Fecha"), errors="coerce")
                        misma_fecha = pd.notna(f1) and pd.notna(f2) and f1.date() == f2.date()

                    v1 = valor_limpio(value)
                    v2 = valor_limpio(row_next[col_name])

                    mismos_valores = str(v1) == str(v2)

                    if misma_fecha and mismos_valores:
                        formato = formato_columna(col_name)

                        # xlsxwriter permite merge_range con formatos.
                        # Para fechas conviene escribir el valor como texto visual para evitar problemas.
                        if col_name == "Fecha":
                            fecha_txt = pd.to_datetime(value).strftime("%d-%m-%Y") if pd.notna(value) else ""
                            worksheet.merge_range(
                                excel_row, 
                                excel_col, 
                                excel_row + 1, 
                                excel_col, 
                                fecha_txt, 
                                fmt_texto_gris
                                )
                        else:
                            if es_numero_invalido(value):
                                worksheet.merge_range(
                                    excel_row,
                                    excel_col,
                                    excel_row + 1,
                                    excel_col,
                                    "",
                                    fmt_texto
                                )
                            else:
                                worksheet.merge_range(
                                    excel_row,
                                    excel_col,
                                    excel_row + 1,
                                    excel_col,
                                    value,
                                    formato
                                )
                        celdas_saltadas.add((excel_row + 1, excel_col))
                        continue

                # Escritura normal
                if col_name in ["Fecha_Turno", "Turno_excel", "Muestra_Quimica", "Muestra_Fisica"]:
                    escribir_valor(excel_row, excel_col, col_name, value, fmt_texto)
                elif col_name == "Avance":
                    escribir_valor(excel_row, excel_col, col_name, value, fmt_decimal_gris)
                elif col_name in columnas_grises:
                    escribir_valor(excel_row, excel_col, col_name, value, fmt_texto_gris)
                else:
                    escribir_valor(excel_row, excel_col, col_name, value)

        # ============================================================
        # FORMATO GENERAL
        # ============================================================
        worksheet.set_column("A:A", 4)
        worksheet.set_column("B:B", 4)
        worksheet.set_column("C:C", 18)
        worksheet.set_column("D:D", 11)
        worksheet.set_column("E:E", 13)
        worksheet.set_column("F:F", 13)
        worksheet.set_column("G:G", 13)
        worksheet.set_column("H:H", 11)

        worksheet.set_column("I:J", 13)
        worksheet.set_column("K:M", 9)
        worksheet.set_column("L:W", 11)
        worksheet.set_column("X:AA", 12)
        worksheet.set_column("AB:AB", 12)
        worksheet.set_column("AC:AC", 23)
        worksheet.set_column("AD:AF", 12)
        worksheet.set_column("AG:AI", 12)
        worksheet.set_column("AJ:AK", 15)
        worksheet.set_column("AL:AM", 15)
        worksheet.set_column("AN:AO", 18)
        worksheet.set_column("AP:AP", 3)
        
        # Espacio superior para logo y encabezado institucional
        worksheet.set_row(0, 42)
        worksheet.set_row(1, 42)
        worksheet.set_row(2, 28)
        worksheet.set_row(3, 24)
        worksheet.set_row(4, 24)
        worksheet.set_row(5, 24)

        worksheet.set_row(18, 22)
        worksheet.set_row(19, 22)
        worksheet.set_row(20, 28)
        worksheet.set_row(21, 38)

        # Alto de filas de datos
        for r in range(fila_data, fila_data + len(df_export)):
            worksheet.set_row(r, 20)

        last_row = fila_data + len(df_export) - 1
        last_col = len(columnas_finales) - 1 + col_offset

        # ============================================================
        # MARGEN VISUAL + FRANJA / MARCO DEL REPORTE
        # ============================================================

        # Márgenes reales de impresión
        worksheet.set_margins(
            left=0.35,
            right=0.35,
            top=0.35,
            bottom=0.35
        )

        # Centrar horizontalmente al imprimir
        worksheet.center_horizontally()

        # Orientación y ajuste a página
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)

        # Definir área de impresión considerando logo + tabla
        worksheet.print_area(0, 0, last_row + 2, last_col + 1)

        # Marco exterior visual del reporte
        fmt_marco_superior = workbook.add_format({
            "top": 2,
            "top_color": "#808080"
        })

        fmt_marco_inferior = workbook.add_format({
            "bottom": 2,
            "bottom_color": "#808080"
        })

        fmt_marco_izquierdo = workbook.add_format({
            "left": 2,
            "left_color": "#808080"
        })

        fmt_marco_derecho = workbook.add_format({
            "right": 2,
            "right_color": "#808080"
        })

        # Coordenadas del marco visual
        marco_fila_ini = 0
        marco_fila_fin = last_row + 2
        marco_col_ini = 0
        marco_col_fin = last_col + 1

        # Borde superior
        for c in range(marco_col_ini, marco_col_fin + 1):
            worksheet.write_blank(marco_fila_ini, c, None, fmt_marco_superior)

        # Borde inferior
        for c in range(marco_col_ini, marco_col_fin + 1):
            worksheet.write_blank(marco_fila_fin, c, None, fmt_marco_inferior)

        # Borde izquierdo
        for r in range(marco_fila_ini, marco_fila_fin + 1):
            worksheet.write_blank(r, marco_col_ini, None, fmt_marco_izquierdo)

        # Borde derecho
        for r in range(marco_fila_ini, marco_fila_fin + 1):
            worksheet.write_blank(r, marco_col_fin, None, fmt_marco_derecho)
        # Ocultar líneas de cuadrícula para parecer más plantilla
        worksheet.hide_gridlines(2)

        # ============================================================
        # SEGUNDA HOJA: GENERADOR REPORTE
        # ============================================================
        if df_generador is not None:
            agregar_hoja_generador_reporte(
                writer=writer,
                df_diario=df_generador,
            )
