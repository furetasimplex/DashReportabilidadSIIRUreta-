import os
import io
import calendar
import pandas as pd
import numpy as np
from datetime import date, timedelta
try:
    from db_connection import get_engine
except Exception as e:
    raise RuntimeError("No se pudo importar get_engine desde db_connection.py") from e

from sqlalchemy import text as _sa_text
from report_export.balance_contract import BALANCE_RECON_SOURCE


class BalanceReportError(ValueError):
    """Error de validacion del reporte Balance apto para mostrar en Dash."""


def _get_engine():
    engine = get_engine()
    if engine is None:
        raise RuntimeError("get_engine() devolvio None: revisar configuracion de DB.")
    return engine


def fetch_recon_balance_run_report(run_id: int):
    """Lee y valida los 120 flujos de un Run del reconciliador (solo SELECT)."""
    try:
        run_id = int(run_id)
    except (TypeError, ValueError) as exc:
        raise BalanceReportError("run_id debe ser un entero valido.") from exc

    sql_flujos = _sa_text(f"""
        SELECT
            rf.codigo_flujo,
            rf.tolerancia_masa,
            rf.tolerancia_ley,
            rf.masa_medida,
            rf.masa_reconciliada,
            rf.ley_cu_medida,
            rf.ley_cu_reconciliada,
            rf.fino_cu_medido,
            rf.fino_cu_reconciliado
        FROM {BALANCE_RECON_SOURCE}.recon_resultado_flujo AS rf
        WHERE rf.run_id = :run_id
    """)
    sql_metadata = _sa_text(f"""
        SELECT
            sr.id AS run_id,
            sr.caso_id,
            sr.estado AS estado_run,
            sr.solver_name,
            sr.solver_version,
            sr.started_at,
            sr.finished_at,
            c.nombre_caso,
            c.fecha_inicio,
            c.fecha_fin,
            c.modelo_id,
            CASE WHEN co.solver_run_id = sr.id THEN 1 ELSE 0 END AS es_oficial
        FROM {BALANCE_RECON_SOURCE}.recon_solver_run AS sr
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_caso AS c ON c.id = sr.caso_id
        LEFT JOIN {BALANCE_RECON_SOURCE}.recon_caso_oficial AS co
          ON co.caso_id = sr.caso_id
         AND co.solver_run_id = sr.id
        WHERE sr.id = :run_id
    """)

    try:
        with _get_engine().connect() as conn:
            df_metadata = pd.read_sql_query(
                sql_metadata, conn, params={"run_id": run_id}
            )
            df_run = pd.read_sql_query(
                sql_flujos, conn, params={"run_id": run_id}
            )
    except BalanceReportError:
        raise
    except Exception as exc:
        raise BalanceReportError(
            "No fue posible consultar los resultados oficiales del Balance."
        ) from exc

    if df_metadata.empty:
        raise BalanceReportError(f"El Run {run_id} no existe.")
    if len(df_metadata) != 1:
        raise BalanceReportError(
            f"El Run {run_id} devolvio metadata ambigua ({len(df_metadata)} filas)."
        )

    metadata = df_metadata.iloc[0].to_dict()
    if str(metadata.get("estado_run", "")).strip().lower() != "success":
        raise BalanceReportError(
            f"El Run {run_id} no finalizo con estado success."
        )

    if len(df_run) != 120:
        raise BalanceReportError(
            f"El Run {run_id} posee {len(df_run)} flujos; se esperaban 120."
        )
    if "codigo_flujo" not in df_run.columns:
        raise BalanceReportError("La consulta del Run no devolvio codigo_flujo.")
    codigos = df_run["codigo_flujo"]
    if codigos.isna().any():
        raise BalanceReportError(f"El Run {run_id} contiene codigo_flujo NULL.")
    codigos = codigos.astype(str).str.strip()
    duplicados = sorted(codigos[codigos.duplicated(keep=False)].unique())
    if duplicados:
        raise BalanceReportError(
            "El Run contiene codigos duplicados: " + ", ".join(duplicados) + "."
        )
    esperados = {f"F{i}" for i in range(1, 121)}
    recibidos = set(codigos)
    faltantes = sorted(esperados - recibidos, key=lambda x: int(x[1:]))
    extras = sorted(recibidos - esperados)
    if faltantes:
        raise BalanceReportError("Faltan flujos: " + ", ".join(faltantes) + ".")
    if extras:
        raise BalanceReportError("Existen flujos no esperados: " + ", ".join(extras) + ".")

    df_run = df_run.copy()
    df_run["codigo_flujo"] = codigos
    if df_run["codigo_flujo"].nunique() != 120:
        raise BalanceReportError(
            f"El Run {run_id} no posee 120 codigo_flujo distintos."
        )
    metadata["es_oficial"] = bool(metadata.get("es_oficial"))
    return df_run.set_index("codigo_flujo", drop=False), metadata


def validate_recon_balance_result(df_run, metadata, identifier):
    """Valida el contrato comun de cualquier Run de Balance F1-F120."""
    if df_run is None or len(df_run) != 120:
        count = 0 if df_run is None else len(df_run)
        raise BalanceReportError(
            f"{identifier} posee {count} flujos; se esperaban 120."
        )
    if "codigo_flujo" not in df_run.columns:
        raise BalanceReportError(f"{identifier} no devolvio codigo_flujo.")
    codes = df_run["codigo_flujo"]
    if codes.isna().any():
        raise BalanceReportError(f"{identifier} contiene codigo_flujo NULL.")
    codes = codes.astype(str).str.strip()
    duplicates = sorted(codes[codes.duplicated(keep=False)].unique())
    if duplicates:
        raise BalanceReportError(
            f"{identifier} contiene codigos duplicados: "
            + ", ".join(duplicates)
            + "."
        )
    expected = {f"F{i}" for i in range(1, 121)}
    received = set(codes)
    missing = sorted(expected - received, key=lambda value: int(value[1:]))
    extras = sorted(received - expected)
    if missing:
        raise BalanceReportError("Faltan flujos: " + ", ".join(missing) + ".")
    if extras:
        raise BalanceReportError(
            "Existen flujos no esperados: " + ", ".join(extras) + "."
        )
    state = str(metadata.get("estado_run", "")).strip().lower()
    if state != "success":
        raise BalanceReportError(
            f"{identifier} no finalizo con estado success."
        )
    validated = df_run.copy()
    validated["codigo_flujo"] = codes
    return validated.set_index("codigo_flujo", drop=False)


def fetch_recon_balance_official_cases():
    """Lista Casos con una relacion oficial para el selector de Balance."""
    sql = _sa_text(f"""
        SELECT
            c.id AS caso_id,
            c.nombre_caso,
            c.fecha_inicio,
            c.fecha_fin,
            c.modelo_id,
            co.solver_run_id,
            sr.estado AS estado_run
        FROM {BALANCE_RECON_SOURCE}.recon_caso AS c
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_caso_oficial AS co
            ON co.caso_id = c.id
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_solver_run AS sr
            ON sr.id = co.solver_run_id
           AND sr.caso_id = c.id
        ORDER BY c.fecha_fin DESC, c.fecha_inicio DESC, c.id DESC
    """)
    try:
        with _get_engine().connect() as conn:
            return pd.read_sql_query(sql, conn)
    except Exception as exc:
        raise BalanceReportError(
            f"No fue posible listar los Casos oficiales de Balance: {exc}"
        ) from exc


def fetch_recon_balance_official_case(caso_id):
    """Resuelve caso_id -> Run oficial y devuelve sus 120 resultados."""
    try:
        caso_id = int(caso_id)
    except (TypeError, ValueError) as exc:
        raise BalanceReportError("caso_id debe ser un entero valido.") from exc

    sql_case = _sa_text(f"""
        SELECT id AS caso_id
        FROM {BALANCE_RECON_SOURCE}.recon_caso
        WHERE id = :caso_id
    """)
    sql_metadata = _sa_text(f"""
        SELECT
            c.id AS caso_id,
            c.nombre_caso,
            c.fecha_inicio,
            c.fecha_fin,
            c.modelo_id,
            sr.id AS solver_run_id,
            sr.id AS run_id,
            sr.estado AS estado_run,
            sr.solver_name,
            sr.solver_version,
            sr.started_at,
            sr.finished_at,
            co.oficializado_en,
            CAST(1 AS bit) AS es_oficial
        FROM {BALANCE_RECON_SOURCE}.recon_caso AS c
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_caso_oficial AS co
            ON co.caso_id = c.id
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_solver_run AS sr
            ON sr.id = co.solver_run_id
           AND sr.caso_id = c.id
        WHERE c.id = :caso_id
    """)
    sql_flows = _sa_text(f"""
        SELECT
            rf.codigo_flujo,
            rf.tolerancia_masa,
            rf.tolerancia_ley,
            rf.masa_medida,
            rf.masa_reconciliada,
            rf.ley_cu_medida,
            rf.ley_cu_reconciliada,
            rf.fino_cu_medido,
            rf.fino_cu_reconciliado
        FROM {BALANCE_RECON_SOURCE}.recon_caso AS c
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_caso_oficial AS co
            ON co.caso_id = c.id
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_solver_run AS sr
            ON sr.id = co.solver_run_id
           AND sr.caso_id = c.id
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_resultado_flujo AS rf
            ON rf.run_id = sr.id
           AND rf.caso_id = c.id
        WHERE c.id = :caso_id
    """)
    try:
        with _get_engine().connect() as conn:
            exists = pd.read_sql_query(
                sql_case, conn, params={"caso_id": caso_id}
            )
            metadata_df = pd.read_sql_query(
                sql_metadata, conn, params={"caso_id": caso_id}
            )
            flows = pd.read_sql_query(
                sql_flows, conn, params={"caso_id": caso_id}
            )
    except Exception as exc:
        raise BalanceReportError(
            "No fue posible consultar los resultados oficiales del Balance."
        ) from exc

    if exists.empty:
        raise BalanceReportError(f"El Caso {caso_id} no existe.")
    if metadata_df.empty:
        raise BalanceReportError(f"El Caso {caso_id} no posee un Run oficial.")
    if len(metadata_df) != 1:
        raise BalanceReportError(
            f"El Caso {caso_id} posee {len(metadata_df)} Runs oficiales; "
            "se esperaba exactamente uno."
        )
    metadata = metadata_df.iloc[0].to_dict()
    metadata["es_oficial"] = True
    validated = validate_recon_balance_result(
        flows, metadata, f"El Run oficial {int(metadata['solver_run_id'])}"
    )
    return validated, metadata


def fetch_recon_balance_mtd_candidates(modelo_id, fecha_inicio, fecha_fin):
    """Lee resultados de Casos oficiales que intersectan la ventana MTD."""
    sql = _sa_text(f"""
        SELECT
            c.id AS caso_id,
            c.nombre_caso,
            c.fecha_inicio,
            c.fecha_fin,
            c.modelo_id,
            sr.id AS solver_run_id,
            sr.estado AS estado_run,
            sr.solver_name,
            sr.solver_version,
            co.oficializado_en,
            rf.codigo_flujo,
            rf.tolerancia_masa,
            rf.tolerancia_ley,
            rf.masa_medida,
            rf.masa_reconciliada,
            rf.ley_cu_medida,
            rf.ley_cu_reconciliada,
            rf.fino_cu_medido,
            rf.fino_cu_reconciliado
        FROM {BALANCE_RECON_SOURCE}.recon_caso AS c
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_caso_oficial AS co
            ON co.caso_id = c.id
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_solver_run AS sr
            ON sr.id = co.solver_run_id
           AND sr.caso_id = c.id
        INNER JOIN {BALANCE_RECON_SOURCE}.recon_resultado_flujo AS rf
            ON rf.run_id = sr.id
           AND rf.caso_id = c.id
        WHERE c.modelo_id = :modelo_id
          AND c.fecha_fin >= :fecha_inicio
          AND c.fecha_inicio <= :fecha_fin
        ORDER BY c.fecha_inicio, c.fecha_fin, c.id, rf.codigo_flujo
    """)
    try:
        with _get_engine().connect() as conn:
            return pd.read_sql_query(
                sql,
                conn,
                params={
                    "modelo_id": int(modelo_id),
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                },
            )
    except Exception as exc:
        raise BalanceReportError(
            "No fue posible consultar los resultados oficiales del Balance."
        ) from exc


def log_db_destino_reporte_torre() -> dict:
    """Registra la instancia SQL efectiva usada por el flujo RTO."""
    sql = _sa_text("""
        SELECT
            @@SERVERNAME AS server_name,
            DB_NAME() AS database_name,
            SUSER_SNAME() AS login_name
    """)
    try:
        with _get_engine().connect() as conn:
            fila = conn.execute(sql).mappings().one()
        destino = {
            "server_name": fila.get("server_name"),
            "database_name": fila.get("database_name"),
            "login_name": fila.get("login_name"),
        }
    except Exception as exc:
        raise RuntimeError(
            f"No fue posible identificar la DB destino de RTO: {exc}"
        ) from exc

    print(f"[RTO] DB destino: {destino}")
    return destino

# Nombre completo de la tabla (ajusta si cambia)
TABLE_FQN = "[inventar_SpcHidr].[Datos_conciliados_of]"
TABLE_DATOS_CONCILIADOS = "[inventar_SpcHidr].[Datos_conciliados_of]"
# Decision 2026-08-01: se rompe el vinculo con la copia de prueba
# Datos_conciliados_of_emision_test. El flujo "emision" (usado por la
# vista previa, la exportacion a Excel y la exportacion a PDF de Datos
# Conciliados) ahora lee y escribe directamente sobre la tabla productiva
# Datos_conciliados_of, usando sp_mantiene_datos_conciliados_emision_test
# (SP_MANTIENE_DATOS_CONCILIADOS_EMISION, sin cambios) como unico
# mantenedor. La tabla Datos_conciliados_of_emision_test queda obsoleta:
# se elimina de la base de datos solo despues de validar dias 1-26 de
# julio 2026 contra el dashboard de reclamo.
TABLE_DATOS_CONCILIADOS_EMISION = "[inventar_SpcHidr].[Datos_conciliados_of]"
# Centralizado para que posteriormente pueda resolverse según ENTORNO.
# Por requerimiento actual se mantiene el esquema existente.
DATOS_CONCILIADOS_SCHEMA = "inventar_SpcHidr"
SP_MANTIENE_DATOS_CONCILIADOS = (
    f"[{DATOS_CONCILIADOS_SCHEMA}].[sp_mantiene_datos_conciliados_of]"
)
SP_MANTIENE_DATOS_CONCILIADOS_EMISION = (
    f"[{DATOS_CONCILIADOS_SCHEMA}].[sp_mantiene_datos_conciliados_emision_test]"
)
SP_REFRESCA_HISTORICO_APILADO = (
    f"[{DATOS_CONCILIADOS_SCHEMA}].[sp_refrescar_historico_apilado_test]"
)
SP_ACTUALIZA_REPORTE_TURNO_CACHE = (
    f"[{DATOS_CONCILIADOS_SCHEMA}].[sp_actualizar_reporte_turno_cache]"
)
TABLE_REPORTE_TURNO_CACHE_EMISION = (
    f"[{DATOS_CONCILIADOS_SCHEMA}].[reporte_turno_cache_emision_test]"
)
SP_ACTUALIZA_REPORTE_TURNO_CACHE_EMISION = (
    f"[{DATOS_CONCILIADOS_SCHEMA}].[sp_actualizar_reporte_turno_cache_emision_test]"
)
SP_REFRESCA_CLAYS_CUFE = (
    f"[{DATOS_CONCILIADOS_SCHEMA}].[sp_refrescar_clays_cufe]"
)
FECHA_CORTE_CLAYS_CUFE = date(2026, 8, 1)
SP_GENERADOR_REPORTE_DIARIO_EMISION = (
    f"[{DATOS_CONCILIADOS_SCHEMA}].[sp_generador_reporte_diario_emision_test]"
)
# Ruta del logo BHP
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

BHP_LOGO_PATH = os.path.join(PROJECT_DIR, "assets", "pampa-norte-bhp-oficial.png")

COLOR_PAMPA_NORTE = "#018982"
COLOR_BLANCO = "#FFFFFF"
COLOR_BORDE = "#808080"
COLOR_IMP = "#FF0000"
COLOR_MB = "#FFC000"
COLOR_TM2 = "#92D050"
COLOR_TM1 = "#00B0F0"

def _aplicar_dimensiones_oficiales_torre(worksheet, con_turno=False):
    worksheet.set_column("A:A", 15 if con_turno else 11)
    worksheet.set_column("B:B", 10 if con_turno else 9)
    worksheet.set_column("C:C", 13.8)
    worksheet.set_column("D:D", 14.3 if con_turno else 15.4)
    worksheet.set_column("E:E", 12.8)
    worksheet.set_column("F:F", 11.8)
    worksheet.set_column("G:AM", 13)
    worksheet.set_column("AN:AN", 10.2 if con_turno else 13)
    worksheet.set_column("AO:AO", 9.8 if con_turno else 13)
    worksheet.set_column("AP:AP", 5.2 if con_turno else 11.4)

    # Alturas medidas en la versión oficial del 17-07-2026.
    worksheet.set_row(0, 15)
    worksheet.set_row(1, 15.6)
    worksheet.set_row(2, 21 if con_turno else 21.6)
    worksheet.set_row(3, 23.7 if con_turno else 21)
    worksheet.set_row(4, 23.7 if con_turno else 21)
    worksheet.set_row(5, 23.7 if con_turno else 21)
    worksheet.set_row(6, 15)


def _agregar_encabezado_institucional_torre(
    worksheet,
    fmt_titulo,
    fmt_subtitulo,
    con_turno=False,
):
    """Replica el encabezado de la versión oficial del 17-07-2026."""
    if os.path.exists(BHP_LOGO_PATH):
        # La hoja por turno usa una imagen apenas más alta en el original.
        # El PNG oficial declara 144 dpi; XlsxWriter normaliza a 96 dpi.
        # Estos factores compensados reproducen el tamaño físico de Excel.
        x_scale = 0.65865 if con_turno else 0.65235
        y_scale = 0.73695 if con_turno else 0.66195
        worksheet.insert_image(
            "C3",
            BHP_LOGO_PATH,
            {
                "x_scale": x_scale,
                "y_scale": y_scale,
                "x_offset": 55.2,
                "y_offset": 24.2 if con_turno else 25.25,
                "object_position": 1,
            },
        )

    worksheet.merge_range(
        "H4:T4",
        "Superintendencia de Medición y Reconciliación",
        fmt_titulo,
    )
    worksheet.merge_range(
        "H5:T5",
        "Gerencia de Planificación de la Producción",
        fmt_subtitulo,
    )
    worksheet.merge_range(
        "H6:T6",
        "Minerals Americas / Pampa Norte / Spence",
        fmt_subtitulo,
    )


def _agregar_cuadro_formula_dosis_acido(workbook, worksheet):
    """Agrega la nota metodolÃ³gica visual de dosis de Ã¡cido ideal."""
    fmt_titulo = workbook.add_format({
        "font_name": "Arial",
        "font_size": 9,
        "bold": True,
        "font_color": COLOR_PAMPA_NORTE,
        "align": "left",
        "valign": "vcenter",
        "bottom": 1,
        "bottom_color": "#B7B7B7",
    })
    fmt_formula = workbook.add_format({
        "font_name": "Arial",
        "font_size": 7,
        "font_color": "#555555",
        "align": "left",
        "valign": "vcenter",
    })
    fmt_nota = workbook.add_format({
        "font_name": "Arial",
        "font_size": 6,
        "italic": True,
        "font_color": "#8A8A8A",
        "align": "left",
        "valign": "vcenter",
    })

    # Cuadro metodolÃ³gico informativo.
    # No calcula la dosis; documenta la lÃ³gica vigente utilizada
    # para Dosis_Acido_Ideal_TM.
    worksheet.merge_range(
        "V4:AO4",
        "Dosis \u00e1cido Ideal TM",
        fmt_titulo,
    )
    worksheet.merge_range(
        "V5:AO5",
        "S = CuS/CuT   |   S < 0,25:  14 si CO\u2083 \u2264 0,25;   "
        "11 + 15,51\u00b7CO\u2083 si CO\u2083 > 0,25",
        fmt_formula,
    )
    worksheet.merge_range(
        "V6:AO6",
        "S \u2265 0,25:  MAX(14; 8,182\u00b7LN(CuS) + 18,99 + "
        "15,51\u00b7CO\u2083)   |   CuS \u2264 0 \u2192 0",
        fmt_formula,
    )
    worksheet.merge_range(
        "V7:AO7",
        "Sin Apilado real o variables requeridas: no evaluable.",
        fmt_nota,
    )


def _agregar_marco_exterior_torre(
    workbook,
    worksheet,
    last_row,
    last_col,
    filas_respiro_final=2,
):
    """Agrega el marco dinámico compartido por las dos hojas de torres."""
    color_marco = "#000000"
    fmt_marco_superior = workbook.add_format({
        "top": 2, "top_color": color_marco,
    })
    fmt_marco_izquierdo = workbook.add_format({
        "left": 2, "left_color": color_marco,
    })
    fmt_marco_derecho = workbook.add_format({
        "right": 2, "right_color": color_marco,
    })
    fmt_marco_inferior = workbook.add_format({
        "bottom": 2, "bottom_color": color_marco,
    })
    fmt_esquina_sup_izq = workbook.add_format({
        "top": 2, "top_color": color_marco,
        "left": 2, "left_color": color_marco,
    })
    fmt_esquina_sup_der = workbook.add_format({
        "top": 2, "top_color": color_marco,
        "right": 2, "right_color": color_marco,
    })
    fmt_esquina_inf_izq = workbook.add_format({
        "bottom": 2, "bottom_color": color_marco,
        "left": 2, "left_color": color_marco,
    })
    fmt_esquina_inf_der = workbook.add_format({
        "bottom": 2, "bottom_color": color_marco,
        "right": 2, "right_color": color_marco,
    })

    marco_fila_ini = 1
    marco_fila_fin = last_row + filas_respiro_final
    marco_col_ini = 1
    # Ambas plantillas oficiales cierran en AP, incluso si una consulta
    # devuelve temporalmente menos columnas con datos.
    marco_col_fin = max(last_col + 1, 41)

    worksheet.write_blank(
        marco_fila_ini, marco_col_ini, None, fmt_esquina_sup_izq,
    )
    worksheet.write_blank(
        marco_fila_ini, marco_col_fin, None, fmt_esquina_sup_der,
    )
    for c in range(marco_col_ini + 1, marco_col_fin):
        worksheet.write_blank(marco_fila_ini, c, None, fmt_marco_superior)

    for r in range(marco_fila_ini + 1, marco_fila_fin):
        worksheet.write_blank(r, marco_col_ini, None, fmt_marco_izquierdo)
        worksheet.write_blank(r, marco_col_fin, None, fmt_marco_derecho)

    worksheet.write_blank(
        marco_fila_fin, marco_col_ini, None, fmt_esquina_inf_izq,
    )
    worksheet.write_blank(
        marco_fila_fin, marco_col_fin, None, fmt_esquina_inf_der,
    )
    for c in range(marco_col_ini + 1, marco_col_fin):
        worksheet.write_blank(marco_fila_fin, c, None, fmt_marco_inferior)
# Columnas exactas para el reporte "Producción Diaria" / plantilla Datos conciliados
COLUMNAS_DATOS_CONCILIADOS = [
    "Fecha", "Chancado_TMS_Real", "Humedad_Turno_A", "Humedad_Turno_B", "Humedad_promedio_dia",
    "Sal_turno_A", "Sal_Turno_B", "Sal_promedio_dia", "SRR_TMS_Turno_A", 
	"SRR_TMS_Turno_B", 
	"SRR_TMS_promedio_dia", 
	"SRR_TMS_Plan", 
	"Ley_CuT_Real_srr", 
	"Ley_CuT_Plan_srr",
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


def refrescar_historico_apilado_report(
    start_date: date,
    end_date: date,
    dias_reproceso: int = 0,
) -> None:
    """Refresca el histórico de apilado antes de mantener Datos Conciliados."""
    if start_date is None or end_date is None:
        raise ValueError("FechaInicio y FechaFin son obligatorias para refrescar el histórico de apilado.")
    if start_date > end_date:
        raise ValueError("FechaInicio no puede ser posterior a FechaFin.")

    sql = _sa_text(f"""
        SET NOCOUNT ON;
        EXEC {SP_REFRESCA_HISTORICO_APILADO}
            @FechaInicio = :fecha_inicio,
            @FechaFin = :fecha_fin,
            @DiasReproceso = :dias_reproceso
    """)
    try:
        with _get_engine().begin() as conn:
            conn.execute(
                sql,
                {
                    "fecha_inicio": start_date,
                    "fecha_fin": end_date,
                    "dias_reproceso": int(dias_reproceso),
                },
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al refrescar el histórico de apilado mediante "
            f"{SP_REFRESCA_HISTORICO_APILADO}: {exc}"
        ) from exc


def actualizar_datos_conciliados_report(
    start_date: date,
    end_date: date,
    dias_reproceso: int = 0,
) -> None:
    """Actualiza Datos_conciliados_of antes de generar el reporte Excel."""
    if start_date is None or end_date is None:
        raise ValueError("FechaInicio y FechaFin son obligatorias para actualizar Datos Conciliados.")
    if start_date > end_date:
        raise ValueError("FechaInicio no puede ser posterior a FechaFin.")

    sql = _sa_text(f"""
        SET NOCOUNT ON;
        EXEC {SP_MANTIENE_DATOS_CONCILIADOS}
            @FechaInicio = :fecha_inicio,
            @FechaFin = :fecha_fin,
            @DiasReproceso = :dias_reproceso
    """)
    try:
        with _get_engine().begin() as conn:
            conn.execute(
                sql,
                {
                    "fecha_inicio": start_date,
                    "fecha_fin": end_date,
                    "dias_reproceso": int(dias_reproceso),
                },
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al actualizar Datos conciliados mediante "
            f"{SP_MANTIENE_DATOS_CONCILIADOS}: {exc}"
        ) from exc


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


def actualizar_datos_conciliados_emision_report(
    start_date: date,
    end_date: date,
    dias_reproceso: int = 0,
) -> None:
    """Actualiza exclusivamente Datos Conciliados de emision."""
    if start_date is None or end_date is None:
        raise ValueError(
            "FechaInicio y FechaFin son obligatorias para actualizar "
            "Datos Conciliados de emision."
        )
    if start_date > end_date:
        raise ValueError("FechaInicio no puede ser posterior a FechaFin.")

    sql = _sa_text(f"""
        SET NOCOUNT ON;
        EXEC {SP_MANTIENE_DATOS_CONCILIADOS_EMISION}
            @FechaInicio   = :fecha_inicio,
            @FechaFin      = :fecha_fin,
            @DiasReproceso = :dias_reproceso;
    """)
    try:
        with _get_engine().begin() as conn:
            conn.execute(
                sql,
                {
                    "fecha_inicio": start_date,
                    "fecha_fin": end_date,
                    "dias_reproceso": int(dias_reproceso),
                },
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al actualizar Datos Conciliados de emision mediante "
            f"{SP_MANTIENE_DATOS_CONCILIADOS_EMISION}: {exc}"
        ) from exc


def fetch_datos_conciliados_emision_report(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Consulta exclusivamente Datos Conciliados de emision."""
    if start_date is None or end_date is None:
        raise ValueError(
            "FechaInicio y FechaFin son obligatorias para consultar "
            "Datos Conciliados de emision."
        )
    if start_date > end_date:
        raise ValueError("FechaInicio no puede ser posterior a FechaFin.")

    columnas = ", ".join(f"[{columna}]" for columna in COLUMNAS_DATOS_CONCILIADOS)
    sql = _sa_text(f"""
        SELECT {columnas}
        FROM {TABLE_DATOS_CONCILIADOS_EMISION}
        WHERE [Fecha] BETWEEN :start AND :end
        ORDER BY [Fecha] ASC;
    """)
    try:
        with _get_engine().connect() as conn:
            df = pd.read_sql(
                sql,
                conn,
                params={"start": start_date, "end": end_date},
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al leer Datos Conciliados desde "
            f"{TABLE_DATOS_CONCILIADOS_EMISION}: {exc}"
        ) from exc

    return df[
        [columna for columna in COLUMNAS_DATOS_CONCILIADOS if columna in df.columns]
    ]


def fetch_factor_ajuste_camiones_report(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Lee el factor oficial de camiones ya calculado por el mantenedor."""
    if start_date is None or end_date is None:
        raise ValueError(
            "FechaInicio y FechaFin son obligatorias para consultar el factor "
            "de ajuste de camiones."
        )
    if start_date > end_date:
        raise ValueError("FechaInicio no puede ser posterior a FechaFin.")

    sql = _sa_text("""
        SELECT
            Fecha,
            Chancado_TMH_Sin_Ajuste,
            Chancado_TMS_Sin_Ajuste,
            CASE
                WHEN KOM_TMH_Corregido IS NOT NULL
                 AND CAT_TMH_Corregido IS NOT NULL
                THEN KOM_TMH_Corregido + CAT_TMH_Corregido
                ELSE NULL
            END AS Chancado_TMH_Con_Ajuste,
            Chancado_TMS_Ajustado AS Chancado_TMS_Con_Ajuste,
            Carga_KOM_TMH_Viaje_Sin_Ajuste,
            Carga_CAT_TMH_Viaje_Sin_Ajuste,
            CASE
                WHEN Vueltas_KOM > 0 AND KOM_TMH_Corregido IS NOT NULL
                THEN KOM_TMH_Corregido / Vueltas_KOM
                ELSE NULL
            END AS Carga_KOM_TMH_Viaje_Con_Ajuste,
            CASE
                WHEN Vueltas_CAT > 0 AND CAT_TMH_Corregido IS NOT NULL
                THEN CAT_TMH_Corregido / Vueltas_CAT
                ELSE NULL
            END AS Carga_CAT_TMH_Viaje_Con_Ajuste,
            Factor_Ajuste_Calculado,
            Factor_Aplicacion_Reportes,
            Vueltas_KOM,
            Vueltas_CAT,
            Flag_Factor_Ajuste_Valido,
            Estado_Calculo,
            Regla_Aplicacion,
            SRR_TMS_Dia,
            Produccion_KOM_TMH,
            Produccion_CAT_TMH,
            Metodo,
            Fuente_Camiones,
            Fecha_Calculo
        FROM inventar_SpcHidr.v_ajuste_camiones_emision_test
        WHERE Fecha >= :fecha_inicio
          AND Fecha < DATEADD(DAY, 1, :fecha_fin)
        ORDER BY Fecha;
    """)
    try:
        with _get_engine().connect() as conn:
            df = pd.read_sql(
                sql,
                conn,
                params={"fecha_inicio": start_date, "fecha_fin": end_date},
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al leer el factor de ajuste de camiones desde "
            "inventar_SpcHidr.v_ajuste_camiones_emision_test: "
            f"{exc}"
        ) from exc

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.normalize()
        if df["Fecha"].isna().any():
            raise ValueError(
                "La vista del factor de ajuste contiene fechas nulas o inválidas."
            )
        if df["Fecha"].duplicated().any():
            duplicadas = df.loc[df["Fecha"].duplicated(keep=False), "Fecha"]
            fechas = ", ".join(
                duplicadas.dropna().dt.strftime("%d-%m-%Y").unique()
            )
            raise ValueError(
                "La vista del factor de ajuste contiene fechas duplicadas"
                + (f": {fechas}" if fechas else ".")
            )
        df = df.sort_values("Fecha", kind="stable").reset_index(drop=True)
    if "Fecha_Calculo" in df.columns:
        df["Fecha_Calculo"] = pd.to_datetime(
            df["Fecha_Calculo"], errors="coerce"
        )
    return df


def fetch_balance_chancado_report(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Lee el balance diario de chancado sin ejecutar mantenedores."""
    if start_date is None or end_date is None:
        raise ValueError(
            "FechaInicio y FechaFin son obligatorias para consultar Balance Chancado."
        )
    if start_date > end_date:
        raise ValueError("FechaInicio no puede ser posterior a FechaFin.")

    sql = _sa_text("""
        ;WITH Niveles08 AS
        (
            SELECT
                CAST(df.fecha_inicial AS date) AS Fecha,
                COUNT(*) AS Cantidad_Registros_08,
                AVG(TRY_CONVERT(float, df.nivel_harnero_a)) AS Nivel_Harnero_A,
                AVG(TRY_CONVERT(float, df.nivel_harnero_b)) AS Nivel_Harnero_B,
                AVG(TRY_CONVERT(float, df.nivel_harnero_c)) AS Nivel_Harnero_C,
                AVG(TRY_CONVERT(float, df.nivel_harnero_d)) AS Nivel_Harnero_D,
                AVG(TRY_CONVERT(float, df.nivel_harnero_e)) AS Nivel_Harnero_E,
                AVG(TRY_CONVERT(float, df.nivel_chancado_a)) AS Nivel_Chancado_A,
                AVG(TRY_CONVERT(float, df.nivel_chancado_b)) AS Nivel_Chancado_B,
                AVG(TRY_CONVERT(float, df.nivel_chancado_c)) AS Nivel_Chancado_C,
                AVG(TRY_CONVERT(float, df.nivel_chancado_d)) AS Nivel_Chancado_D,
                AVG(TRY_CONVERT(float, df.nivel_chancado_e)) AS Nivel_Chancado_E,
                AVG(TRY_CONVERT(float, df.nivel_silo_a)) AS Nivel_Silo_A,
                AVG(TRY_CONVERT(float, df.nivel_silo_b)) AS Nivel_Silo_B
            FROM inventar_SpcHidr.datos_filtrados AS df
            WHERE df.fecha_inicial >= :fecha_inicio
              AND df.fecha_inicial < DATEADD(DAY, 1, :fecha_fin)
              AND DATEPART(HOUR, df.fecha_inicial) = 8
              AND DATEPART(MINUTE, df.fecha_inicial) = 0
            GROUP BY CAST(df.fecha_inicial AS date)
        ),
        GeneradorRaw AS
        (
            SELECT
                CAST(g.Fecha AS date) AS Fecha,
                g.Material_Operacion,
                ROW_NUMBER() OVER
                (
                    PARTITION BY CAST(g.Fecha AS date)
                    ORDER BY
                        CASE WHEN g.Material_Operacion IS NULL THEN 1 ELSE 0 END,
                        g.Material_Operacion
                ) AS rn
            FROM inventar_SpcHidr.fn_generador_reporte_diario_emision_test
            (
                :fecha_inicio,
                DATEADD(DAY, 1, :fecha_fin)
            ) AS g
        ),
        Generador AS
        (
            SELECT Fecha, Material_Operacion
            FROM GeneradorRaw
            WHERE rn = 1
        ),
        Base AS
        (
            SELECT
                i.Fecha,
                h.Humedad_Inventario AS Humedad,
                aj.Apilado_TMH_Bruto_Original AS Mineral_Apilado_TMH_Original,
                aj.Factor_Aplicacion_Reportes AS Factor_Ajuste,
                aj.Apilado_TMH_Bruto_Ajustado AS Mineral_Apilado_TMH_Ajustado,
                (aj.Apilado_TMH_Bruto_Ajustado - aj.Apilado_TMH_Bruto_Original)
                    AS Delta_Ajuste_TMH,
                g.Material_Operacion AS Material,
                i.Nivel_Inventario_Chancado AS Nivel_Promedio_Chancado,
                i.Nivel_Inventario_Harnero AS Nivel_Promedio_Harneros,
                i.Nivel_Inventario_Silo AS Nivel_Promedio_Silo,
                i.TMH_Chancado AS Bin_Chancado,
                i.TMH_Harnero AS Bin_Harneros,
                i.Tolva_Compensacion_TMH AS Tolva_Compensacion,
                i.TMH_Silo AS Silo,
                (i.TMH_Chancado + i.TMH_Harnero + i.Tolva_Compensacion_TMH)
                    AS Inventario_Chancado_TMH,
                i.TMH_Silo AS Inventario_Silo_TMH,
                i.Total_Inventario_Chancado_TMH AS Total_TMH,
                CASE
                    WHEN h.Humedad_Inventario IS NOT NULL
                     AND i.TMH_Chancado IS NOT NULL
                     AND i.TMH_Harnero IS NOT NULL
                     AND i.Tolva_Compensacion_TMH IS NOT NULL
                    THEN (i.TMH_Chancado + i.TMH_Harnero
                          + i.Tolva_Compensacion_TMH)
                         * (1.0 - h.Humedad_Inventario / 100.0)
                END AS Inventario_Chancado_TMS,
                CASE
                    WHEN h.Humedad_Inventario IS NOT NULL
                     AND i.TMH_Silo IS NOT NULL
                    THEN i.TMH_Silo * (1.0 - h.Humedad_Inventario / 100.0)
                END AS Inventario_Silo_TMS,
                i.Total_Inventario_Chancado_TMS AS Total_TMS,
                n.Nivel_Harnero_A, n.Nivel_Harnero_B, n.Nivel_Harnero_C,
                n.Nivel_Harnero_D, n.Nivel_Harnero_E,
                n.Nivel_Chancado_A, n.Nivel_Chancado_B, n.Nivel_Chancado_C,
                n.Nivel_Chancado_D, n.Nivel_Chancado_E,
                n.Nivel_Silo_A, n.Nivel_Silo_B,
                i.Fecha_Inventario_Anterior,
                i.Inventario_Chancado_TMS_Anterior,
                i.Delta_Inventario_Chancado_TMS,
                TRY_CONVERT(float, a.Sal_promedio_dia) AS Sal_TMH_Dia,
                dc.SRR_TMS_promedio_dia,
                dc.Chancado_TMS_Real,
                i.Flag_Continuidad_Diaria,
                i.Flag_Inventario_Valido,
                h.Flag_Humedad_Inventario_Valida
            FROM inventar_SpcHidr.v_inventario_chancado_test AS i
            LEFT JOIN inventar_SpcHidr.v_humedad_inventario_test AS h
                ON h.Fecha = i.Fecha
            LEFT JOIN inventar_SpcHidr.Historico_Apilado_Diario AS a
                ON CAST(a.Fecha AS date) = i.Fecha
            LEFT JOIN Niveles08 AS n ON n.Fecha = i.Fecha
            LEFT JOIN Generador AS g ON g.Fecha = i.Fecha
            LEFT JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test AS aj
                ON aj.Fecha = i.Fecha
            LEFT JOIN inventar_SpcHidr.Datos_conciliados_of AS dc
                ON dc.Fecha = i.Fecha
            WHERE i.Fecha >= :fecha_inicio
              AND i.Fecha <= :fecha_fin
        )
        SELECT
            Fecha, Humedad,
            Mineral_Apilado_TMH_Original,
            Factor_Ajuste,
            Mineral_Apilado_TMH_Ajustado,
            Delta_Ajuste_TMH,
            CASE
                WHEN Mineral_Apilado_TMH_Ajustado IS NOT NULL
                 AND Humedad IS NOT NULL
                 AND Delta_Inventario_Chancado_TMS IS NOT NULL
                THEN Mineral_Apilado_TMH_Ajustado * (1.0 - Humedad / 100.0)
                     + Delta_Inventario_Chancado_TMS
            END AS Mineral_Chancado_Balance,
            Material,
            Nivel_Promedio_Chancado, Nivel_Promedio_Harneros,
            Nivel_Promedio_Silo,
            Bin_Chancado, Bin_Harneros, Tolva_Compensacion, Silo,
            Inventario_Chancado_TMH, Inventario_Silo_TMH, Total_TMH,
            Inventario_Chancado_TMS, Inventario_Silo_TMS, Total_TMS,
            Nivel_Harnero_A, Nivel_Harnero_B, Nivel_Harnero_C,
            Nivel_Harnero_D, Nivel_Harnero_E,
            Nivel_Chancado_A, Nivel_Chancado_B, Nivel_Chancado_C,
            Nivel_Chancado_D, Nivel_Chancado_E,
            Nivel_Silo_A, Nivel_Silo_B,
            Fecha_Inventario_Anterior, Inventario_Chancado_TMS_Anterior,
            Delta_Inventario_Chancado_TMS,
            Sal_TMH_Dia, SRR_TMS_promedio_dia,
            CASE
                WHEN Mineral_Apilado_TMH_Ajustado IS NOT NULL
                 AND Humedad IS NOT NULL
                 AND Delta_Inventario_Chancado_TMS IS NOT NULL
                 AND Sal_TMH_Dia IS NOT NULL
                 AND SRR_TMS_promedio_dia IS NOT NULL
                THEN Mineral_Apilado_TMH_Ajustado * (1.0 - Humedad / 100.0)
                     + Delta_Inventario_Chancado_TMS
                     - Sal_TMH_Dia - SRR_TMS_promedio_dia
            END AS Chancado_TMS_Reconstruido,
            Chancado_TMS_Real,
            CASE
                WHEN Chancado_TMS_Real IS NOT NULL
                 AND Mineral_Apilado_TMH_Ajustado IS NOT NULL
                 AND Humedad IS NOT NULL
                 AND Delta_Inventario_Chancado_TMS IS NOT NULL
                 AND Sal_TMH_Dia IS NOT NULL
                 AND SRR_TMS_promedio_dia IS NOT NULL
                THEN Mineral_Apilado_TMH_Ajustado * (1.0 - Humedad / 100.0)
                     + Delta_Inventario_Chancado_TMS
                     - Sal_TMH_Dia - SRR_TMS_promedio_dia
                     - Chancado_TMS_Real
            END AS Diferencia_vs_Datos_Conciliados,
            Flag_Humedad_Inventario_Valida,
            Flag_Continuidad_Diaria,
            Flag_Inventario_Valido
        FROM Base
        ORDER BY Fecha;
    """)
    try:
        with _get_engine().connect() as conn:
            df = pd.read_sql(
                sql,
                conn,
                params={"fecha_inicio": start_date, "fecha_fin": end_date},
            )
    except Exception as exc:
        raise RuntimeError(f"Error al leer Balance Chancado: {exc}") from exc

    if "Fecha" not in df.columns:
        raise ValueError("Balance Chancado no contiene la columna Fecha.")
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.normalize()
    if df["Fecha"].isna().any():
        raise ValueError("Balance Chancado contiene fechas nulas o inválidas.")
    if df["Fecha"].duplicated().any():
        fechas = df.loc[df["Fecha"].duplicated(keep=False), "Fecha"]
        raise ValueError(
            "Balance Chancado contiene fechas duplicadas: "
            + ", ".join(fechas.dt.strftime("%d-%m-%Y").unique())
        )
    if "Fecha_Inventario_Anterior" in df.columns:
        df["Fecha_Inventario_Anterior"] = pd.to_datetime(
            df["Fecha_Inventario_Anterior"], errors="coerce"
        ).dt.normalize()
    return df.sort_values("Fecha", kind="stable").reset_index(drop=True)

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
    # El SP actual ya entrega SRR con estos nombres canónicos. Solo se completa
    # desde la vista oficial si una instalación histórica aún no los expone;
    # así se evitan colisiones pandas (_x/_y) que oculten los valores reales.
    mapa_srr = {
        "Rep. SRR TA Qui.": "SRR_TurnoA_Quimico",
        "Rep. SRR TA Fis.": "SRR_TurnoA_Fisico",
        "Rep. SRR TB Qui.": "SRR_TurnoB_Quimico",
        "Rep. SRR TB Fis.": "SRR_TurnoB_Fisico",
    }
    faltantes = {
        origen: destino
        for origen, destino in mapa_srr.items()
        if destino not in df.columns
    }
    if not faltantes:
        return df

    bd_srr = fetch_bd_ton_report(start_date, end_date)
    disponibles = ["Fecha", *[col for col in faltantes if col in bd_srr.columns]]
    if len(disponibles) > 1:
        srr = bd_srr[disponibles].rename(columns={"Fecha": "Dia", **faltantes})
        df["Dia"] = pd.to_datetime(df["Dia"], errors="coerce").dt.normalize()
        srr["Dia"] = pd.to_datetime(srr["Dia"], errors="coerce").dt.normalize()
        df = df.merge(srr, on="Dia", how="left")
    return df


PESOS_REPRESENTATIVIDAD_COLUMNAS = (
    "Fecha", "Turno", "Torre", "Horas_Reales", "Factor_Masa",
    "Fraccion_Muestreo", "PesoTeo_Quimico", "PesoReal_Quimico",
    "Representatividad_Quimica", "PesoTeo_Fisico", "PesoReal_Fisico",
    "Representatividad_Fisica", "Estado_Evaluacion", "nombre_archivo",
    "fecha_carga",
)


def validar_pesos_representatividad(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza y valida la trazabilidad sin sustituir valores ausentes."""
    if df is None:
        raise ValueError("La trazabilidad de pesos no puede ser None.")
    if df.empty:
        return df.copy()

    faltantes = [col for col in PESOS_REPRESENTATIVIDAD_COLUMNAS if col not in df]
    if faltantes:
        raise RuntimeError(
            "Trazabilidad de pesos sin columnas obligatorias: "
            + ", ".join(faltantes)
        )

    resultado = df.copy()
    resultado["Fecha"] = pd.to_datetime(resultado["Fecha"], errors="coerce").dt.normalize()
    for col in ("Turno", "Torre"):
        resultado[col] = resultado[col].astype("string").str.strip().str.upper()

    if resultado["Fecha"].isna().any():
        raise RuntimeError("Trazabilidad de pesos contiene fechas invalidas o NULL.")
    mascara_turno = ~resultado["Turno"].isin({"A", "B"})
    invalidos_turno = sorted(set(resultado.loc[mascara_turno, "Turno"].dropna()))
    if mascara_turno.any():
        raise RuntimeError(f"Turnos invalidos en trazabilidad de pesos: {invalidos_turno}")
    mascara_torre = ~resultado["Torre"].isin({"T1", "T2", "SRR"})
    invalidos_torre = sorted(set(resultado.loc[mascara_torre, "Torre"].dropna()))
    if mascara_torre.any():
        raise RuntimeError(f"Torres invalidas en trazabilidad de pesos: {invalidos_torre}")

    duplicadas = resultado.duplicated(["Fecha", "Turno", "Torre"], keep=False)
    if duplicadas.any():
        llaves = resultado.loc[duplicadas, ["Fecha", "Turno", "Torre"]].drop_duplicates()
        raise RuntimeError(
            "Llaves duplicadas Fecha + Turno + Torre en trazabilidad de pesos: "
            + llaves.to_dict(orient="records").__repr__()
        )

    for col in ("Representatividad_Quimica", "Representatividad_Fisica"):
        valores = pd.to_numeric(resultado[col], errors="coerce")
        fuera = valores.notna() & ~valores.between(0, 1)
        if fuera.any():
            raise RuntimeError(f"{col} debe estar entre 0 y 1.")
    for col in ("PesoTeo_Quimico", "PesoTeo_Fisico", "PesoReal_Quimico", "PesoReal_Fisico"):
        valores = pd.to_numeric(resultado[col], errors="coerce")
        if (valores.dropna() < 0).any():
            raise RuntimeError(f"{col} no puede contener valores negativos.")

    resultado = resultado.assign(
        _orden_turno=resultado["Turno"].map({"A": 1, "B": 2}),
        _orden_torre=resultado["Torre"].map({"T1": 1, "T2": 2, "SRR": 3}),
    )
    return (
        resultado.sort_values(["Fecha", "_orden_turno", "_orden_torre"])
        .drop(columns=["_orden_turno", "_orden_torre"])
        .reset_index(drop=True)
    )


def fetch_pesos_representatividad_report(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Lee los pesos teoricos y reales usados por representatividad."""
    if start_date is None or end_date is None:
        raise ValueError("FechaInicio y FechaFin son obligatorias para consultar pesos.")
    if start_date > end_date:
        raise ValueError("FechaInicio no puede ser posterior a FechaFin.")

    sql = _sa_text("""
        SELECT teo.Fecha, teo.Turno, teo.Torre, teo.Horas_Reales,
               teo.Factor_Masa, teo.Fraccion_Muestreo,
               teo.PesoTeo_Quimico, real.PesoReal_Quimico,
               CASE WHEN teo.PesoTeo_Quimico > 0 AND real.PesoReal_Quimico IS NOT NULL
                    THEN CASE WHEN CAST(real.PesoReal_Quimico AS float) / CAST(teo.PesoTeo_Quimico AS float) >= 1
                              THEN 1.0 ELSE CAST(real.PesoReal_Quimico AS float) / CAST(teo.PesoTeo_Quimico AS float) END
                    ELSE NULL END AS Representatividad_Quimica,
               teo.PesoTeo_Fisico, real.PesoReal_Fisico,
               CASE WHEN teo.PesoTeo_Fisico > 0 AND real.PesoReal_Fisico IS NOT NULL
                    THEN CASE WHEN CAST(real.PesoReal_Fisico AS float) / CAST(teo.PesoTeo_Fisico AS float) >= 1
                              THEN 1.0 ELSE CAST(real.PesoReal_Fisico AS float) / CAST(teo.PesoTeo_Fisico AS float) END
                    ELSE NULL END AS Representatividad_Fisica,
               CASE WHEN ISNULL(teo.PesoTeo_Quimico, 0) <= 0 AND ISNULL(teo.PesoTeo_Fisico, 0) <= 0 THEN 'NO EVALUABLE'
                    WHEN real.PesoReal_Quimico IS NULL AND real.PesoReal_Fisico IS NULL THEN 'SIN PESO REAL'
                    ELSE 'EVALUABLE' END AS Estado_Evaluacion,
               real.nombre_archivo, real.fecha_carga
        FROM inventar_SpcHidr.v_peso_teorico_turno_torre_excel AS teo
        OUTER APPLY (
            SELECT TOP (1) r.PesoReal_Quimico, r.PesoReal_Fisico,
                   r.nombre_archivo, r.fecha_carga
            FROM inventar_SpcHidr.peso_real_torre_turno AS r
            WHERE r.Fecha = teo.Fecha AND r.Turno = teo.Turno AND r.Torre = teo.Torre
            ORDER BY r.fecha_carga DESC, r.ID_Registro DESC
        ) AS real
        WHERE teo.Fecha >= :start AND teo.Fecha <= :end
        ORDER BY teo.Fecha,
                 CASE teo.Turno WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END,
                 CASE teo.Torre WHEN 'T1' THEN 1 WHEN 'T2' THEN 2 WHEN 'SRR' THEN 3 ELSE 4 END;
    """)
    try:
        with _get_engine().connect() as conn:
            df = pd.read_sql(sql, conn, params={"start": start_date, "end": end_date})
    except Exception as exc:
        raise RuntimeError(f"Error al leer trazabilidad de pesos: {exc}") from exc
    return validar_pesos_representatividad(df)


def fetch_fecha_corte_representatividad(
    start_date: date,
    end_date: date,
) -> date | None:
    """
    Devuelve la última fecha operacional completamente cerrada
    para el Reporte de Representatividad de Torres.

    Un día se considera cerrado cuando existen los cuatro
    incrementos brutos:

    - CV-008 turno A
    - CV-008 turno B
    - CV-108 turno A
    - CV-108 turno B
    """
    engine = _get_engine()

    sql = """
        SELECT
            MAX(Fecha) AS Fecha_Corte
        FROM inventar_SpcHidr.v_datos_apilado_tmh_v2
        WHERE Fecha >= :start
          AND Fecha <= :end
          AND TMH_CV008_A_Bruto IS NOT NULL
          AND TMH_CV008_B_Bruto IS NOT NULL
          AND TMH_CV108_A_Bruto IS NOT NULL
          AND TMH_CV108_B_Bruto IS NOT NULL;
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                _sa_text(sql),
                conn,
                params={
                    "start": start_date,
                    "end": end_date,
                },
            )

    except Exception as exc:
        raise RuntimeError(
            "Error al obtener la fecha de corte operacional "
            "de Representatividad de Torres: "
            f"{exc}"
        ) from exc

    if (
        df.empty
        or "Fecha_Corte" not in df.columns
        or pd.isna(df.loc[0, "Fecha_Corte"])
    ):
        return None

    return pd.to_datetime(
        df.loc[0, "Fecha_Corte"],
        errors="coerce",
    ).date()


def fetch_fecha_corte_operacional_representatividad(
    start_date: date,
    end_date: date,
) -> date | None:
    """
    Devuelve la ultima fecha operacional completamente cubierta por el
    totalizador de 10 segundos para T1, T2 y SRR.

    El rango solicitado es inclusivo y el calculo no depende de capas
    derivadas de apilado o representatividad.
    """
    engine = _get_engine()
    sql = """
        ;WITH max_totalizador AS
        (
            SELECT MAX(fecha) AS Max_Fecha_Totalizador
            FROM inventar_SpcHidr.tot_TM
        ),
        rangos_dia AS
        (
            SELECT
                fecha_turno,
                MAX(ts_fin) AS Max_ts_fin_dia
            FROM inventar_SpcHidr.v_bitacora_rangos_norm
            WHERE fecha_turno >= :start
              AND fecha_turno <= :end
              AND Torre IN ('T1', 'T2', 'SRR')
            GROUP BY fecha_turno
        )
        SELECT MAX(r.fecha_turno) AS Fecha_Maxima_Exportable
        FROM rangos_dia r
        CROSS JOIN max_totalizador mt
        WHERE r.Max_ts_fin_dia <= mt.Max_Fecha_Totalizador;
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                _sa_text(sql),
                conn,
                params={"start": start_date, "end": end_date},
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al obtener la fecha de corte operacional de "
            f"Representatividad de Torres: {exc}"
        ) from exc

    if (
        df.empty
        or "Fecha_Maxima_Exportable" not in df.columns
        or pd.isna(df.loc[0, "Fecha_Maxima_Exportable"])
    ):
        return None

    fecha_corte = pd.to_datetime(
        df.loc[0, "Fecha_Maxima_Exportable"],
        errors="coerce",
    )
    return None if pd.isna(fecha_corte) else fecha_corte.date()


# ponytail: applock de SQL Server en vez de tabla de estado o lock en Python.
# gunicorn corre 2 workers: un lock de proceso no sirve.
LOCK_REFRESCO_REP_TIMEOUT_MS = 180_000

SQL_GETAPPLOCK_REFRESCO_REP = """
    SET NOCOUNT ON;
    DECLARE @rc int;
    EXEC @rc = sp_getapplock
        @Resource = :recurso,
        @LockMode = 'Exclusive',
        @LockOwner = 'Session',
        @LockTimeout = :timeout;
    SELECT @rc AS rc;
"""

SQL_RELEASEAPPLOCK_REFRESCO_REP = """
    SET NOCOUNT ON;
    EXEC sp_releaseapplock @Resource = :recurso, @LockOwner = 'Session';
"""


def _recurso_lock_representatividad(end_date: date) -> str:
    """Un lock por mes de reporte: la grilla y la publicacion usan el mismo."""
    return f"rep_torres_refresco:{end_date:%Y-%m}"


def refrescar_representatividad_para_exportacion(
    start_date: date,
    end_date: date,
) -> date:
    """
    Calcula el corte operacional y refresca, en orden, las capas requeridas
    antes de que el exportador realice cualquier lectura:
    apilado TMH v2 (Turno_Evaluable) -> resumen intervalo -> representatividad
    -> BD Ton. El apilado va primero porque los otros tres no lo tocan y la
    grilla decide con su flag si el dia se muestra.

    Serializado por mes con un applock de sesion: dos refrescos del mismo
    periodo no pueden entrelazarse (uno reescribiendo
    representatividad_torres_resultado mientras el otro sincroniza BD Ton
    desde esa misma tabla).
    """
    fecha_corte = fetch_fecha_corte_operacional_representatividad(
        start_date=start_date,
        end_date=end_date,
    )
    if fecha_corte is None:
        raise RuntimeError(
            "No existe una fecha operacional cerrada para exportar "
            "Representatividad de Torres."
        )

    print(f"[RTO] Fecha corte operacional: {fecha_corte:%Y-%m-%d}")
    pasos = (
        (
            # Primero: Control_Apilado_TMH_v2_test alimenta, via
            # v_datos_apilado_tmh_v2, el Turno_Evaluable que
            # _preparar_material_por_turno usa como flag oficial desde 2026.
            # Sin este paso un dia congelado antes del cierre de turno queda
            # con Flag_Apilado_Valido=0 para siempre: BD Ton se refresca y
            # muestra tonelaje, pero la grilla oculta el dia igual.
            # ponytail: @DiasReproceso fijo en 7 (mismo valor que ya usa el
            # flujo de reporte_turno); parametrizar solo si hace falta
            # reprocesar ventanas mas largas.
            "inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test",
            "[RTO] Refrescando Control_Apilado_TMH_v2_test (Turno_Evaluable)...",
            """
                EXEC inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test
                    @FechaInicio = :start,
                    @FechaFin = :end,
                    @DiasReproceso = 7
            """,
        ),
        (
            "inventar_SpcHidr.sp_calcular_resumen_intervalo_totTM",
            "[RTO] Recalculando Resumen_Intervalo_TotTM...",
            """
                EXEC inventar_SpcHidr.sp_calcular_resumen_intervalo_totTM
                    @FechaInicio = :start,
                    @FechaFin = :end
            """,
        ),
        (
            "inventar_SpcHidr.sp_refrescar_representatividad_torres",
            "[RTO] Refrescando representatividad_torres_resultado...",
            """
                EXEC inventar_SpcHidr.sp_refrescar_representatividad_torres
                    @fecha_inicio = :start,
                    @fecha_fin = :end
            """,
        ),
        (
            "inventar_SpcHidr.sp_sincronizar_bd_ton",
            "[RTO] Sincronizando BD Ton...",
            """
                EXEC inventar_SpcHidr.sp_sincronizar_bd_ton
                    @fecha_inicio = :start,
                    @fecha_fin = :end
            """,
        ),
    )

    recurso = _recurso_lock_representatividad(end_date)
    engine = _get_engine()
    with engine.connect() as conn:
        rc = conn.execute(
            _sa_text(SQL_GETAPPLOCK_REFRESCO_REP),
            {"recurso": recurso, "timeout": LOCK_REFRESCO_REP_TIMEOUT_MS},
        ).scalar()
        conn.commit()  # el lock de sesion sobrevive al commit
        if rc is None or int(rc) < 0:
            raise RuntimeError(
                "Otro proceso esta actualizando la representatividad de "
                f"{recurso.split(':')[1]}. Espere a que termine y reintente."
            )
        print(f"[RTO] Lock {recurso} tomado (rc={rc})")
        try:
            for nombre_sp, mensaje, sql in pasos:
                print(mensaje)
                try:
                    with conn.begin():
                        conn.execute(
                            _sa_text(sql),
                            {"start": start_date, "end": fecha_corte},
                        )
                except Exception as exc:
                    raise RuntimeError(
                        f"Error al ejecutar {nombre_sp}: {exc}"
                    ) from exc
        finally:
            # Sin este release el lock viaja de vuelta al pool y bloquea al
            # resto hasta pool_recycle (30 min).
            conn.execute(
                _sa_text(SQL_RELEASEAPPLOCK_REFRESCO_REP),
                {"recurso": recurso},
            )
            conn.commit()

    return fecha_corte


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
        [Apilado_TMH_CV01_TA] AS [Apilado TMH CV-01 TA],
        [Apilado_TMH_CV01_TB] AS [Apilado TMH CV-01 TB],
        [Rep_TM1_TA_Qui] AS [Rep. TM1 TA Qui.],
        [Rep_TM1_TA_Fis] AS [Rep. TM1 TA Fis.],
        [Rep_TM1_TB_Qui] AS [Rep. TM1 TB Qui.],
        [Rep_TM1_TB_Fis] AS [Rep. TM1 TB Fis.],
        [Rep_TM2_TA_Qui] AS [Rep. TM2 TA Qui.],
        [Rep_TM2_TA_Fis] AS [Rep. TM2 TA Fis.],
        [Rep_TM2_TB_Qui] AS [Rep. TM2 TB Qui.],
        [Rep_TM2_TB_Fis] AS [Rep. TM2 TB Fis.],
        [Rep_SRR_TA_Qui] AS [Rep. SRR TA Qui.],
        [Rep_SRR_TA_Fis] AS [Rep. SRR TA Fis.],
        [Rep_SRR_TB_Qui] AS [Rep. SRR TB Qui.],
        [Rep_SRR_TB_Fis] AS [Rep. SRR TB Fis.],
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
        [Muestra_representativa_TM3_TA] AS [Muestra representativa TM3 TA],
        [Muestra_representativa_TM3_TB] AS [Muestra representativa TM3 TB],
        [FISICO_TM3_TA] AS [FISICO TM3 TA],
        [FISICO_TM3_TB] AS [FISICO TM3 TB],
        [Evaluable_TM1_TA],
        [Evaluable_TM1_TB],
        [Evaluable_TM2_TA],
        [Evaluable_TM2_TB],
        [Evaluable_Combinado_TA],
        [Evaluable_Combinado_TB],
        [Evaluable_TM3_TA],
        [Evaluable_TM3_TB],
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
        [Apilado_TMH_CV01_TA] AS [Apilado TMH CV-01 TA],
        [Apilado_TMH_CV01_TB] AS [Apilado TMH CV-01 TB],
        [Rep_TM1_TA_Qui] AS [Rep. TM1 TA Qui.],
        [Rep_TM1_TA_Fis] AS [Rep. TM1 TA Fis.],
        [Rep_TM1_TB_Qui] AS [Rep. TM1 TB Qui.],
        [Rep_TM1_TB_Fis] AS [Rep. TM1 TB Fis.],
        [Rep_TM2_TA_Qui] AS [Rep. TM2 TA Qui.],
        [Rep_TM2_TA_Fis] AS [Rep. TM2 TA Fis.],
        [Rep_TM2_TB_Qui] AS [Rep. TM2 TB Qui.],
        [Rep_TM2_TB_Fis] AS [Rep. TM2 TB Fis.],
        [Rep_SRR_TA_Qui] AS [Rep. SRR TA Qui.],
        [Rep_SRR_TA_Fis] AS [Rep. SRR TA Fis.],
        [Rep_SRR_TB_Qui] AS [Rep. SRR TB Qui.],
        [Rep_SRR_TB_Fis] AS [Rep. SRR TB Fis.],
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
        [Muestra_representativa_TM3_TA] AS [Muestra representativa TM3 TA],
        [Muestra_representativa_TM3_TB] AS [Muestra representativa TM3 TB],
        [FISICO_TM3_TA] AS [FISICO TM3 TA],
        [FISICO_TM3_TB] AS [FISICO TM3 TB],
        [Evaluable_TM1_TA],
        [Evaluable_TM1_TB],
        [Evaluable_TM2_TA],
        [Evaluable_TM2_TB],
        [Evaluable_Combinado_TA],
        [Evaluable_Combinado_TB],
        [Evaluable_TM3_TA],
        [Evaluable_TM3_TB],
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


def actualizar_reporte_turno_cache(start_date: date, end_date: date) -> None:
    """Actualiza el caché antes de exportar Análisis Torres de Muestreo."""
    if start_date is None or end_date is None:
        raise ValueError("fecha_inicio y fecha_fin son obligatorias para actualizar el reporte por turno.")
    if start_date > end_date:
        raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")

    sql = _sa_text(f"""
        SET NOCOUNT ON;
        EXEC {SP_ACTUALIZA_REPORTE_TURNO_CACHE}
            @fecha_inicio = :fecha_inicio,
            @fecha_fin = :fecha_fin
    """)
    try:
        with _get_engine().begin() as conn:
            conn.execute(
                sql,
                {
                    "fecha_inicio": start_date,
                    "fecha_fin": end_date,
                },
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al actualizar el caché del reporte por turno mediante "
            f"{SP_ACTUALIZA_REPORTE_TURNO_CACHE}: {exc}"
        ) from exc


def fetch_fecha_corte_apilado_tmh_report(start_date: date, end_date: date) -> date | None:
    """Último día con las cuatro claves CV008/CV108 A/B resolubles.

    Fuente: diagnóstico PI/TUM, anterior al resolver y a Control_Apilado.
    Antes de septiembre de 2026 exige fronteras PI completas (incluido cero).
    Desde septiembre exige PI utilizable según el resolver vigente o TUM
    disponible no negativo, incluido TUM=0. No calcula tonelajes ni flags.
    No depende de SRR ni de la materialización que se va a refrescar.
    """
    if start_date is None or end_date is None or start_date > end_date:
        raise ValueError("Rango inclusivo inválido para el corte de apilado TMH.")
    sql = _sa_text("""
        WITH dias_cerrados AS (
            SELECT fecha_operacional
            FROM inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno
            WHERE fecha_operacional >= :inicio AND fecha_operacional <= :fin
              AND equipo_codigo IN ('PRINCIPAL_CV008', 'PRINCIPAL_CV108')
              AND turno IN ('A', 'B')
            GROUP BY fecha_operacional
            HAVING COUNT(DISTINCT CONCAT(equipo_codigo, '|', turno)) = 4
               AND MIN(CASE
                   WHEN fecha_operacional < '2026-09-01'
                    AND estado_fronteras = 'FRONTERAS_COMPLETAS' THEN 1
                   WHEN fecha_operacional >= '2026-09-01' AND (
                       (estado_fronteras = 'FRONTERAS_COMPLETAS'
                        AND delta_frontera_pi >= 0
                        AND estado_tecnico_pi IN
                            ('CON_VARIACION', 'CON_VARIACION_COBERTURA_PARCIAL'))
                       OR (tum_disponible = 1 AND valor_turno_tum >= 0)
                   ) THEN 1 ELSE 0 END) = 1
        )
        SELECT MAX(fecha_operacional) FROM dias_cerrados;
    """)
    with _get_engine().connect() as conn:
        corte = conn.execute(sql, {"inicio": start_date, "fin": end_date}).scalar()
    return None if corte is None else pd.Timestamp(corte).date()


def _validar_frescura_cache_turno(filas, inicio, fin_exclusivo, corte, regenerado_desde):
    """Valida claves y auditoría real; no demuestra igualdad numérica con el SP.

    El cache se reemplaza transaccionalmente y Fecha_Actualizacion tiene
    DEFAULT SYSDATETIME(). Se compara con el reloj del mismo SQL Server.
    """
    if not filas:
        raise RuntimeError("El cache de emisión no entregó filas después del refresco.")
    claves = set()
    for fila in filas:
        fecha = pd.Timestamp(fila["Fecha"]).date()
        turno = str(fila["Turno"]).strip().upper()
        clave = (fecha, turno)
        if not inicio <= fecha < fin_exclusivo or turno not in {"A", "B"}:
            raise RuntimeError(f"Clave fuera del contrato del cache: {clave}.")
        if clave in claves:
            raise RuntimeError(f"Clave duplicada en el cache: {clave}.")
        claves.add(clave)
        marca = fila["Fecha_Actualizacion"]
        if marca is None or pd.isna(marca) or marca < regenerado_desde:
            raise RuntimeError(f"Cache obsoleto después del refresco: {clave}.")
    if not {(corte, "A"), (corte, "B")}.issubset(claves):
        raise RuntimeError(f"El cache no contiene ambos turnos A/B del corte {corte}.")


def refrescar_dependencias_reporte_turno_emision(
    start_date: date, end_date: date, dias_reproceso: int = 7,
) -> dict:
    """Preparación común de preview y Excel; fechas solicitadas inclusivas.

    Sólo el fin del mantenedor de apilado se ancla al corte. Factor conserva
    su rango inclusivo y Clays/cache el rango solicitado, con fin exclusivo
    para cache. No recorta plantilla, generador ni exportación.
    """
    if start_date is None or end_date is None or start_date > end_date:
        raise ValueError("Rango inclusivo inválido para Reporte por Turno.")
    if not isinstance(dias_reproceso, int) or dias_reproceso < 1:
        raise ValueError("DiasReproceso debe ser un entero positivo.")
    corte = fetch_fecha_corte_apilado_tmh_report(start_date, end_date)
    if corte is None:
        raise RuntimeError("No existe una fecha operacional cerrada para actualizar el apilado TMH.")
    fin_efectiva = min(end_date, corte)
    if fin_efectiva < start_date:
        raise RuntimeError("La fecha de corte de apilado está fuera del rango solicitado.")
    ventana = max(start_date, fin_efectiva - timedelta(days=dias_reproceso - 1))
    fin_exclusivo = end_date + timedelta(days=1)
    print(f"[RTO] Periodo solicitado: {start_date} -> {end_date}")
    print(f"[RTO] Fecha corte apilado: {fin_efectiva}")
    print(f"[RTO] Dias reproceso: {dias_reproceso}")
    print(f"[RTO] Ventana efectiva reproceso: {ventana} -> {fin_efectiva}")
    with _get_engine().connect() as conn:
        desde = conn.execute(_sa_text("SELECT SYSDATETIME()")).scalar()
    actualizar_apilado_tmh_v2_report(start_date, fin_efectiva, dias_reproceso)
    print(f"[RTO] Apilado TMH actualizado: {start_date} -> {fin_efectiva}")
    actualizar_factor_ajuste_camiones_v2_report(start_date, end_date, dias_reproceso=0)
    print(f"[RTO] Factor ajuste actualizado: {start_date} -> {end_date}")
    actualizar_reporte_turno_cache_emision(start_date, fin_exclusivo)
    with _get_engine().connect() as conn:
        filas = conn.execute(_sa_text(f"""
            SELECT Fecha, Turno, Fecha_Actualizacion
            FROM {TABLE_REPORTE_TURNO_CACHE_EMISION}
            WHERE Fecha >= :inicio AND Fecha < :fin
        """), {"inicio": start_date, "fin": fin_exclusivo}).mappings().all()
        apilado = conn.execute(_sa_text("""
            SELECT Fecha, Fecha_Calculo
            FROM inventar_SpcHidr.Control_Apilado_TMH_v2_test
            WHERE Fecha >= :inicio AND Fecha <= :fin
        """), {"inicio": ventana, "fin": fin_efectiva}).mappings().all()
    if not any(pd.Timestamp(f["Fecha"]).date() == fin_efectiva for f in apilado):
        raise RuntimeError("El apilado actualizado no contiene el último día operacional.")
    if any(f["Fecha_Calculo"] is None or f["Fecha_Calculo"] < desde for f in apilado):
        raise RuntimeError("El apilado conserva filas obsoletas en la ventana de reproceso.")
    _validar_frescura_cache_turno(filas, start_date, fin_exclusivo, fin_efectiva, desde)
    print(f"[RTO] Validación cache: OK; filas={len(filas)}; corte={fin_efectiva}; A/B presentes")
    return {"inicio": start_date, "fin_solicitada": end_date,
            "fecha_corte_operacional": fin_efectiva, "inicio_ventana": ventana,
            "fin_sql_exclusivo": fin_exclusivo, "filas_cache": len(filas)}


def actualizar_apilado_tmh_v2_report(
    start_date: date,
    end_date: date,
    dias_reproceso: int = 7,
) -> None:
    """
    Refresca la tabla congelada Control_Apilado_TMH_v2_test (TMH bruto de
    los totalizadores CV008/CV108). Debe llamarse ANTES de
    actualizar_factor_ajuste_camiones_v2_report, ya que ese calculo depende
    en cadena de v_datos_apilado_tmh_v2. dias_reproceso=7 por defecto: solo
    recalcula los ultimos 7 dias del rango pedido, mas cualquier fecha que
    todavia no tenga fila en la tabla -- ver encabezado de
    sp_mantiene_apilado_tmh_v2_test para el detalle de esa ventana.
    ``start_date`` y ``end_date`` son inclusivos.
    """
    sql = _sa_text("""
        SET NOCOUNT ON;

        EXEC [inventar_SpcHidr].[sp_mantiene_apilado_tmh_v2_test]
            @FechaInicio   = :fecha_inicio,
            @FechaFin      = :fecha_fin,
            @DiasReproceso = :dias_reproceso;
    """)

    with _get_engine().begin() as conn:
        conn.execute(
            sql,
            {
                "fecha_inicio": start_date,
                "fecha_fin": end_date,
                "dias_reproceso": int(dias_reproceso),
            },
        )


def actualizar_factor_ajuste_camiones_v2_report(
    start_date: date,
    end_date: date,
    dias_reproceso: int = 0,
) -> None:
    """Refresca los factores V2; ``start_date`` y ``end_date`` son inclusivos."""
    sql = _sa_text("""
        SET NOCOUNT ON;

        EXEC [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_test]
            @FechaInicio   = :fecha_inicio,
            @FechaFin      = :fecha_fin,
            @DiasReproceso = :dias_reproceso;
    """)

    with _get_engine().begin() as conn:
        conn.execute(
            sql,
            {
                "fecha_inicio": start_date,
                "fecha_fin": end_date,
                "dias_reproceso": int(dias_reproceso),
            },
        )


def actualizar_reporte_turno_cache_emision(
    start_date: date,
    end_date: date,
) -> None:
    """
    Actualiza Clays_CuFe y luego el cache de emision.

    ``start_date`` es inclusiva y ``end_date`` es exclusiva.
    """
    if start_date is None or end_date is None:
        raise ValueError(
            "FechaInicio y FechaFin son obligatorias para actualizar "
            "el cache del Reporte por Turno."
        )
    if start_date >= end_date:
        raise ValueError(
            "FechaInicio debe ser anterior a FechaFin; FechaFin es exclusiva."
        )

    fecha_fin_clays = end_date - timedelta(days=1)
    if fecha_fin_clays >= FECHA_CORTE_CLAYS_CUFE:
        fecha_inicio_clays = max(start_date, FECHA_CORTE_CLAYS_CUFE)
        sql_clays = _sa_text(f"""
            SET NOCOUNT ON;
            EXEC {SP_REFRESCA_CLAYS_CUFE}
                @FechaInicio = :fecha_inicio,
                @FechaFin = :fecha_fin,
                @SoloVistaPrevia = 0;
        """)
        try:
            with _get_engine().begin() as conn:
                conn.execute(
                    sql_clays,
                    {
                        "fecha_inicio": fecha_inicio_clays,
                        "fecha_fin": fecha_fin_clays,
                    },
                )
        except Exception as exc:
            raise RuntimeError(
                "Error al actualizar Clays/CuFe mediante "
                f"{SP_REFRESCA_CLAYS_CUFE}: {exc}"
            ) from exc

        print(f"[RTO] Clays CuFe actualizado: {fecha_inicio_clays} -> {fecha_fin_clays}")

    sql_cache = _sa_text(f"""
        SET NOCOUNT ON;
        EXEC {SP_ACTUALIZA_REPORTE_TURNO_CACHE_EMISION}
            @fecha_inicio = :fecha_inicio,
            @fecha_fin = :fecha_fin;
    """)
    try:
        with _get_engine().begin() as conn:
            conn.execute(
                sql_cache,
                {"fecha_inicio": start_date, "fecha_fin": end_date},
            )
    except Exception as exc:
        raise RuntimeError(
            "Error al actualizar el cache del Reporte por Turno mediante "
            f"{SP_ACTUALIZA_REPORTE_TURNO_CACHE_EMISION}: {exc}"
        ) from exc

    print(f"[RTO] Cache emisión actualizado: {start_date} -> {end_date} (fin exclusivo)")


def fetch_clays_cufe_report(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Consulta Clays/CuFe y su fuente real; ``end_date`` es exclusiva.

    La procedencia se lee de la misma vista calculada consumida por
    ``sp_refrescar_clays_cufe``. No se deduce comparando valores numéricos.
    """
    if start_date is None or end_date is None:
        raise ValueError("FechaInicio y FechaFin son obligatorias.")
    if start_date >= end_date:
        raise ValueError(
            "FechaInicio debe ser anterior a FechaFin; FechaFin es exclusiva."
        )

    sql = _sa_text("""
        WITH clays_normalizado AS
        (
            SELECT
                c.Fecha,
                CASE
                    WHEN n.Torre_Normalizada IN ('TM1', 'T1', 'TORRE1') THEN 'TM1'
                    WHEN n.Torre_Normalizada IN ('TM2', 'T2', 'TORRE2') THEN 'TM2'
                END AS Torre,
                CASE
                    WHEN n.Turno_Normalizado IN ('A', 'TA', 'TURNOA') THEN 'A'
                    WHEN n.Turno_Normalizado IN ('B', 'TB', 'TURNOB') THEN 'B'
                END AS Turno,
                c.CaolBeta,
                c.CuFe
            FROM [inventar_SpcHidr].[Clays_CuFe] AS c
            CROSS APPLY
            (
                VALUES
                (
                    REPLACE(REPLACE(REPLACE(UPPER(LTRIM(RTRIM(ISNULL(c.Torre, '')))), ' ', ''), '-', ''), '_', ''),
                    REPLACE(REPLACE(REPLACE(UPPER(LTRIM(RTRIM(ISNULL(c.Turno, '')))), ' ', ''), '-', ''), '_', '')
                )
            ) AS n(Torre_Normalizada, Turno_Normalizado)
            WHERE c.Fecha >= :start_date
              AND c.Fecha < :end_date
        ),
        trazabilidad_caol AS
        (
            SELECT Fecha, Turno, Torre, Fuente_CaolBeta
            FROM
            (
                SELECT
                    t.Fecha,
                    t.Turno,
                    t.Torre,
                    t.Fuente_CaolBeta,
                    ROW_NUMBER() OVER
                    (
                        PARTITION BY t.Fecha, t.Turno, t.Torre
                        ORDER BY t.fecha_proceso DESC, t.id_trazabilidad DESC
                    ) AS rn
                FROM [inventar_SpcHidr].[Clays_CuFe_trazabilidad] AS t
                WHERE t.Fecha >= :start_date
                  AND t.Fecha < :end_date
                  AND ISNULL(t.Fuente_CaolBeta, 'SIN_DATO') <> 'SIN_DATO'
            ) AS ranked
            WHERE rn = 1
        ),
        trazabilidad_cufe AS
        (
            SELECT Fecha, Turno, Torre, Fuente_CuFe
            FROM
            (
                SELECT
                    t.Fecha,
                    t.Turno,
                    t.Torre,
                    t.Fuente_CuFe,
                    ROW_NUMBER() OVER
                    (
                        PARTITION BY t.Fecha, t.Turno, t.Torre
                        ORDER BY t.fecha_proceso DESC, t.id_trazabilidad DESC
                    ) AS rn
                FROM [inventar_SpcHidr].[Clays_CuFe_trazabilidad] AS t
                WHERE t.Fecha >= :start_date
                  AND t.Fecha < :end_date
                  AND ISNULL(t.Fuente_CuFe, 'SIN_DATO') <> 'SIN_DATO'
            ) AS ranked
            WHERE rn = 1
        )
        SELECT
            c.Fecha,
            c.Torre,
            c.Turno,
            c.CaolBeta,
            c.CuFe,
            CASE
                WHEN UPPER(ISNULL(f.Fuente_CaolBeta, '')) LIKE 'NIR_TM2_%' THEN 'TM2'
                WHEN UPPER(ISNULL(f.Fuente_CaolBeta, '')) LIKE 'NIR_PROPIO_%' THEN c.Torre
                WHEN UPPER(ISNULL(f.Fuente_CaolBeta, '')) LIKE 'MB_%' THEN 'MB'
                WHEN UPPER(ISNULL(f.Fuente_CaolBeta, '')) LIKE 'IMP%' THEN 'IMP'
            END AS Fuente_CaolBeta,
            CASE
                WHEN UPPER(ISNULL(f.Fuente_CuFe, '')) LIKE 'LAB_TM2_%' THEN 'TM2'
                WHEN UPPER(ISNULL(f.Fuente_CuFe, '')) LIKE 'LAB_PROPIO_%' THEN c.Torre
                WHEN UPPER(ISNULL(f.Fuente_CuFe, '')) LIKE 'MB_%' THEN 'MB'
                WHEN UPPER(ISNULL(f.Fuente_CuFe, '')) LIKE 'IMP%' THEN 'IMP'
            END AS Fuente_CuFe
        FROM clays_normalizado AS c
        LEFT JOIN [inventar_SpcHidr].[v_clays_cufe_calculado_v2_test] AS v
          ON v.Fecha = c.Fecha
         AND v.Torre = c.Torre
         AND v.Turno = c.Turno
        LEFT JOIN trazabilidad_caol AS tc
          ON tc.Fecha = c.Fecha
         AND tc.Torre = c.Torre
         AND tc.Turno = c.Turno
        LEFT JOIN trazabilidad_cufe AS tf
          ON tf.Fecha = c.Fecha
         AND tf.Torre = c.Torre
         AND tf.Turno = c.Turno
        CROSS APPLY
        (
            VALUES
            (
                CASE
                    WHEN ISNULL(v.Fuente_CaolBeta, 'SIN_DATO') <> 'SIN_DATO'
                        THEN v.Fuente_CaolBeta
                    ELSE tc.Fuente_CaolBeta
                END,
                CASE
                    WHEN ISNULL(v.Fuente_CuFe, 'SIN_DATO') <> 'SIN_DATO'
                        THEN v.Fuente_CuFe
                    ELSE tf.Fuente_CuFe
                END
            )
        ) AS f(Fuente_CaolBeta, Fuente_CuFe)
        WHERE c.Torre IS NOT NULL
          AND c.Turno IS NOT NULL
        ORDER BY
            c.Fecha,
            CASE c.Torre WHEN 'TM1' THEN 1 WHEN 'TM2' THEN 2 ELSE 3 END,
            CASE c.Turno WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END;
    """)
    with _get_engine().connect() as conn:
        return pd.read_sql(
            sql,
            conn,
            params={"start_date": start_date, "end_date": end_date},
        )


def fetch_trazabilidad_analitos_report(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Lee la trazabilidad final persistida por el SP; fin exclusivo."""
    if start_date is None or end_date is None or start_date >= end_date:
        raise ValueError("Rango de fechas inválido; FechaFin es exclusiva.")
    sql = _sa_text("""
        SELECT
            t.Fecha, t.Turno, t.TM_Destino, t.Analito, t.Valor_Final,
            t.Fuente_Base, t.Fuente_Tecnica, t.Fecha_Origen,
            t.Turno_Origen, t.TM_Origen, t.Resolucion,
            t.Representatividad_Quimica, t.Representatividad_Fisica,
            t.Fecha_Proceso,
            c.Apilado_TMS_Real,
            f.Fuente_Info_Quimica AS Resumen_Quimico_Actual,
            f.Fuente_Info_Fisica AS Resumen_Fisico_Actual
        FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test t
        LEFT JOIN inventar_SpcHidr.reporte_turno_cache_emision_test c
          ON c.Fecha=t.Fecha AND c.Turno=t.Turno
        LEFT JOIN inventar_SpcHidr.v_reporte_turno_fuentes_info_test f
          ON f.Fecha=t.Fecha AND f.Turno=t.Turno
        WHERE t.Fecha>=:start_date AND t.Fecha<:end_date
        ORDER BY t.Fecha,
          CASE t.TM_Destino WHEN 'TM1' THEN 1 WHEN 'TM2' THEN 2 ELSE 3 END,
          CASE t.Turno WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END,
          t.Analito;
    """)
    with _get_engine().connect() as conn:
        return pd.read_sql(
            sql, conn, params={"start_date": start_date, "end_date": end_date}
        )


def fetch_curva_granulometrica_report(
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Lee la curva granulometrica oficial ya ponderada; fin exclusivo."""
    if start_date is None or end_date is None or start_date >= end_date:
        raise ValueError("Rango de fechas invalido; FechaFin es exclusiva.")
    sql = _sa_text("""
        SELECT
            Fecha, Turno, Ton_TM1, Ton_TM2, Rep_Fisica_TM1, Rep_Fisica_TM2,
            Tiene_Curva_TM1, Tiene_Curva_TM2, Torres_Utilizadas,
            P2, P1, P34, P12, P14, P10, P35, P100, P150, P200, P325,
            PBajo325
        FROM inventar_SpcHidr.v_curva_granulometrica_torres_test
        WHERE Fecha >= :start_date AND Fecha < :end_date
        ORDER BY Fecha, CASE Turno WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END;
    """)
    with _get_engine().connect() as conn:
        return pd.read_sql(
            sql, conn, params={"start_date": start_date, "end_date": end_date}
        )


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


def fetch_reporte_turno_cache_emision(start_date: date, end_date: date) -> pd.DataFrame:
    """Lee exclusivamente el cache de emision; ``end_date`` es exclusivo."""
    sql = f"""
    SELECT
        Fecha, Campania, Material, Modulo, Avance, Turno,
        Apilado_TMS_Real, Apilado_TMS_Plan_Mensual, STOCK, MINA, SRR,
        CuT_Real, CuT_Plan_Mensual, CuT_Plan_Semanal,
        CuS_Real, CuS_Plan_Mensual, CuS_Plan_Semanal,
        Solubilidad_Real, Solubilidad_Plan_Mensual, Solubilidad_Plan_Semanal,
        CO3_Real, CO3_Plan_Mensual, CO3_Plan_Semanal,
        CuFe_Real, CuFe_Plan_Mensual, CuFe_Plan_Semanal,
        FeT_Real, FeS_Real, ConsH_Real,
        Malla_Menos_1_2_Real, Malla_Menos_1_2_Plan_Semanal,
        Malla_Menos_100_Real, Malla_Menos_100_Plan_Mensual,
        Malla_Menos_100_Plan_Semanal,
        CaolBeta_Real, CaolBeta_Plan_Mensual, CaolBeta_Plan_Semanal,
        Dosis_Acido_Ideal_TM, Dosis_Acido_Programa_Semanal,
        Fuente_Info_Quimica, Fuente_Info_Fisica, Muestra_Quimica, Muestra_Fisica
    FROM {TABLE_REPORTE_TURNO_CACHE_EMISION}
    WHERE Fecha >= :start AND Fecha < :end
    ORDER BY Fecha, Turno;
    """
    with _get_engine().connect() as conn:
        return pd.read_sql(
            _sa_text(sql), conn, params={"start": start_date, "end": end_date}
        )

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


def fetch_generador_reporte_diario_emision(start_date: date, end_date: date) -> pd.DataFrame:
    """Ejecuta exclusivamente el generador diario de emision."""
    sql = _sa_text(f"""
        EXEC {SP_GENERADOR_REPORTE_DIARIO_EMISION}
            @fecha_inicio = :start,
            @fecha_fin = :end;
    """)
    with _get_engine().connect() as conn:
        return pd.read_sql(sql, conn, params={"start": start_date, "end": end_date})


def _normalizar_claves_reconst_srr(df: pd.DataFrame) -> pd.DataFrame:
    """Copia local con claves diarias únicas; no transforma las leyes."""
    datos = df.copy()
    datos["Fecha"] = pd.to_datetime(datos["Fecha"]).dt.normalize()
    datos["Turno"] = datos["Turno"].map(
        lambda v: _normalizar_turno_rep(v) if pd.notna(v) else ""
    ).replace({"TA": "A", "TB": "B"})
    if datos["Fecha"].isna().any() or not datos["Turno"].isin(["A", "B"]).all():
        raise ValueError("Reconst Mod SRR contiene claves Fecha/Turno inválidas.")
    duplicados = datos.duplicated(subset=["Fecha", "Turno"], keep=False)
    if duplicados.any():
        raise ValueError("Reconst Mod SRR contiene duplicados Fecha/Turno.")
    return datos.sort_values(["Fecha", "Turno"], kind="stable").reset_index(drop=True)


def fetch_reconstitucion_srr_report(start_date: date, end_date: date) -> pd.DataFrame:
    """Insumos SRR independientes; inicio inclusivo y fin exclusivo."""
    if start_date is None or end_date is None or start_date >= end_date:
        raise ValueError("Reconst Mod SRR requiere inicio anterior al fin exclusivo.")
    sql = _sa_text("""
        SELECT t.Fecha, t.Turno, t.SRR_TMS_Turno,
               t.CuT_SRR, t.CuS_SRR, t.ClayBeta_SRR, t.Malla100_SRR,
               t.CO3_SRR, t.Recuperacion_SRR,
               d.CuT_MinaStock, d.CuS_MinaStock, d.ClayBeta_MinaStock,
               d.Malla100_MinaStock, d.CO3_MinaStock,
               d.SRR_TMS_Dia, d.Participacion_SRR,
               d.Factor_Sensibilidad_Reconstitucion,
               d.Flag_Reconstitucion, d.Flag_Sensibilidad,
               CASE t.Turno WHEN 'A' THEN c.Apilado_TMH_turno_A
                            WHEN 'B' THEN c.Apilado_TMH_turno_B END AS TMH_Total_Conciliado,
               CASE t.Turno WHEN 'A' THEN c.Sal_turno_A
                            WHEN 'B' THEN c.Sal_Turno_B END AS Sal_Turno,
               CASE t.Turno WHEN 'A' THEN b.TMH_CV008_A
                            WHEN 'B' THEN b.TMH_CV008_B END AS TMH_CV008,
               CASE t.Turno WHEN 'A' THEN b.TMH_CV108_A
                            WHEN 'B' THEN b.TMH_CV108_B END AS TMH_CV108,
               f.Factor_Aplicacion_Reportes
        FROM inventar_SpcHidr.fn_reconstitucion_srr_turno_emision_test(
            :start, :end
        ) AS t
        LEFT JOIN inventar_SpcHidr.fn_reconstitucion_srr_emision_test(
            :start, :end
        ) AS d ON d.Fecha = t.Fecha
        LEFT JOIN inventar_SpcHidr.Datos_conciliados_of AS c ON c.Fecha = t.Fecha
        LEFT JOIN inventar_SpcHidr.v_datos_apilado_tmh_v2 AS b ON b.Fecha = t.Fecha
        LEFT JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test AS f ON f.Fecha = t.Fecha
        ORDER BY t.Fecha, CASE t.Turno WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END;
    """)
    with _get_engine().connect() as conn:
        datos = pd.read_sql(sql, conn, params={"start": start_date, "end": end_date})
    return _normalizar_claves_reconst_srr(datos)


RTO_CAB_TABLE = "inventar_SpcHidr.reporte_torre_oficial_cab"
RTO_SNAPSHOT_TABLE = "inventar_SpcHidr.reporte_torre_oficial_snapshot"
RTO_DETALLE_TABLE = "inventar_SpcHidr.reporte_torre_oficial_detalle"

RTO_SNAPSHOT_BLOQUES = (
    "rep_torres",
    "bd_ton_fy",
    "bd_ton_mes",
    "turno_mes",
    "gestion_fy_quimico",
    "gestion_fy_fisico",
    "pesos_turno",
)

RTO_DETALLE_COLUMNAS = (
    "Fecha", "Turno", "Semana", "Pad", "Pad_Original", "Pad_Ajustado_Por",
    "TMH_CV08", "Rep_TM1_Quimico", "TMH_CV108", "Rep_TM2_Quimico",
    "Rep_Turno_Quimico", "Rep_TM1_Fisico", "Rep_TM2_Fisico",
    "Rep_Turno_Fisico", "TM1_Activo", "TM2_Activo",
    "Comentario_TM1_Quimico", "Comentario_TM2_Quimico",
    "Comentario_TM1_Fisico", "Comentario_TM2_Fisico",
    "TMH_CV01", "Rep_TM3_Quimico", "Rep_TM3_Fisico", "TM3_Activo",
    "Comentario_TM3_Quimico", "Comentario_TM3_Fisico",
)

RTO_TM3_COLUMNAS_OBLIGATORIAS = (
    "TMH_CV01",
    "TM3_Activo",
    "Rep_TM3_Quimico",
    "Rep_TM3_Fisico",
    "Comentario_TM3_Quimico",
    "Comentario_TM3_Fisico",
)


def _dataframe_a_snapshot_json(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "[]"
    copia = df.copy()
    for col in copia.columns:
        if pd.api.types.is_datetime64_any_dtype(copia[col]):
            formato = "%Y-%m-%dT%H:%M:%S.%f" if col == "fecha_carga" else "%Y-%m-%d"
            copia[col] = copia[col].dt.strftime(formato)
    return copia.to_json(orient="records", date_format="iso", double_precision=15)


def _snapshot_json_a_dataframe(payload: str) -> pd.DataFrame:
    if not payload or payload.strip() in ("", "[]", "null"):
        return pd.DataFrame()
    df = pd.read_json(io.StringIO(payload), orient="records")
    for col in df.columns:
        if col.lower() in {"dia", "fecha", "fecha_carga"}:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _obtener_rango_fiscal_hasta_mes(fecha_reporte) -> dict:
    fecha = pd.to_datetime(fecha_reporte).date()
    anio_fiscal = fecha.year + 1 if fecha.month >= 7 else fecha.year
    fecha_inicio_fy = date(anio_fiscal - 1, 7, 1)
    ultimo_dia_mes = calendar.monthrange(fecha.year, fecha.month)[1]
    fecha_fin_mes = fecha.replace(day=ultimo_dia_mes)
    return {
        "anio_fiscal": anio_fiscal,
        "fecha_inicio": fecha_inicio_fy,
        "fecha_fin": fecha_fin_mes,
    }


def _completar_calendario_representatividad(
    df: pd.DataFrame,
    fecha_inicio,
    fecha_fin,
) -> pd.DataFrame:
    calendario = pd.DataFrame({
        "Dia": pd.date_range(start=fecha_inicio, end=fecha_fin, freq="D"),
    })
    datos = df.copy()
    if "Dia" in datos.columns:
        datos["Dia"] = pd.to_datetime(datos["Dia"], errors="coerce").dt.normalize()
    else:
        datos["Dia"] = pd.NaT
    return (
        calendario
        .merge(datos, on="Dia", how="left")
        .sort_values("Dia")
        .reset_index(drop=True)
    )


def _fetch_fuentes_mensuales_torres_oficial(fecha_fin, fecha_corte_operacional=None) -> dict:
    fin_d = pd.to_datetime(fecha_fin).date()
    corte_d = pd.to_datetime(fecha_corte_operacional or fin_d).date()
    rango_fy = _obtener_rango_fiscal_hasta_mes(corte_d)
    fecha_inicio_mes = fin_d.replace(day=1)
    fecha_fin_mes = fin_d
    fecha_corte_exclusiva = (pd.Timestamp(corte_d) + pd.Timedelta(days=1)).date()

    df_bd_ton_mes = fetch_bd_ton_report(start_date=fecha_inicio_mes, end_date=corte_d)
    if df_bd_ton_mes.empty:
        raise RuntimeError("BD Ton no entregó datos para el mes evaluado.")

    df_turno_mes = fetch_estado_apilado_turno_representatividad(
        start_date=fecha_inicio_mes,
        end_date=fecha_corte_exclusiva,
    )
    if df_turno_mes.empty:
        raise RuntimeError(
            "El estado de apilado por turno no entregó datos para el mes evaluado."
        )

    df_gestion_fy_quimico = fetch_gestion_representatividad_fy(
        anio_fiscal=rango_fy["anio_fiscal"],
        tipo="QUIMICO",
        alcance="COMBINADO",
        objetivo=0.85,
        fecha_corte=corte_d,
    )
    if df_gestion_fy_quimico.empty:
        raise RuntimeError("La gestión FY química no entregó resultados.")

    df_gestion_fy_fisico = fetch_gestion_representatividad_fy(
        anio_fiscal=rango_fy["anio_fiscal"],
        tipo="FISICO",
        alcance="COMBINADO",
        objetivo=0.85,
        fecha_corte=corte_d,
    )
    if df_gestion_fy_fisico.empty:
        raise RuntimeError("La gestión FY física no entregó resultados.")

    return {
        "rango_fy": rango_fy,
        "fecha_inicio_mes": fecha_inicio_mes,
        "fecha_fin_mes": fecha_fin_mes,
        "fecha_corte_operacional": corte_d,
        "df_bd_ton_mes": df_bd_ton_mes,
        "df_turno_mes": df_turno_mes,
        "df_gestion_fy_quimico": df_gestion_fy_quimico,
        "df_gestion_fy_fisico": df_gestion_fy_fisico,
    }


def armar_paquete_reporte_torre_oficial(
    periodo_inicio: date,
    periodo_fin: date,
) -> dict:
    """
    Ejecuta SPs y consultas pesadas una vez (solo al publicar).
    Devuelve dict con DataFrames y metadatos para snapshot + export.
    """
    periodo_inicio, periodo_fin, _ = normalizar_periodo_mes(
        periodo_inicio,
        periodo_fin,
    )

    fecha_corte_operacional = refrescar_representatividad_para_exportacion(
        start_date=periodo_inicio,
        end_date=periodo_fin,
    )
    if fecha_corte_operacional is None:
        raise RuntimeError(
            "No existe información disponible en Peso Torres para el rango."
        )

    df_rep_real = fetch_representatividad_torres_report(
        start_date=periodo_inicio,
        end_date=fecha_corte_operacional,
    )
    if df_rep_real.empty:
        raise RuntimeError("Sin datos de representatividad para el rango seleccionado.")

    df_pesos_turno = fetch_pesos_representatividad_report(
        start_date=periodo_inicio,
        end_date=fecha_corte_operacional,
    )
    print(f"[RTO] Filas trazabilidad pesos: {len(df_pesos_turno)}")

    df_rep = _completar_calendario_representatividad(
        df=df_rep_real,
        fecha_inicio=periodo_inicio,
        fecha_fin=periodo_fin,
    )

    rango_fy = _obtener_rango_fiscal_hasta_mes(fecha_corte_operacional)
    df_bd_ton_fy = fetch_bd_ton_report(
        start_date=rango_fy["fecha_inicio"],
        end_date=fecha_corte_operacional,
    )
    if df_bd_ton_fy.empty:
        raise RuntimeError("BD Ton no entregó datos históricos para el año fiscal.")

    fuentes = _fetch_fuentes_mensuales_torres_oficial(
        periodo_fin,
        fecha_corte_operacional,
    )

    return {
        "rep_torres": df_rep,
        "bd_ton_fy": df_bd_ton_fy,
        "bd_ton_mes": fuentes["df_bd_ton_mes"],
        "turno_mes": fuentes["df_turno_mes"],
        "gestion_fy_quimico": fuentes["df_gestion_fy_quimico"],
        "gestion_fy_fisico": fuentes["df_gestion_fy_fisico"],
        "pesos_turno": df_pesos_turno,
        "fecha_corte_operacional": fecha_corte_operacional,
        "anio_fiscal": rango_fy["anio_fiscal"],
        "fecha_inicio_mes": fuentes["fecha_inicio_mes"],
        "fecha_fin_mes": fuentes["fecha_fin_mes"],
    }


def _siguiente_id_reporte_torre_oficial(conn) -> int:
    sql = _sa_text(
        f"SELECT ISNULL(MAX(id_reporte), 0) + 1 AS next_id FROM {RTO_CAB_TABLE}"
    )
    return int(conn.execute(sql).scalar() or 1)


def _valor_parametro_sql(valor):
    """Convierte escalares pandas/numpy nulos a NULL DBAPI real."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(valor, "item"):
        try:
            return valor.item()
        except (TypeError, ValueError):
            pass
    return valor


def _nullable_int_sql(valor):
    """Convierte un entero nullable de pandas en 1, 0 o None para DBAPI."""
    if valor is None:
        return None

    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    return int(valor)


def _resumen_parametros_tm3(registros: list) -> dict:
    """Resume los valores reales que se enviarán al INSERT de detalle."""
    activos = [registro.get("TM3_Activo") for registro in registros]
    invalidos = [
        valor for valor in activos
        if valor is not None and valor not in (0, 1, 0.0, 1.0)
    ]
    if invalidos:
        raise RuntimeError(
            f"TM3_Activo contiene valores distintos de 0, 1 o NULL: {invalidos}"
        )
    return {
        "filas": len(registros),
        "TMH_CV01_no_nulo": sum(
            registro.get("TMH_CV01") is not None for registro in registros
        ),
        "TM3_Activo_1": sum(valor in (1, 1.0) for valor in activos),
        "TM3_Activo_0": sum(valor in (0, 0.0) for valor in activos),
        "TM3_Activo_NULL": sum(valor is None for valor in activos),
        "Rep_TM3_Quimico_no_nulo": sum(
            registro.get("Rep_TM3_Quimico") is not None
            for registro in registros
        ),
        "Rep_TM3_Fisico_no_nulo": sum(
            registro.get("Rep_TM3_Fisico") is not None
            for registro in registros
        ),
    }


def _registros_detalle_torre_oficial(df_guardar: pd.DataFrame) -> list:
    registros = []
    for _, fila in df_guardar.iterrows():
        fecha = pd.to_datetime(fila.get("Fecha"), errors="coerce")
        turno = _normalizar_turno_rep(fila.get("Turno"))
        if pd.isna(fecha) or turno not in {"TA", "TB"}:
            continue
        registro = {"Fecha": fecha.date(), "Turno": turno}
        for col in RTO_DETALLE_COLUMNAS:
            if col in ("Fecha", "Turno"):
                continue
            if col == "TM3_Activo":
                registro[col] = _nullable_int_sql(
                    fila.get("TM3_Activo")
                )
            else:
                registro[col] = _valor_parametro_sql(fila.get(col))
        registros.append(registro)
    return registros


def write_reporte_torre_oficial(
    df_detalle: pd.DataFrame,
    periodo_inicio: date,
    periodo_fin: date,
    usuario: str,
    paquete: dict,
) -> int:
    """
    Persiste snapshot oficial: cab + bloques JSON + detalle.
    Reemplaza el reporte activo del mes (soft-delete cab anterior).
    """
    if df_detalle is None or df_detalle.empty:
        raise ValueError("No hay filas para guardar.")
    if not paquete:
        raise ValueError("Paquete de snapshot vacío.")

    faltantes_tm3 = [
        columna for columna in RTO_TM3_COLUMNAS_OBLIGATORIAS
        if columna not in df_detalle.columns
    ]
    if faltantes_tm3:
        raise RuntimeError(
            f"No se puede publicar: faltan columnas TM3 {faltantes_tm3}"
        )

    periodo_inicio, periodo_fin, periodo_mes = normalizar_periodo_mes(
        periodo_inicio,
        periodo_fin,
    )

    previo = fetch_reporte_torre_oficial_detalle(periodo_mes=periodo_mes)
    mapa_prev = comentarios_mapa_desde_dataframe(previo)
    df_guardar = _merge_comentarios_representatividad(
        df_detalle, mapa_prev, usuario=usuario,
    )
    registros_detalle = _registros_detalle_torre_oficial(df_guardar)
    if not registros_detalle:
        raise ValueError("No hay filas válidas para guardar.")
    resumen_tm3 = _resumen_parametros_tm3(registros_detalle)
    print(f"[RTO] Parámetros INSERT detalle TM3: {resumen_tm3}")

    fecha_corte = paquete.get("fecha_corte_operacional")
    if fecha_corte is None:
        raise ValueError("El paquete debe incluir fecha_corte_operacional.")

    insert_cab = _sa_text(f"""
        INSERT INTO {RTO_CAB_TABLE} (
            id_reporte, periodo_mes, periodo_inicio, periodo_fin,
            fecha_corte_operacional, anio_fiscal,
            usuario, estado, activo
        ) VALUES (
            :id_reporte, :periodo_mes, :periodo_inicio, :periodo_fin,
            :fecha_corte_operacional, :anio_fiscal,
            :usuario, :estado, :activo
        )
    """)

    insert_snap = _sa_text(f"""
        INSERT INTO {RTO_SNAPSHOT_TABLE} (
            id_reporte, bloque, payload, filas
        ) VALUES (
            :id_reporte, :bloque, :payload, :filas
        )
    """)

    insert_det = _sa_text(f"""
        INSERT INTO {RTO_DETALLE_TABLE} (
            id_reporte, Fecha, Turno, Semana, Pad, Pad_Original, Pad_Ajustado_Por,
            TMH_CV08, Rep_TM1_Quimico, TMH_CV108, Rep_TM2_Quimico, Rep_Turno_Quimico,
            Rep_TM1_Fisico, Rep_TM2_Fisico, Rep_Turno_Fisico,
            TM1_Activo, TM2_Activo,
            Comentario_TM1_Quimico, Comentario_TM2_Quimico,
            Comentario_TM1_Fisico, Comentario_TM2_Fisico
            , TMH_CV01, Rep_TM3_Quimico, Rep_TM3_Fisico, TM3_Activo
            , Comentario_TM3_Quimico, Comentario_TM3_Fisico
        ) VALUES (
            :id_reporte, :Fecha, :Turno, :Semana, :Pad, :Pad_Original, :Pad_Ajustado_Por,
            :TMH_CV08, :Rep_TM1_Quimico, :TMH_CV108, :Rep_TM2_Quimico, :Rep_Turno_Quimico,
            :Rep_TM1_Fisico, :Rep_TM2_Fisico, :Rep_Turno_Fisico,
            :TM1_Activo, :TM2_Activo,
            :Comentario_TM1_Quimico, :Comentario_TM2_Quimico,
            :Comentario_TM1_Fisico, :Comentario_TM2_Fisico
            , :TMH_CV01, :Rep_TM3_Quimico, :Rep_TM3_Fisico, :TM3_Activo
            , :Comentario_TM3_Quimico, :Comentario_TM3_Fisico
        )
    """)

    soft_delete_cab = _sa_text(f"""
        UPDATE {RTO_CAB_TABLE}
        SET activo = 0,
            fecha_eliminacion = SYSDATETIME(),
            usuario_eliminacion = :usuario
        WHERE periodo_mes = :periodo_mes
          AND activo = 1
    """)

    engine = _get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(
                soft_delete_cab,
                {"periodo_mes": periodo_mes, "usuario": usuario},
            )
            id_reporte = _siguiente_id_reporte_torre_oficial(conn)
            conn.execute(
                insert_cab,
                {
                    "id_reporte": id_reporte,
                    "periodo_mes": periodo_mes,
                    "periodo_inicio": periodo_inicio,
                    "periodo_fin": periodo_fin,
                    "fecha_corte_operacional": pd.to_datetime(fecha_corte).date(),
                    "anio_fiscal": paquete.get("anio_fiscal"),
                    "usuario": usuario,
                    "estado": "FINALIZADO",
                    "activo": 1,
                },
            )
            for bloque in RTO_SNAPSHOT_BLOQUES:
                df_bloque = paquete.get(bloque)
                payload = _dataframe_a_snapshot_json(df_bloque)
                filas = 0 if df_bloque is None or df_bloque.empty else len(df_bloque)
                conn.execute(
                    insert_snap,
                    {
                        "id_reporte": id_reporte,
                        "bloque": bloque,
                        "payload": payload,
                        "filas": filas,
                    },
                )
            for registro in registros_detalle:
                registro["id_reporte"] = id_reporte
                conn.execute(insert_det, registro)
    except Exception as exc:
        raise RuntimeError(
            f"Error al guardar reporte_torre_oficial: {exc}"
        ) from exc

    return id_reporte


def fetch_reporte_torre_oficial_cab(id_reporte: int) -> pd.Series | None:
    sql = _sa_text(f"""
        SELECT *
        FROM {RTO_CAB_TABLE}
        WHERE id_reporte = :id_reporte
          AND activo = 1
    """)
    with _get_engine().connect() as conn:
        df = pd.read_sql(sql, conn, params={"id_reporte": id_reporte})
    if df.empty:
        return None
    return df.iloc[0]


def fetch_reporte_torre_oficial_snapshot(id_reporte: int) -> dict:
    sql = _sa_text(f"""
        SELECT bloque, payload
        FROM {RTO_SNAPSHOT_TABLE}
        WHERE id_reporte = :id_reporte
    """)
    with _get_engine().connect() as conn:
        df = pd.read_sql(sql, conn, params={"id_reporte": id_reporte})

    paquete = {}
    for _, fila in df.iterrows():
        bloque = str(fila["bloque"])
        paquete[bloque] = _snapshot_json_a_dataframe(fila["payload"])

    cab = fetch_reporte_torre_oficial_cab(id_reporte)
    if cab is not None:
        paquete["fecha_corte_operacional"] = cab.get("fecha_corte_operacional")
        paquete["anio_fiscal"] = cab.get("anio_fiscal")
        paquete["fecha_inicio_mes"] = cab.get("periodo_inicio")
        paquete["fecha_fin_mes"] = cab.get("periodo_fin")
        paquete["periodo_inicio"] = cab.get("periodo_inicio")
        paquete["periodo_fin"] = cab.get("periodo_fin")
        paquete["periodo_mes"] = cab.get("periodo_mes")

    return paquete


def fetch_reporte_torre_oficial_detalle(
    id_reporte: int | None = None,
    periodo_mes: str | None = None,
) -> pd.DataFrame:
    if id_reporte is not None:
        sql = _sa_text(f"""
            SELECT d.*, c.periodo_mes, c.periodo_inicio, c.periodo_fin, c.usuario
            FROM {RTO_DETALLE_TABLE} d
            INNER JOIN {RTO_CAB_TABLE} c ON c.id_reporte = d.id_reporte
            WHERE d.id_reporte = :id_reporte
              AND c.activo = 1
            ORDER BY d.Fecha, d.Turno
        """)
        params = {"id_reporte": id_reporte}
    elif periodo_mes:
        sql = _sa_text(f"""
            SELECT d.*, c.periodo_mes, c.periodo_inicio, c.periodo_fin, c.usuario
            FROM {RTO_DETALLE_TABLE} d
            INNER JOIN {RTO_CAB_TABLE} c ON c.id_reporte = d.id_reporte
            WHERE c.periodo_mes = :periodo_mes
              AND c.activo = 1
            ORDER BY d.Fecha, d.Turno
        """)
        params = {"periodo_mes": periodo_mes}
    else:
        return pd.DataFrame()

    with _get_engine().connect() as conn:
        df = pd.read_sql(sql, conn, params=params)

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df


def mes_tiene_reporte_activo(periodo_mes: str) -> bool:
    """True si existe un reporte oficial activo para el mes YYYY-MM."""
    if not periodo_mes:
        return False
    sql = _sa_text(f"""
        SELECT TOP 1 1 AS ok
        FROM {RTO_CAB_TABLE}
        WHERE periodo_mes = :periodo_mes
          AND activo = 1
    """)
    try:
        with _get_engine().connect() as conn:
            val = conn.execute(sql, {"periodo_mes": periodo_mes}).scalar()
        return val is not None
    except Exception:
        return False


def fetch_historial_reporte_torre_oficial(limit: int = 50) -> pd.DataFrame:
    sql = _sa_text(f"""
        SELECT TOP (:limite)
            c.id_reporte,
            c.periodo_mes,
            c.periodo_inicio,
            c.periodo_fin,
            c.fecha_corte_operacional,
            c.fecha_generacion,
            c.usuario,
            c.estado,
            (
                SELECT COUNT(*)
                FROM {RTO_DETALLE_TABLE} d
                WHERE d.id_reporte = c.id_reporte
            ) AS filas
        FROM {RTO_CAB_TABLE} c
        WHERE c.activo = 1
        ORDER BY c.periodo_mes DESC, c.fecha_generacion DESC
    """)
    try:
        with _get_engine().connect() as conn:
            return pd.read_sql(sql, conn, params={"limite": limit})
    except Exception as exc:
        raise RuntimeError(
            f"Error al leer historial reporte_torre_oficial: {exc}"
        ) from exc


def soft_delete_reporte_torre_oficial(id_reporte: int, usuario: str) -> None:
    sql = _sa_text(f"""
        UPDATE {RTO_CAB_TABLE}
        SET activo = 0,
            fecha_eliminacion = SYSDATETIME(),
            usuario_eliminacion = :usuario
        WHERE id_reporte = :id_reporte
          AND activo = 1
    """)
    try:
        with _get_engine().begin() as conn:
            conn.execute(sql, {"id_reporte": id_reporte, "usuario": usuario})
    except Exception as exc:
        raise RuntimeError(
            f"Error al eliminar reporte_torre_oficial: {exc}"
        ) from exc


def _normalizar_turno_rep(valor) -> str:
    texto = str(valor or "").strip().upper()
    if texto in {"A", "TA"}:
        return "TA"
    if texto in {"B", "TB"}:
        return "TB"
    return texto


def comentarios_mapa_desde_dataframe(df: pd.DataFrame) -> dict:
    """Construye mapa (fecha, turno) -> dict de comentarios por torre/tipo."""
    if df is None or df.empty:
        return {}

    mapa = {}
    for _, fila in df.iterrows():
        fecha = pd.to_datetime(fila.get("Fecha"), errors="coerce")
        turno = _normalizar_turno_rep(fila.get("Turno"))
        if pd.isna(fecha) or turno not in {"TA", "TB"}:
            continue
        clave = (fecha.normalize(), turno)
        mapa[clave] = {
            "Comentario_TM1_Quimico": fila.get("Comentario_TM1_Quimico"),
            "Comentario_TM2_Quimico": fila.get("Comentario_TM2_Quimico"),
            "Comentario_TM1_Fisico": fila.get("Comentario_TM1_Fisico"),
            "Comentario_TM2_Fisico": fila.get("Comentario_TM2_Fisico"),
            "Comentario_TM3_Quimico": fila.get("Comentario_TM3_Quimico"),
            "Comentario_TM3_Fisico": fila.get("Comentario_TM3_Fisico"),
            # Pad efectivo y derivado: permiten reconocer un ajuste manual
            # previo (Pad <> Pad_Original) y arrastrarlo a la nueva version
            # sin perder quien lo hizo.
            "Pad": fila.get("Pad"),
            "Pad_Original": fila.get("Pad_Original"),
            "Pad_Ajustado_Por": fila.get("Pad_Ajustado_Por"),
        }
    return mapa


def comentario_torres_para_tipo(mapa: dict, fecha, turno: str, torre: str, tipo: str):
    """Devuelve comentario para export (TM1/TM2/TM3 + quimico/fisico)."""
    if not mapa:
        return None
    fecha_norm = pd.to_datetime(fecha, errors="coerce")
    if pd.isna(fecha_norm):
        return None
    turno_norm = _normalizar_turno_rep(turno)
    datos = mapa.get((fecha_norm.normalize(), turno_norm), {})
    if not datos:
        return None
    tipo_norm = str(tipo).strip().lower()
    torre_norm = str(torre).strip().upper()
    if torre_norm not in {"TM1", "TM2", "TM3"}:
        return None
    sufijo = "Quimico" if tipo_norm == "quimico" else "Fisico"
    valor = datos.get(f"Comentario_{torre_norm}_{sufijo}")
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = str(valor).strip()
    return texto or None


def pad_ajustado_para(mapa: dict, fecha, turno: str):
    """
    Pad ajustado a mano para el export, o None si vale el derivado.

    El Excel se arma desde el snapshot y recalcula el Pad en cada corrida;
    este es el unico canal por el que un ajuste del editor llega a la tabla
    "Mineral apilado por Pad".
    """
    if not mapa:
        return None
    fecha_norm = pd.to_datetime(fecha, errors="coerce")
    if pd.isna(fecha_norm):
        return None
    datos = mapa.get((fecha_norm.normalize(), _normalizar_turno_rep(turno)), {})
    if not datos:
        return None

    def _texto(valor):
        if valor is None:
            return None
        try:
            if pd.isna(valor):
                return None
        except (TypeError, ValueError):
            pass
        return str(valor).strip() or None

    pad = _texto(datos.get("Pad"))
    original = _texto(datos.get("Pad_Original"))
    # Sin original no se sabe si hubo ajuste: es una fila anterior al backfill
    # de Pad_Original. Tratarla como ajuste fijaria un Pad viejo sobre el
    # derivado fresco.
    if pad is None or original is None:
        return None
    return pad if pad != original else None


def _periodo_mes_desde_fecha(fecha: date) -> str:
    return f"{fecha.year:04d}-{fecha.month:02d}"


def es_mes_completo(periodo_inicio: date, periodo_fin: date) -> bool:
    """True si el rango es el mes calendario completo (día 1 al último)."""
    ini = pd.to_datetime(periodo_inicio).date()
    fin = pd.to_datetime(periodo_fin).date()
    if ini.day != 1:
        return False
    ultimo = calendar.monthrange(ini.year, ini.month)[1]
    esperado_fin = date(ini.year, ini.month, ultimo)
    return fin == esperado_fin and _periodo_mes_desde_fecha(ini) == _periodo_mes_desde_fecha(fin)


def normalizar_periodo_mes(periodo_inicio: date, periodo_fin: date) -> tuple[date, date, str]:
    """
    Valida mes calendario completo y devuelve (inicio, fin, periodo_mes YYYY-MM).
  """
    if not es_mes_completo(periodo_inicio, periodo_fin):
        raise ValueError(
            "Solo se pueden guardar reportes de mes calendario completo "
            f"({periodo_inicio} a {periodo_fin})."
        )
    ini = pd.to_datetime(periodo_inicio).date()
    ultimo = calendar.monthrange(ini.year, ini.month)[1]
    fin = date(ini.year, ini.month, ultimo)
    return ini, fin, _periodo_mes_desde_fecha(ini)


def _merge_comentarios_representatividad(
    df_detalle: pd.DataFrame,
    comentarios_previos: dict,
    usuario: str | None = None,
) -> pd.DataFrame:
    """
    Datos referenciales siempre del detalle actual.
    Comentarios: manda la pantalla, incluido el vacío (permite borrarlos).
    Pad: única excepción a la regla referencial, ver bloque al final.
    """
    if df_detalle is None or df_detalle.empty:
        return df_detalle

    df = df_detalle.copy()
    cols_com = [
        "Comentario_TM1_Quimico",
        "Comentario_TM2_Quimico",
        "Comentario_TM1_Fisico",
        "Comentario_TM2_Fisico",
        "Comentario_TM3_Quimico",
        "Comentario_TM3_Fisico",
    ]
    for col in (*cols_com, "Pad", "Pad_Original", "Pad_Ajustado_Por"):
        if col not in df.columns:
            df[col] = None

    def _texto(valor):
        if valor is None:
            return None
        try:
            if pd.isna(valor):
                return None
        except (TypeError, ValueError):
            pass
        texto = str(valor).strip()
        return texto or None

    for idx, fila in df.iterrows():
        fecha = pd.to_datetime(fila.get("Fecha"), errors="coerce")
        turno = _normalizar_turno_rep(fila.get("Turno"))
        if pd.isna(fecha) or turno not in {"TA", "TB"}:
            continue
        prev = (comentarios_previos or {}).get(
            (fecha.normalize(), turno),
            {},
        )
        for col in cols_com:
            # El editor ya se abre con los comentarios guardados, asi que un
            # vacio aqui es un borrado deliberado. Reponerlo desde BD los
            # volveria imborrables, igual que pasaba con el Pad mas abajo.
            df.at[idx, col] = _texto(fila.get(col))

        # Pad_Original siempre viene del detalle recien calculado. Pad es el
        # valor efectivo: gana el ajuste de esta sesion, si no hay se arrastra
        # el ajuste guardado en BD, y si tampoco vuelve al derivado.
        original = _texto(fila.get("Pad_Original"))
        ajuste_sesion = _texto(fila.get("Pad"))
        prev_pad = _texto(prev.get("Pad"))
        prev_original = _texto(prev.get("Pad_Original"))
        prev_autor = _texto(prev.get("Pad_Ajustado_Por"))
        prev_es_ajuste = prev_pad is not None and prev_pad != prev_original

        # El editor manda: al abrirlo ya trae el override guardado fundido en
        # el detalle, asi que si aqui llega Pad == Pad_Original es porque el
        # ajuste se quito. Reponerlo desde BD lo volveria imborrable.
        es_ajuste = (
            ajuste_sesion is not None
            and original is not None
            and ajuste_sesion != original
        )
        if es_ajuste:
            df.at[idx, "Pad"] = ajuste_sesion
            # Republicar sin tocar el ajuste no debe robarle la autoria a
            # quien lo hizo; solo un valor distinto sella un autor nuevo.
            df.at[idx, "Pad_Ajustado_Por"] = (
                prev_autor
                if prev_es_ajuste and prev_pad == ajuste_sesion
                else usuario
            )
        else:
            df.at[idx, "Pad"] = original
            df.at[idx, "Pad_Ajustado_Por"] = None
    return df


def write_representatividad_torres_generado(
    df_detalle: pd.DataFrame,
    periodo_inicio: date,
    periodo_fin: date,
    usuario: str,
    paquete: dict | None = None,
) -> int:
    """Compat: requiere paquete snapshot; usar write_reporte_torre_oficial."""
    if paquete is None:
        paquete = armar_paquete_reporte_torre_oficial(periodo_inicio, periodo_fin)
    return write_reporte_torre_oficial(
        df_detalle, periodo_inicio, periodo_fin, usuario, paquete
    )


def fetch_historial_representatividad(limit: int = 50) -> pd.DataFrame:
    return fetch_historial_reporte_torre_oficial(limit)


def fetch_representatividad_por_mes(periodo_mes: str) -> pd.DataFrame:
    return fetch_reporte_torre_oficial_detalle(periodo_mes=periodo_mes)


def fetch_representatividad_guardado(id_reporte: int) -> pd.DataFrame:
    return fetch_reporte_torre_oficial_detalle(id_reporte=id_reporte)


def fetch_comentarios_representatividad_periodo(
    periodo_inicio: date,
    periodo_fin: date,
) -> pd.DataFrame:
    try:
        _, _, periodo_mes = normalizar_periodo_mes(periodo_inicio, periodo_fin)
    except ValueError:
        return pd.DataFrame()
    return fetch_reporte_torre_oficial_detalle(periodo_mes=periodo_mes)


def soft_delete_representatividad_por_mes(periodo_mes: str, usuario: str) -> None:
    sql = _sa_text(f"""
        UPDATE {RTO_CAB_TABLE}
        SET activo = 0,
            fecha_eliminacion = SYSDATETIME(),
            usuario_eliminacion = :usuario
        WHERE periodo_mes = :periodo_mes
          AND activo = 1
    """)
    with _get_engine().begin() as conn:
        conn.execute(sql, {"periodo_mes": periodo_mes, "usuario": usuario})


def soft_delete_representatividad_generado(id_reporte: int, usuario: str) -> None:
    soft_delete_reporte_torre_oficial(id_reporte, usuario)


def _semana_mes_lunes_domingo(fecha) -> int:
    """Semana del mes con semanas calendario de lunes a domingo."""
    fecha = pd.Timestamp(fecha)
    if pd.isna(fecha):
        raise ValueError("La fecha es obligatoria para calcular la semana del mes.")
    primer_dia = fecha.replace(day=1).normalize()
    return int(((fecha.normalize() - primer_dia).days + primer_dia.weekday()) // 7 + 1)


def _filtrar_periodo_resumen(
    df_src: pd.DataFrame,
    fecha_ref,
    solo_semana: bool = False,
) -> pd.DataFrame:
    """Filtra desde el inicio del mes hasta la fecha de referencia."""
    if df_src is None or df_src.empty or "Fecha" not in df_src.columns:
        return pd.DataFrame(columns=df_src.columns if df_src is not None else None)

    fecha_ref = pd.Timestamp(fecha_ref).normalize()
    data = df_src.copy()
    fechas = pd.to_datetime(data["Fecha"], errors="coerce").dt.normalize()
    mascara = (
        fechas.notna()
        & fechas.ge(fecha_ref.replace(day=1))
        & fechas.le(fecha_ref)
    )
    if solo_semana:
        semana_ref = _semana_mes_lunes_domingo(fecha_ref)
        semanas = fechas.map(
            lambda fecha: (
                _semana_mes_lunes_domingo(fecha)
                if pd.notna(fecha) and fecha.month == fecha_ref.month and fecha.year == fecha_ref.year
                else np.nan
            )
        )
        mascara &= semanas.eq(semana_ref)
    return data.loc[mascara].copy()


def _promedio_ponderado_periodo(
    df_src: pd.DataFrame,
    fecha_ref,
    valor_col: str,
    peso_col: str,
    solo_semana: bool = False,
):
    """Promedio ponderado por TMS, excluyendo valores/pesos inválidos."""
    if (
        not valor_col
        or not peso_col
        or df_src is None
        or df_src.empty
        or valor_col not in df_src.columns
        or peso_col not in df_src.columns
    ):
        return ""

    data = _filtrar_periodo_resumen(df_src, fecha_ref, solo_semana=solo_semana)
    if data.empty:
        return ""
    valores = pd.to_numeric(data[valor_col], errors="coerce")
    pesos = pd.to_numeric(data[peso_col], errors="coerce")
    validos = valores.notna() & pesos.notna() & pesos.gt(0)
    if not validos.any():
        return ""
    denominador = pesos.loc[validos].sum()
    if not np.isfinite(denominador) or denominador <= 0:
        return ""
    return float((valores.loc[validos] * pesos.loc[validos]).sum() / denominador)


def preparar_df_reporte_turno_excel(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Campaña se presenta igual que Módulo: como número entero.
    if "Campania" in df.columns:
        df["Campania"] = pd.to_numeric(df["Campania"], errors="coerce")

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    if "Turno" in df.columns:
        df["Turno"] = df["Turno"].astype(str).str.upper().str.strip()
        df["Turno_excel"] = df["Turno"].map({"A": "TA", "B": "TB"}).fillna(df["Turno"])
    else:
        df["Turno_excel"] = ""

    if "Fecha" in df.columns:
        df["Fecha_Turno"] = df["Fecha"].dt.strftime("%d-%m-%Y") + " " + df["Turno_excel"]
        semanas = df["Fecha"].map(
            lambda fecha: _semana_mes_lunes_domingo(fecha) if pd.notna(fecha) else np.nan
        )
        df["Semana"] = semanas.map(
            lambda semana: f"Semana {int(semana)}" if pd.notna(semana) else ""
        )
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

    # Conservar ceros y NULL de origen, sin inferirlos desde el tonelaje.
    columnas_texto_export = {
        "Fecha",
        "Turno",
        "Turno_excel",
        "Fecha_Turno",
        "Semana",
        "Material",
        "Fuente_Info_Quimica",
        "Fuente_Info_Fisica",
        "Muestra_Quimica",
        "Muestra_Fisica",
        "Malla_Menos_1_2_Plan_Semanal",
    }

    for col in df.columns:
        if col not in columnas_texto_export:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Solo para Excel: rellenar NULL reales si el TMS es exactamente cero.
    # TMS nulo no implica cero; planes y valores existentes se conservan.
    columnas_reales = [
        'STOCK',
        'MINA',
        'SRR',
        'CuT_Real',
        'CuS_Real',
        'Solubilidad_Real',
        'CO3_Real',
        'CuFe_Real',
        'FeT_Real',
        'FeS_Real',
        'ConsH_Real',
        'Malla_Menos_1_2_Real',
        'Malla_Menos_100_Real',
        'CaolBeta_Real',
        'Dosis_Acido_Ideal_TM',
    ]
    if 'Apilado_TMS_Real' in df.columns:
        sin_apilado = pd.to_numeric(df['Apilado_TMS_Real'], errors="coerce").eq(0)
        reales_presentes = [col for col in columnas_reales if col in df.columns]
        df.loc[sin_apilado, reales_presentes] = df.loc[sin_apilado, reales_presentes].fillna(0)

    return df

def preparar_df_generador_reporte_excel(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepara la capa diaria para exportación.

    Importante:
    - Solo los NULL reales con TMS cero se presentan como cero.
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
        pd.to_numeric(df["Campania"], errors="coerce")
        if "Campania" in df.columns
        else np.nan
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

    # Conservar ceros y NULL de origen, incluidos planes y programas.
    columnas_texto_export = {"Fecha", "Material", "Malla_Menos_1_2_Programa"}
    for col in columnas:
        if col not in columnas_texto_export:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Solo para Excel: rellenar NULL reales si el TMS es exactamente cero.
    # TMS nulo no implica cero; planes y valores existentes se conservan.
    columnas_reales = [
        'STOCK_Dia',
        'MINA_Dia',
        'SRR_Dia',
        'CuT_Real_Dia',
        'CuS_Real_Dia',
        'Solubilidad_Real_Dia',
        'CO3_Real_Dia',
        'CuFe_Real_Dia',
        'FeT_Real_Dia',
        'FeS_Real_Dia',
        'ConsH_Real_Dia',
        'Malla_Menos_1_2_Real_Dia',
        'Malla_Menos_100_Real_Dia',
        'CaolBeta_Real_Dia',
        'Dosis_Acido_Ideal_Dia',
    ]
    if 'Apilado_TMS_Real_Dia' in df.columns:
        sin_apilado = pd.to_numeric(df['Apilado_TMS_Real_Dia'], errors="coerce").eq(0)
        reales_presentes = [col for col in columnas_reales if col in df.columns]
        df.loc[sin_apilado, reales_presentes] = df.loc[sin_apilado, reales_presentes].fillna(0)

    return df[columnas]

def agregar_hoja_generador_reporte(
    writer: pd.ExcelWriter,
    df_diario: pd.DataFrame,
    df_turno_resumen: pd.DataFrame = None,
    df_diario_resumen: pd.DataFrame = None,
) -> None:
    """
    Agrega la hoja diaria "Generador Reporte" al mismo archivo Excel
    que ya contiene la hoja "Reporte por Turno".

    No modifica el DataFrame ni el diseño de la hoja por turno.
    """

    df_resumen = (
        df_diario.copy()
        if df_diario_resumen is None
        else df_diario_resumen.copy()
    )
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
        "font_name": "Arial",
        "font_size": 18,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_subtitulo = workbook.add_format({
        "bold": True,
        "font_name": "Arial",
        "font_size": 18,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_grupo = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 16,
        "font_color": COLOR_BLANCO,
        "align": "center",
        "valign": "vcenter",
        "bg_color": COLOR_PAMPA_NORTE,
        "border": 2,
        "border_color": COLOR_BORDE,
        "text_wrap": True,
    })

    fmt_header = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 12,
        "align": "center",
        "valign": "vcenter",
        "bg_color": COLOR_PAMPA_NORTE,
        "font_color": COLOR_BLANCO,
        "border": 2,
        "border_color": COLOR_BORDE,
        "text_wrap": True,
    })

    fmt_header_claro = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 12,
        "align": "center",
        "valign": "vcenter",
        "bg_color": COLOR_PAMPA_NORTE,
        "font_color": COLOR_BLANCO,
        "border": 2,
        "border_color": COLOR_BORDE,
        "text_wrap": True,
    })

    fmt_texto = workbook.add_format({
        "font_name": "Calibri",
        "font_size": 10,
        "border": 1,
        "border_color": COLOR_BORDE,
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })

    fmt_texto_gris = workbook.add_format({
        "font_name": "Calibri",
        "font_size": 10,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "border": 2,
        "border_color": COLOR_BORDE,
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })

    fmt_fecha = workbook.add_format({
        "font_name": "Calibri",
        "font_size": 10,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "num_format": "dd-mm-yyyy",
        "border": 2,
        "border_color": COLOR_BORDE,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_numero = workbook.add_format({
        "font_name": "Calibri",
        "font_size": 10,
        "num_format": "#,##0",
        "border": 1,
        "border_color": COLOR_BORDE,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_decimal_2 = workbook.add_format({
        "font_name": "Calibri",
        "font_size": 10,
        "num_format": "0.00",
        "border": 1,
        "border_color": COLOR_BORDE,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_decimal_3 = workbook.add_format({
        "font_name": "Calibri",
        "font_size": 10,
        "num_format": "0.000",
        "border": 1,
        "border_color": COLOR_BORDE,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_decimal_gris = workbook.add_format({
        "font_name": "Calibri",
        "font_size": 10,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "num_format": "0.00",
        "border": 2,
        "border_color": COLOR_BORDE,
        "align": "center",
        "valign": "vcenter",
    })

    fmt_resumen_titulo = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 16,
        "align": "center",
        "valign": "vcenter",
    })
    fmt_resumen_header = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 12,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "align": "center",
        "valign": "vcenter",
        "border": 2,
        "border_color": COLOR_BORDE,
        "text_wrap": True,
    })
    fmt_resumen_fecha = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 12,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "num_format": "dd-mm-yyyy",
        "align": "center",
        "valign": "vcenter",
        "border": 2,
        "border_color": COLOR_BORDE,
    })
    fmt_resumen_subheader = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 11,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": COLOR_BORDE,
        "text_wrap": True,
    })
    fmt_resumen_label = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 11,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "align": "center",
        "valign": "vcenter",
        "border": 2,
        "border_color": COLOR_BORDE,
    })
    fmt_resumen_num = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 11,
        "num_format": "0.00",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": COLOR_BORDE,
    })
    fmt_resumen_texto = workbook.add_format({
        "bold": True,
        "font_name": "Calibri",
        "font_size": 11,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": COLOR_BORDE,
    })

    # ============================================================
    # LOGO Y ENCABEZADO INSTITUCIONAL
    # ============================================================
    _agregar_encabezado_institucional_torre(
        worksheet,
        fmt_titulo,
        fmt_subtitulo,
        con_turno=False,
    )

    # ============================================================
    # ENCABEZADOS SEGÚN LA HOJA ORIGINAL "GENERADOR REPORTE"
    #
    # Se elimina únicamente la columna Semana.
    # No se agrega una columna visible llamada
    # "Clasificación Solubilidad".
    # ============================================================

    def _valor_ultimo_dia(df_src, fecha_ref, col_name):
        if not col_name or df_src is None or df_src.empty or col_name not in df_src.columns:
            return ""
        data = df_src.copy()
        if "Fecha" in data.columns:
            fechas = pd.to_datetime(data["Fecha"], errors="coerce")
            data = data.loc[fechas.dt.date == fecha_ref.date()]
        if data.empty:
            return ""
        value = data.iloc[-1][col_name]
        return "" if pd.isna(value) else value

    def _valor_turno(fecha_ref, turno, col_name):
        if df_turno_resumen is None or df_turno_resumen.empty or col_name not in df_turno_resumen.columns:
            return ""
        data = df_turno_resumen.copy()
        if "Fecha" in data.columns:
            fechas = pd.to_datetime(data["Fecha"], errors="coerce")
            data = data.loc[fechas.dt.date == fecha_ref.date()]
        if "Turno_excel" in data.columns:
            data = data.loc[data["Turno_excel"].astype(str).str.upper().eq(turno)]
        elif "Turno" in data.columns:
            data = data.loc[data["Turno"].astype(str).str.upper().eq(turno)]
        if data.empty:
            return ""
        value = data.iloc[-1][col_name]
        return "" if pd.isna(value) else value

    def _escribir_resumen_ultimo_dia():
        if df_export.empty or "Fecha" not in df_export.columns:
            return
        fechas = pd.to_datetime(df_export["Fecha"], errors="coerce").dropna()
        if fechas.empty:
            return

        fecha_ref = fechas.max()
        semana = _semana_mes_lunes_domingo(fecha_ref)

        worksheet.merge_range("V3:AE3", "Reporte Diario Análisis Torre de Muestreo", fmt_resumen_titulo)
        worksheet.merge_range("V4:W4", fecha_ref.to_pydatetime(), fmt_resumen_fecha)
        worksheet.write("X4", "TA", fmt_resumen_header)
        worksheet.write("Y4", "TB", fmt_resumen_header)
        worksheet.write("Z4", "Día", fmt_resumen_header)
        worksheet.write("AA4", "Día ", fmt_resumen_header)
        worksheet.merge_range("AB4:AC4", "Acumulado Semana", fmt_resumen_header)
        worksheet.merge_range("AD4:AE4", "Acumulado Mes", fmt_resumen_header)
        worksheet.merge_range("V5:W5", f"Semana {semana}", fmt_resumen_header)
        for cell, text in {
            "X5": "Real",
            "Y5": "Real",
            "Z5": "Real",
            "AA5": "Programa",
            "AB5": "Real",
            "AC5": "Programa Semanal",
            "AD5": "Real",
            "AE5": "Mensual",
        }.items():
            worksheet.write(cell, text, fmt_resumen_subheader)

        filas = [
            ("CuT", "%", "CuT_Real", "CuT_Real_Dia", "CuT_Programa", "CuT_Plan"),
            ("CuS", "%", "CuS_Real", "CuS_Real_Dia", "CuS_Programa", "CuS_Plan"),
            ("Solubilidad", "%", "Solubilidad_Real", "Solubilidad_Real_Dia", "Solubilidad_Programa", "Solubilidad_Plan"),
            ("CO3", "%", "CO3_Real", "CO3_Real_Dia", "CO3_Programa", "CO3_Plan"),
            ("CuFe", "%", "CuFe_Real", "CuFe_Real_Dia", "CuFe_Programa", "CuFe_Plan"),
            ("-100#Ty", "%", "Malla_Menos_100_Real", "Malla_Menos_100_Real_Dia", "Malla_Menos_100_Programa", "Malla_Menos_100_Plan"),
            ("-1/2´", "%", "Malla_Menos_1_2_Real", "Malla_Menos_1_2_Real_Dia", "Malla_Menos_1_2_Programa", "Malla_Menos_1_2_Programa"),
            ("Caolbeta", "%", "CaolBeta_Real", "CaolBeta_Real_Dia", "CaolBeta_Programa", "CaolBeta_Plan"),
            ("Mina", "%", "MINA", "MINA_Dia", None, None),
            ("Stock", "%", "STOCK", "STOCK_Dia", None, None),
            ("SRR", "%", "SRR", "SRR_Dia", None, None),
        ]

        for row_idx, (label, unidad, turno_col, dia_col, programa_col, plan_col) in enumerate(filas, start=5):
            worksheet.write(row_idx, 21, label, fmt_resumen_label)
            worksheet.write(row_idx, 22, unidad, fmt_resumen_label)
            valores = [
                _valor_turno(fecha_ref, "TA", turno_col),
                _valor_turno(fecha_ref, "TB", turno_col),
                _valor_ultimo_dia(df_export, fecha_ref, dia_col),
                _valor_ultimo_dia(df_export, fecha_ref, programa_col),
                _promedio_ponderado_periodo(
                    df_resumen, fecha_ref, dia_col,
                    "Apilado_TMS_Real_Dia", solo_semana=True,
                ),
                _promedio_ponderado_periodo(
                    df_resumen, fecha_ref, programa_col,
                    "Apilado_TMS_Programa", solo_semana=True,
                ),
                _promedio_ponderado_periodo(
                    df_resumen, fecha_ref, dia_col,
                    "Apilado_TMS_Real_Dia", solo_semana=False,
                ),
                _promedio_ponderado_periodo(
                    df_resumen, fecha_ref, plan_col,
                    "Apilado_TMS_Plan", solo_semana=False,
                ),
            ]
            for col_idx, value in enumerate(valores, start=23):
                if value == "":
                    worksheet.write_blank(row_idx, col_idx, None, fmt_resumen_num)
                elif isinstance(value, str):
                    worksheet.write(row_idx, col_idx, value, fmt_resumen_texto)
                else:
                    worksheet.write_number(row_idx, col_idx, float(value), fmt_resumen_num)

    _escribir_resumen_ultimo_dia()

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
    worksheet.merge_range("T20:V20", "Solubilidad %", fmt_header)
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
        "Material",
        "Malla_Menos_1_2_Programa",
    }

    columnas_grises = {
        "Fecha",
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
                formato = fmt_decimal_2
                worksheet.write_number(excel_row, excel_col, float(value), formato)
                continue

            formato = fmt_texto_gris if col_name in columnas_grises else fmt_texto
            worksheet.write(excel_row, excel_col, str(value), formato)

    # ============================================================
    # ANCHOS Y PRESENTACIÓN
    # ============================================================
    _aplicar_dimensiones_oficiales_torre(worksheet, con_turno=False)

    worksheet.set_row(16, 14.7)
    worksheet.set_row(17, 21)
    worksheet.set_row(18, 21.75)
    worksheet.set_row(19, 46.5)
    worksheet.set_row(20, 26.1)
    for row_num in range(fila_data, fila_data + len(df_export)):
        worksheet.set_row(row_num, 15)

    last_row = fila_data + len(df_export) - 1
    last_col = col_offset + len(df_export.columns) - 1

    # Sin paneles congelados ni autofiltro, para mantener
    # el mismo comportamiento visual de la hoja "Reporte por Turno".

    worksheet.set_margins(left=0.35, right=0.35, top=0.35, bottom=0.35)
    worksheet.center_horizontally()
    worksheet.set_landscape()
    worksheet.set_paper(8)
    worksheet.fit_to_pages(1, 0)
    worksheet.print_area(0, 0, last_row + 2, max(last_col + 1, 41))
    _agregar_marco_exterior_torre(
        workbook,
        worksheet,
        last_row,
        last_col,
    )
    worksheet.hide_gridlines(2)


def agregar_hoja_malla_100(
    writer: pd.ExcelWriter,
    df_diario: pd.DataFrame,
) -> None:
    """Agrega el grafico mensual de Malla #100 al libro de Analisis TM."""

    workbook = writer.book
    worksheet = workbook.add_worksheet("Malla #100")
    writer.sheets["Malla #100"] = worksheet

    fechas = pd.to_datetime(
        df_diario.get("Fecha", pd.Series(dtype="datetime64[ns]")),
        errors="coerce",
    ).dropna()
    if fechas.empty:
        fecha_referencia = pd.Timestamp.today().normalize()
    else:
        fecha_referencia = fechas.min().normalize()

    inicio_mes = fecha_referencia.replace(day=1)
    fin_mes = fecha_referencia.replace(
        day=calendar.monthrange(fecha_referencia.year, fecha_referencia.month)[1]
    )
    fechas_categoria = [
        float(fecha.toordinal() - 693594)
        for fecha in fechas.iloc[:31]
    ]
    fechas_categoria.extend([None] * (31 - len(fechas_categoria)))

    chart = workbook.add_chart({
        "type": "scatter",
        "subtype": "smooth_with_markers",
    })

    color_real = "#ED7D31"
    color_plan = "#00766D"

    chart.add_series({
        "name": "='Generador Reporte'!$AH$21",
        "categories": ["Generador Reporte", 21, 2, 51, 2],
        "categories_data": fechas_categoria,
        "values": "='Generador Reporte'!$AH$22:$AH$52",
        "line": {"color": color_real, "width": 1},
        "marker": {
            "type": "circle",
            "size": 5,
            "border": {"color": color_real},
            "fill": {"color": color_real},
        },
        "data_labels": {
            "value": True,
            "position": "above",
            "num_format": "0.00",
            "font": {
                "name": "Arial",
                "size": 7,
                "bold": True,
                "color": "#D5500D",
            },
        },
    })
    chart.add_series({
        "name": "Plan",
        "categories": ["Generador Reporte", 21, 2, 51, 2],
        "categories_data": fechas_categoria,
        "values": "='Generador Reporte'!$AJ$22:$AJ$52",
        "line": {"color": color_plan, "width": 1},
        "marker": {
            "type": "circle",
            "size": 5,
            "border": {"color": color_plan},
            "fill": {"color": color_plan},
        },
        "data_labels": {
            "value": True,
            "position": "below",
            "num_format": "#,##0.0",
            "font": {
                "name": "Arial",
                "size": 7,
                "bold": True,
                "color": COLOR_PAMPA_NORTE,
            },
        },
    })

    chart.set_title({
        "name": "Malla #100",
        "name_font": {
            "name": "Arial",
            "size": 12,
            "bold": True,
            "color": COLOR_PAMPA_NORTE,
        },
    })
    chart.set_x_axis({
        "date_axis": True,
        "num_format": "m/d/yyyy",
        "min": inicio_mes.to_pydatetime(),
        "max": fin_mes.to_pydatetime(),
        "major_unit": 1,
        "major_unit_type": "days",
        "line": {"color": "#000000", "width": 1},
        "num_font": {
            "name": "Arial",
            "size": 8,
            "color": COLOR_PAMPA_NORTE,
            "rotation": -45,
        },
        "major_tick_mark": "none",
        "minor_tick_mark": "none",
    })
    chart.set_y_axis({
        "name": "[%]",
        "min": 0,
        "max": 29,
        "num_format": "0.00",
        "num_font": {
            "name": "Arial",
            "size": 9,
            "color": COLOR_PAMPA_NORTE,
        },
        "name_font": {
            "name": "Arial",
            "size": 9,
            "bold": True,
            "color": COLOR_PAMPA_NORTE,
        },
        "name_layout": {
            "x": 0.00466623032874213,
            "y": 0.4370740287479753,
        },
        "major_tick_mark": "outside",
        "minor_tick_mark": "none",
        "major_gridlines": {"visible": False},
        "minor_gridlines": {"visible": False},
    })
    chart.set_legend({
        "position": "right",
        "font": {
            "name": "Arial",
            "size": 10,
            "color": "#666699",
        },
        "layout": {
            "x": 0.5685058019,
            "y": 0.0197537521,
            "width": 0.4259834231,
            "height": 0.2921561232,
        },
    })
    chart.set_plotarea({
        "layout": {
            "x": 0.0730116361,
            "y": 0.1870726491,
            "width": 0.9059622915,
            "height": 0.6424189400,
        },
    })
    chart.set_size({"width": 896, "height": 324})

    worksheet.hide_gridlines(2)
    worksheet.set_zoom(120)
    worksheet.set_column("A:A", 2)
    worksheet.insert_chart(
        "B2",
        chart,
        {
            "x_offset": 78,
            "y_offset": 6,
        },
    )


def agregar_hoja_curva_granulometrica(
    writer: pd.ExcelWriter,
    df_curva_granulometrica: pd.DataFrame,
    periodo_inicio: date = None,
    periodo_fin: date = None,
) -> None:
    """Agrega la curva observada ya calculada en SQL, sin reponderarla."""
    columnas = [
        "Fecha", "Turno", "Ton_TM1", "Ton_TM2", "Rep_Fisica_TM1",
        "Rep_Fisica_TM2", "Tiene_Curva_TM1", "Tiene_Curva_TM2",
        "Torres_Utilizadas", "P2", "P1", "P34", "P12", "P14", "P10",
        "P35", "P100", "P150", "P200", "P325", "PBajo325",
    ]
    df_export = df_curva_granulometrica.copy().reindex(columns=columnas)
    if not df_export.empty:
        df_export["Fecha"] = pd.to_datetime(df_export["Fecha"], errors="coerce")
        df_export = df_export.sort_values(
            ["Fecha", "Turno"],
            key=lambda s: s.map({"A": 1, "B": 2}) if s.name == "Turno" else s,
            kind="stable",
        )
    fechas_validas = df_export["Fecha"].dropna()
    if periodo_inicio is None and not fechas_validas.empty:
        periodo_inicio = fechas_validas.min().date()
    if periodo_fin is None and not fechas_validas.empty:
        periodo_fin = fechas_validas.max().date()
    texto_periodo = "Período: sin datos"
    if periodo_inicio is not None and periodo_fin is not None:
        texto_periodo = (
            f"Período: {pd.Timestamp(periodo_inicio).strftime('%d-%m-%Y')} al "
            f"{pd.Timestamp(periodo_fin).strftime('%d-%m-%Y')}"
        )

    workbook = writer.book
    worksheet = workbook.add_worksheet("Curva Granulométrica")
    writer.sheets["Curva Granulométrica"] = worksheet
    base = {
        "font_name": "Arial", "font_size": 9, "font_color": "#476475",
        "align": "center", "valign": "vcenter", "border": 1,
        "border_color": "#A6A6A6",
    }
    titulo = workbook.add_format({
        "font_name": "Arial", "font_size": 18, "bold": True,
        "font_color": COLOR_BLANCO, "bg_color": COLOR_PAMPA_NORTE,
        "align": "center", "valign": "vcenter",
    })
    subtitulo = workbook.add_format({
        "font_name": "Arial", "font_size": 10, "italic": True,
        "font_color": "#476475", "align": "center", "valign": "vcenter",
    })
    nota = workbook.add_format({
        "font_name": "Arial", "font_size": 9, "italic": True,
        "font_color": "#7F8F99", "align": "center", "valign": "vcenter",
        "text_wrap": True,
    })
    header_grupo = workbook.add_format({
        **base, "bold": True, "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE, "border_color": "#476475",
    })
    header = workbook.add_format({
        **base, "bold": True, "bg_color": "#D7E1E7",
        "border_color": "#476475", "text_wrap": True,
    })
    texto = workbook.add_format(base)
    fecha_fmt = workbook.add_format({**base, "num_format": "dd-mm-yyyy"})
    numero_fmt = workbook.add_format({**base, "num_format": "#,##0.0"})
    porcentaje_fmt = workbook.add_format({**base, "num_format": "0.00%"})
    curva_fmt = workbook.add_format({**base, "num_format": '0.00 "%"'})

    last_col = len(columnas) - 1
    worksheet.merge_range(
        0, 0, 1, last_col, "Curva Granulométrica - Torres de Muestreo", titulo
    )
    worksheet.merge_range(
        2, 0, 2, last_col, texto_periodo, subtitulo,
    )
    worksheet.merge_range(
        3, 0, 4, last_col,
        "Curva observada ponderada por tonelaje real de cada torre. Las torres "
        "sin ensayo granulométrico no participan de la ponderación. La "
        "representatividad física se presenta como información diagnóstica y no "
        "como filtro de esta curva. La estructura conserva todas las fracciones "
        "del formato oficial; en los archivos basales actuales, las fracciones "
        "posteriores a #100 corresponden al cierre del formato granulométrico.",
        nota,
    )
    worksheet.merge_range(6, 0, 6, 1, "IDENTIFICACIÓN", header_grupo)
    worksheet.merge_range(6, 2, 6, 3, "MASA", header_grupo)
    worksheet.merge_range(6, 4, 6, 5, "REPRESENTATIVIDAD FÍSICA", header_grupo)
    worksheet.merge_range(6, 6, 6, 8, "TRAZABILIDAD", header_grupo)
    worksheet.merge_range(
        6, 9, 6, last_col, "PASANTE ACUMULADO (%)", header_grupo
    )
    etiquetas = {
        "Torres_Utilizadas": "Torres utilizadas", "Ton_TM1": "Ton TM1",
        "Ton_TM2": "Ton TM2", "Rep_Fisica_TM1": "Rep TM1",
        "Rep_Fisica_TM2": "Rep TM2",
        "Tiene_Curva_TM1": "Curva TM1", "Tiene_Curva_TM2": "Curva TM2",
        "P2": "2\"", "P1": "1\"", "P34": "3/4\"", "P12": "1/2\"",
        "P14": "1/4\"", "P10": "#10", "P35": "#35", "P100": "#100",
        "P150": "#150", "P200": "#200", "P325": "#325",
        "PBajo325": "-#325",
    }
    for col_idx, columna in enumerate(columnas):
        worksheet.write(7, col_idx, etiquetas.get(columna, columna), header)

    curva_cols = set(columnas[9:])
    for row_idx, fila in enumerate(df_export.itertuples(index=False, name=None), start=8):
        for col_idx, (columna, valor) in enumerate(zip(columnas, fila)):
            if pd.isna(valor):
                worksheet.write_blank(row_idx, col_idx, None, texto)
            elif columna == "Fecha":
                worksheet.write_datetime(
                    row_idx, col_idx, pd.Timestamp(valor).to_pydatetime(), fecha_fmt
                )
            elif columna in {"Ton_TM1", "Ton_TM2"}:
                worksheet.write_number(row_idx, col_idx, float(valor), numero_fmt)
            elif columna in {"Rep_Fisica_TM1", "Rep_Fisica_TM2"}:
                worksheet.write_number(row_idx, col_idx, float(valor), porcentaje_fmt)
            elif columna in {"Tiene_Curva_TM1", "Tiene_Curva_TM2"}:
                worksheet.write(row_idx, col_idx, "Sí" if int(valor) == 1 else "No", texto)
            elif columna in curva_cols:
                worksheet.write_number(row_idx, col_idx, float(valor), curva_fmt)
            else:
                worksheet.write(row_idx, col_idx, valor, texto)

    worksheet.set_column(0, 0, 12)
    worksheet.set_column(1, 1, 8)
    worksheet.set_column(2, 5, 12)
    worksheet.set_column(6, 7, 11)
    worksheet.set_column(8, 8, 17)
    worksheet.set_column(9, last_col, 10)
    worksheet.set_row(0, 24)
    worksheet.set_row(3, 22)
    worksheet.set_row(4, 22)
    worksheet.set_row(6, 22)
    worksheet.set_row(7, 32)
    worksheet.freeze_panes(8, 2)
    if not df_export.empty:
        worksheet.autofilter(7, 0, 7 + len(df_export), last_col)
    worksheet.hide_gridlines(2)
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)


def agregar_hoja_clays_cufe(
    writer: pd.ExcelWriter,
    df_clays_cufe: pd.DataFrame,
) -> None:
    """Agrega la hoja visual Clays-CuFe sin mutar ni recalcular sus datos."""
    df_export = df_clays_cufe.copy()
    columnas = [
        "Identificador", "Muestra", "Caolinita", "Qz", "CaolBeta", "CuFe",
        "Fuente CaolBeta", "Fuente CuFe",
    ]

    if not df_export.empty:
        df_export["Fecha"] = pd.to_datetime(df_export["Fecha"], errors="coerce")
        df_export["Torre"] = df_export["Torre"].astype("string").str.upper()
        df_export["Turno"] = df_export["Turno"].astype("string").str.upper()
        torre_num = df_export["Torre"].map({"TM1": 1, "TM2": 2})
        turno_excel = df_export["Turno"].map({"A": "TA", "B": "TB"})
        df_export["Identificador"] = (
            df_export["Fecha"].dt.strftime("%d-%m-%Y")
            + " TORRE N°" + torre_num.astype("Int64").astype("string")
            + " " + turno_excel
        )
        df_export["Muestra"] = (
            "TM-" + torre_num.astype("Int64").astype("string")
            + "_" + df_export["Fecha"].dt.strftime("%d-%m-%y")
            + "-" + turno_excel
        )
        df_export["Caolinita"] = np.nan
        df_export["Qz"] = np.nan
        df_export["Fuente CaolBeta"] = df_export.get("Fuente_CaolBeta")
        df_export["Fuente CuFe"] = df_export.get("Fuente_CuFe")
        df_export["_torre_orden"] = torre_num
        df_export["_turno_orden"] = df_export["Turno"].map({"A": 1, "B": 2})
        df_export = df_export.sort_values(
            ["Fecha", "_torre_orden", "_turno_orden"], kind="stable"
        )[columnas]
    else:
        df_export = pd.DataFrame(columns=columnas)

    workbook = writer.book
    worksheet = workbook.add_worksheet("Clays-CuFe")
    writer.sheets["Clays-CuFe"] = worksheet
    base = {
        "font_name": "Calibri", "font_size": 10, "align": "center",
        "valign": "vcenter", "border": 1, "border_color": COLOR_BORDE,
    }
    fmt_titulo = workbook.add_format({
        "bold": True, "font_name": "Arial", "font_size": 18,
        "font_color": COLOR_BLANCO, "bg_color": COLOR_PAMPA_NORTE,
        "align": "center", "valign": "vcenter",
    })
    fmt_header = workbook.add_format({
        **base, "bold": True, "font_size": 11, "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE, "text_wrap": True,
    })
    fmt_texto = workbook.add_format(base)
    fmt_num_2 = workbook.add_format({**base, "num_format": "0.00"})
    fmt_num_4 = workbook.add_format({**base, "num_format": "0.0000"})
    colores = {"IMP": COLOR_IMP, "MB": COLOR_MB, "TM2": COLOR_TM2, "TM1": COLOR_TM1}
    formatos_caol = {
        fuente: workbook.add_format({**base, "num_format": "0.00", "bg_color": color})
        for fuente, color in colores.items()
    }
    formatos_cufe = {
        fuente: workbook.add_format({**base, "num_format": "0.0000", "bg_color": color})
        for fuente, color in colores.items()
    }

    worksheet.merge_range("A1:H2", "Clays-CuFe", fmt_titulo)
    for col_idx, nombre in enumerate(columnas):
        worksheet.write(3, col_idx, nombre, fmt_header)

    for row_idx, (_, row) in enumerate(df_export.iterrows(), start=4):
        for col_idx, nombre in enumerate(columnas):
            valor = row[nombre]
            if pd.isna(valor):
                worksheet.write_blank(row_idx, col_idx, None, fmt_texto)
            elif nombre == "CaolBeta":
                worksheet.write_number(
                    row_idx, col_idx, float(valor),
                    formatos_caol.get(row["Fuente CaolBeta"], fmt_num_2),
                )
            elif nombre == "CuFe":
                worksheet.write_number(
                    row_idx, col_idx, float(valor),
                    formatos_cufe.get(row["Fuente CuFe"], fmt_num_4),
                )
            else:
                worksheet.write(row_idx, col_idx, valor, fmt_texto)

    worksheet.write("J2", "Fuente", fmt_header)
    descripciones = {
        "IMP": "Fuente provisional IMP", "MB": "Modelo de Bloque",
        "TM2": "Torre de Muestreo 2", "TM1": "Torre de Muestreo 1",
    }
    for fila, fuente in enumerate(("IMP", "MB", "TM2", "TM1"), start=2):
        fmt_leyenda = workbook.add_format({**base, "bg_color": colores[fuente]})
        worksheet.write(fila, 9, fuente, fmt_leyenda)
        worksheet.write(fila, 10, descripciones[fuente], fmt_texto)

    worksheet.set_column("A:A", 27)
    worksheet.set_column("B:B", 21)
    worksheet.set_column("C:D", 11)
    worksheet.set_column("E:F", 12)
    worksheet.set_column("G:H", 18)
    worksheet.set_column("I:I", 3)
    worksheet.set_column("J:J", 10)
    worksheet.set_column("K:K", 25)
    worksheet.set_row(0, 24)
    worksheet.set_row(3, 32)
    worksheet.freeze_panes(4, 0)
    if not df_export.empty:
        worksheet.autofilter(3, 0, 3 + len(df_export), len(columnas) - 1)
    worksheet.hide_gridlines(2)
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)


def agregar_hoja_trazabilidad_analitos(
    writer: pd.ExcelWriter,
    df_trazabilidad_analitos: pd.DataFrame,
    df_cobertura_operacional: pd.DataFrame = None,
) -> None:
    """Agrega trazabilidad real y completa solo turnos no evaluables en Excel."""
    df_export = df_trazabilidad_analitos.copy()
    analitos = [
        "CuT", "CuS", "FeT", "FeS", "CO3", "ConsH", "CuFe", "CaolBeta",
        "Malla_Menos_1_2", "Malla_Menos_100",
    ]
    etiquetas = {
        "Malla_Menos_1_2": "Malla -1/2",
        "Malla_Menos_100": "Malla -100",
    }
    quimicos = set(analitos[:8])
    fisicos = set(analitos[8:])
    claves = ["Fecha", "Turno", "TM_Destino"]

    if df_export.empty:
        ancho = pd.DataFrame(columns=claves)
    else:
        df_export["Fecha"] = pd.to_datetime(df_export["Fecha"], errors="coerce")
        if "Apilado_TMS_Real" in df_export.columns:
            evaluable = pd.to_numeric(
                df_export["Apilado_TMS_Real"], errors="coerce"
            ).gt(0)
        else:
            evaluable = pd.Series(True, index=df_export.index)
        df_visible = df_export.copy()
        df_visible["Estado"] = evaluable.map(
            {True: "EVALUABLE", False: "NO EVALUABLE"}
        )
        no_evaluable = ~evaluable
        df_visible.loc[no_evaluable, [
            "Valor_Final", "Fuente_Base", "Representatividad_Quimica",
            "Representatividad_Fisica",
        ]] = pd.NA

        valores = df_visible.pivot(index=claves, columns="Analito", values="Valor_Final")
        fuentes = df_visible.pivot(index=claves, columns="Analito", values="Fuente_Base")
        reps = df_visible.groupby(claves, as_index=True)[
            ["Estado", "Representatividad_Quimica", "Representatividad_Fisica"]
        ].first()
        ancho = reps.reset_index()
        for analito in analitos:
            etiqueta = etiquetas.get(analito, analito)
            serie_valor = (
                valores[analito] if analito in valores.columns
                else pd.Series(index=valores.index, dtype="float64")
            )
            serie_fuente = (
                fuentes[analito] if analito in fuentes.columns
                else pd.Series(index=fuentes.index, dtype="object")
            )
            ancho[etiqueta] = serie_valor.reindex(valores.index).values
            fuente = serie_fuente.reindex(fuentes.index).values
            ancho[f"Fuente {etiqueta}"] = pd.Series(fuente).fillna("-").values

        orden_fuentes = ["TM1", "TM2", "MB", "IMP"]
        def _resumen_turno(grupo, conjunto):
            presentes = set(
                grupo.loc[grupo["Analito"].isin(conjunto), "Fuente_Base"].dropna()
            )
            return "; ".join(
                {"TM1": "T1", "TM2": "T2"}.get(x, x)
                for x in orden_fuentes if x in presentes
            ) or "-"

        resumen_q = df_visible.groupby(["Fecha", "Turno"]).apply(
            lambda g: _resumen_turno(g, quimicos), include_groups=False
        ).rename("Resumen Químico")
        resumen_f = df_visible.groupby(["Fecha", "Turno"]).apply(
            lambda g: _resumen_turno(g, fisicos), include_groups=False
        ).rename("Resumen Físico")
        ancho = ancho.merge(resumen_q, on=["Fecha", "Turno"], how="left")
        ancho = ancho.merge(resumen_f, on=["Fecha", "Turno"], how="left")
        ancho = ancho.sort_values(
            ["Fecha", "Turno", "TM_Destino"],
            key=lambda s: s.map({"TM1": 1, "TM2": 2, "A": 1, "B": 2})
            if s.name in {"TM_Destino", "Turno"} else s,
            kind="stable",
        )

    if df_cobertura_operacional is not None:
        requeridas = {"Fecha", "Turno", "Apilado_TMS_Real"}
        faltantes = requeridas - set(df_cobertura_operacional.columns)
        if faltantes:
            raise RuntimeError(
                "Cobertura operacional incompleta para Trazabilidad Analitos: "
                + ", ".join(sorted(faltantes))
            )
        cobertura = df_cobertura_operacional[
            ["Fecha", "Turno", "Apilado_TMS_Real"]
        ].copy()
        cobertura["Fecha"] = pd.to_datetime(cobertura["Fecha"], errors="coerce")
        cobertura["Turno"] = cobertura["Turno"].astype("string").str.strip().str.upper()
        cobertura["Apilado_TMS_Real"] = pd.to_numeric(
            cobertura["Apilado_TMS_Real"], errors="coerce"
        )
        if cobertura[["Fecha", "Turno"]].isna().any().any():
            raise RuntimeError("Cobertura operacional contiene Fecha o Turno NULL.")
        conflictos = cobertura.groupby(["Fecha", "Turno"])[
            "Apilado_TMS_Real"
        ].nunique(dropna=False)
        if (conflictos > 1).any():
            raise RuntimeError(
                "Cobertura operacional contiene TMS contradictorio por Fecha + Turno."
            )
        cobertura = cobertura.drop_duplicates(["Fecha", "Turno"])
        claves_trazadas = set()
        if not df_export.empty:
            claves_trazadas = set(zip(df_export["Fecha"], df_export["Turno"]))
        sin_trazabilidad = cobertura.loc[
            ~cobertura.apply(
                lambda r: (r["Fecha"], r["Turno"]) in claves_trazadas,
                axis=1,
            )
        ]
        anomalias = sin_trazabilidad.loc[
            sin_trazabilidad["Apilado_TMS_Real"].isna()
            | sin_trazabilidad["Apilado_TMS_Real"].gt(0)
        ]
        if not anomalias.empty:
            detalle = anomalias[
                ["Fecha", "Turno", "Apilado_TMS_Real"]
            ].to_dict(orient="records")
            raise RuntimeError(
                "ANOMALIA_TRAZABILIDAD: turno con TMS positivo o desconocido "
                f"sin trazabilidad analítica: {detalle}"
            )
        filas_no_evaluables = []
        for fila in sin_trazabilidad.loc[
            sin_trazabilidad["Apilado_TMS_Real"].le(0)
        ].itertuples(index=False):
            for tm in ("TM1", "TM2"):
                nueva = {
                    "Fecha": fila.Fecha, "Turno": fila.Turno,
                    "TM_Destino": tm, "Estado": "NO EVALUABLE",
                    "Representatividad_Quimica": pd.NA,
                    "Representatividad_Fisica": pd.NA,
                    "Resumen Químico": "-", "Resumen Físico": "-",
                }
                for analito in analitos:
                    etiqueta = etiquetas.get(analito, analito)
                    nueva[etiqueta] = pd.NA
                    nueva[f"Fuente {etiqueta}"] = "-"
                filas_no_evaluables.append(nueva)
        if filas_no_evaluables:
            nuevas_filas = pd.DataFrame(filas_no_evaluables)
            if ancho.empty:
                ancho = nuevas_filas
            else:
                ancho = pd.DataFrame.from_records(
                    ancho.to_dict(orient="records") + filas_no_evaluables
                )

    if not ancho.empty:
        ancho = ancho.sort_values(
            ["Fecha", "Turno", "TM_Destino"],
            key=lambda s: s.map({"TM1": 1, "TM2": 2, "A": 1, "B": 2})
            if s.name in {"TM_Destino", "Turno"} else s,
            kind="stable",
        )

    columnas = ["Fecha", "Turno", "TM_Destino", "Estado",
        "Representatividad_Quimica", "Representatividad_Fisica"]
    for analito in analitos:
        etiqueta = etiquetas.get(analito, analito)
        columnas.extend([etiqueta, f"Fuente {etiqueta}"])
    columnas.extend(["Resumen Químico", "Resumen Físico"])
    ancho = ancho.reindex(columns=columnas)

    workbook = writer.book
    worksheet = workbook.add_worksheet("Trazabilidad Analitos")
    writer.sheets["Trazabilidad Analitos"] = worksheet
    base = {"font_name": "Arial", "font_size": 9, "font_color": "#476475",
            "align": "center", "valign": "vcenter", "border": 1,
            "border_color": "#A6A6A6"}
    titulo = workbook.add_format({"font_name": "Arial", "font_size": 18,
        "bold": True, "font_color": COLOR_BLANCO, "bg_color": COLOR_PAMPA_NORTE,
        "align": "center", "valign": "vcenter"})
    subtitulo = workbook.add_format({"font_name": "Arial", "font_size": 11,
        "italic": True, "font_color": "#476475", "align": "center"})
    nota = workbook.add_format({"font_name": "Arial", "font_size": 8,
        "italic": True, "font_color": "#7F8F99", "align": "center",
        "valign": "vcenter"})
    header_grupo = workbook.add_format({**base, "bold": True,
        "font_color": COLOR_BLANCO, "bg_color": COLOR_PAMPA_NORTE,
        "text_wrap": True, "border_color": "#476475"})
    header_analito = workbook.add_format({**base, "bold": True,
        "bg_color": "#D7E1E7", "text_wrap": True,
        "border_color": "#476475"})
    header_campo = workbook.add_format({**base, "bold": True,
        "bg_color": "#EAF0F3", "text_wrap": True,
        "border_color": "#476475"})
    colores = {"TM1": COLOR_TM1, "TM2": COLOR_TM2, "MB": COLOR_MB, "IMP": COLOR_IMP}
    cache_formatos = {}

    def _formato_cuerpo(
        tipo, alterno=False, fin_grupo=False, fuente=None,
        no_evaluable=False,
    ):
        clave = (tipo, alterno, fin_grupo, fuente, no_evaluable)
        if clave in cache_formatos:
            return cache_formatos[clave]
        cfg = dict(base)
        cfg["bg_color"] = "#F5F8FA" if alterno else "#FFFFFF"
        if fin_grupo:
            cfg["bottom"] = 2
            cfg["bottom_color"] = "#476475"
        if tipo == "fecha":
            cfg["num_format"] = "dd-mm-yyyy"
        elif tipo == "valor4":
            cfg.update({"num_format": "0.0000", "align": "right"})
        elif tipo == "valor2":
            cfg.update({"num_format": "0.00", "align": "right"})
        elif tipo == "rep":
            cfg["num_format"] = "0.0%"
        elif tipo == "rep_ok":
            cfg.update({"num_format": "0.0%", "bg_color": "#E2F0D9", "bold": True})
        elif tipo == "rep_baja":
            cfg.update({"num_format": "0.0%", "bg_color": "#FCE4D6", "bold": True})
        elif tipo == "torre":
            cfg.update({"bg_color": "#EAF0F3", "bold": True,
                        "left": 2, "left_color": "#476475"})
        elif tipo == "fuente" and fuente in colores:
            cfg.update({"bg_color": colores[fuente], "bold": True})
            if fuente == "IMP":
                cfg["font_color"] = COLOR_BLANCO
        elif tipo == "resumen":
            cfg.update({"bold": True, "left": 2, "left_color": "#476475"})
        if no_evaluable:
            cfg.update({"bg_color": "#E7E6E6", "font_color": "#7F7F7F"})
        cache_formatos[clave] = workbook.add_format(cfg)
        return cache_formatos[clave]

    last_col = len(columnas) - 1
    worksheet.merge_range(0, 0, 1, last_col, "Trazabilidad de Analitos", titulo)
    worksheet.merge_range(2, 0, 2, last_col,
        "Origen final de información por Torre, Turno y Analito", subtitulo)
    worksheet.merge_range(3, 0, 3, last_col,
        "Los valores corresponden a la resolución final por torre antes de "
        "la ponderación por TMS del turno.", nota)

    worksheet.merge_range(4, 0, 4, 5, "IDENTIFICACIÓN", header_grupo)
    worksheet.merge_range(4, 6, 4, 21, "QUÍMICA", header_grupo)
    worksheet.merge_range(4, 22, 4, 25, "FÍSICA", header_grupo)
    worksheet.merge_range(4, 26, 4, 27, "RESUMEN", header_grupo)
    identificadores = ["Fecha", "Turno", "Torre", "Estado Operacional",
                       "Rep. Química", "Rep. Física"]
    for c, nombre in enumerate(identificadores):
        worksheet.write_blank(5, c, None, header_analito)
        worksheet.write(6, c, nombre, header_campo)
    for idx, analito in enumerate(analitos):
        etiqueta = etiquetas.get(analito, analito)
        inicio = 6 + idx * 2
        worksheet.merge_range(5, inicio, 5, inicio + 1, etiqueta, header_analito)
        worksheet.write(6, inicio, "Valor", header_campo)
        worksheet.write(6, inicio + 1, "Fuente", header_campo)
    for c, nombre in (
        (26, "Fuentes Químicas Turno"),
        (27, "Fuentes Físicas Turno"),
    ):
        worksheet.write_blank(5, c, None, header_analito)
        worksheet.write(6, c, nombre, header_campo)

    detalles = {}
    if not df_export.empty:
        detalles = {
            (r.Fecha, r.Turno, r.TM_Destino, r.Analito): r
            for r in df_export.itertuples(index=False)
        }
    filas_ancho = list(ancho.itertuples(index=False, name=None))
    grupos = []
    for row in filas_ancho:
        row_map = dict(zip(columnas, row))
        clave = (row_map["Fecha"], row_map["Turno"])
        if not grupos or grupos[-1] != clave:
            grupos.append(clave)
    orden_grupo = {clave: idx for idx, clave in enumerate(grupos)}

    for pos, row in enumerate(filas_ancho):
        r_idx = 7 + pos
        row_map = dict(zip(columnas, row))
        clave_grupo = (row_map["Fecha"], row_map["Turno"])
        alterno = bool(orden_grupo[clave_grupo] % 2)
        siguiente = filas_ancho[pos + 1] if pos + 1 < len(filas_ancho) else None
        if siguiente is None:
            fin_grupo = True
        else:
            siguiente_map = dict(zip(columnas, siguiente))
            fin_grupo = clave_grupo != (
                siguiente_map["Fecha"], siguiente_map["Turno"]
            )
        no_evaluable_fila = row_map.get("Estado") == "NO EVALUABLE"
        for c_idx, col in enumerate(columnas):
            value = row_map[col]
            if no_evaluable_fila:
                if col == "Fecha":
                    tipo_no_evaluable = "fecha"
                elif col.startswith("Representatividad"):
                    tipo_no_evaluable = "rep"
                elif col in {"ConsH", "CaolBeta", "Malla -1/2", "Malla -100"}:
                    tipo_no_evaluable = "valor2"
                elif col in analitos or col in set(etiquetas.values()):
                    tipo_no_evaluable = "valor4"
                else:
                    tipo_no_evaluable = "texto"
                fmt = _formato_cuerpo(
                    tipo_no_evaluable, alterno, fin_grupo,
                    no_evaluable=True,
                )
            elif col == "Fecha":
                fmt = _formato_cuerpo("fecha", alterno, fin_grupo)
            elif col == "TM_Destino":
                fmt = _formato_cuerpo("torre", alterno, fin_grupo)
            elif col.startswith("Representatividad"):
                if pd.isna(value):
                    fmt = _formato_cuerpo("rep", alterno, fin_grupo)
                else:
                    tipo_rep = "rep_ok" if float(value) >= 0.75 else "rep_baja"
                    fmt = _formato_cuerpo(tipo_rep, alterno, fin_grupo)
            elif col.startswith("Fuente "):
                fmt = _formato_cuerpo("fuente", alterno, fin_grupo, value)
            elif col.startswith("Resumen "):
                fmt = _formato_cuerpo("resumen", alterno, fin_grupo)
            elif col in {"ConsH", "CaolBeta", "Malla -1/2", "Malla -100"}:
                fmt = _formato_cuerpo("valor2", alterno, fin_grupo)
            elif col in analitos or col in set(etiquetas.values()):
                fmt = _formato_cuerpo("valor4", alterno, fin_grupo)
            else:
                fmt = _formato_cuerpo("texto", alterno, fin_grupo)
            if pd.isna(value):
                worksheet.write_blank(r_idx, c_idx, None, fmt)
            elif col == "Fecha":
                worksheet.write_datetime(r_idx, c_idx, pd.Timestamp(value).to_pydatetime(), fmt)
            elif col.startswith("Representatividad"):
                worksheet.write_number(r_idx, c_idx, float(value), fmt)
            elif col.startswith("Fuente "):
                worksheet.write(r_idx, c_idx, value, fmt)
            elif col in {"Turno", "TM_Destino", "Estado", "Resumen Químico", "Resumen Físico"}:
                valor_visible = value
                if col in {"Resumen Químico", "Resumen Físico"}:
                    valor_visible = "; ".join(
                        {"T1": "TM1", "T2": "TM2"}.get(parte.strip(), parte.strip())
                        for parte in str(value).split(";")
                    )
                worksheet.write(r_idx, c_idx, valor_visible, fmt)
            else:
                worksheet.write_number(r_idx, c_idx, float(value), fmt)
                analito_db = next((k for k, v in etiquetas.items() if v == col), col)
                d = detalles.get((pd.Timestamp(row_map["Fecha"]), row_map["Turno"], row_map["TM_Destino"], analito_db))
                if d is not None:
                    worksheet.write_comment(r_idx, c_idx,
                        f"Fuente técnica: {d.Fuente_Tecnica or '-'}\n"
                        f"Resolución: {d.Resolucion or '-'}\n"
                        f"Origen: {d.Fecha_Origen or '-'} / {d.Turno_Origen or '-'} / {d.TM_Origen or '-'}")

    worksheet.set_column(0, 0, 12)
    worksheet.set_column(1, 2, 7)
    worksheet.set_column(3, 3, 14)
    worksheet.set_column(4, 5, 12)
    for idx in range(len(analitos)):
        inicio = 6 + idx * 2
        worksheet.set_column(inicio, inicio, 10)
        worksheet.set_column(inicio + 1, inicio + 1, 9)
    worksheet.set_column(26, 27, 14)
    worksheet.set_row(0, 24)
    worksheet.set_row(4, 22)
    worksheet.set_row(5, 24)
    worksheet.set_row(6, 32)
    for r_idx in range(7, 7 + len(filas_ancho)):
        worksheet.set_row(r_idx, 19)
    worksheet.freeze_panes(7, 6)
    if not ancho.empty:
        worksheet.autofilter(6, 0, 6 + len(ancho), last_col)
    legend_col = last_col + 2
    worksheet.write(4, legend_col, "Fuente", header_grupo)
    descripciones = {"TM1": "Torre de Muestreo 1", "TM2": "Torre de Muestreo 2",
        "MB": "Modelo de Bloque / fuente oficial mina", "IMP": "Fuente provisional IMP"}
    for offset, fuente in enumerate(("TM1", "TM2", "MB", "IMP"), start=5):
        worksheet.write(offset, legend_col, fuente,
            _formato_cuerpo("fuente", False, False, fuente))
        worksheet.write(offset, legend_col + 1, descripciones[fuente],
            _formato_cuerpo("texto"))
    worksheet.write(10, legend_col, "Rep.", header_grupo)
    worksheet.write(11, legend_col, ">=75 %", _formato_cuerpo("rep_ok"))
    worksheet.write(11, legend_col + 1, "Representativo",
        _formato_cuerpo("texto"))
    worksheet.write(12, legend_col, "<75 %", _formato_cuerpo("rep_baja"))
    worksheet.write(12, legend_col + 1, "No representativo",
        _formato_cuerpo("texto"))
    worksheet.set_column(legend_col, legend_col, 10)
    worksheet.set_column(legend_col + 1, legend_col + 1, 34)
    worksheet.hide_gridlines(2)
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)


def _calcular_tmh_reconst_srr(df: pd.DataFrame) -> pd.DataFrame:
    """TMH neto por turno: total publicado, TM2 con factor/sal y TM1 residual.

    Solo consume insumos independientes de SRR; no modifica Datos Conciliados.
    """
    datos = df.copy()
    columnas = ["TMH_Total_Conciliado", "TMH_CV008", "TMH_CV108",
                "Sal_Turno", "Factor_Aplicacion_Reportes"]
    faltantes = sorted(set(columnas) - set(datos.columns))
    if faltantes:
        raise ValueError(f"Reconst Mod SRR: faltan insumos TMH {faltantes}.")
    insumos = datos[columnas].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(insumos.to_numpy(dtype=float)).all():
        raise ValueError("Reconst Mod SRR: insumos TMH incompletos o no finitos.")
    bruto = insumos["TMH_CV008"] + insumos["TMH_CV108"]
    sin_bruto = bruto.eq(0)
    if (sin_bruto & (insumos["Sal_Turno"].ne(0) | insumos["TMH_Total_Conciliado"].ne(0))).any():
        raise ValueError("Reconst Mod SRR: total bruto TMH cero con sal o total conciliado distinto de cero.")
    # Sin actividad y sin sal, la asignación TM2 es cero; no divide por cero.
    sal_tm2 = pd.Series(0.0, index=datos.index)
    activos = ~sin_bruto
    sal_tm2.loc[activos] = (
        insumos.loc[activos, "Sal_Turno"] * insumos.loc[activos, "TMH_CV108"]
        / bruto.loc[activos]
    )
    datos["TMH_TM2_Final"] = insumos["TMH_CV108"] * insumos["Factor_Aplicacion_Reportes"] - sal_tm2
    # Metodología validada: TM1 = total AUTORITATIVO de Datos Conciliados - TM2.
    datos["TMH_TM1_Final"] = insumos["TMH_Total_Conciliado"] - datos["TMH_TM2_Final"]
    diferencia = datos["TMH_TM1_Final"] + datos["TMH_TM2_Final"] - insumos["TMH_Total_Conciliado"]
    if not np.isfinite(diferencia).all() or diferencia.abs().gt(0.001).any():
        raise ValueError("Reconst Mod SRR: cuadratura TM1 + TM2 difiere del total en más de 0.001 TMH.")
    return datos


def _agregar_hoja_reconst_mod_srr(wb, df_reconst_srr, df_turno=None):
    """Agrega únicamente la hoja SRR al workbook XlsxWriter del exportador.

    Una fila por fecha; leyes SQL por turno, MB una vez al día. Las fuentes
    auxiliares se copian y nunca se incorporan a los DataFrames productivos.
    """
    datos = _normalizar_claves_reconst_srr(df_reconst_srr)
    columnas_mb = ["CuT_MinaStock", "CuS_MinaStock", "ClayBeta_MinaStock",
                   "Malla100_MinaStock", "CO3_MinaStock"]
    columnas_requeridas = columnas_mb + [
        "SRR_TMS_Dia", "SRR_TMS_Turno", "CuT_SRR", "CuS_SRR",
        "ClayBeta_SRR", "Malla100_SRR", "CO3_SRR", "Recuperacion_SRR",
    ]
    faltantes = sorted(set(columnas_requeridas) - set(datos.columns))
    if faltantes:
        raise ValueError(f"Reconst Mod SRR: faltan columnas SQL {faltantes}.")
    # El LEFT JOIN diario debe entregar el mismo bloque MB para A/B.
    columnas_diarias = columnas_mb + ["SRR_TMS_Dia"]
    if (datos.groupby("Fecha")[columnas_diarias].nunique(dropna=False) > 1).any().any():
        raise ValueError("Reconst Mod SRR contiene datos diarios inconsistentes entre A/B.")
    datos = _calcular_tmh_reconst_srr(datos)
    if df_turno is not None and not df_turno.empty:
        origen = _normalizar_claves_reconst_srr(
            df_turno[["Fecha", "Turno", "STOCK", "MINA", "SRR"]].copy()
        )
        datos = datos.merge(origen, on=["Fecha", "Turno"], how="left", validate="one_to_one")

    # El exportador crea un workbook nuevo en cada llamada: la hoja se agrega
    # una sola vez al final, sin reabrir/regrabar ni reordenar las otras hojas.
    ws = wb.add_worksheet("Reconst Mod SRR")
    base = {"font_name": "Calibri", "font_size": 10, "border": 1,
            "border_color": "#808080", "valign": "vcenter"}
    titulo = wb.add_format({"font_name": "Calibri", "font_size": 16,
                            "bold": True, "font_color": "#FFFFFF", "bg_color": "#018982"})
    grupo = wb.add_format(dict(base, bold=True, font_size=12, border=2, font_color="#FFFFFF",
                              bg_color="#018982", align="center", text_wrap=True))
    sub = wb.add_format(dict(base, bold=True, font_size=12, border=2, font_color="#FFFFFF", bg_color="#018982", align="center", text_wrap=True))
    nota = wb.add_format({"font_name": "Calibri", "font_size": 10,
                          "font_color": "#526579", "valign": "vcenter"})
    formatos = {}
    for banda, color in enumerate(("#FFFFFF", "#FFFFFF")):
        for tipo, formato in {"tmh": "#,##0", "ley": "0.00",
                              "fis": "0.00", "origen": "0.00",
                              "fecha": "dd-mm-yyyy", "dia": "0"}.items():
            formatos[banda, tipo] = wb.add_format(dict(
                base, bg_color=color, num_format=formato,
                align="center"))
    ws.hide_gridlines(2)
    ws.set_zoom(100)
    ws.set_column("A:B", 2.5)
    ws.set_column("C:C", 13)
    ws.set_column("D:I", 14)
    ws.set_column("J:K", 3)
    ws.set_column("L:L", 5)
    ws.set_column("M:R", 10)
    ws.set_column("S:T", 15)
    ws.set_column("U:AF", 13)
    ws.set_column("AG:AG", 3)
    ws.set_column("AH:AL", 13)
    ws.merge_range("C2:AL3", "Reconstitución de Módulos SRR", titulo)
    inicio, fin = datos["Fecha"].min(), datos["Fecha"].max()
    ws.merge_range("C4:AL4", f"Período: {inicio:%d-%m-%Y} al {fin:%d-%m-%Y}", nota)
    ws.merge_range("C5:AL5", "Leyes SRR diarias repetidas en A/B; tonelaje individual por turno. Celdas vacías: sin dato de origen.", nota)
    ws.merge_range("C6:AL6", "TMH neto: total de Datos Conciliados; Tambor 2 con factor y descuento proporcional de sal; Tambor 1 por diferencia.", nota)
    ws.set_row(6, 46.5)
    ws.set_row(7, 26.1)
    ws.merge_range("C7:C8", "Fecha", grupo)
    ws.merge_range("L7:L8", "Día", grupo)
    grupos = [(3, "Total Apilado TMH"), (5, "Tambor 1 Apilado TMH"),
              (7, "Tambor 2 Apilado TMH"), (12, "Stock"), (14, "Mina"),
              (16, "SRR"), (18, "Tonelaje SRR (TMS)"), (20, "CuT SRR"),
              (22, "CuS SRR"), (24, "ClayBeta SRR"), (26, "Malla 100 SRR"),
              (28, "CO3 SRR"), (30, "Recuperación SRR")]
    for col, label in grupos:
        ws.merge_range(6, col, 6, col + 1, label, grupo)
        ws.write(7, col, "A", sub)
        ws.write(7, col + 1, "B", sub)
    ws.merge_range("AH7:AL7", "Datos MB Mina + Stock sin SRR", grupo)
    for col, label in enumerate(["CuT", "CuS", "ClayBeta", "Malla 100", "CO3"], 33):
        ws.write(7, col, label, sub)
    ws.write_comment("D7", "Fuente autoritativa: Datos_conciliados_of.Apilado_TMH_turno_A/B. TM2 = CV108 * Factor_Aplicacion_Reportes - Sal_Turno * CV108 / (CV008 + CV108). TM1 = Total - TM2. Correas operacionales: v_datos_apilado_tmh_v2; sal: Datos_conciliados_of; factor: v_ajuste_camiones_emision_test.")
    ws.write_comment("M7", "STOCK, MINA y SRR se copian del Reporte por Turno en su escala original 0–100.")

    campos = [(12, "STOCK", "origen"), (14, "MINA", "origen"), (16, "SRR", "origen"),
              (18, "SRR_TMS_Turno", "tmh"), (20, "CuT_SRR", "ley"),
              (22, "CuS_SRR", "ley"), (24, "ClayBeta_SRR", "fis"),
              (26, "Malla100_SRR", "fis"), (28, "CO3_SRR", "ley"),
              (30, "Recuperacion_SRR", "fis")]
    for row, (fecha, diario) in enumerate(datos.groupby("Fecha", sort=True), 8):
        banda = (row - 8) % 2
        def escribir(col, valor, tipo):
            ws.write(row, col, None if pd.isna(valor) else valor, formatos[banda, tipo])

        ws.set_row(row, 19)
        escribir(2, fecha.to_pydatetime(), "fecha")
        escribir(11, fecha.day, "dia")
        turnos = diario.set_index("Turno").to_dict("index")
        for offset, turno in enumerate(("A", "B")):
            registro = turnos.get(turno, {})
            for col, campo in ((3, "TMH_Total_Conciliado"), (5, "TMH_TM1_Final"), (7, "TMH_TM2_Final")):
                escribir(col + offset, registro.get(campo), "tmh")
            for col, campo, tipo in campos:
                escribir(col + offset, registro.get(campo), tipo)
        for col, campo in enumerate(columnas_mb, 33):
            escribir(col, diario.iloc[0][campo], "fis" if col in (35, 36) else "ley")
    ws.set_landscape()
    ws.set_paper(8)  # A3
    ws.fit_to_pages(1, 0)
    ws.repeat_rows(6, 7)
    ws.print_area(1, 2, 7 + datos["Fecha"].nunique(), 37)
    ws.set_margins(0.35, 0.35, 0.35, 0.35)


def export_reporte_turno_estilo_leyes_finos(
    df: pd.DataFrame,
    output,
    df_generador: pd.DataFrame = None,
    df_generador_resumen: pd.DataFrame = None,
    df_clays_cufe: pd.DataFrame = None,
    df_trazabilidad_analitos: pd.DataFrame = None,
    df_curva_granulometrica: pd.DataFrame = None,
    periodo_inicio: date = None,
    periodo_fin: date = None,
    df_reconst_srr: pd.DataFrame = None,
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

    df_turno_reconst = df.copy() if df_reconst_srr is not None and not df_reconst_srr.empty else None
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
        # FORMATOS
        # ============================================================
        fmt_titulo = workbook.add_format({
            "bold": True,
            "font_name": "Arial",
            "font_size": 18,
            "font_color": COLOR_BLANCO,
            "bg_color": COLOR_PAMPA_NORTE,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_subtitulo = workbook.add_format({
        "bold": True,
        "font_name": "Arial",
        "font_size": 18,
        "font_color": COLOR_BLANCO,
        "bg_color": COLOR_PAMPA_NORTE,
        "align": "center",
        "valign": "vcenter"
        })

        fmt_grupo = workbook.add_format({
            "bold": True,
            "font_name": "Calibri",
            "font_size": 16,
            "font_color": COLOR_BLANCO,
            "align": "center",
            "valign": "vcenter",
            "bg_color": COLOR_PAMPA_NORTE,
            "border": 2,
            "border_color": COLOR_BORDE,
            "text_wrap": True
        })

        fmt_header = workbook.add_format({
            "bold": True,
            "font_name": "Calibri",
            "font_size": 12,
            "align": "center",
            "valign": "vcenter",
            "bg_color": COLOR_PAMPA_NORTE,
            "font_color": COLOR_BLANCO,
            "border": 2,
            "border_color": COLOR_BORDE,
            "text_wrap": True
        })

        fmt_header_claro = workbook.add_format({
            "bold": True,
            "font_name": "Calibri",
            "font_size": 12,
            "align": "center",
            "valign": "vcenter",
            "bg_color": COLOR_PAMPA_NORTE,
            "font_color": COLOR_BLANCO,
            "border": 2,
            "border_color": COLOR_BORDE,
            "text_wrap": True
        })

        fmt_texto = workbook.add_format({
            "font_name": "Calibri",
            "font_size": 10,
            "border": 1,
            "border_color": COLOR_BORDE,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True
        })

        fmt_texto_gris = workbook.add_format({
            "font_name": "Calibri",
            "font_size": 10,
            "font_color": COLOR_BLANCO,
            "bg_color": COLOR_PAMPA_NORTE,
            "border": 2,
            "border_color": COLOR_BORDE,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True
        })

        fmt_fecha = workbook.add_format({
            "font_name": "Calibri",
            "font_size": 10,
            "font_color": COLOR_BLANCO,
            "bg_color": COLOR_PAMPA_NORTE,
            "num_format": "dd-mm-yyyy",
            "border": 2,
            "border_color": COLOR_BORDE,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_numero = workbook.add_format({
            "font_name": "Calibri",
            "font_size": 10,
            "num_format": "#,##0",
            "border": 1,
            "border_color": COLOR_BORDE,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_num_2 = workbook.add_format({
            "font_name": "Calibri",
            "font_size": 10,
            "num_format": "0.00",
            "border": 1,
            "border_color": COLOR_BORDE,
            "align": "center",
            "valign": "vcenter",
        })

        fmt_decimal = workbook.add_format({
            "font_name": "Calibri",
            "font_size": 10,
            "num_format": "0.00",
            "border": 1,
            "border_color": COLOR_BORDE,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_decimal_gris = workbook.add_format({
            "font_name": "Calibri",
            "font_size": 10,
            "font_color": COLOR_BLANCO,
            "bg_color": COLOR_PAMPA_NORTE,
            "num_format": "0.00",
            "border": 2,
            "border_color": COLOR_BORDE,
            "align": "center",
            "valign": "vcenter",
        })

        fmt_porcentaje = workbook.add_format({
            "font_name": "Calibri",
            "font_size": 10,
            "num_format": "0.00",
            "border": 1,
            "border_color": COLOR_BORDE,
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
        _agregar_encabezado_institucional_torre(
            worksheet,
            fmt_titulo,
            fmt_subtitulo,
            con_turno=True,
        )
        _agregar_cuadro_formula_dosis_acido(workbook, worksheet)

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

        worksheet.merge_range("T21:V21", "Solubilidad %", fmt_header)
        worksheet.write("T22", "Real", fmt_header)
        worksheet.write("U22", "Programa", fmt_header)
        worksheet.write("V22", "Plan", fmt_header)

        worksheet.merge_range("W21:Y21", "CO3 (%)", fmt_header)
        worksheet.write("W22", "Real", fmt_header)
        worksheet.write("X22", "Programa", fmt_header)
        worksheet.write("Y22", "Plan", fmt_header)

        worksheet.write("Z21", "CuFe", fmt_header)
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
            "Campania",
            "Modulo",
            "Apilado_TMS_Real",
            "Apilado_TMS_Plan_Mensual",
        ]

        columnas_porcentaje = [
            "STOCK",
            "MINA",
            "SRR",
        ]

        columnas_grises = [
            "Fecha",
        ]

        def formato_columna(col_name):
            if col_name == "Fecha":
                return fmt_fecha
            if col_name == "Avance":
                return fmt_decimal
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
                    escribir_valor(excel_row, excel_col, col_name, value, fmt_decimal)
                elif col_name in columnas_grises:
                    escribir_valor(excel_row, excel_col, col_name, value, fmt_texto_gris)
                else:
                    escribir_valor(excel_row, excel_col, col_name, value)

        # ============================================================
        # FORMATO GENERAL
        # ============================================================
        _aplicar_dimensiones_oficiales_torre(worksheet, con_turno=True)

        worksheet.set_row(17, 14.7)
        worksheet.set_row(18, 21)
        worksheet.set_row(19, 21.75)
        worksheet.set_row(20, 46.5)
        worksheet.set_row(21, 26.1)

        # Alto de filas de datos
        for r in range(fila_data, fila_data + len(df_export)):
            worksheet.set_row(r, 15)

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
        worksheet.set_paper(8)
        worksheet.fit_to_pages(1, 0)

        # Definir área de impresión considerando logo + tabla
        worksheet.print_area(0, 0, last_row + 2, max(last_col + 1, 41))

        _agregar_marco_exterior_torre(
            workbook,
            worksheet,
            last_row,
            last_col,
        )
        # Ocultar líneas de cuadrícula para parecer más plantilla
        worksheet.hide_gridlines(2)

        # ============================================================
        # SEGUNDA HOJA: GENERADOR REPORTE
        # ============================================================
        if df_generador is not None:
            agregar_hoja_generador_reporte(
                writer=writer,
                df_diario=df_generador,
                df_turno_resumen=df_export,
                df_diario_resumen=df_generador_resumen,
            )
            agregar_hoja_malla_100(
                writer=writer,
                df_diario=df_generador,
            )
        if df_curva_granulometrica is not None:
            agregar_hoja_curva_granulometrica(
                writer=writer,
                df_curva_granulometrica=df_curva_granulometrica,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
            )
        if df_clays_cufe is not None:
            agregar_hoja_clays_cufe(
                writer=writer,
                df_clays_cufe=df_clays_cufe,
            )
        if df_trazabilidad_analitos is not None:
            cobertura_operacional = None
            columnas_cobertura = {"Fecha", "Turno", "Apilado_TMS_Real"}
            if columnas_cobertura.issubset(df.columns):
                cobertura_operacional = df[list(columnas_cobertura)].copy()
            agregar_hoja_trazabilidad_analitos(
                writer=writer,
                df_trazabilidad_analitos=df_trazabilidad_analitos,
                df_cobertura_operacional=cobertura_operacional,
            )
        if df_reconst_srr is not None and not df_reconst_srr.empty:
            _agregar_hoja_reconst_mod_srr(
                workbook, df_reconst_srr, df_turno=df_turno_reconst,
            )
