# Auto-generated on 2025-10-27 18:21:09. Edit as needed.

import os
import io
import time
import calendar
from datetime import date
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, clientside_callback, no_update, dcc, html, dash_table, ALL, MATCH, ctx
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc

from report_export.report_export import (
    BalanceReportError,
    fetch_recon_balance_official_cases,
    fetch_report_data,
    refrescar_historico_apilado_report,
    actualizar_datos_conciliados_report,
    fetch_datos_conciliados_report,
    actualizar_datos_conciliados_emision_report,
    fetch_datos_conciliados_emision_report,
    fetch_factor_ajuste_camiones_report,
    fetch_balance_chancado_report,
    fetch_representatividad_torres_report,
    fetch_bd_ton_report,
    fetch_gestion_representatividad_fy,
    fetch_estado_apilado_turno_representatividad,
    fetch_fecha_corte_representatividad,
    refrescar_representatividad_para_exportacion,
    fetch_reporte_turno_report,
    actualizar_apilado_tmh_v2_report,
    actualizar_factor_ajuste_camiones_v2_report,
    actualizar_reporte_turno_cache_emision,
    fetch_reporte_turno_cache_emision,
    fetch_clays_cufe_report,
    fetch_trazabilidad_analitos_report,
    fetch_curva_granulometrica_report,
    fetch_generador_reporte_diario_emision,
    export_reporte_turno_estilo_leyes_finos,
    write_reporte_torre_oficial,
    armar_paquete_reporte_torre_oficial,
    fetch_historial_reporte_torre_oficial,
    fetch_reporte_torre_oficial_detalle,
    fetch_reporte_torre_oficial_snapshot,
    fetch_comentarios_representatividad_periodo,
    soft_delete_reporte_torre_oficial,
    log_db_destino_reporte_torre,
    es_mes_completo,
    normalizar_periodo_mes,
    comentarios_mapa_desde_dataframe,
    pad_ajustado_para,
    mes_tiene_reporte_activo,
    comentario_torres_para_tipo,
    validar_pesos_representatividad,
)
from report_export.export_to_excel import (
    DependenciaDatosExportError,
    export_balance_reconciliacion_to_template,
    export_dataframe_with_template,
    export_datos_conciliados_to_template,
)
from report_export.pdf_generator import (
    generar_pdf_datos_conciliados,
)
from report_export.xlsx_to_pdf import (
    convert_xlsx_bytes_to_pdf,
    normalize_pages_to_a3_landscape,
    normalize_single_page_to_a3,
)

_REPORT_EXPORT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_PROJECT_DIR = os.path.dirname(_REPORT_EXPORT_DIR)
TEMPLATE_XLSX_PATH = os.path.join(_PROJECT_DIR, "reporte", "Template_DatosConcialiados.xlsx")
BALANCE_TEMPLATE_XLSX_PATH = os.path.join(
    _PROJECT_DIR, "reporte", "Template_Balance_Planta_Hidrometalurgia.xlsx"
)
from report_export.balance_service import (
    build_balance_official_report,
    get_balance_case_status,
)
from report_export.balance_contract import build_balance_report_identity
_NOMBRE_REPORTE_REPRESENTATIVIDAD_TORRES = "Representatividad Torres"
_TEXTO_CONFIRMACION_BORRADO = "confirmar borrado"

_COLUMNAS_COMENTARIOS_REP = (
    "Comentario_TM1_Quimico",
    "Comentario_TM2_Quimico",
    "Comentario_TM3_Quimico",
    "Comentario_TM1_Fisico",
    "Comentario_TM2_Fisico",
    "Comentario_TM3_Fisico",
)

# Unicos ajustes que el operador puede elegir. "Sin clasificar" es un valor
# derivado legitimo (aparece en Pad_Original) pero no un destino valido: la
# tabla "Mineral apilado por Pad" solo agrega Óxido y Sulfuro.
_PAD_VALORES_VALIDOS = ("Óxido", "Sulfuro")

_COLUMNAS_METRICAS_VIVAS_REP = (
    "TMH_CV08",
    "TMH_CV108",
    "TMH_CV01",
    "TM1_Activo",
    "TM2_Activo",
    "TM3_Activo",
    "Rep_TM1_Quimico",
    "Rep_TM2_Quimico",
    "Rep_TM3_Quimico",
    "Rep_TM1_Fisico",
    "Rep_TM2_Fisico",
    "Rep_TM3_Fisico",
)

_COLUMNAS_OBLIGATORIAS_TM3 = (
    "TMH_CV01",
    "TM3_Activo",
    "Rep_TM3_Quimico",
    "Rep_TM3_Fisico",
    "Comentario_TM3_Quimico",
    "Comentario_TM3_Fisico",
)


def _refrescar_dependencias_datos_conciliados(
    ini_d: date,
    fin_d: date,
    fin_sql_exclusivo: date,
) -> None:
    refrescar_historico_apilado_report(
        start_date=ini_d, end_date=fin_d, dias_reproceso=0,
    )
    print(
        "[DATOS-CONCILIADOS] 1/3 Histórico apilado actualizado "
        f"({ini_d} -> {fin_d}, fin inclusivo)"
    )

    actualizar_reporte_turno_cache_emision(
        start_date=ini_d, end_date=fin_sql_exclusivo,
    )
    print(
        "[DATOS-CONCILIADOS] 2/3 Cache reporte turno actualizado "
        f"({ini_d} -> {fin_sql_exclusivo}, fin exclusivo)"
    )

    actualizar_datos_conciliados_emision_report(
        start_date=ini_d, end_date=fin_d, dias_reproceso=0,
    )
    print(
        "[DATOS-CONCILIADOS] 3/3 Datos conciliados actualizados "
        f"({ini_d} -> {fin_d}, fin inclusivo)"
    )

_ETIQUETAS_DEPENDENCIAS_DATOS = {
    "Fecha": "Fecha", "Chancado_TMS_Real": "Chancado real",
    "Apilado_TMS_Real": "Apilado real", "Apilado_TMS_Plan": "Plan de apilado",
    "Ley_CuT_Real": "Ley de cobre real", "Ley_CuT_Plan": "Ley de cobre plan",
    "Cobre_fino_Apilado_Real": "Cobre fino apilado real",
    "Cobre_fino_Apilado_Plan": "Cobre fino apilado plan",
    "SRR_TMS_promedio_dia": "SRR real", "SRR_TMS_Plan": "Plan SRR",
    "Ley_CuT_Real_srr": "Ley de cobre SRR real",
    "Ley_CuT_Plan_srr": "Ley de cobre SRR plan",
    "TMS_Rotopala_1_Real": "Rotopala 1 real",
    "TMS_Rotopala_1_Plan": "Rotopala 1 plan",
    "TMS_Rotopala_2_Real": "Rotopala 2 real",
    "TMS_Rotopala_2_Plan": "Rotopala 2 plan",
    "Camiones_TMS_total": "Camiones real", "Camiones_TMS_plan": "Camiones plan",
    "Total_Ripios_Incluye_Camiones_Real": "Ripios total real",
    "Total_Ripios_Incluye_Camiones_Plan": "Ripios total plan",
    "Produccion_Catodos_Real": "Producción de cátodos real",
    "Produccion_Catodos_Plan": "Producción de cátodos plan",
}


def _usuario_sesion() -> str:
    try:
        from flask import has_request_context, session
        if has_request_context():
            return str(session.get("user") or "desconocido")
    except Exception as exc:
        raise RuntimeError(
            "No fue posible recuperar los comentarios históricos de "
            "representatividad."
        ) from exc
    return "desconocido"


def _fusionar_detalle_representatividad(df_quimico: pd.DataFrame, df_fisico: pd.DataFrame) -> pd.DataFrame:
    """Une detalle químico y físico por Fecha+Turno con sus seis comentarios."""
    if df_quimico is None or df_quimico.empty:
        return pd.DataFrame()

    base = df_quimico.copy()
    base["Fecha"] = pd.to_datetime(base["Fecha"], errors="coerce").dt.normalize()
    if "Comentario_TM1" in base.columns:
        base["Comentario_TM1_Quimico"] = base["Comentario_TM1"]
    if "Comentario_TM2" in base.columns:
        base["Comentario_TM2_Quimico"] = base["Comentario_TM2"]
    if "Comentario_TM3" in base.columns:
        base["Comentario_TM3_Quimico"] = base["Comentario_TM3"]
    for col in [
        "Comentario_TM1_Quimico",
        "Comentario_TM2_Quimico",
        "Comentario_TM1_Fisico",
        "Comentario_TM2_Fisico",
        "Comentario_TM3_Quimico",
        "Comentario_TM3_Fisico",
    ]:
        if col not in base.columns:
            base[col] = None

    base = base.rename(columns={
        "Rep_TM1": "Rep_TM1_Quimico",
        "Rep_TM2": "Rep_TM2_Quimico",
        "Rep_Turno": "Rep_Turno_Quimico",
        "Rep_TM3": "Rep_TM3_Quimico",
    })
    base = base.drop(columns=["Comentario_TM1", "Comentario_TM2", "Comentario_TM3"], errors="ignore")

    if df_fisico is not None and not df_fisico.empty:
        base = base.drop(columns=[
            "Comentario_TM1_Fisico", "Comentario_TM2_Fisico",
            "Comentario_TM3_Fisico",
        ], errors="ignore")
        fis = df_fisico.copy()
        fis["Fecha"] = pd.to_datetime(fis["Fecha"], errors="coerce").dt.normalize()
        if "Comentario_TM1" in fis.columns:
            fis["Comentario_TM1_Fisico"] = fis["Comentario_TM1"]
        if "Comentario_TM2" in fis.columns:
            fis["Comentario_TM2_Fisico"] = fis["Comentario_TM2"]
        if "Comentario_TM3" in fis.columns:
            fis["Comentario_TM3_Fisico"] = fis["Comentario_TM3"]
        fis = fis.rename(columns={
            "Rep_TM1": "Rep_TM1_Fisico",
            "Rep_TM2": "Rep_TM2_Fisico",
            "Rep_Turno": "Rep_Turno_Fisico",
            "Rep_TM3": "Rep_TM3_Fisico",
        })
        cols_fis = [
            "Fecha", "Turno",
            "Rep_TM1_Fisico", "Rep_TM2_Fisico", "Rep_Turno_Fisico",
            "Rep_TM3_Fisico", "Comentario_TM1_Fisico", "Comentario_TM2_Fisico",
            "Comentario_TM3_Fisico",
        ]
        base = base.merge(
            fis[cols_fis],
            on=["Fecha", "Turno"],
            how="left",
        )
    else:
        base["Rep_TM1_Fisico"] = None
        base["Rep_TM2_Fisico"] = None
        base["Rep_Turno_Fisico"] = None
        base["Rep_TM3_Fisico"] = None

    return base.sort_values(["Fecha", "Turno"]).reset_index(drop=True)


def _rep_cols_por_tab(tab_activo: str) -> dict:
    tab = str(tab_activo or "quimico").lower()
    if tab == "fisico":
        return {
            "rep_tm1": "Rep_TM1_Fisico",
            "rep_tm2": "Rep_TM2_Fisico",
            "rep_turno": "Rep_Turno_Fisico",
            "com_tm1": "Comentario_TM1_Fisico",
            "com_tm2": "Comentario_TM2_Fisico",
            "rep_tm3": "Rep_TM3_Fisico",
            "com_tm3": "Comentario_TM3_Fisico",
        }
    return {
        "rep_tm1": "Rep_TM1_Quimico",
        "rep_tm2": "Rep_TM2_Quimico",
        "rep_turno": "Rep_Turno_Quimico",
        "com_tm1": "Comentario_TM1_Quimico",
        "com_tm2": "Comentario_TM2_Quimico",
        "rep_tm3": "Rep_TM3_Quimico",
        "com_tm3": "Comentario_TM3_Quimico",
    }


def _texto_comentario_rep(valor):
    """Normaliza un comentario: texto no vacío o NULL."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    texto = str(valor).strip()
    return texto or None


def _turno_key_rep(valor) -> str:
    turno = str(valor or "").strip().upper()
    if turno in {"A", "TA"}:
        return "TA"
    if turno in {"B", "TB"}:
        return "TB"
    return turno


def _fecha_key_rep(valor) -> str:
    if isinstance(valor, str):
        texto = valor.strip()
        if (
            len(texto) >= 10
            and texto[4:5] == "-"
            and texto[7:8] == "-"
        ):
            fecha = pd.to_datetime(
                texto[:10],
                format="%Y-%m-%d",
                errors="coerce",
            )
        else:
            fecha = pd.to_datetime(texto, errors="coerce", dayfirst=True)
    else:
        fecha = pd.to_datetime(valor, errors="coerce")
    return fecha.strftime("%Y-%m-%d") if pd.notna(fecha) else ""


def _fusionar_solo_comentarios_en_detalle_vivo(
    detalle_vivo: pd.DataFrame,
    registros_editor,
) -> pd.DataFrame:
    """
    Aplica al detalle vivo los seis comentarios del editor y el Pad ajustado.

    Prioridad: comentario del editor (vacío incluido) > histórico vivo > NULL.
    El Pad solo viaja desde el editor cuando difiere de ``Pad_Original``, es
    decir cuando hubo un ajuste manual. Ninguna otra métrica se lee desde
    ``registros_editor``.
    """
    if detalle_vivo is None or detalle_vivo.empty:
        return pd.DataFrame() if detalle_vivo is None else detalle_vivo.copy()

    resultado = detalle_vivo.copy()
    for columna in _COLUMNAS_COMENTARIOS_REP:
        if columna not in resultado.columns:
            resultado[columna] = None

    ediciones = {}
    if isinstance(registros_editor, pd.DataFrame):
        registros = registros_editor.to_dict("records")
    else:
        registros = registros_editor or []

    for fila in registros:
        clave = (
            _fecha_key_rep(fila.get("Fecha")),
            _turno_key_rep(fila.get("Turno")),
        )
        if not all(clave):
            continue
        destino = ediciones.setdefault(clave, {})
        for columna in _COLUMNAS_COMENTARIOS_REP:
            # La columna presente manda, aunque venga vacía: así el borrado
            # viaja. Una columna ausente sí cae al valor vivo más abajo.
            if columna in fila:
                destino[columna] = _texto_comentario_rep(fila.get(columna))
        # El Pad ajustado a mano si es un override real; el derivado se
        # recalcula siempre y no debe viajar desde el editor.
        pad_editado = _texto_comentario_rep(fila.get("Pad"))
        pad_original = _texto_comentario_rep(fila.get("Pad_Original"))
        if pad_editado is not None and pad_editado != pad_original:
            destino["Pad"] = pad_editado

    for indice, fila in resultado.iterrows():
        clave = (
            _fecha_key_rep(fila.get("Fecha")),
            _turno_key_rep(fila.get("Turno")),
        )
        editados = ediciones.get(clave, {})
        for columna in _COLUMNAS_COMENTARIOS_REP:
            resultado.at[indice, columna] = editados.get(
                columna,
                _texto_comentario_rep(fila.get(columna)),
            )
        if "Pad" in editados:
            # Un ajuste nuevo aun no tiene autor: se sella al publicar, con
            # el usuario de la sesion que lo confirma.
            if editados["Pad"] != _texto_comentario_rep(fila.get("Pad")):
                resultado.at[indice, "Pad_Ajustado_Por"] = None
            resultado.at[indice, "Pad"] = editados["Pad"]

    return resultado


def _completar_tm3_editor_desde_fuente_viva(
    detalle: pd.DataFrame,
    df_bd_ton: pd.DataFrame,
) -> pd.DataFrame:
    """Completa métricas TM3 del editor sin cambiar la exportación mensual."""
    if detalle is None or detalle.empty:
        return pd.DataFrame() if detalle is None else detalle.copy()
    if df_bd_ton is None or df_bd_ton.empty or "Fecha" not in df_bd_ton.columns:
        return detalle.copy()

    resultado = detalle.copy()
    if "TMH_CV01" not in resultado.columns:
        resultado["TMH_CV01"] = None

    fuente = df_bd_ton.copy()
    fuente["_fecha_key"] = fuente["Fecha"].apply(_fecha_key_rep)
    resultado["_fecha_key"] = resultado["Fecha"].apply(_fecha_key_rep)
    resultado["_turno_key"] = resultado["Turno"].apply(_turno_key_rep)

    fuente_por_fecha = fuente.drop_duplicates(
        "_fecha_key",
        keep="last",
    ).set_index("_fecha_key")

    for turno in ("TA", "TB"):
        mask = resultado["_turno_key"] == turno
        sufijo = turno[-1]
        configuracion = {
            "TMH_CV01": (
                f"Apilado TMH CV-01 {turno}",
                f"Apilado_TMH_CV01_T{sufijo}",
            ),
            "TM3_Activo": (f"Evaluable_TM3_T{sufijo}",),
            "Rep_TM3_Quimico": (
                f"Muestra representativa TM3 {turno}",
                f"Muestra_representativa_TM3_T{sufijo}",
            ),
            "Rep_TM3_Fisico": (
                f"FISICO TM3 {turno}",
                f"FISICO_TM3_T{sufijo}",
            ),
        }

        for destino, candidatos in configuracion.items():
            columna = next(
                (
                    candidato for candidato in candidatos
                    if candidato in fuente_por_fecha.columns
                ),
                None,
            )
            if columna is None:
                continue
            if destino not in resultado.columns:
                resultado[destino] = None
            valores = pd.to_numeric(
                resultado.loc[mask, "_fecha_key"].map(
                    fuente_por_fecha[columna]
                ),
                errors="coerce",
            )
            indices_validos = valores[valores.notna()].index
            resultado.loc[indices_validos, destino] = valores.loc[
                indices_validos
            ]

    return resultado.drop(
        columns=["_fecha_key", "_turno_key"],
        errors="ignore",
    )


def _validar_detalle_publicacion_rep(df_final: pd.DataFrame) -> dict:
    """Valida el contrato vivo antes de llamar al escritor oficial."""
    columnas = set(df_final.columns) if df_final is not None else set()
    faltantes_tm3 = [
        columna for columna in _COLUMNAS_OBLIGATORIAS_TM3
        if columna not in columnas
    ]
    if faltantes_tm3:
        raise RuntimeError(
            f"No se puede publicar: faltan columnas TM3 {faltantes_tm3}"
        )

    faltantes_metricas = [
        columna for columna in _COLUMNAS_METRICAS_VIVAS_REP
        if columna not in columnas
    ]
    if faltantes_metricas:
        raise RuntimeError(
            "No se puede publicar: faltan métricas de la fuente viva "
            f"{faltantes_metricas}"
        )

    tm3_activo = df_final["TM3_Activo"]
    invalidos = tm3_activo[
        tm3_activo.notna() & ~tm3_activo.isin([0, 1, 0.0, 1.0])
    ].tolist()
    if invalidos:
        raise RuntimeError(
            "No se puede publicar: TM3_Activo contiene valores distintos "
            f"de 0, 1 o NULL: {invalidos}"
        )

    return {
        "filas": len(df_final),
        "TMH_CV01_no_nulo": len(df_final[df_final["TMH_CV01"].notna()]),
        "TM3_Activo_1": len(df_final[tm3_activo == 1]),
        "TM3_Activo_0": len(df_final[tm3_activo == 0]),
        "TM3_Activo_NULL": len(df_final[tm3_activo.isna()]),
        "Rep_TM3_Quimico_no_nulo": len(
            df_final[df_final["Rep_TM3_Quimico"].notna()]
        ),
        "Rep_TM3_Fisico_no_nulo": len(
            df_final[df_final["Rep_TM3_Fisico"].notna()]
        ),
    }


def _etiqueta_semaforo_rep(valor, activo: bool) -> str:
    if not activo:
        return ""
    rep = pd.to_numeric(valor, errors="coerce")
    if pd.isna(rep):
        return ""
    return "Representativo" if int(rep) == 1 else "No representativo"


def _df_a_grilla_rep(df: pd.DataFrame, tab_activo: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    cols = _rep_cols_por_tab(tab_activo)

    def _es_activo(valor) -> bool:
        numero = pd.to_numeric(valor, errors="coerce")
        return bool(pd.notna(numero) and float(numero) == 1.0)

    filas = []
    for _, fila in df.iterrows():
        fecha = pd.to_datetime(fila.get("Fecha"), errors="coerce")
        tm1_activo = _es_activo(fila.get("TM1_Activo"))
        tm2_activo = _es_activo(fila.get("TM2_Activo"))
        tm3_activo = _es_activo(fila.get("TM3_Activo"))
        turno_activo = tm1_activo or tm2_activo
        rep_tm1 = fila.get(cols["rep_tm1"]) if tm1_activo else None
        rep_tm2 = fila.get(cols["rep_tm2"]) if tm2_activo else None
        rep_turno = fila.get(cols["rep_turno"]) if turno_activo else None
        rep_tm3 = fila.get(cols["rep_tm3"]) if tm3_activo else None

        tmh_tm1 = pd.to_numeric(fila.get("TMH_CV08"), errors="coerce")
        tmh_tm2 = pd.to_numeric(fila.get("TMH_CV108"), errors="coerce")
        tmh_tm3 = pd.to_numeric(fila.get("TMH_CV01"), errors="coerce")

        filas.append({
            "Semana": fila.get("Semana"),
            "Fecha": fecha.strftime("%d-%m-%Y") if pd.notna(fecha) else "",
            "Pad_Original": fila.get("Pad_Original"),
            "Pad": fila.get("Pad"),
            "Pad_Ajustado_Por": fila.get("Pad_Ajustado_Por"),
            "Turno": fila.get("Turno"),
            "TMH_CV08": round(float(tmh_tm1), 1) if tm1_activo and pd.notna(tmh_tm1) else None,
            "Rep_TM1": _etiqueta_semaforo_rep(rep_tm1, tm1_activo),
            "Comentario_TM1": _texto_comentario_rep(
                fila.get(cols["com_tm1"])
            ) or "",
            "TMH_CV108": round(float(tmh_tm2), 1) if tm2_activo and pd.notna(tmh_tm2) else None,
            "Rep_TM2": _etiqueta_semaforo_rep(rep_tm2, tm2_activo),
            "Comentario_TM2": _texto_comentario_rep(
                fila.get(cols["com_tm2"])
            ) or "",
            "TMH_CV01": round(float(tmh_tm3), 1) if pd.notna(tmh_tm3) else None,
            "Rep_TM3": _etiqueta_semaforo_rep(rep_tm3, tm3_activo),
            "Comentario_TM3": _texto_comentario_rep(
                fila.get(cols["com_tm3"])
            ) or "",
            "Rep_Turno": _etiqueta_semaforo_rep(rep_turno, turno_activo),
        })

    return pd.DataFrame(filas)


def _fusionar_comentarios_grilla(
    registros: list,
    grid_data: list | None,
    tab_activo: str,
) -> list:
    if not registros:
        return []

    cols = _rep_cols_por_tab(tab_activo)
    df = pd.DataFrame(registros)
    if "Fecha" not in df.columns or "Turno" not in df.columns:
        return registros
    # Comentarios suelen venir como None desde el Store y pandas infiere
    # float64; forzar object evita perder el texto al asignar.
    for columna in _COLUMNAS_COMENTARIOS_REP:
        if columna not in df.columns:
            df[columna] = None
        df[columna] = df[columna].astype(object)
    df["_fecha_key"] = df["Fecha"].apply(_fecha_key_rep)
    df["_turno_key"] = df["Turno"].apply(_turno_key_rep)

    for fila in grid_data or []:
        fecha = _fecha_key_rep(fila.get("Fecha"))
        turno = _turno_key_rep(fila.get("Turno"))
        mask = (
            (df["_fecha_key"].astype(str) == fecha)
            & (df["_turno_key"].astype(str) == turno)
        )
        if mask.any():
            for columna_grilla, clave_columna in (
                ("Comentario_TM1", "com_tm1"),
                ("Comentario_TM2", "com_tm2"),
                ("Comentario_TM3", "com_tm3"),
            ):
                # Vaciar la celda borra el comentario: la grilla ya se abre
                # con los guardados, así que un vacío es deliberado y
                # conservar el previo los volvería imborrables. La pestaña
                # opuesta no se toca porque ``cols`` solo trae las activas.
                if columna_grilla in fila:
                    df.loc[mask, cols[clave_columna]] = _texto_comentario_rep(
                        fila.get(columna_grilla)
                    )

            # Pad es único para ambas pestañas (no depende del análisis).
            # Sin Pad_Original la fila es futura o sin apilado: no hay nada
            # que ajustar y clasificarla inventaria un dato.
            pad = _texto_comentario_rep(fila.get("Pad"))
            original = _texto_comentario_rep(fila.get("Pad_Original"))
            if pad in _PAD_VALORES_VALIDOS and original:
                df.loc[mask, "Pad"] = pad

    df = df.drop(columns=["_fecha_key", "_turno_key"], errors="ignore")
    return (
        df.astype(object)
        .where(pd.notna(df), None)
        .to_dict("records")
    )


def _tooltip_pad_rep(fila: dict) -> dict:
    """Tooltip de la celda Pad: valor anterior y quién lo ajustó."""
    pad = _texto_comentario_rep(fila.get("Pad"))
    original = _texto_comentario_rep(fila.get("Pad_Original"))
    if not pad or not original or pad == original:
        return {}

    autor = _texto_comentario_rep(fila.get("Pad_Ajustado_Por"))
    lineas = [f"**Valor anterior:** {original}"]
    # Sin autor todavia = ajuste de esta sesion, aun sin publicar.
    lineas.append(f"**Ajustado por:** {autor}" if autor else "_Ajuste sin publicar_")
    return {"Pad": {"value": "  \n".join(lineas), "type": "markdown"}}


def _registros_tooltips_grilla_rep(df: pd.DataFrame, tab_activo: str):
    """Datos + tooltips de la grilla sin remountar el DataTable."""
    df_grilla = _df_a_grilla_rep(df, tab_activo)
    registros = (
        df_grilla.astype(object).where(pd.notna(df_grilla), None).to_dict("records")
    )
    for fila in registros:
        fila["id"] = f"{fila.get('Fecha')}|{fila.get('Turno')}"
    tooltips = [_tooltip_pad_rep(fila) for fila in registros]
    return registros, tooltips


def _grilla_comentarios_representatividad(df_grilla: pd.DataFrame):
    columns = [
        {"name": ["", "Semana"], "id": "Semana", "editable": False},
        {"name": ["", "Fecha"], "id": "Fecha", "editable": False},
        # Pad_Original viaja en ``data`` pero no es columna: el valor
        # calculado se ve en el tooltip, solo si hubo ajuste.
        # No editable: el valor se cambia con clic (ver alternar_pad_rep).
        {"name": ["", "Pad (clic alterna)"], "id": "Pad", "editable": False},
        {"name": ["", "Turno"], "id": "Turno", "editable": False},
        {"name": ["Torre de muestreo #1", "TMH CV-08"], "id": "TMH_CV08", "type": "numeric", "editable": False},
        {"name": ["Torre de muestreo #1", "Muestra representativa"], "id": "Rep_TM1", "editable": False},
        {"name": ["Torre de muestreo #1", "Comentarios"], "id": "Comentario_TM1", "editable": True},
        {"name": ["Torre de muestreo #2", "TMH CV-108"], "id": "TMH_CV108", "type": "numeric", "editable": False},
        {"name": ["Torre de muestreo #2", "Muestra representativa"], "id": "Rep_TM2", "editable": False},
        {"name": ["Torre de muestreo #2", "Comentarios"], "id": "Comentario_TM2", "editable": True},
        {"name": ["Torre de muestreo #3 / SRR", "TMH CV-01"], "id": "TMH_CV01", "type": "numeric", "editable": False},
        {"name": ["Torre de muestreo #3 / SRR", "Muestra representativa"], "id": "Rep_TM3", "editable": False},
        {"name": ["Torre de muestreo #3 / SRR", "Comentarios"], "id": "Comentario_TM3", "editable": True},
    ]

    style_data_conditional = [
        {"if": {"row_index": "odd"}, "backgroundColor": "#eef3f6"},
        {"if": {"column_id": "Fecha"}, "backgroundColor": "#fff2cc", "fontWeight": "bold"},
        {"if": {"column_id": "Semana"}, "backgroundColor": "#f2f2f2", "fontWeight": "bold"},
        {
            "if": {
                "filter_query": '{Pad} = "Sin clasificar"',
                "column_id": "Pad",
            },
            "backgroundColor": "#d9d9d9",
        },
        # Un Pad ajustado a mano queda marcado: cambia cifras del reporte
        # oficial y tiene que verse de un vistazo.
        {
            "if": {"filter_query": "{Pad} != {Pad_Original}", "column_id": "Pad"},
            "backgroundColor": "#fce4d6",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Rep_TM1} = "Representativo"', "column_id": "Rep_TM1"},
            "color": "#70AD47",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Rep_TM1} = "No representativo"', "column_id": "Rep_TM1"},
            "color": "#C55A11",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Rep_TM2} = "Representativo"', "column_id": "Rep_TM2"},
            "color": "#70AD47",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Rep_TM2} = "No representativo"', "column_id": "Rep_TM2"},
            "color": "#C55A11",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Rep_TM3} = "Representativo"', "column_id": "Rep_TM3"},
            "color": "#70AD47", "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Rep_TM3} = "No representativo"', "column_id": "Rep_TM3"},
            "color": "#C55A11", "fontWeight": "bold",
        },
    ]

    registros = (
        df_grilla.astype(object).where(pd.notna(df_grilla), None).to_dict("records")
    )
    # ``id`` por fila: active_cell entrega row_id, que sobrevive al orden
    # nativo de la tabla. Sin esto, ordenar desalinearia el clic.
    for fila in registros:
        fila["id"] = f"{fila.get('Fecha')}|{fila.get('Turno')}"

    return dash_table.DataTable(
        id="rep-comentarios-grid",
        columns=columns,
        data=registros,
        tooltip_data=[_tooltip_pad_rep(fila) for fila in registros],
        tooltip_duration=None,
        editable=True,
        merge_duplicate_headers=True,
        page_size=40,
        sort_action="native",
        filter_action="none",
        fixed_rows={"headers": True},
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "560px",
            "width": "100%",
            "border": "1px solid #b8b8b8",
        },
        style_cell={
            "textAlign": "center",
            "fontFamily": "Arial",
            "fontSize": "12px",
            "padding": "6px",
            "border": "1px solid #b8b8b8",
            "minWidth": "90px",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_cell_conditional=[
            {
                "if": {
                    "column_id": [
                        "Comentario_TM1",
                        "Comentario_TM2",
                        "Comentario_TM3",
                    ]
                },
                "textAlign": "left",
                "minWidth": "160px",
                "width": "180px",
                "maxWidth": "220px",
            },
        ],
        style_header={
            "backgroundColor": "#d9e3ea",
            "fontWeight": "bold",
            "color": "#1f4e79",
            "border": "1px solid #7f9db9",
            "textAlign": "center",
        },
        style_data_conditional=style_data_conditional,
    )


def _etiqueta_mes_periodo(periodo_mes: str) -> str:
    if not periodo_mes:
        return "—"
    try:
        year, month = map(int, str(periodo_mes).split("-"))
    except (ValueError, TypeError):
        return str(periodo_mes)
    nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }
    return f"{nombres.get(month, str(month))} {year}"


def _periodo_store_desde_fechas(ini, fin, modo: str) -> dict:
    modo = str(modo or "mes").lower()
    store = {
        "inicio": str(ini),
        "fin": str(fin),
        "modo": modo,
        "periodo_mes": None,
    }
    if modo == "mes" and es_mes_completo(ini, fin):
        _, _, periodo_mes = normalizar_periodo_mes(ini, fin)
        store["periodo_mes"] = periodo_mes
    return store


def _cargar_detalle_representatividad_periodo(
    ini,
    fin,
    periodo_mes=None,
    paquete=None,
):
    if paquete is not None:
        fecha_corte_operacional = paquete.get("fecha_corte_operacional")
        if fecha_corte_operacional is None:
            raise RuntimeError(
                "El paquete oficial no incluye fecha_corte_operacional."
            )
        fuentes = {
            "fecha_inicio_mes": paquete.get("fecha_inicio_mes", ini),
            "fecha_fin_mes": paquete.get("fecha_fin_mes", fin),
            "fecha_corte_operacional": fecha_corte_operacional,
            "df_bd_ton_mes": paquete.get("bd_ton_mes", pd.DataFrame()),
            "df_turno_mes": paquete.get("turno_mes", pd.DataFrame()),
        }
        if fuentes["df_bd_ton_mes"].empty or fuentes["df_turno_mes"].empty:
            raise RuntimeError(
                "El paquete oficial no contiene las fuentes mensuales "
                "necesarias para construir el detalle."
            )
    else:
        # Mismo refresco que usa la publicacion, sobre el mes que la grilla
        # realmente muestra (_fetch_fuentes_mensuales_torres trabaja el mes de
        # `fin`). Sin esto el editor mostraba el estado que dejo la ultima
        # publicacion o PDF, y ademas cortaba por una fecha distinta a la que
        # despues usa el reporte final. El refresco serializa por mes con
        # sp_getapplock (ver refrescar_representatividad_para_exportacion).
        fecha_corte_operacional = refrescar_representatividad_para_exportacion(
            start_date=pd.to_datetime(fin).date().replace(day=1),
            end_date=fin,
        )
        fuentes = _fetch_fuentes_mensuales_torres(
            fin,
            fecha_corte_operacional,
        )
    df_turno_preparado = _preparar_material_por_turno(fuentes["df_turno_mes"])
    df_quimico = _preparar_detalle_mensual_torres(
        df_bd_ton=fuentes["df_bd_ton_mes"],
        tipo="quimico",
        df_material_turno=df_turno_preparado,
        fecha_inicio_mes=fuentes["fecha_inicio_mes"],
        fecha_fin_mes=fuentes["fecha_fin_mes"],
        fecha_corte_operacional=fecha_corte_operacional,
    )
    df_fisico = _preparar_detalle_mensual_torres(
        df_bd_ton=fuentes["df_bd_ton_mes"],
        tipo="fisico",
        df_material_turno=df_turno_preparado,
        fecha_inicio_mes=fuentes["fecha_inicio_mes"],
        fecha_fin_mes=fuentes["fecha_fin_mes"],
        fecha_corte_operacional=fecha_corte_operacional,
    )
    detalle = _fusionar_detalle_representatividad(df_quimico, df_fisico)
    # Misma fuente que las hojas mensuales del XLSX/PDF: [dia1, corte
    # operacional]. Antes el editor releia BD Ton con [ini, fin] y mostraba TM3
    # de dias posteriores al corte que el reporte no incluye.
    detalle = _completar_tm3_editor_desde_fuente_viva(
        detalle,
        fuentes["df_bd_ton_mes"],
    )

    try:
        # Al publicar, los comentarios ya vienen del editor y las metricas
        # deben proceder exclusivamente del paquete recien refrescado.
        if paquete is not None:
            return detalle, pd.to_datetime(fecha_corte_operacional).date()
        if periodo_mes:
            guardado = fetch_reporte_torre_oficial_detalle(periodo_mes=periodo_mes)
        elif es_mes_completo(ini, fin):
            _, _, pm = normalizar_periodo_mes(ini, fin)
            guardado = fetch_reporte_torre_oficial_detalle(periodo_mes=pm)
        else:
            guardado = fetch_comentarios_representatividad_periodo(ini, fin)
        if not guardado.empty:
            detalle = _fusionar_solo_comentarios_en_detalle_vivo(
                detalle,
                guardado,
            )
    except Exception:
        pass

    return detalle, fecha_corte_operacional


def _tabla_historial_representatividad(df_hist: pd.DataFrame):
    if df_hist is None or df_hist.empty:
        return dbc.Card([
            dbc.CardHeader("Historial de reportes oficiales"),
            dbc.CardBody(
                html.P(
                    "Aun no hay reportes publicados. Use Generar reporte final "
                    "en modo mes completo para guardar el primer reporte del mes.",
                    className="text-muted mb-0",
                )
            ),
        ], className="mt-2")

    filas = []
    for _, fila in df_hist.iterrows():
        id_reporte = int(fila["id_reporte"])
        periodo_mes = fila.get("periodo_mes")
        if periodo_mes and pd.notna(periodo_mes):
            etiqueta_mes = _etiqueta_mes_periodo(str(periodo_mes))
            subtitulo_mes = str(periodo_mes)
        else:
            etiqueta_mes = (
                f"{pd.to_datetime(fila['periodo_inicio']).strftime('%d-%m-%Y')} "
                f"a {pd.to_datetime(fila['periodo_fin']).strftime('%d-%m-%Y')}"
            )
            subtitulo_mes = ""

        corte = fila.get("fecha_corte_operacional")
        if corte is not None and pd.notna(corte):
            etiqueta_corte = pd.to_datetime(corte).strftime("%d-%m-%Y")
        else:
            etiqueta_corte = "-"

        filas.append(html.Tr([
            html.Td([
                html.Div(etiqueta_mes, className="fw-semibold"),
                html.Small(subtitulo_mes, className="text-muted") if subtitulo_mes else None,
            ]),
            html.Td(
                _NOMBRE_REPORTE_REPRESENTATIVIDAD_TORRES,
                className="text-nowrap",
            ),
            html.Td(etiqueta_corte),
            html.Td(pd.to_datetime(fila["fecha_generacion"]).strftime("%d-%m-%Y %H:%M")),
            html.Td(fila.get("usuario") or "-"),
            html.Td(int(fila.get("filas") or 0)),
            html.Td([
                dbc.Button(
                    "Excel",
                    size="sm",
                    color="success",
                    outline=True,
                    className="me-1 mb-1",
                    title="Descargar el Excel de esta versión publicada",
                    id={"type": "rep-hist-xlsx", "id_reporte": id_reporte},
                ),
                dbc.Button(
                    "PDF Químico",
                    size="sm",
                    color="danger",
                    outline=True,
                    className="me-1 mb-1",
                    title="Descargar el PDF Químico de esta versión publicada",
                    id={"type": "rep-hist-pdf", "id_reporte": id_reporte, "subtipo": "quimico"},
                ),
                dbc.Button(
                    "PDF Físico",
                    size="sm",
                    color="danger",
                    outline=True,
                    className="me-1 mb-1",
                    title="Descargar el PDF Físico de esta versión publicada",
                    id={"type": "rep-hist-pdf", "id_reporte": id_reporte, "subtipo": "fisico"},
                ),
                dbc.Button(
                    "PDF SRR", size="sm", color="danger", outline=True,
                    className="me-1 mb-1",
                    title="Descargar el PDF SRR de esta versión publicada",
                    id={"type": "rep-hist-pdf", "id_reporte": id_reporte, "subtipo": "srr"},
                ),
                dbc.Button(
                    "Reabrir",
                    size="sm",
                    color="primary",
                    outline=True,
                    className="me-1 mb-1",
                    title="Reabrir esta versión en el editor de comentarios",
                    id={"type": "rep-hist-reabrir", "id_reporte": id_reporte},
                ),
                dbc.Button(
                    "Eliminar",
                    size="sm",
                    color="secondary",
                    outline=True,
                    className="mb-1",
                    title="Eliminar esta versión del historial",
                    id={"type": "rep-hist-del", "id_reporte": id_reporte},
                ),
            ], className="d-flex flex-wrap"),
        ]))

    cantidad = len(df_hist)
    return dbc.Card([
        dbc.CardHeader([
            html.Span("Historial de reportes oficiales", className="me-2"),
            dbc.Badge(f"{cantidad} mes{'es' if cantidad != 1 else ''}", color="secondary"),
        ]),
        dbc.CardBody(
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Mes"),
                    html.Th("Reporte"),
                    html.Th("Corte operacional"),
                    html.Th("Actualizado"),
                    html.Th("Usuario"),
                    html.Th("Turnos"),
                    html.Th("Acciones"),
                ])),
                html.Tbody(filas),
            ], bordered=True, hover=True, responsive=True, className="mb-0"),
        ),
    ], className="mt-2")


def _reporte_oficial_activo_para_periodo(ini, fin) -> dict | None:
    """Obtiene el snapshot activo que corresponde al mes seleccionado."""
    ini_d = pd.to_datetime(ini).date()
    fin_d = pd.to_datetime(fin).date()
    if ini_d.year != fin_d.year or ini_d.month != fin_d.month:
        return None
    periodo_mes = f"{ini_d.year:04d}-{ini_d.month:02d}"
    historial = fetch_historial_reporte_torre_oficial()
    if historial is None or historial.empty:
        return None
    candidatos = historial[
        historial["periodo_mes"].astype(str).eq(periodo_mes)
    ]
    if candidatos.empty:
        return None
    return candidatos.iloc[0].to_dict()


def _editor_comentarios_representatividad(
    df: pd.DataFrame,
    tab_activo: str = "quimico",
    registros_store=None,
    periodo_store=None,
    puede_publicar: bool = True,
    es_republicacion: bool = False,
):
    if df is None or df.empty:
        return dbc.Alert("Sin detalle para editar comentarios.", color="info")

    tab_activo = str(tab_activo or "quimico").lower()
    df_grilla = _df_a_grilla_rep(df, tab_activo)
    titulo_tab = "Quimico" if tab_activo == "quimico" else "Fisico"

    if not puede_publicar:
        texto_ayuda = html.P(
            "La publicacion solo esta disponible en modo Mes completo. "
            "En rango personalizado puede exportar XLSX/PDF sin guardar en historial.",
            className="text-warning small mb-2",
        )
        texto_boton = "Publicar reporte oficial"
        color_boton = "success"
    elif es_republicacion:
        texto_ayuda = html.P(
            "Actualiza el reporte del mes con datos al dia y los comentarios editados.",
            className="text-muted small mb-2",
        )
        texto_boton = "Publicar nueva versión oficial"
        color_boton = "primary"
    else:
        texto_ayuda = html.P(
            "Guarda el reporte oficial del mes en historial (incluye datos y comentarios).",
            className="text-muted small mb-2",
        )
        texto_boton = "Publicar reporte oficial"
        color_boton = "success"

    return html.Div([
        html.H5("5.- Detalle turno a turno — comentarios", className="mb-2"),
        html.P(
            f"Vista {titulo_tab}: misma estructura que la seccion 5 del reporte. "
            "Los comentarios son opcionales; edite directamente en la grilla.",
            className="text-muted small mb-3",
        ),
        texto_ayuda,
        dbc.ButtonGroup([
            dbc.Button(
                "Quimico",
                id="rep-tab-quimico",
                color="primary",
                outline=(tab_activo != "quimico"),
                size="sm",
            ),
            dbc.Button(
                "Fisico",
                id="rep-tab-fisico",
                color="primary",
                outline=(tab_activo != "fisico"),
                size="sm",
            ),
        ], className="mb-3"),
        _grilla_comentarios_representatividad(df_grilla),
        html.Div([
            dbc.Button(
                texto_boton,
                id="rep-generar-final-btn",
                color=color_boton,
                className="mt-3 me-2",
                disabled=not puede_publicar,
            ),
            html.Span(id="rep-publicar-status", className="text-muted small"),
        ]),
        # Stores viven en el layout fijo (reportabilidad_page): evita
        # remount al editar y el pestañeo de dcc.Loading.
    ])


def setup_download_route(server):
    """No-op kept for import compatibility in main.py."""
    pass


def _enviar_descarga(contenido: bytes, nombre_archivo: str):
    """Fuerza una descarga binaria y evita la previsualización inline."""
    return dcc.send_bytes(
        contenido,
        nombre_archivo,
        type="application/octet-stream",
    )


# ── Clientside callback: show "generating" bar immediately on any button click ──
clientside_callback(
    """
    function(export_clicks, pdf_clicks) {
        const ctx = dash_clientside.callback_context;
        if (!ctx || !ctx.triggered || ctx.triggered.length === 0) {
            return window.dash_clientside.no_update;
        }
        const t = ctx.triggered[0];
        if (!t.value || t.value === 0) return window.dash_clientside.no_update;

        const isPdf = t.prop_id.toLowerCase().includes('pdf');
        const label = isPdf ? 'Generando PDF' : 'Generando Excel';
        return label + ', por favor espere…';
    }
    """,
    Output("report-progress", "children"),
    Input({"type": "report-export-btn", "tipo": ALL}, "n_clicks"),
    Input({"type": "report-pdf-btn", "tipo": ALL}, "n_clicks"),
    prevent_initial_call=True,
)


clientside_callback(
    """
    function(tabla_children) {
        setTimeout(function() {
            const table = document.getElementById('rep-comentarios-grid');
            if (!table) return;

            // DataTable (React) confirma la celda al perder el foco.
            // Un Enter sintético no siempre llega al handler de React.
            function commitInput(input) {
                if (!input || input.tagName !== 'INPUT') return;
                input.blur();
            }

            if (table._repBlurCommitHandler) {
                table.removeEventListener('focusout', table._repBlurCommitHandler, true);
            }
            if (table._repGridClickHandler) {
                table.removeEventListener('click', table._repGridClickHandler, true);
            }

            table._repBlurCommitHandler = function(e) {
                if (e.target.tagName === 'INPUT' && table.contains(e.target)) {
                    setTimeout(function() { commitInput(e.target); }, 0);
                }
            };
            table._repGridClickHandler = function(e) {
                const active = document.activeElement;
                if (
                    active
                    && active.tagName === 'INPUT'
                    && table.contains(active)
                    && e.target !== active
                ) {
                    commitInput(active);
                }
            };

            table.addEventListener('focusout', table._repBlurCommitHandler, true);
            table.addEventListener('click', table._repGridClickHandler, true);

            if (!window._repGridDocMouseDown) {
                window._repGridDocMouseDown = true;
                document.addEventListener('mousedown', function(e) {
                    const grid = document.getElementById('rep-comentarios-grid');
                    const active = document.activeElement;
                    if (
                        grid
                        && active
                        && grid.contains(active)
                        && active.tagName === 'INPUT'
                        && !active.contains(e.target)
                        && e.target !== active
                    ) {
                        commitInput(active);
                    }
                }, true);
            }
        }, 50);
        return Date.now();
    }
    """,
    Output("rep-grid-blur-hook", "data"),
    Input("report-tabla", "children"),
    prevent_initial_call=True,
)


@callback(
    Output("report-balance-caso", "options"),
    Output("report-balance-caso", "value"),
    Input("report-subtabs", "value"),
    State("report-balance-caso", "value"),
)
def cargar_casos_oficiales_balance(tab_activo, caso_actual):
    if tab_activo != "tab-semanales":
        return no_update, no_update
    try:
        cases = fetch_recon_balance_official_cases()
    except BalanceReportError as exc:
        print(f"[BALANCE] no fue posible cargar selector: {exc}")
        return [], None
    if cases.empty:
        return [], None
    options = []
    seen = set()
    for _, row in cases.iterrows():
        case_id = int(row["caso_id"])
        if case_id in seen:
            continue
        seen.add(case_id)
        start = pd.to_datetime(row["fecha_inicio"]).date()
        end = pd.to_datetime(row["fecha_fin"]).date()
        options.append({
            "label": (
                f"Caso {case_id} — {row.get('nombre_caso') or 'Sin nombre'} — "
                f"{start:%d/%m/%Y} al {end:%d/%m/%Y}"
            ),
            "value": case_id,
        })
    values = {option["value"] for option in options}
    selected = caso_actual if caso_actual in values else options[0]["value"]
    return options, selected


def _balance_status_content(status):
    available = bool(status["mtd_disponible"])
    items = [
        (
            "Caso seleccionado",
            f"Caso {status['caso_id']} — {status.get('nombre_caso') or 'Sin nombre'}",
        ),
        (
            "Período",
            f"{status['fecha_inicio']:%d-%m-%Y} al {status['fecha_fin']:%d-%m-%Y}",
        ),
        ("Run oficial", str(status["solver_run_id"])),
        ("Estado Run", str(status.get("estado_run") or "Sin estado")),
    ]
    if available:
        items.extend([
            (
                "Período acumulado",
                f"{status['mtd_fecha_inicio']:%d-%m-%Y} al "
                f"{status['mtd_fecha_fin']:%d-%m-%Y}",
            ),
            ("Casos MTD", ", ".join(map(str, status["mtd_casos"]))),
        ])
    rows = [
        html.Div([
            html.Small(label, className="text-muted d-block"),
            html.Span(value, className="fw-semibold"),
        ], className="mb-2")
        for label, value in items
    ]
    rows.insert(4, html.Div([
        html.Small("Acumulado MTD", className="text-muted d-block"),
        dbc.Badge(
            "Disponible" if available else "No disponible",
            color="success" if available else "warning",
            pill=True,
        ),
    ], className="mb-2"))
    if not available:
        rows.append(html.Div([
            html.Small("Motivo", className="text-muted d-block"),
            html.Span(status.get("mensaje_mtd") or "Cobertura MTD no disponible."),
        ]))
    return dbc.Alert(
        rows,
        color="success" if available else "warning",
        className="mb-0 py-2",
    )


@callback(
    Output("report-balance-status", "children"),
    Output(
        {"type": "report-export-btn", "tipo": "balance"},
        "disabled",
        allow_duplicate=True,
    ),
    Input("report-balance-caso", "value"),
    prevent_initial_call=True,
)
def actualizar_estado_balance(caso_id):
    if caso_id is None:
        return (
            dbc.Alert(
                "Seleccione un Caso oficial para consultar su estado.",
                color="secondary",
                className="mb-0 py-2",
            ),
            True,
        )
    print(f"[BALANCE UI] caso seleccionado={caso_id}")
    try:
        status = get_balance_case_status(int(caso_id))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"[BALANCE UI] error tecnico={exc}")
        return (
            dbc.Alert(
                "No fue posible consultar el estado del Caso. "
                "Intente nuevamente o contacte a soporte.",
                color="danger",
                className="mb-0 py-2",
            ),
            True,
        )
    print(f"[BALANCE UI] run oficial={status['solver_run_id']}")
    print(f"[BALANCE UI] mtd_disponible={status['mtd_disponible']}")
    if status.get("mensaje_mtd"):
        print(f"[BALANCE UI] motivo={status['mensaje_mtd']}")
    return _balance_status_content(status), not status["mtd_disponible"]


@callback(
    Output("report-fecha-mes-wrap", "style"),
    Output("report-fecha-rango-wrap", "style"),
    Output("report-fecha-inicio", "date", allow_duplicate=True),
    Output("report-fecha-final", "date", allow_duplicate=True),
    Output("report-fecha-inicio", "initial_visible_month"),
    Output("report-fecha-final", "initial_visible_month"),
    Output("report-fecha-inicio", "max_date_allowed"),
    Output("report-fecha-final", "max_date_allowed"),
    Input("report-fecha-modo", "value"),
    Input("report-fecha-mes", "value"),
    prevent_initial_call="initial_duplicate",
)
def sync_modo_y_mes(modo, mes_val):
    """Alterna controles visibles y sincroniza fechas al elegir mes completo.

    También refresca max_date_allowed a la fecha de hoy del servidor en cada
    carga/cambio de modo, para que no quede congelada al arranque del proceso.
    """
    hoy = date.today().isoformat()
    if modo == "rango":
        return (
            {"display": "none"},
            {"display": "block"},
            no_update,
            no_update,
            no_update,
            no_update,
            hoy,
            hoy,
        )

    if not mes_val:
        return (
            {"display": "block"},
            {"display": "none"},
            no_update,
            no_update,
            no_update,
            no_update,
            hoy,
            hoy,
        )

    year, month = map(int, mes_val.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    ini = f"{year:04d}-{month:02d}-01"
    fin = f"{year:04d}-{month:02d}-{last_day:02d}"
    return (
        {"display": "block"},
        {"display": "none"},
        ini,
        fin,
        ini,
        fin,
        hoy,
        hoy,
    )


@callback(
    Output("report-fecha-inicio", "date", allow_duplicate=True),
    Output("report-fecha-warning", "children"),
    Output("report-status", "children", allow_duplicate=True),
    Input("report-fecha-inicio", "date"),
    Input("report-fecha-final", "date"),
    State("report-fecha-modo", "value"),
    prevent_initial_call=True,
)
def validar_rango_fechas(fecha_ini, fecha_fin, modo):
    if modo == "mes":
        return no_update, html.Div(), html.Div()

    if not fecha_ini or not fecha_fin:
        return no_update, html.Div(), html.Div()

    ini = pd.to_datetime(fecha_ini)
    fin = pd.to_datetime(fecha_fin)

    if ini > fin:
        corregida = fin - pd.Timedelta(days=7)
        warning = dbc.Alert(
            "Fecha inicio ajustada a una semana antes de Fecha final.",
            color="warning",
            className="py-1 px-2 mb-0 small",
            dismissable=True,
        )
        return corregida.strftime("%Y-%m-%d"), warning, html.Div()

    return no_update, html.Div(), html.Div()


def _find_plantilla_propuesta():
    """Resuelve la ruta de la plantilla VF listando el directorio (evita problemas con 'á' en Windows)."""
    try:
        for name in os.listdir(_REPORT_EXPORT_DIR):
            if not name.startswith("~$") and name.endswith(".xlsx"):
                if "Propuesta_Identidad" in name and "DatosConcialiados" in name and "VF" in name:
                    return os.path.join(_REPORT_EXPORT_DIR, name)
    except OSError:
        pass
    return os.path.join(_REPORT_EXPORT_DIR, "Propuesta_Identidad_Gráfica_DatosConcialiados VF.xlsx")

def _style_table(df: pd.DataFrame) -> dash_table.DataTable:
    df = df.copy()
    columnas_numericas = [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
    ]

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col]).dt.strftime("%d-%m-%Y")

    df = df.astype(object).where(pd.notna(df), None)

    return dash_table.DataTable(
        id="tabla-reporte-general",
        columns=[
            {
                "name": col,
                "id": col,
                "type": "numeric" if col in columnas_numericas else "text",
            }
            for col in df.columns
        ],
        data=df.to_dict("records"),
        page_size=20,
        sort_action="native",
        filter_action="none",
        fixed_rows={"headers": True},
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "650px",
            "width": "100%",
            "maxWidth": "100%",
            "border": "1px solid #d0d0d0",
        },
        style_cell={
            "textAlign": "center",
            "fontFamily": "Arial",
            "fontSize": "11px",
            "padding": "5px",
            "minWidth": "90px",
            "width": "105px",
            "maxWidth": "140px",
            "whiteSpace": "normal",
            "height": "auto",
            "border": "1px solid #d9d9d9",
        },
        style_header={
            "backgroundColor": "#9DC3E6",
            "fontWeight": "bold",
            "color": "#1f4e79",
            "textAlign": "center",
            "border": "1px solid #7f9db9",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f7f3ef"},
            {"if": {"column_id": "Fecha"}, "backgroundColor": "#d9eaf7", "fontWeight": "bold"},
        ],
    )
def _completar_calendario_representatividad(
    df: pd.DataFrame,
    fecha_inicio,
    fecha_fin,
) -> pd.DataFrame:
    calendario = pd.DataFrame({
        "Dia": pd.date_range(
            start=fecha_inicio,
            end=fecha_fin,
            freq="D",
        )
    })

    datos = df.copy()
    if "Dia" in datos.columns:
        datos["Dia"] = pd.to_datetime(
            datos["Dia"],
            errors="coerce",
        ).dt.normalize()
    else:
        datos["Dia"] = pd.NaT

    return (
        calendario
        .merge(datos, on="Dia", how="left")
        .sort_values("Dia")
        .reset_index(drop=True)
    )


def _tabla_representatividad_torres(
    df: pd.DataFrame,
    fecha_corte_operacional=None,
):
    df = df.copy()
    df_num = df.copy()

    if "Dia" in df.columns:
        df["Dia"] = pd.to_datetime(df["Dia"]).dt.strftime("%d-%m-%Y")

    columnas_pct = [
        "TM1_TurnoA_Quimico",
        "TM1_TurnoA_Fisico",
        "TM1_TurnoB_Quimico",
        "TM1_TurnoB_Fisico",
        "TM2_TurnoA_Quimico",
        "TM2_TurnoA_Fisico",
        "TM2_TurnoB_Quimico",
        "TM2_TurnoB_Fisico",
        "SRR_TurnoA_Quimico",
        "SRR_TurnoA_Fisico",
        "SRR_TurnoB_Quimico",
        "SRR_TurnoB_Fisico",
    ]

    for col in columnas_pct:
        if col in df_num.columns:
            df_num[col] = pd.to_numeric(df_num[col], errors="coerce")

    # Crear columnas auxiliares ocultas para definir el color de cada celda
    hidden_cols = []

    for col in columnas_pct:
        if col not in df.columns:
            continue

        estado_col = f"estado_{col}"
        hidden_cols.append(estado_col)

        valores_formateados = []
        estados = []

        for indice, valor in enumerate(df_num[col]):
            fecha_fila = pd.to_datetime(
                df_num.iloc[indice].get("Dia"),
                errors="coerce",
            )
            es_futura = (
                fecha_corte_operacional is not None
                and pd.notna(fecha_fila)
                and fecha_fila.date() > fecha_corte_operacional
            )

            if es_futura:
                valores_formateados.append("")
                estados.append("sin_dato")
            elif pd.isna(valor):
                valores_formateados.append("Tambor detenido")
                estados.append("detenido")
            else:
                valores_formateados.append(f"{valor * 100:.1f}%")

                if valor < 0.75:
                    estados.append("bajo")
                else:
                    estados.append("normal")

        df[col] = valores_formateados
        df[estado_col] = estados

    columns = [
        {"name": ["", "Día"], "id": "Dia"},

        {"name": ["Representatividad TM1", "Turno A - Químico"], "id": "TM1_TurnoA_Quimico"},
        {"name": ["Representatividad TM1", "Turno A - Físico"], "id": "TM1_TurnoA_Fisico"},
        {"name": ["Representatividad TM1", "Turno B - Químico"], "id": "TM1_TurnoB_Quimico"},
        {"name": ["Representatividad TM1", "Turno B - Físico"], "id": "TM1_TurnoB_Fisico"},

        {"name": ["Representatividad TM2", "Turno A - Químico"], "id": "TM2_TurnoA_Quimico"},
        {"name": ["Representatividad TM2", "Turno A - Físico"], "id": "TM2_TurnoA_Fisico"},
        {"name": ["Representatividad TM2", "Turno B - Químico"], "id": "TM2_TurnoB_Quimico"},
        {"name": ["Representatividad TM2", "Turno B - Físico"], "id": "TM2_TurnoB_Fisico"},
        {"name": ["Representatividad TM3 / SRR", "Turno A - Químico"], "id": "SRR_TurnoA_Quimico"},
        {"name": ["Representatividad TM3 / SRR", "Turno A - Físico"], "id": "SRR_TurnoA_Fisico"},
        {"name": ["Representatividad TM3 / SRR", "Turno B - Químico"], "id": "SRR_TurnoB_Quimico"},
        {"name": ["Representatividad TM3 / SRR", "Turno B - Físico"], "id": "SRR_TurnoB_Fisico"},
    ]

    # Agregar columnas auxiliares ocultas al DataTable
    for col in hidden_cols:
        columns.append({"name": col, "id": col})

    style_data_conditional = [
        {
            "if": {"row_index": "odd"},
            "backgroundColor": "#eef3f6",
        },
        {
            "if": {"column_id": "Dia"},
            "backgroundColor": "#fff2cc",
            "fontWeight": "bold",
        },
    ]

    # Estilos por columna usando la columna auxiliar de estado
    for col in columnas_pct:
        estado_col = f"estado_{col}"

        if estado_col not in df.columns:
            continue

        style_data_conditional.append({
            "if": {
                "filter_query": f'{{{estado_col}}} = "detenido"',
                "column_id": col,
            },
            "color": "#1f4e79",
            "fontWeight": "500",
        })

        # Representatividad menor a 75%, incluyendo 0.0%: rojo
        style_data_conditional.append({
            "if": {
                "filter_query": f'{{{estado_col}}} = "bajo"',
                "column_id": col
            },
            "color": "red",
            "fontWeight": "bold"
        })

    return dash_table.DataTable(
        id="tabla-representatividad-torres",
        columns=columns,
        data=df.to_dict("records"),
        merge_duplicate_headers=True,
        hidden_columns=hidden_cols,

        style_table={
            "overflowX": "auto",
            "width": "100%",
        },

        style_cell={
            "textAlign": "center",
            "fontFamily": "Arial",
            "fontSize": "13px",
            "padding": "7px",
            "border": "1px solid #b8b8b8",
            "minWidth": "115px",
            "width": "125px",
            "maxWidth": "160px",
            "whiteSpace": "normal",
        },

        style_header={
            "backgroundColor": "#d9e3ea",
            "fontWeight": "bold",
            "color": "#1f4e79",
            "border": "1px solid #7f9db9",
            "textAlign": "center",
        },

        style_data_conditional=style_data_conditional,

        page_size=40,
        sort_action="native",
        filter_action="native",
    )
_COLUMNAS_VISIBLES_BD_TON = [
    "Fecha",
    "Apilado TMH CV-08 TA",
    "Apilado TMH CV-08 TB",
    "Apilado TMH CV-108 TA",
    "Apilado TMH CV-108 TB",
    "Rep. TM1 TA Qui.",
    "Rep. TM1 TA Fis.",
    "Rep. TM1 TB Qui.",
    "Rep. TM1 TB Fis.",
    "Rep. TM2 TA Qui.",
    "Rep. TM2 TA Fis.",
    "Rep. TM2 TB Qui.",
    "Rep. TM2 TB Fis.",
    "Muestra representativa TM1 TA",
    "Muestra representativa TM1 TB",
    "Muestra representativa TM2 TA",
    "Muestra representativa TM2 TB",
    "FISICO TM1 TA",
    "FISICO TM1 TB",
    "FISICO TM2 TA",
    "FISICO TM2 TB",
    "Apilado TMH CV-01 TA",
    "Apilado TMH CV-01 TB",
    "Rep. SRR TA Qui.",
    "Rep. SRR TA Fis.",
    "Rep. SRR TB Qui.",
    "Rep. SRR TB Fis.",
    "Muestra representativa TM3 TA",
    "Muestra representativa TM3 TB",
    "FISICO TM3 TA",
    "FISICO TM3 TB",
]


def _agregar_hoja_bd_ton(wb, df_bd_ton: pd.DataFrame) -> None:
    """
    Agrega la hoja BD Ton con la estética del bloque AT:BM de
    Reporte Diario: fondo blanco, encabezados jerárquicos,
    bordes completos y desplazamiento libre sin paneles inmovilizados.
    """
    from openpyxl.styles import (
        Font,
        Alignment,
        PatternFill,
        Border,
        Side,
    )
    from openpyxl.utils import get_column_letter

    df = df_bd_ton.copy()
    columnas_faltantes = [
        columna
        for columna in _COLUMNAS_VISIBLES_BD_TON
        if columna not in df.columns
    ]
    if columnas_faltantes:
        raise RuntimeError(
            "BD Ton no contiene todas las columnas visibles requeridas. "
            f"Faltantes: {columnas_faltantes}. "
            f"Recibidas: {list(df.columns)}"
        )

    # Las columnas auxiliares de evaluabilidad permanecen disponibles en
    # los DataFrames de cálculo, pero no alteran la estructura visual A:U.
    df = df[_COLUMNAS_VISIBLES_BD_TON].copy()

    if "BD Ton" in wb.sheetnames:
        del wb["BD Ton"]

    ws = wb.create_sheet(title="BD Ton")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = None

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce",
        )
        df = (
            df[df["Fecha"].notna()]
            .sort_values("Fecha", kind="stable")
            .drop_duplicates(
                subset=["Fecha"],
                keep="last",
            )
            .reset_index(drop=True)
        )

    # Paleta equivalente a Reporte Diario, columnas AT:BM.
    color_header = "D7E1E7"
    color_texto = "476475"
    color_borde = "476475"
    color_borde_interno = "A6A6A6"
    color_subtitulo = "666666"

    fill_blanco = PatternFill("solid", fgColor="FFFFFF")
    fill_header = PatternFill("solid", fgColor=color_header)
    fill_alt = PatternFill("solid", fgColor=color_header)

    font_titulo = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=14,
    )
    font_subtitulo = Font(
        name="Arial",
        italic=True,
        color=color_subtitulo,
        size=9,
    )
    font_header = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=10,
    )
    font_normal = Font(
        name="Arial",
        color=color_texto,
        size=9,
    )
    font_fecha = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=9,
    )

    thin = Side(style="thin", color=color_borde_interno)
    thin_header = Side(style="thin", color=color_borde)
    medium = Side(style="medium", color=color_borde)

    border_datos = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin,
    )
    border_header = Border(
        left=thin_header,
        right=thin_header,
        top=thin_header,
        bottom=thin_header,
    )

    center = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )

    def _aplicar_contorno(
        fila_ini: int,
        col_ini: int,
        fila_fin: int,
        col_fin: int,
    ) -> None:
        """Refuerza solo el contorno del bloque, conservando la grilla interna."""
        for fila in range(fila_ini, fila_fin + 1):
            for col in range(col_ini, col_fin + 1):
                celda = ws.cell(fila, col)
                borde_actual = celda.border
                celda.border = Border(
                    left=medium if col == col_ini else borde_actual.left,
                    right=medium if col == col_fin else borde_actual.right,
                    top=medium if fila == fila_ini else borde_actual.top,
                    bottom=medium if fila == fila_fin else borde_actual.bottom,
                )

    # ------------------------------------------------------------
    # Título y descripción
    # ------------------------------------------------------------
    ws.merge_cells("A1:AE1")
    ws["A1"] = "Base de datos de tonelajes e indicadores de representatividad"
    ws["A1"].font = font_titulo
    ws["A1"].alignment = center
    ws["A1"].fill = fill_blanco

    ws.merge_cells("A2:AE2")
    ws["A2"] = (
        "Detalle diario de tonelajes, representatividad calculada "
        "e indicadores oficiales de muestra."
    )
    ws["A2"].font = font_subtitulo
    ws["A2"].alignment = center
    ws["A2"].fill = fill_blanco

    # ------------------------------------------------------------
    # Encabezados jerárquicos
    # ------------------------------------------------------------
    ws.merge_cells("A4:A6")
    ws.merge_cells("B4:E4")
    ws.merge_cells("F4:M4")
    ws.merge_cells("N4:U4")
    ws.merge_cells("V4:W4")
    ws.merge_cells("X4:AA4")
    ws.merge_cells("AB4:AC4")
    ws.merge_cells("AD4:AE4")

    ws.merge_cells("B5:C5")
    ws.merge_cells("D5:E5")
    ws.merge_cells("F5:I5")
    ws.merge_cells("J5:M5")
    ws.merge_cells("N5:Q5")
    ws.merge_cells("R5:U5")
    ws.merge_cells("V5:W5")
    ws.merge_cells("X5:Y5")
    ws.merge_cells("Z5:AA5")
    ws.merge_cells("AB5:AC5")
    ws.merge_cells("AD5:AE5")

    ws["A4"] = "Fecha"
    ws["B4"] = "Tonelaje apilado TMH"
    ws["F4"] = "Representatividad calculada"
    ws["N4"] = "Indicador oficial de muestra representativa"
    ws["V4"] = "Tonelaje apilado TMH - TM3 / CV-01"
    ws["X4"] = "Representatividad calculada - Torre de muestreo 3 / SRR"
    ws["AB4"] = "Indicador oficial químico - TM3"
    ws["AD4"] = "Indicador oficial físico - TM3"

    ws["B5"] = "TM1 · CV-08"
    ws["D5"] = "TM2 · CV-108"
    ws["F5"] = "Torre de muestreo 1"
    ws["J5"] = "Torre de muestreo 2"
    ws["N5"] = "Químico"
    ws["R5"] = "Físico"
    ws["V5"] = "TM3 · CV-01"
    ws["X5"] = "Turno A"
    ws["Z5"] = "Turno B"
    ws["AB5"] = "Químico"
    ws["AD5"] = "Físico"

    headers_fila_6 = [
        "TA",
        "TB",
        "TA",
        "TB",
        "TA Químico",
        "TA Físico",
        "TB Químico",
        "TB Físico",
        "TA Químico",
        "TA Físico",
        "TB Químico",
        "TB Físico",
        "TM1 TA",
        "TM1 TB",
        "TM2 TA",
        "TM2 TB",
        "TM1 TA",
        "TM1 TB",
        "TM2 TA",
        "TM2 TB",
        "TA", "TB",
        "TA Químico", "TA Físico", "TB Químico", "TB Físico",
        "TM3 TA", "TM3 TB", "TM3 TA", "TM3 TB",
    ]

    for col, valor in enumerate(headers_fila_6, start=2):
        ws.cell(6, col, valor)

    for fila in range(4, 7):
        for col in range(1, 32):
            celda = ws.cell(fila, col)
            celda.fill = fill_header
            celda.font = font_header
            celda.alignment = center
            celda.border = border_header

    # ------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------
    fila_inicio = 7

    for fila_excel, valores in enumerate(
        df.itertuples(index=False, name=None),
        start=fila_inicio,
    ):
        es_alterna = (fila_excel - fila_inicio) % 2 == 1

        for col_idx, valor in enumerate(valores, start=1):
            nombre_columna = str(df.columns[col_idx - 1])

            if pd.isna(valor):
                valor_excel = None
            elif isinstance(valor, pd.Timestamp):
                valor_excel = valor.to_pydatetime()
            elif hasattr(valor, "item"):
                valor_excel = valor.item()
            else:
                valor_excel = valor

            celda = ws.cell(
                row=fila_excel,
                column=col_idx,
                value=valor_excel,
            )
            celda.fill = fill_alt if es_alterna else fill_blanco
            celda.font = font_normal
            celda.alignment = center
            celda.border = border_datos

            if nombre_columna == "Fecha":
                celda.number_format = "dd-mm-yyyy"
                celda.font = font_fecha
            elif nombre_columna.startswith("Apilado TMH"):
                celda.number_format = "#,##0.0"
            elif nombre_columna.startswith("Rep."):
                celda.number_format = "0.000"
            elif (
                nombre_columna.startswith("Muestra representativa")
                or nombre_columna.startswith("FISICO")
            ):
                celda.number_format = "0"

    ultima_fila = max(fila_inicio + len(df) - 1, fila_inicio)

    # Contornos por bloque funcional.
    for col_ini, col_fin in [
        (1, 1),
        (2, 5),
        (6, 13),
        (14, 21),
        (22, 23),
        (24, 27),
        (28, 29),
        (30, 31),
    ]:
        _aplicar_contorno(4, col_ini, ultima_fila, col_fin)

    # Dimensiones equivalentes al bloque AT:BM.
    ws.column_dimensions["A"].width = 13
    for col in range(2, 6):
        ws.column_dimensions[get_column_letter(col)].width = 14
    for col in range(6, 14):
        ws.column_dimensions[get_column_letter(col)].width = 14
    for col in range(14, 22):
        ws.column_dimensions[get_column_letter(col)].width = 13
    for col in range(22, 32):
        ws.column_dimensions[get_column_letter(col)].width = 14

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 26
    ws.row_dimensions[6].height = 26
    for fila in range(fila_inicio, ultima_fila + 1):
        ws.row_dimensions[fila].height = 21

    if len(df.columns) > 0 and len(df) > 0:
        ultima_columna = get_column_letter(len(df.columns))
        ws.auto_filter.ref = f"A6:{ultima_columna}{ultima_fila}"


_MESES_ABR_TORRES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}

_MESES_NOMBRE_TORRES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

def _obtener_rango_fiscal_hasta_mes(fecha_reporte) -> dict:
    """
    Obtiene el rango desde el inicio del año fiscal hasta el último
    día del mes evaluado.

    Ejemplo:
        Enero 2026 -> FY26
        Desde 01-07-2025 hasta 31-01-2026.
    """

    fecha = pd.to_datetime(fecha_reporte).date()

    anio_fiscal = (
        fecha.year + 1
        if fecha.month >= 7
        else fecha.year
    )

    fecha_inicio_fy = pd.Timestamp(
        year=anio_fiscal - 1,
        month=7,
        day=1,
    ).date()

    ultimo_dia_mes = calendar.monthrange(
        fecha.year,
        fecha.month,
    )[1]

    fecha_fin_mes = fecha.replace(
        day=ultimo_dia_mes
    )

    return {
        "anio_fiscal": anio_fiscal,
        "fecha_inicio": fecha_inicio_fy,
        "fecha_fin": fecha_fin_mes,
    }

def _normalizar_turno_torres(valor) -> str:
    texto = str(valor or "").strip().upper().replace(" ", "")

    if texto in {"A", "TA", "TURNOA"}:
        return "TA"
    if texto in {"B", "TB", "TURNOB"}:
        return "TB"

    return texto


def _normalizar_material_torres(valor) -> str:
    texto = str(valor or "").strip().upper()

    if "SULF" in texto:
        return "Sulfuro"
    if "OX" in texto or "ÓX" in texto:
        return "Óxido"

    return "Sin clasificar"

def _preparar_material_por_turno(
    df_turno: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza la fuente independiente de estado de apilado para cada
    Fecha + Turno y entrega:

    - El material informado por la fuente independiente.
    - El apilado oficial del turno.
    - El estado de evaluabilidad según RN-046.

    Desde el 01-01-2026 la evaluabilidad se toma directamente del campo
    oficial Turno_Evaluable. Para fechas anteriores se conserva la regla
    histórica basada en apilado mayor que cero.
    """
    columnas_salida = [
        "Fecha",
        "Turno",
        "Pad",
        "Apilado_TMS_Real_Turno",
        "Turno_Evaluable",
        "Turno_Activo_Oficial",
    ]

    if df_turno is None or df_turno.empty:
        return pd.DataFrame(columns=columnas_salida)

    requeridas = {
        "Fecha",
        "Turno",
        "Material",
        "Apilado_TMS_Real",
    }

    if not requeridas.issubset(df_turno.columns):
        return pd.DataFrame(columns=columnas_salida)

    df = df_turno.copy()

    df["Fecha"] = pd.to_datetime(
        df["Fecha"],
        errors="coerce",
    ).dt.normalize()

    df["Turno"] = df["Turno"].apply(
        _normalizar_turno_torres
    )

    df["Pad"] = df["Material"].apply(
        _normalizar_material_torres
    )

    df["Tonelaje"] = pd.to_numeric(
        df["Apilado_TMS_Real"],
        errors="coerce",
    ).fillna(0.0)

    if "Turno_Evaluable" in df.columns:
        df["Turno_Evaluable"] = (
            pd.to_numeric(
                df["Turno_Evaluable"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )
    else:
        # Compatibilidad con fuentes históricas que no incluían el flag.
        df["Turno_Evaluable"] = 0

    df = df[
        df["Fecha"].notna()
        & df["Turno"].isin(["TA", "TB"])
    ].copy()

    if df.empty:
        return pd.DataFrame(columns=columnas_salida)

    # Normalización defensiva por material para garantizar una sola fila
    # por Fecha + Turno, incluso si la fuente cambia accidentalmente.
    tonelaje_material = (
        df.groupby(
            ["Fecha", "Turno", "Pad"],
            as_index=False,
            dropna=False,
        )["Tonelaje"]
        .sum()
    )

    # Conservar un único material por Fecha + Turno.
    material_predominante = (
        tonelaje_material.sort_values(
            ["Fecha", "Turno", "Tonelaje", "Pad"],
            ascending=[True, True, False, True],
        )
        .drop_duplicates(["Fecha", "Turno"])
        [["Fecha", "Turno", "Pad"]]
    )

    # Obtener el apilado oficial del turno.
    apilado_turno = (
        df.groupby(
            ["Fecha", "Turno"],
            as_index=False,
        )["Tonelaje"]
        .sum()
        .rename(
            columns={
                "Tonelaje": "Apilado_TMS_Real_Turno"
            }
        )
    )

    # Conservar el indicador oficial en la misma granularidad Fecha + Turno.
    evaluabilidad_turno = (
        df.groupby(
            ["Fecha", "Turno"],
            as_index=False,
        )["Turno_Evaluable"]
        .max()
    )

    resultado = material_predominante.merge(
        apilado_turno,
        on=["Fecha", "Turno"],
        how="left",
        validate="one_to_one",
    )
    resultado = resultado.merge(
        evaluabilidad_turno,
        on=["Fecha", "Turno"],
        how="left",
        validate="one_to_one",
    )

    resultado["Apilado_TMS_Real_Turno"] = (
        pd.to_numeric(
            resultado["Apilado_TMS_Real_Turno"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    resultado["Turno_Evaluable"] = (
        pd.to_numeric(
            resultado["Turno_Evaluable"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    resultado["Turno_Activo_Oficial"] = (
        resultado["Apilado_TMS_Real_Turno"] > 0
    )

    mascara_flag_oficial = resultado["Fecha"] >= pd.Timestamp("2026-01-01")
    resultado.loc[
        mascara_flag_oficial,
        "Turno_Activo_Oficial",
    ] = resultado.loc[
        mascara_flag_oficial,
        "Turno_Evaluable",
    ].eq(1)

    resultado["Turno_Activo_Oficial"] = resultado[
        "Turno_Activo_Oficial"
    ].astype(bool)

    return (
        resultado[columnas_salida]
        .sort_values(["Fecha", "Turno"])
        .reset_index(drop=True)
    )

def _numero_semana_mensual(
    fecha: pd.Timestamp,
    primera_fecha: pd.Timestamp,
) -> int:
    """Replica WEEKNUM(fecha, 2) con semanas iniciadas en lunes."""
    fecha = pd.Timestamp(fecha).normalize()
    primera_fecha = pd.Timestamp(primera_fecha).normalize()

    lunes_fecha = fecha - pd.Timedelta(days=fecha.weekday())
    lunes_inicial = primera_fecha - pd.Timedelta(
        days=primera_fecha.weekday()
    )

    return int((lunes_fecha - lunes_inicial).days // 7) + 1


def _numero_torres(valor) -> float:
    numero = pd.to_numeric(valor, errors="coerce")
    return 0.0 if pd.isna(numero) else float(numero)


def _flag_representatividad_torres(
    activo: bool,
    valor_flag,
    valor_representatividad,
) -> int | None:
    if not activo:
        return None

    flag = pd.to_numeric(valor_flag, errors="coerce")
    if pd.notna(flag):
        return 1 if float(flag) >= 1 else 0

    representatividad = pd.to_numeric(
        valor_representatividad,
        errors="coerce",
    )
    if pd.notna(representatividad):
        return 1 if float(representatividad) >= 0.75 else 0

    # El turno posee apilado oficial, pero no existe un indicador
    # trazable de representatividad. Se clasifica provisionalmente
    # como no representativo. El campo Comentarios permanece vacío.
    return 0


def _preparar_detalle_mensual_torres(
    df_bd_ton: pd.DataFrame,
    tipo: str,
    df_material_turno: pd.DataFrame | None = None,
    fecha_inicio_mes=None,
    fecha_fin_mes=None,
    fecha_corte_operacional=None,
    mapa_comentarios: dict | None = None,
) -> pd.DataFrame:
    """
    Construye el detalle Fecha + Turno de las hojas mensuales.

    La BD Ton aporta tonelajes e indicadores de cada torre.
    La fuente independiente de estado de apilado aporta el material
    y determina si el turno es evaluable por Fecha + Turno,
    según RN-046.
    """
    tipo_normalizado = str(tipo).strip().lower()

    if tipo_normalizado == "quimico":
        config = {
            "tm1_flag": "Muestra representativa TM1 {turno}",
            "tm2_flag": "Muestra representativa TM2 {turno}",
            "tm1_rep": "Rep. TM1 {turno} Qui.",
            "tm2_rep": "Rep. TM2 {turno} Qui.",
            "tm3_flag": "Muestra representativa TM3 {turno}",
            "tm3_rep": "Rep. SRR {turno} Qui.",
        }
    elif tipo_normalizado == "fisico":
        config = {
            "tm1_flag": "FISICO TM1 {turno}",
            "tm2_flag": "FISICO TM2 {turno}",
            "tm1_rep": "Rep. TM1 {turno} Fis.",
            "tm2_rep": "Rep. TM2 {turno} Fis.",
            "tm3_flag": "FISICO TM3 {turno}",
            "tm3_rep": "Rep. SRR {turno} Fis.",
        }
    else:
        raise ValueError(f"Tipo de hoja no soportado: {tipo}")

    df = df_bd_ton.copy()
    if "Fecha" not in df.columns:
        df["Fecha"] = pd.NaT

    df["Fecha"] = pd.to_datetime(
        df["Fecha"],
        errors="coerce",
    ).dt.normalize()

    df = (
        df[df["Fecha"].notna()]
        .sort_values("Fecha")
        .reset_index(drop=True)
    )

    inicio = pd.to_datetime(fecha_inicio_mes, errors="coerce")
    fin = pd.to_datetime(fecha_fin_mes, errors="coerce")
    corte = pd.to_datetime(fecha_corte_operacional, errors="coerce")

    if pd.isna(inicio) and not df.empty:
        inicio = df["Fecha"].min()
    if pd.isna(fin) and not df.empty:
        fin = df["Fecha"].max()
    if pd.isna(corte):
        corte = fin

    if pd.isna(inicio) or pd.isna(fin):
        return pd.DataFrame()

    inicio = inicio.normalize()
    fin = fin.normalize()
    corte = corte.normalize()
    primera_fecha = inicio

    calendario = pd.DataFrame({
        "Fecha": pd.date_range(inicio, fin, freq="D")
    })
    df = (
        calendario
        .merge(df, on="Fecha", how="left")
        .sort_values("Fecha")
        .reset_index(drop=True)
    )

    mapa_material = {}
    mapa_actividad = {}
    mapa_apilado_oficial = {}

    if df_material_turno is not None and not df_material_turno.empty:
        for _, fila_material in df_material_turno.iterrows():
            fecha_material = pd.to_datetime(
                fila_material.get("Fecha"),
                errors="coerce",
            )
            turno_material = _normalizar_turno_torres(
                fila_material.get("Turno")
            )

            if pd.isna(fecha_material):
                continue
            if turno_material not in {"TA", "TB"}:
                continue

            clave = (
                fecha_material.normalize(),
                turno_material,
            )

            mapa_material[clave] = _normalizar_material_torres(
                fila_material.get("Pad")
            )

            apilado_oficial = pd.to_numeric(
                fila_material.get("Apilado_TMS_Real_Turno"),
                errors="coerce",
            )
            if pd.isna(apilado_oficial):
                apilado_oficial = 0.0

            apilado_oficial = float(apilado_oficial)
            mapa_apilado_oficial[clave] = apilado_oficial

            actividad_fuente = fila_material.get(
                "Turno_Activo_Oficial"
            )
            if pd.isna(actividad_fuente):
                mapa_actividad[clave] = apilado_oficial > 0
            else:
                mapa_actividad[clave] = bool(actividad_fuente)

    registros = []

    for _, fila in df.iterrows():
        fecha = fila["Fecha"]
        semana_num = _numero_semana_mensual(
            fecha,
            primera_fecha,
        )

        for turno in ["TA", "TB"]:
            clave_turno = (fecha, turno)

            if fecha > corte:
                registros.append({
                    "Semana_Num": semana_num,
                    "Semana": f"Semana {semana_num}",
                    "Fecha": fecha,
                    "Pad": None,
                    "Pad_Original": None,
                    "Turno": turno,
                    "Apilado_Oficial_Turno": None,
                    "TMH_CV08": None,
                    "TM1_Activo": 0,
                    "Rep_TM1": None,
                    "Comentario_TM1": None,
                    "TMH_CV108": None,
                    "TM2_Activo": 0,
                    "Rep_TM2": None,
                    "Comentario_TM2": None,
                    "Rep_Turno": None,
                    "TMH_CV01": None,
                    "TM3_Activo": None,
                    "Rep_TM3": None,
                    "Comentario_TM3": None,
                })
                continue

            turno_activo_oficial = bool(
                mapa_actividad.get(clave_turno, False)
            )

            tm1_tmh_original = fila.get(
                f"Apilado TMH CV-08 {turno}"
            )
            tm2_tmh_original = fila.get(
                f"Apilado TMH CV-108 {turno}"
            )
            tm3_tmh_original = fila.get(f"Apilado TMH CV-01 {turno}")
            tm1_tmh = _numero_torres(
                tm1_tmh_original
            )
            tm2_tmh = _numero_torres(
                tm2_tmh_original
            )
            tm3_tmh = _numero_torres(tm3_tmh_original)

            # TM3/SRR usa la evaluabilidad oficial propia de CV-001. El corte
            # temporal continúa siendo el del reporte (CV-008/CV-108), para no
            # retrasar ni bloquear el flujo histórico existente.
            tm3_evaluable = pd.to_numeric(
                fila.get(f"Evaluable_TM3_{turno}"), errors="coerce"
            )
            if pd.notna(tm3_evaluable):
                tm3_activo = 1 if float(tm3_evaluable) == 1.0 else 0
            elif (
                fecha < pd.Timestamp("2026-01-01")
                and pd.notna(tm3_tmh_original)
            ):
                # Compatibilidad histórica previa a la existencia del flag
                # oficial de evaluabilidad TM3.
                tm3_activo = 1
            else:
                tm3_activo = None

            if fecha >= pd.Timestamp("2026-01-01"):
                # Desde 2026 cada torre usa exclusivamente su evaluabilidad
                # oficial por Fecha + Turno + Torre.
                tm1_evaluable = pd.to_numeric(
                    fila.get(f"Evaluable_TM1_{turno}"),
                    errors="coerce",
                )
                tm2_evaluable = pd.to_numeric(
                    fila.get(f"Evaluable_TM2_{turno}"),
                    errors="coerce",
                )

                tm1_activo = bool(
                    pd.notna(tm1_evaluable)
                    and float(tm1_evaluable) == 1.0
                )
                tm2_activo = bool(
                    pd.notna(tm2_evaluable)
                    and float(tm2_evaluable) == 1.0
                )

                if tm1_activo != tm2_activo:
                    print(
                        "[RTO] Evaluabilidad torre: "
                        f"fecha={fecha:%Y-%m-%d} turno={turno[-1]} "
                        f"TM1={int(tm1_activo)} TM2={int(tm2_activo)}"
                    )
            else:
                # En el histórico la evaluabilidad es independiente por
                # torre. El tonelaje original se consulta antes de convertir
                # nulos a cero para no perder la diferencia NULL/0.
                tm1_evaluable = fila.get(f"Evaluable_TM1_{turno}")
                tm2_evaluable = fila.get(f"Evaluable_TM2_{turno}")

                tm1_evaluable_num = pd.to_numeric(
                    tm1_evaluable,
                    errors="coerce",
                )
                tm2_evaluable_num = pd.to_numeric(
                    tm2_evaluable,
                    errors="coerce",
                )

                tm1_activo = (
                    bool(int(tm1_evaluable_num) == 1)
                    if pd.notna(tm1_evaluable_num)
                    else pd.notna(tm1_tmh_original)
                )
                tm2_activo = (
                    bool(int(tm2_evaluable_num) == 1)
                    if pd.notna(tm2_evaluable_num)
                    else pd.notna(tm2_tmh_original)
                )

            turno_activo_combinado = bool(tm1_activo or tm2_activo)

            tm1_flag_fuente = fila.get(
                config["tm1_flag"].format(turno=turno)
            )
            tm2_flag_fuente = fila.get(
                config["tm2_flag"].format(turno=turno)
            )
            tm1_rep_fuente = fila.get(
                config["tm1_rep"].format(turno=turno)
            )
            tm2_rep_fuente = fila.get(
                config["tm2_rep"].format(turno=turno)
            )
            tm3_flag_fuente = fila.get(config["tm3_flag"].format(turno=turno))
            tm3_rep_fuente = fila.get(config["tm3_rep"].format(turno=turno))

            tm1_flag = _flag_representatividad_torres(
                tm1_activo,
                tm1_flag_fuente,
                tm1_rep_fuente,
            )
            tm2_flag = _flag_representatividad_torres(
                tm2_activo,
                tm2_flag_fuente,
                tm2_rep_fuente,
            )
            if tm3_activo != 1:
                tm3_flag = None
            else:
                flag_tm3_num = pd.to_numeric(tm3_flag_fuente, errors="coerce")
                rep_tm3_num = pd.to_numeric(tm3_rep_fuente, errors="coerce")
                if pd.notna(flag_tm3_num):
                    tm3_flag = 1 if float(flag_tm3_num) >= 1 else 0
                elif pd.notna(rep_tm3_num):
                    tm3_flag = 1 if float(rep_tm3_num) >= 0.75 else 0
                else:
                    tm3_flag = None

            if tm1_flag == 1 or tm2_flag == 1:
                representatividad_turno = 1
            elif not turno_activo_combinado:
                representatividad_turno = None
            else:
                representatividad_turno = 0

            registros.append({
                "Semana_Num": semana_num,
                "Semana": f"Semana {semana_num}",
                "Fecha": fecha,
                # Pad efectivo: gana el ajuste del editor si lo hay, si no el
                # derivado. Pad_Original conserva siempre el calculado.
                "Pad": (
                    pad_ajustado_para(mapa_comentarios, fecha, turno)
                    or mapa_material.get(clave_turno, "Sin clasificar")
                ),
                "Pad_Original": mapa_material.get(
                    clave_turno,
                    "Sin clasificar",
                ),
                "Turno": turno,
                "Apilado_Oficial_Turno": mapa_apilado_oficial.get(
                    clave_turno,
                    0.0,
                ),
                "TMH_CV08": tm1_tmh if tm1_activo else None,
                "TM1_Activo": int(tm1_activo),
                "Rep_TM1": tm1_flag,
                "Comentario_TM1": comentario_torres_para_tipo(
                    mapa_comentarios, fecha, turno, "TM1", tipo_normalizado
                ),
                "TMH_CV108": tm2_tmh if tm2_activo else None,
                "TM2_Activo": int(tm2_activo),
                "Rep_TM2": tm2_flag,
                "Comentario_TM2": comentario_torres_para_tipo(
                    mapa_comentarios, fecha, turno, "TM2", tipo_normalizado
                ),
                "Rep_Turno": representatividad_turno,
                "TMH_CV01": tm3_tmh if tm3_activo == 1 else None,
                "TM3_Activo": tm3_activo,
                "Rep_TM3": tm3_flag,
                "Comentario_TM3": comentario_torres_para_tipo(
                    mapa_comentarios, fecha, turno, "TM3", tipo_normalizado
                ),
            })

    return pd.DataFrame(registros)


def _calcular_resumen_mensual_torres(
    detalle: pd.DataFrame,
) -> dict:
    """
    Calcula resultados semanales y MTD según RN-046.

    TM1 y TM2:
    - Denominador: turnos oficialmente evaluables.
    - Numerador: turnos representativos de la torre.

    Combinado:
    - Unidad de conteo: Fecha + Turno + Torre.
    - Denominador: activos TM1 + activos TM2.
    - Numerador: representativos TM1 + representativos TM2.

    El MTD se calcula como cociente de totales acumulados y no como
    promedio de porcentajes semanales.
    """
    resumen = {"TM1": [], "TM2": [], "COMBINADO": []}

    def _fila_resumen(df_semana, etiqueta):
        tm1_activos = int(df_semana["TM1_Activo"].sum())
        tm2_activos = int(df_semana["TM2_Activo"].sum())

        tm1_rep = int((df_semana["Rep_TM1"] == 1).sum())
        tm2_rep = int((df_semana["Rep_TM2"] == 1).sum())
        tm1_no_rep = max(tm1_activos - tm1_rep, 0)
        tm2_no_rep = max(tm2_activos - tm2_rep, 0)

        activos_combinados = tm1_activos + tm2_activos
        representativos_combinados = tm1_rep + tm2_rep
        no_representativos_combinados = tm1_no_rep + tm2_no_rep

        valores = {
            "TM1": (tm1_activos, tm1_rep, tm1_no_rep),
            "TM2": (tm2_activos, tm2_rep, tm2_no_rep),
            "COMBINADO": (
                activos_combinados,
                representativos_combinados,
                no_representativos_combinados,
            ),
        }

        for clave, (
            activos,
            representativos,
            no_representativos,
        ) in valores.items():
            pct_rep = (
                representativos / activos
                if activos
                else None
            )
            pct_no_rep = (
                no_representativos / activos
                if activos
                else None
            )
            total = 1.0 if activos else None

            resumen[clave].append({
                "Periodo": etiqueta,
                "Turnos_Activos": activos,
                "Representativos": representativos,
                "No_Representativos": no_representativos,
                "Pct_Representativos": pct_rep,
                "Pct_No_Representativos": pct_no_rep,
                "Total": total,
            })

    for semana in range(1, 7):
        _fila_resumen(
            detalle[detalle["Semana_Num"] == semana],
            f"Semana {semana}",
        )

    _fila_resumen(detalle, "MTD")
    return resumen


def _calcular_tonelaje_por_material_torres(
    detalle: pd.DataFrame,
) -> list[dict]:
    resultados = []

    for material in ["Óxido", "Sulfuro"]:
        df_material = detalle[detalle["Pad"] == material]

        con_torre = float(
            df_material.loc[df_material["Rep_TM1"] == 1, "TMH_CV08"].sum()
            + df_material.loc[df_material["Rep_TM2"] == 1, "TMH_CV108"].sum()
        )
        sin_torre = float(
            df_material.loc[
                (df_material["TM1_Activo"] == 1)
                & (df_material["Rep_TM1"] != 1),
                "TMH_CV08",
            ].sum()
            + df_material.loc[
                (df_material["TM2_Activo"] == 1)
                & (df_material["Rep_TM2"] != 1),
                "TMH_CV108",
            ].sum()
        )

        total = con_torre + sin_torre
        resultados.extend([
            {
                "Pad": material,
                "Estado": "Con Torre",
                "Tonelaje": con_torre,
                "Distribucion": con_torre / total if total else 0.0,
            },
            {
                "Pad": material,
                "Estado": "Sin Torre",
                "Tonelaje": sin_torre,
                "Distribucion": sin_torre / total if total else 0.0,
            },
        ])

    return resultados


def _normalizar_gestion_fy(
    df_gestion_fy: pd.DataFrame,
    fecha_base,
) -> pd.DataFrame:
    """Adapta la salida del SP FY al contrato canónico del gráfico."""
    from datetime import date
    import re
    import unicodedata

    columnas_canonicas = [
        "Etiqueta",
        "Turnos_Evaluables",
        "Turnos_Representativos",
        "Representatividad",
        "Objetivo",
        "Orden",
        "Es_YTD",
    ]
    if df_gestion_fy is None or df_gestion_fy.empty:
        return pd.DataFrame(columns=columnas_canonicas)

    df = df_gestion_fy.copy()

    def _token(valor) -> str:
        texto = unicodedata.normalize("NFKD", str(valor))
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]", "", texto.lower())

    columnas_por_token = {_token(columna): columna for columna in df.columns}

    def _buscar_columna(*aliases):
        for alias in aliases:
            encontrada = columnas_por_token.get(_token(alias))
            if encontrada is not None:
                return encontrada
        return None

    col_etiqueta = _buscar_columna(
        "Etiqueta",
        "Periodo",
        "Mes",
        "Fecha",
        "Fecha_Mes",
        "Etiqueta_Mes",
        "Mes_Etiqueta",
    )
    col_evaluables = _buscar_columna(
        "Turnos_Evaluables",
        "Evaluables",
        "Total_Evaluables",
        "Cantidad_Evaluable",
    )
    col_representativos = _buscar_columna(
        "Turnos_Representativos",
        "Representativos",
        "Total_Representativos",
        "Cantidad_Representativa",
    )
    col_representatividad = _buscar_columna(
        "Representatividad",
        "Porcentaje",
        "Resultado",
        "Pct_Representatividad",
    )
    col_objetivo = _buscar_columna(
        "Objetivo",
        "Target",
        "Meta",
    )
    col_orden = _buscar_columna(
        "Orden",
        "Orden_Mes",
        "Orden_Fiscal",
    )
    col_es_ytd = _buscar_columna(
        "Es_YTD",
        "Tipo_Fila",
        "Tipo_Registro",
    )

    requeridas = {
        "Etiqueta/Periodo/Mes": col_etiqueta,
        "Turnos_Evaluables/Evaluables": col_evaluables,
        "Turnos_Representativos/Representativos": col_representativos,
        "Objetivo/Target": col_objetivo,
    }
    faltantes = [nombre for nombre, columna in requeridas.items() if columna is None]
    if faltantes:
        raise RuntimeError(
            "La gestión FY no contiene las columnas indispensables. "
            f"Requeridas: {faltantes}. Recibidas: {list(df.columns)}"
        )

    fecha_base = pd.Timestamp(fecha_base).normalize()
    rango_fy = _obtener_rango_fiscal_hasta_mes(fecha_base)
    inicio_fy = pd.Timestamp(rango_fy["fecha_inicio"])
    orden_corte = (
        (fecha_base.year - inicio_fy.year) * 12
        + fecha_base.month
        - inicio_fy.month
        + 1
    )

    etiquetas_originales = df[col_etiqueta]

    def _es_ytd(etiqueta, valor=None) -> bool:
        texto_etiqueta = _token(etiqueta)
        if "ytd" in texto_etiqueta or "acumulado" in texto_etiqueta:
            return True
        if valor is None or pd.isna(valor):
            return False
        if isinstance(valor, (bool, int, float)):
            return bool(valor)
        texto = _token(valor)
        return texto in {"1", "true", "si", "ytd", "acumulado"}

    if col_es_ytd is not None:
        es_ytd = pd.Series(
            [
                _es_ytd(etiqueta, valor)
                for etiqueta, valor in zip(
                    etiquetas_originales,
                    df[col_es_ytd],
                )
            ],
            index=df.index,
            dtype=bool,
        )
    else:
        es_ytd = etiquetas_originales.apply(_es_ytd).astype(bool)

    meses_es = {
        "ene": 1,
        "feb": 2,
        "mar": 3,
        "abr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dic": 12,
    }

    def _orden_desde_etiqueta(valor):
        if pd.isna(valor):
            return None
        if isinstance(valor, (pd.Timestamp, date)):
            fecha = pd.Timestamp(valor)
        elif isinstance(valor, (int, float)) and 1 <= int(valor) <= 12:
            mes = int(valor)
            anio = rango_fy["anio_fiscal"] - 1 if mes >= 7 else rango_fy["anio_fiscal"]
            fecha = pd.Timestamp(year=anio, month=mes, day=1)
        else:
            texto = str(valor).strip()
            token = _token(texto)
            mes = next(
                (numero for nombre, numero in meses_es.items() if token.startswith(nombre)),
                None,
            )
            if mes is not None:
                coincidencia_anio = re.search(r"(\d{2,4})", texto)
                if coincidencia_anio:
                    anio = int(coincidencia_anio.group(1))
                    if anio < 100:
                        anio += 2000
                else:
                    anio = (
                        rango_fy["anio_fiscal"] - 1
                        if mes >= 7
                        else rango_fy["anio_fiscal"]
                    )
                fecha = pd.Timestamp(year=anio, month=mes, day=1)
            else:
                fecha = pd.to_datetime(texto, errors="coerce")
                if pd.isna(fecha):
                    return None

        return int(
            (fecha.year - inicio_fy.year) * 12
            + fecha.month
            - inicio_fy.month
            + 1
        )

    if col_orden is not None:
        orden = pd.to_numeric(df[col_orden], errors="coerce")
    else:
        orden = pd.Series(index=df.index, dtype=float)

    orden_derivado = etiquetas_originales.apply(_orden_desde_etiqueta)
    orden = orden.where(orden.notna(), orden_derivado)
    orden = orden.where(~es_ytd, 13)

    gestion = pd.DataFrame({
        "Etiqueta_Original": etiquetas_originales,
        "Turnos_Evaluables": pd.to_numeric(
            df[col_evaluables], errors="coerce"
        ),
        "Turnos_Representativos": pd.to_numeric(
            df[col_representativos], errors="coerce"
        ),
        "Objetivo": pd.to_numeric(df[col_objetivo], errors="coerce"),
        "Orden": pd.to_numeric(orden, errors="coerce"),
        "Es_YTD": es_ytd,
    })

    if col_representatividad is not None:
        gestion["Representatividad"] = pd.to_numeric(
            df[col_representatividad],
            errors="coerce",
        )
    else:
        gestion["Representatividad"] = pd.NA

    for columna in ["Representatividad", "Objetivo"]:
        gestion[columna] = gestion[columna].apply(
            lambda valor: (
                float(valor) / 100.0
                if pd.notna(valor) and abs(float(valor)) > 1
                else float(valor)
                if pd.notna(valor)
                else float("nan")
            )
        )

    meses = gestion[
        (~gestion["Es_YTD"])
        & gestion["Orden"].between(1, orden_corte, inclusive="both")
    ].copy()
    meses = (
        meses.sort_values("Orden", kind="stable")
        .drop_duplicates("Orden", keep="last")
        .reset_index(drop=True)
    )

    if meses.empty:
        raise RuntimeError(
            "La gestión FY no contiene meses hasta la fecha evaluada. "
            f"Columnas recibidas: {list(df.columns)}"
        )
    if meses[["Turnos_Evaluables", "Turnos_Representativos", "Objetivo"]].isna().any().any():
        raise RuntimeError(
            "La gestión FY contiene valores nulos en evaluables, "
            "representativos u objetivo."
        )

    # La razón se deriva siempre de los conteos oficiales. Así el gráfico no
    # puede conservar un porcentaje calculado con una metodología anterior
    # (por ejemplo, Fecha + Turno consolidado por OR) si los conteos ya fueron
    # corregidos a Fecha + Turno + Torre.
    meses["Representatividad"] = meses["Turnos_Representativos"].div(
        meses["Turnos_Evaluables"].where(meses["Turnos_Evaluables"] != 0)
    ).fillna(0.0)

    def _etiqueta_fiscal(valor_orden: int) -> str:
        fecha = inicio_fy + pd.DateOffset(months=int(valor_orden) - 1)
        return f"{_MESES_ABR_TORRES[fecha.month]}-{str(fecha.year)[-2:]}"

    meses["Etiqueta"] = meses["Orden"].astype(int).apply(_etiqueta_fiscal)

    total_evaluables = float(meses["Turnos_Evaluables"].sum())
    total_representativos = float(meses["Turnos_Representativos"].sum())
    representatividad_ytd = (
        total_representativos / total_evaluables
        if total_evaluables
        else 0.0
    )

    filas_ytd = gestion[gestion["Es_YTD"]]
    objetivo_ytd = (
        float(filas_ytd["Objetivo"].dropna().iloc[-1])
        if not filas_ytd["Objetivo"].dropna().empty
        else float(meses["Objetivo"].iloc[-1])
    )
    ytd = pd.DataFrame([{
        "Etiqueta": "YTD",
        "Turnos_Evaluables": total_evaluables,
        "Turnos_Representativos": total_representativos,
        "Representatividad": representatividad_ytd,
        "Objetivo": objetivo_ytd,
        "Orden": 13,
        "Es_YTD": True,
    }])

    resultado = pd.concat(
        [meses[columnas_canonicas], ytd[columnas_canonicas]],
        ignore_index=True,
    )
    return resultado


def _agregar_grafico_gestion_fy(
    ws,
    df_gestion_fy: pd.DataFrame,
    tipo: str,
    fecha_base,
    fila_inicio: int,
) -> None:
    """Agrega el gráfico FY y su tabla auxiliar oculta en T:X."""
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.chart.axis import ChartLines
    from openpyxl.chart.data_source import (
        AxDataSource,
        NumData,
        NumVal,
        StrData,
        StrRef,
        StrVal,
    )
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.marker import DataPoint
    from openpyxl.chart.series import SeriesLabel
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.geometry import PresetGeometry2D
    from openpyxl.drawing.spreadsheet_drawing import (
        AnchorMarker,
        TwoCellAnchor,
    )
    from openpyxl.drawing.text import (
        CharacterProperties,
        Paragraph,
        ParagraphProperties,
        RichTextProperties,
    )
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import quote_sheetname

    if df_gestion_fy is None or df_gestion_fy.empty:
        raise RuntimeError("La gestión FY normalizada está vacía.")

    fecha_base = pd.Timestamp(fecha_base)
    anio_fiscal = _obtener_rango_fiscal_hasta_mes(fecha_base)["anio_fiscal"]
    es_quimico = str(tipo).lower() == "quimico"
    titulo = f"Gestión sobre representatividad FY{anio_fiscal % 100:02d}"

    ws.merge_cells(
        start_row=fila_inicio,
        start_column=3,
        end_row=fila_inicio,
        end_column=13,
    )
    celda_titulo = ws.cell(fila_inicio, 3, f"6.- {titulo}.")
    celda_titulo.font = Font(
        name="Arial",
        bold=True,
        color="476475",
        size=10,
    )
    celda_titulo.alignment = Alignment(
        horizontal="left",
        vertical="center",
        wrap_text=True,
    )
    ws.row_dimensions[fila_inicio].height = 20
    lado = Side(style="thin", color="595959")
    for columna in range(3, 14):
        ws.cell(fila_inicio, columna).border = Border(bottom=lado)

    # Tabla auxiliar del gráfico FY: T:X.
    fila_tabla = fila_inicio
    encabezados = [
        "Periodo",
        "Turnos evaluables",
        "Turnos representativos",
        "Representatividad",
        "Objetivo",
    ]
    for columna, encabezado in enumerate(encabezados, start=20):
        ws.cell(fila_tabla, columna, encabezado)

    etiquetas = []
    valores_representatividad = []
    valores_objetivo = []

    for offset, (_, fila) in enumerate(df_gestion_fy.iterrows(), start=1):
        etiqueta = str(fila["Etiqueta"])
        representatividad = float(fila["Representatividad"])
        objetivo = float(fila["Objetivo"])

        valores = [
            etiqueta,
            float(fila["Turnos_Evaluables"]),
            float(fila["Turnos_Representativos"]),
            representatividad,
            objetivo,
        ]
        for columna, valor in enumerate(valores, start=20):
            ws.cell(fila_tabla + offset, columna, valor)

        ws.cell(fila_tabla + offset, 23).number_format = "0.0%"
        ws.cell(fila_tabla + offset, 24).number_format = "0.0%"

        etiquetas.append(etiqueta)
        valores_representatividad.append(representatividad)
        valores_objetivo.append(objetivo)

    fila_final = fila_tabla + len(df_gestion_fy)
    categorias = Reference(
        ws,
        min_col=20,
        min_row=fila_tabla + 1,
        max_row=fila_final,
    )

    # Categorías como texto explícito y con caché. Esto evita que Excel
    # transforme o descarte las categorías cuando T:X están ocultas.
    formula_categorias = (
        f"{quote_sheetname(ws.title)}!"
        f"$T${fila_tabla + 1}:$T${fila_final}"
    )

    def _fuente_categorias() -> AxDataSource:
        return AxDataSource(
            strRef=StrRef(
                f=formula_categorias,
                strCache=StrData(
                    ptCount=len(etiquetas),
                    pt=[
                        StrVal(idx=indice, v=etiqueta)
                        for indice, etiqueta in enumerate(etiquetas)
                    ],
                ),
            )
        )

    chart = BarChart()
    chart.type = "col"
    # Químico y Físico comparten la misma estética FY vigente.
    chart.style = None
    chart.grouping = "clustered"
    chart.varyColors = False
    chart.gapWidth = 500
    chart.title = titulo
    chart.width = 30
    chart.height = 10.5
    chart.roundedCorners = False
    chart.graphical_properties = GraphicalProperties()
    chart.graphical_properties.solidFill = "FFFFFF"
    chart.graphical_properties.line.solidFill = "D9D9D9"
    chart.graphical_properties.line.width = 9525
    chart.graphical_properties.prstGeom = PresetGeometry2D(prst="rect")

    # Fundamental: el gráfico debe leer los datos aunque T:X estén ocultas.
    # openpyxl lo serializa como <plotVisOnly val="0"/>.
    chart.visible_cells_only = False

    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = 1
    chart.y_axis.numFmt = "0%"
    chart.y_axis.majorUnit = 0.1
    chart.y_axis.title = None
    chart.y_axis.delete = False
    chart.y_axis.axPos = "l"
    chart.y_axis.tickLblPos = "nextTo"
    chart.y_axis.majorTickMark = "none"
    chart.y_axis.minorTickMark = "none"
    chart.y_axis.majorGridlines = ChartLines()
    chart.y_axis.majorGridlines.graphicalProperties = GraphicalProperties()
    chart.y_axis.majorGridlines.graphicalProperties.line.solidFill = "D9D9D9"
    chart.y_axis.majorGridlines.graphicalProperties.line.width = 6350
    chart.x_axis.title = None
    chart.x_axis.delete = False
    chart.x_axis.axPos = "b"
    chart.x_axis.tickLblPos = "nextTo"
    chart.x_axis.majorTickMark = "none"
    chart.x_axis.minorTickMark = "none"
    chart.x_axis.spPr = GraphicalProperties()
    chart.x_axis.spPr.line.solidFill = "D9D9D9"
    chart.x_axis.spPr.line.width = 6350
    chart.y_axis.spPr = GraphicalProperties()
    chart.y_axis.spPr.line.noFill = True
    chart.legend.position = "b"
    chart.legend.overlay = False

    datos = Reference(
        ws,
        min_col=23,
        min_row=fila_tabla,
        max_row=fila_final,
    )
    chart.add_data(datos, titles_from_data=True)
    chart.set_categories(categorias)
    chart.series[0].cat = _fuente_categorias()
    chart.series[0].tx = SeriesLabel(v="Representatividad")
    chart.series[0].graphicalProperties.solidFill = "476475"
    chart.series[0].graphicalProperties.line.noFill = True
    if valores_representatividad:
        punto_ytd = DataPoint(idx=len(valores_representatividad) - 1)
        punto_ytd.graphicalProperties.solidFill = "E65400"
        punto_ytd.graphicalProperties.line.noFill = True
        chart.series[0].dPt = [punto_ytd]

    # Caché numérica explícita para que Excel, LibreOffice y los
    # previsualizadores rendericen el gráfico sin depender de recálculo.
    chart.series[0].val.numRef.numCache = NumData(
        formatCode="0.0%",
        ptCount=len(valores_representatividad),
        pt=[
            NumVal(idx=indice, v=valor)
            for indice, valor in enumerate(valores_representatividad)
        ],
    )

    chart.dLbls = DataLabelList()
    chart.dLbls.showVal = True
    chart.dLbls.showLegendKey = False
    chart.dLbls.showCatName = False
    chart.dLbls.showSerName = False
    chart.dLbls.showPercent = False
    chart.dLbls.showBubbleSize = False
    chart.dLbls.numFmt = "0.0%"
    # Las representatividades bajas no tienen altura suficiente para alojar
    # una etiqueta blanca centrada: Excel/LibreOffice la omiten al renderizar.
    # Ubicarla sobre la barra mantiene visibles los porcentajes pequeños.
    chart.dLbls.position = "outEnd"
    chart.dLbls.txPr = RichText(
        bodyPr=RichTextProperties(anchor="ctr"),
        p=[
            Paragraph(
                pPr=ParagraphProperties(
                    defRPr=CharacterProperties(
                        sz=1000,
                        b=True,
                        solidFill="595959",
                    )
                ),
                endParaRPr=CharacterProperties(lang="es-CL"),
            )
        ],
    )

    chart.title.tx.rich.p[0].pPr.defRPr.sz = 1400
    chart.title.tx.rich.p[0].pPr.defRPr.b = True
    chart.title.tx.rich.p[0].pPr.defRPr.solidFill = "595959"
    chart.legend.txPr = RichText(
        bodyPr=RichTextProperties(),
        p=[
            Paragraph(
                pPr=ParagraphProperties(
                    defRPr=CharacterProperties(
                        sz=1000,
                        solidFill="595959",
                    )
                ),
                endParaRPr=CharacterProperties(lang="es-CL"),
            )
        ],
    )
    chart.x_axis.txPr = RichText(
        bodyPr=RichTextProperties(),
        p=[
            Paragraph(
                pPr=ParagraphProperties(
                    defRPr=CharacterProperties(
                        sz=900,
                        solidFill="595959",
                    )
                ),
                endParaRPr=CharacterProperties(lang="es-CL"),
            )
        ],
    )
    chart.y_axis.txPr = RichText(
        bodyPr=RichTextProperties(),
        p=[
            Paragraph(
                pPr=ParagraphProperties(
                    defRPr=CharacterProperties(
                        sz=900,
                        b=False,
                        solidFill="595959",
                    )
                ),
                endParaRPr=CharacterProperties(lang="es-CL"),
            )
        ],
    )

    target_chart = LineChart()
    target_chart.visible_cells_only = False
    target_data = Reference(
        ws,
        min_col=24,
        min_row=fila_tabla,
        max_row=fila_final,
    )
    target_chart.add_data(target_data, titles_from_data=True)
    target_chart.set_categories(categorias)
    target_chart.series[0].cat = _fuente_categorias()
    target_chart.series[0].tx = SeriesLabel(v="Target")
    target_chart.series[0].val.numRef.numCache = NumData(
        formatCode="0%",
        ptCount=len(valores_objetivo),
        pt=[
            NumVal(idx=indice, v=valor)
            for indice, valor in enumerate(valores_objetivo)
        ],
    )
    target_chart.series[0].graphicalProperties.line.solidFill = "4F81BD"
    target_chart.series[0].graphicalProperties.line.prstDash = "dash"
    target_chart.series[0].graphicalProperties.line.width = 22225
    target_chart.series[0].marker.symbol = "none"
    target_chart.x_axis.axId = chart.x_axis.axId
    target_chart.y_axis.axId = chart.y_axis.axId
    # Los ejes comparten IDs con el gráfico de columnas. No deben marcarse
    # como eliminados, porque Excel aplicaría esa propiedad al eje combinado
    # y ocultaría los meses fiscales y la escala porcentual.
    target_chart.x_axis.delete = False
    target_chart.y_axis.delete = False
    chart += target_chart

    # Mantener separados el encabezado visible, los datos auxiliares y el
    # objeto gráfico. Los marcadores son base cero: para un título en la
    # fila 122, este anclaje ocupa visualmente C126:M142 y deja libre la
    # fila 125. El marcador final cae en el borde inicial de N para incluir
    # todo el ancho de M sin aumentar la altura.
    chart.anchor = TwoCellAnchor(
        editAs="twoCell",
        _from=AnchorMarker(col=2, row=fila_inicio + 3),
        to=AnchorMarker(col=13, row=fila_inicio + 19),
    )
    ws.add_chart(chart)

    # La tabla auxiliar sigue oculta, pero el gráfico puede leerla porque
    # visible_cells_only=False.
    for columna in range(20, 25):
        ws.column_dimensions[
            ws.cell(1, columna).column_letter
        ].hidden = True

    fila_fin_impresion = fila_inicio + 20
    ws.print_area = f"A1:M{fila_fin_impresion}"

    # El grafico se ancla a filas que no existen en el archivo (openpyxl no
    # escribe <row> para filas vacias, y aca max_row queda en fila_inicio+2).
    # LibreOffice tiene que inventarse su alto, y no todas las versiones
    # llegan al mismo numero. Se crean con alto explicito.
    for fila in range(fila_inicio + 1, fila_fin_impresion + 1):
        ws.row_dimensions[fila].height = 15.0


def _nombre_hoja_gestion_fy(fecha_base, tipo: str) -> str:
    fecha = pd.Timestamp(fecha_base)
    prefijo = (
        f"01_{_MESES_ABR_TORRES[fecha.month]}_"
        f"{str(fecha.year)[-2:]}"
    )
    sufijo = "Quimico" if str(tipo).lower() == "quimico" else "Fisico"
    return f"{prefijo} FY {sufijo}"[:31]


def _agregar_hoja_grafico_gestion_fy(
    wb,
    df_gestion_fy: pd.DataFrame,
    tipo: str,
    fecha_base,
) -> str | None:
    """Hoja dedicada solo al gráfico de gestión FY (para PDF sin solapes)."""
    gestion_fy_normalizada = _normalizar_gestion_fy(
        df_gestion_fy,
        fecha_base,
    )
    if gestion_fy_normalizada.empty:
        raise RuntimeError(
            f"La gestión FY {tipo.lower()} no entregó resultados "
            "para construir el gráfico."
        )

    nombre_hoja = _nombre_hoja_gestion_fy(fecha_base, tipo)
    if nombre_hoja in wb.sheetnames:
        del wb[nombre_hoja]

    ws = wb.create_sheet(title=nombre_hoja)
    ws.sheet_view.showGridLines = False

    # El gráfico FY ocupa C:M. En una hoja independiente estas columnas
    # deben ampliarse para evitar que Excel recorte meses y la barra YTD.
    for columna in range(3, 14):
        ws.column_dimensions[
            ws.cell(1, columna).column_letter
        ].width = 15

    _agregar_grafico_gestion_fy(
        ws=ws,
        df_gestion_fy=gestion_fy_normalizada,
        tipo=tipo,
        fecha_base=fecha_base,
        fila_inicio=3,
    )

    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.page_margins.left = 0.35
    ws.page_margins.right = 0.35
    ws.page_margins.top = 0.45
    ws.page_margins.bottom = 0.45

    return nombre_hoja


def _aplicar_bordes_tabla_limpia(
    ws,
    fila_ini: int,
    fila_fin: int,
    col_ini: int,
    col_fin: int,
    fila_header: int,
    fila_mtd: int | None = None,
    columnas_separadoras: tuple[int, ...] = (),
    filas_separadoras: tuple[int, ...] = (),
    lado_exterior=None,
    lado_estructura=None,
    lado_mtd=None,
) -> None:
    """Dibuja una tabla oficial sin grilla horizontal en el cuerpo.

    ``columnas_separadoras`` contiene las columnas tras las que se conserva
    una división vertical. ``filas_separadoras`` permite mantener divisiones
    semánticas puntuales, por ejemplo entre Óxido y Sulfuro.
    """
    from openpyxl.styles import Border, Side

    vacio = Side()
    exterior = lado_exterior or Side(style="thin", color="595959")
    estructura = lado_estructura or exterior
    mtd = lado_mtd or Side(style="medium", color="404040")
    separadores_col = set(columnas_separadoras)
    separadores_fila = set(filas_separadoras)

    for fila in range(fila_ini, fila_fin + 1):
        for col in range(col_ini, col_fin + 1):
            izquierda = exterior if col == col_ini else vacio
            derecha = (
                exterior
                if col == col_fin
                else estructura if col in separadores_col else vacio
            )
            arriba = exterior if fila == fila_ini else vacio
            abajo = exterior if fila == fila_fin else vacio

            if fila == fila_header:
                abajo = estructura
            if fila in separadores_fila:
                abajo = estructura
            if fila_mtd is not None and fila == fila_mtd:
                arriba = mtd
                abajo = exterior

            ws.cell(fila, col).border = Border(
                left=izquierda,
                right=derecha,
                top=arriba,
                bottom=abajo,
            )


# La hoja mensual completa mide ~2580 pt al 100% (medido sobre un reporte
# real de julio 2026). Al 45% ocupaba 1161 pt y la pagina daba 1161,75: cabia
# por 0,75 pt, y basta con que LibreOffice calcule un alto de fila apenas
# distinto para que el grafico FY se salga y quede sobre la tabla. Al 35%
# ocupa ~900 pt: 290 pt de holgura, unas 15 filas de detalle de mas.
# La escala no afecta el tamano final del reporte: normalize_single_page_to_a3
# recorta y reescala a A3 despues. Solo tiene que caber.
_ESCALA_PDF_TORRES = 35
_ESCALA_PDF_SRR = 55


def _fijar_escala_impresion(ws, escala: int) -> None:
    """Escala de impresion fija (sin fitToPage), reproducible entre versiones."""
    ws.sheet_properties.pageSetUpPr.fitToPage = False
    ws.page_setup.scale = escala
    ws.page_setup.fitToWidth = None
    ws.page_setup.fitToHeight = None


def _forzar_alturas_pdf_deterministas(ws) -> None:
    """
    Fija altura explícita para todas las filas del área de impresión.

    LibreOffice recalcula altura de filas implícitas según fuente/render y
    eso puede desplazar anclajes de gráficos (solape intermitente). Al
    materializar cada altura en la copia PDF, el layout queda estable.
    """
    from openpyxl.utils.cell import range_boundaries

    fila_fin = ws.max_row or 1
    area = ws.print_area
    rangos = getattr(area, "ranges", None)
    if rangos:
        limites = []
        for rango in rangos:
            texto = str(rango)
            coords = texto.split("!")[-1].replace("$", "")
            try:
                _, _, _, max_row = range_boundaries(coords)
            except Exception:
                continue
            limites.append(int(max_row))
        if limites:
            fila_fin = max(fila_fin, max(limites))

    altura_default = float(ws.sheet_format.defaultRowHeight or 15.0)
    for fila in range(1, int(fila_fin) + 1):
        if ws.row_dimensions[fila].height is None:
            ws.row_dimensions[fila].height = altura_default




def _agregar_hoja_mensual_torres(
    wb,
    df_bd_ton_mes: pd.DataFrame,
    tipo: str,
    df_material_turno_mes: pd.DataFrame | None = None,
    df_gestion_fy: pd.DataFrame | None = None,
    incluir_grafico_fy: bool = True,
    fecha_inicio_mes=None,
    fecha_fin_mes=None,
    fecha_corte_operacional=None,
    mapa_comentarios: dict | None = None,
) -> str | None:
    """
    Agrega una hoja mensual Químico/Físico al libro.

    Los resultados se escriben como valores calculados en Python para
    evitar GETPIVOTDATA, tablas dinámicas y fórmulas manuales frágiles.
    """
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.chart.axis import ChartLines
    from openpyxl.chart.data_source import NumData, NumFmt, NumVal
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.layout import Layout, ManualLayout
    from openpyxl.chart.series import SeriesLabel
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.spreadsheet_drawing import (
        AnchorMarker,
        TwoCellAnchor,
    )
    from openpyxl.drawing.geometry import PresetGeometry2D
    from openpyxl.drawing.image import Image as OpenpyxlImage
    from openpyxl.drawing.text import (
        CharacterProperties,
        Paragraph,
        ParagraphProperties,
        RichTextProperties,
    )
    from openpyxl.styles import (
        Alignment,
        Border,
        Font,
        PatternFill,
        Side,
    )
    from openpyxl.utils import get_column_letter

    detalle = _preparar_detalle_mensual_torres(
        df_bd_ton=df_bd_ton_mes,
        tipo=tipo,
        df_material_turno=df_material_turno_mes,
        fecha_inicio_mes=fecha_inicio_mes,
        fecha_fin_mes=fecha_fin_mes,
        fecha_corte_operacional=fecha_corte_operacional,
        mapa_comentarios=mapa_comentarios,
    )

    if detalle.empty:
        return None

    fecha_base = pd.to_datetime(detalle["Fecha"].min())
    nombre_hoja = (
        f"01_{_MESES_ABR_TORRES[fecha_base.month]}_"
        f"{str(fecha_base.year)[-2:]} {tipo}"
    )
    nombre_hoja = nombre_hoja[:31]

    if nombre_hoja in wb.sheetnames:
        del wb[nombre_hoja]

    ws = wb.create_sheet(title=nombre_hoja)
    ws.sheet_view.showGridLines = False

    resumen = _calcular_resumen_mensual_torres(detalle)
    tonelaje_material = _calcular_tonelaje_por_material_torres(detalle)

    # Paleta y tipografías replicadas desde el reporte histórico.
    azul_header = PatternFill("solid", fgColor="D7E1E7")
    azul_grupo = PatternFill("solid", fgColor="D7E1E7")
    azul_alt = PatternFill("solid", fgColor="D7E1E7")
    amarillo = PatternFill("solid", fgColor="FFF2CC")
    gris = PatternFill("solid", fgColor="F2F2F2")

    font_header = Font(
        name="Arial",
        bold=True,
        color="476475",
        size=10,
    )
    font_resumen_header = Font(
        name="Arial",
        bold=False,
        color="476475",
        size=10,
    )
    font_titulo = Font(
        name="Arial",
        bold=True,
        color="476475",
        size=12,
    )
    font_normal = Font(
        name="Arial",
        color="476475",
        size=10,
    )
    thin = Side(style="thin", color="595959")
    medium = Side(style="medium", color="404040")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    border_grupo = Border(
        left=medium,
        right=medium,
        top=medium,
        bottom=medium,
    )

    def _aplicar_bordes_tabla(
        fila_ini: int,
        col_ini: int,
        fila_fin: int,
        col_fin: int,
        borde_exterior=medium,
        borde_interior=thin,
    ) -> None:
        """Aplica grilla interna y contorno reforzado, incluso en rangos combinados."""
        for fila in range(fila_ini, fila_fin + 1):
            for col in range(col_ini, col_fin + 1):
                ws.cell(fila, col).border = Border(
                    left=(borde_exterior if col == col_ini else borde_interior),
                    right=(borde_exterior if col == col_fin else borde_interior),
                    top=(borde_exterior if fila == fila_ini else borde_interior),
                    bottom=(borde_exterior if fila == fila_fin else borde_interior),
                )

    def _aplicar_subrayado(
        fila: int,
        col_ini: int,
        col_fin: int,
        lado=thin,
    ) -> None:
        """Replica la línea inferior de los títulos de sección del reporte oficial."""
        for col in range(col_ini, col_fin + 1):
            celda = ws.cell(fila, col)
            celda.border = Border(bottom=lado)

    def _aplicar_semaforo(cell, valor, center_align):
        """
        Muestra un semáforo visual:
        - 1 -> círculo verde
        - 0 -> círculo rojo
        - None -> vacío
        """
        if valor == 1:
            cell.value = "●"
            cell.font = Font(
                name="Arial",
                bold=True,
                color="70AD47",
                size=16,
            )
            cell.alignment = center_align

        elif valor == 0:
            cell.value = "●"
            cell.font = Font(
                name="Arial",
                bold=True,
                color="C55A11",
                size=16,
            )
            cell.alignment = center_align

        else:
            cell.value = None
            cell.font = font_normal
            cell.alignment = center_align

    center = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )
    left = Alignment(
        horizontal="left",
        vertical="center",
        wrap_text=True,
    )
    left_no_wrap = Alignment(
        horizontal="left",
        vertical="center",
        wrap_text=False,
    )

    tipo_titulo = "Química" if tipo.lower() == "quimico" else "Física"
    mes_texto = f"{_MESES_NOMBRE_TORRES[fecha_base.month]}, {fecha_base.year}"

    ws.merge_cells("C5:M7")
    ws["C5"] = (
        "Muestras representativas de torres de muestreo - "
        f"Muestra {tipo_titulo} - {mes_texto}"
    )
    ws["C5"].font = font_titulo
    ws["C5"].alignment = center

    ws.merge_cells("J2:L4")
    ws["J2"] = (
        "Superintendencia de Medición y Reconciliación\n"
        "Gerencia Planificación Integrada"
    )
    ws["J2"].font = Font(
        name="Arial",
        bold=True,
        color="476475",
        size=10,
    )
    ws["J2"].alignment = center

    logo_path = os.path.join(
        os.path.dirname(_REPORT_EXPORT_DIR),
        "assets",
        "logoBHP.png",
    )
    if os.path.isfile(logo_path):
        logo = OpenpyxlImage(logo_path)
        logo.width = 96
        logo.height = 39
        ws.add_image(logo, "M2")

    # ------------------------------------------------------------
    # 1. Tonelaje por material y condición de representatividad
    # ------------------------------------------------------------
    ws.merge_cells("C9:H9")
    ws["C9"] = (
        "1.- Mineral apilado y caracterizado con información "
        f"{tipo_titulo.lower()} de torres de muestreo."
    )
    ws["C9"].font = font_header
    ws["C9"].alignment = left
    _aplicar_subrayado(9, 3, 8)

    # Misma estructura visual del reporte de referencia:
    # "Pad" y un encabezado agrupado para las tres columnas de mineral.
    ws["C10"] = "Pad"
    ws.merge_cells("D10:F10")
    ws["D10"] = "Mineral Apilado (ton)"

    for celda in ["C10", "D10"]:
        ws[celda].font = font_header
        ws[celda].alignment = center
        ws[celda].border = border

    for idx, fila in enumerate(tonelaje_material, start=11):
        ws.cell(idx, 3, fila["Pad"])
        ws.cell(idx, 4, fila["Estado"])
        ws.cell(idx, 5, fila["Tonelaje"])
        ws.cell(idx, 6, fila["Distribucion"])

        for col in range(3, 7):
            cell = ws.cell(idx, col)
            cell.font = font_normal
            cell.alignment = center
            cell.border = border

        ws.cell(idx, 5).number_format = "#,##0.0"
        ws.cell(idx, 6).number_format = "0.0%"

    ws.merge_cells("C11:C12")
    ws.merge_cells("C13:C14")
    ws["C11"].alignment = center
    ws["C13"].alignment = center

    # Estilo oficial: contorno, separadores de columnas y una sola división
    # semántica entre Óxido y Sulfuro; sin grilla interna por fila.
    _aplicar_bordes_tabla_limpia(
        ws,
        fila_ini=10,
        fila_fin=14,
        col_ini=3,
        col_fin=6,
        fila_header=10,
        columnas_separadoras=(3, 4, 5),
        filas_separadoras=(12,),
        lado_exterior=thin,
        lado_estructura=thin,
        lado_mtd=medium,
    )

    # ------------------------------------------------------------
    # Resúmenes semanales y MTD
    # ------------------------------------------------------------
    # Serie auxiliar de target. Se escriben siete valores para mantener
    # correspondencia exacta con las seis semanas y el MTD. Esta igualdad
    # de longitudes mejora la compatibilidad del gráfico entre Excel y
    # otros renderizadores sin alterar el target oficial de 85%.
    ws["Q1"] = "Target"
    ws["Q1"].font = font_header
    ws["Q1"].fill = azul_header
    ws["Q1"].alignment = center
    ws["Q1"].border = border
    for fila_target_aux in range(2, 9):
        ws.cell(fila_target_aux, 17, 0.85)
        ws.cell(fila_target_aux, 17).number_format = "0%"
        ws.cell(fila_target_aux, 17).alignment = center
        ws.cell(fila_target_aux, 17).border = border
    # Ocultar visualmente la tabla auxiliar del target sin eliminar
    # los valores utilizados por los gráficos.
    for fila_aux in range(1, 9):
        celda_aux = ws.cell(fila_aux, 17)

        celda_aux.number_format = ";;;"
        celda_aux.font = Font(
            name="Arial",
            color="FFFFFF",
            size=1,
        )
        celda_aux.fill = PatternFill(
            fill_type=None,
        )
        celda_aux.border = Border()

    # Rangos auxiliares de los gráficos. Los ceros se conservan para que
    # Excel muestre las etiquetas 0% igual que en el reporte oficial.
    for columna_aux in ("X", "Y", "Z"):
        ws.column_dimensions[columna_aux].hidden = True

    secciones = [
        (
            "TM1",
            16,
            "2.- Torre de muestreo #1: Distribución porcentual de muestras obtenidas y perdidas.",
            "Torre #1",
        ),
        (
            "TM2",
            27,
            "3.- Torre de muestreo #2: Distribución porcentual de muestras obtenidas y perdidas.",
            "Torre #2",
        ),
        (
            "COMBINADO",
            38,
            "4.- Sistema TM1 y TM2: Distribución porcentual de muestras obtenidas y perdidas.",
            "Torre #1 y #2",
        ),
    ]

    for clave, fila_inicio, titulo_seccion, titulo_grafico in secciones:
        ws.merge_cells(
            start_row=fila_inicio,
            start_column=3,
            end_row=fila_inicio,
            end_column=8,
        )
        ws.cell(fila_inicio, 3, titulo_seccion)
        ws.cell(fila_inicio, 3).font = font_header
        ws.cell(fila_inicio, 3).alignment = left
        _aplicar_subrayado(fila_inicio, 3, 8)

        encabezados_por_seccion = {
            "TM1": [
                f"{_MESES_NOMBRE_TORRES[fecha_base.month]} {fecha_base.year}",
                "Muestras representativas TM1",
                "Muestras perdidas por Falla TM 1",
                "Total TM1",
            ],
            "TM2": [
                f"{_MESES_NOMBRE_TORRES[fecha_base.month]} {fecha_base.year}",
                "Muestras representativas TM2",
                "Muestras perdidas por Falla TM 2",
                "Total TM2",
            ],
            "COMBINADO": [
                f"{_MESES_NOMBRE_TORRES[fecha_base.month]} {fecha_base.year}",
                "Muestras representativas TM1+TM2",
                "Muestras perdidas por Falla TM1+TM2",
                "Total TM1+TM2",
            ],
        }
        encabezados = encabezados_por_seccion[clave]
        for col, valor in enumerate(encabezados, start=3):
            cell = ws.cell(fila_inicio + 1, col, valor)
            cell.font = font_resumen_header
            cell.alignment = center
            cell.border = border

        for offset, fila_resumen in enumerate(resumen[clave], start=2):
            fila_excel = fila_inicio + offset
            ws.cell(fila_excel, 3, fila_resumen["Periodo"])
            ws.cell(
                fila_excel,
                4,
                fila_resumen["Pct_Representativos"],
            )
            ws.cell(
                fila_excel,
                5,
                fila_resumen["Pct_No_Representativos"],
            )
            ws.cell(fila_excel, 6, fila_resumen["Total"])

            for col in range(3, 7):
                cell = ws.cell(fila_excel, col)
                cell.font = font_normal
                cell.alignment = center
                cell.border = border

            for col in range(4, 7):
                ws.cell(fila_excel, col).number_format = "0.0%"

            if fila_resumen["Periodo"] == "MTD":
                for col in range(3, 7):
                    ws.cell(fila_excel, col).font = Font(
                        name="Arial",
                        color="476475",
                        size=10,
                    )

        fila_target = fila_inicio + 9
        ws.merge_cells(
            start_row=fila_target,
            start_column=4,
            end_row=fila_target,
            end_column=6,
        )
        ws.cell(
            fila_target,
            4,
            "Target de muestras representativas: 85%",
        )
        ws.cell(fila_target, 4).font = Font(
            name="Arial",
            bold=True,
            color="476475",
            size=10,
        )
        ws.cell(fila_target, 4).alignment = left_no_wrap

        # Resumen limpio: sin líneas entre semanas, conservando contorno,
        # encabezado, separadores de columnas y la entrada destacada a MTD.
        _aplicar_bordes_tabla_limpia(
            ws,
            fila_ini=fila_inicio + 1,
            fila_fin=fila_inicio + 8,
            col_ini=3,
            col_fin=6,
            fila_header=fila_inicio + 1,
            fila_mtd=fila_inicio + 8,
            columnas_separadoras=(3, 4, 5),
            lado_exterior=thin,
            lado_estructura=thin,
            lado_mtd=medium,
        )

        # Gráfico equivalente al reporte oficial:
        # columnas 100% apiladas, etiquetas porcentuales y línea target 85%.
        fila_aux_grafico = {
            "TM1": 2,
            "TM2": 12,
            "COMBINADO": 22,
        }[clave]
        ws.cell(fila_aux_grafico, 24, "Periodo")
        ws.cell(fila_aux_grafico, 25, encabezados[1])
        ws.cell(fila_aux_grafico, 26, encabezados[2])
        for indice_aux, fila_resumen in enumerate(resumen[clave], 1):
            ws.cell(
                fila_aux_grafico + indice_aux, 24,
                fila_resumen["Periodo"],
            )
            ws.cell(
                fila_aux_grafico + indice_aux, 25,
                float(fila_resumen["Pct_Representativos"] or 0.0),
            )
            ws.cell(
                fila_aux_grafico + indice_aux, 26,
                float(fila_resumen["Pct_No_Representativos"] or 0.0),
            )
            ws.cell(fila_aux_grafico + indice_aux, 25).number_format = "0.0%"
            ws.cell(fila_aux_grafico + indice_aux, 26).number_format = "0.0%"

        chart = BarChart()
        chart.visible_cells_only = False
        chart.type = "col"
        chart.grouping = "percentStacked"
        chart.overlap = 100
        chart.gapWidth = 150
        chart.varyColors = False
        chart.title = titulo_grafico
        # El título no debe superponerse con la leyenda. En el reporte
        # oficial ambos elementos reservan su propio espacio vertical.
        chart.title.overlay = False
        chart.roundedCorners = False
        chart.height = 7.24
        chart.width = 18.40
        chart.graphical_properties = GraphicalProperties(solidFill="FFFFFF")
        chart.graphical_properties.prstGeom = PresetGeometry2D(prst="rect")
        chart.graphical_properties.line.solidFill = "7F8F9B"
        chart.graphical_properties.line.width = 9525

        # Ejes como en el reporte oficial:
        # - Eje Y con porcentajes visibles
        # - Eje X con Semana 1 ... Semana 6 y MTD
        # - sin título de eje X
        chart.x_axis.title = None
        chart.y_axis.title = "Muestras representativas"

        chart.x_axis.delete = False
        chart.y_axis.delete = False

        chart.y_axis.scaling.min = 0
        chart.y_axis.scaling.max = 1
        chart.y_axis.numFmt = NumFmt(formatCode="0%", sourceLinked=True)
        chart.y_axis.majorUnit = None
        chart.y_axis.axPos = "l"
        chart.y_axis.tickLblPos = "nextTo"
        chart.y_axis.majorTickMark = "none"
        chart.y_axis.minorTickMark = "none"
        chart.y_axis.crossBetween = "between"

        chart.x_axis.axPos = "b"
        chart.x_axis.tickLblPos = "nextTo"
        chart.x_axis.majorTickMark = "none"
        chart.x_axis.minorTickMark = "none"

        chart.legend.position = "t"
        chart.legend.overlay = False
        chart.x_axis.spPr = GraphicalProperties()
        chart.x_axis.spPr.line.solidFill = "476475"
        chart.x_axis.spPr.line.width = 19050
        chart.y_axis.spPr = GraphicalProperties()
        chart.y_axis.spPr.line.noFill = True
        chart.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties())
        chart.y_axis.majorGridlines.spPr.line.solidFill = "476475"
        chart.y_axis.majorGridlines.spPr.line.width = 3175

        data = Reference(
            ws,
            min_col=25,
            max_col=26,
            min_row=fila_aux_grafico,
            max_row=fila_aux_grafico + 7,
        )
        categorias = Reference(
            ws,
            min_col=24,
            min_row=fila_aux_grafico + 1,
            max_row=fila_aux_grafico + 7,
        )
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categorias)

        # Nombres explícitos para que Excel y otros renderizadores conserven
        # exactamente la leyenda del reporte de referencia.
        chart.series[0].tx = SeriesLabel(v=encabezados[1])
        chart.series[1].tx = SeriesLabel(v=encabezados[2])

        # OpenPyXL no siempre escribe el caché de los datos del gráfico.
        # Se incorpora explícitamente para que Excel, LibreOffice y los
        # previsualizadores interpreten 0,125 como 12,5% y no como 125m.
        valores_series = [
            [
                float(ws.cell(fila_inicio + offset, 4).value or 0.0)
                for offset in range(2, 9)
            ],
            [
                float(ws.cell(fila_inicio + offset, 5).value or 0.0)
                for offset in range(2, 9)
            ],
        ]
        for indice_serie, valores_cache in enumerate(valores_series):
            chart.series[indice_serie].val.numRef.numCache = NumData(
                formatCode="0.0%",
                ptCount=len(valores_cache),
                pt=[
                    NumVal(idx=indice, v=valor)
                    for indice, valor in enumerate(valores_cache)
                ],
            )

        # Colores y bordes de las series del reporte oficial.
        chart.series[0].graphicalProperties.solidFill = "476475"
        chart.series[0].graphicalProperties.line.noFill = True
        chart.series[1].graphicalProperties.solidFill = "E65400"
        chart.series[1].graphicalProperties.line.noFill = True

        # Etiquetas dentro de las columnas, en porcentaje y texto blanco.
        chart.dLbls = DataLabelList()
        chart.dLbls.showLegendKey = False
        # Se muestran los valores con formato porcentual, igual que en
        # el reporte oficial. Más abajo se incorporan cachés numéricas
        # para mejorar la compatibilidad con otros renderizadores.
        chart.dLbls.showVal = False
        chart.dLbls.showCatName = False
        chart.dLbls.showSerName = False
        chart.dLbls.showPercent = False
        chart.dLbls.showLeaderLines = False
        chart.dLbls.txPr = RichText(
            bodyPr=RichTextProperties(anchor="ctr"),
            p=[
                Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(
                            sz=1050,
                            solidFill="FFFFFF",
                        )
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )
            ],
        )

        # Tipografía del título, leyenda y ejes según el reporte histórico.
        # El título y la leyenda se reducen al tamaño del reporte
        # oficial para evitar superposición entre ambos elementos.
        for serie in chart.series:
            serie.dLbls = DataLabelList()
            serie.dLbls.numFmt = "0.0%"
            serie.dLbls.showLegendKey = False
            serie.dLbls.showVal = True
            serie.dLbls.showCatName = False
            serie.dLbls.showSerName = False
            serie.dLbls.showPercent = False
            serie.dLbls.showLeaderLines = False
            serie.dLbls.spPr = GraphicalProperties(noFill=True)
            serie.dLbls.spPr.line.noFill = True
            serie.dLbls.txPr = RichText(
                bodyPr=RichTextProperties(anchor="ctr", spAutoFit=True),
                p=[
                    Paragraph(
                        pPr=ParagraphProperties(
                            defRPr=CharacterProperties(
                                sz=1050,
                                solidFill="FFFFFF",
                            )
                        ),
                        endParaRPr=CharacterProperties(lang="es-CL"),
                    )
                ],
            )

        chart.title.tx.rich.p[0].pPr.defRPr = CharacterProperties(
            sz=1200,
            b=True,
            solidFill="476475",
        )
        chart.legend.txPr = RichText(
            bodyPr=RichTextProperties(),
            p=[
                Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(
                            sz=900,
                            solidFill="476475",
                        )
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )
            ],
        )
        chart.x_axis.txPr = RichText(
            bodyPr=RichTextProperties(),
            p=[
                Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(
                            sz=1000,
                            solidFill="476475",
                        )
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )
            ],
        )
        chart.y_axis.txPr = RichText(
            bodyPr=RichTextProperties(),
            p=[
                Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(
                            sz=1000,
                            solidFill="476475",
                        )
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )
            ],
        )
        chart.y_axis.title.tx.rich.p[0].pPr.defRPr = CharacterProperties(
            sz=1000,
            b=True,
            solidFill="476475",
        )

        # Línea de target en el mismo eje de las columnas. Esto evita el
        # segundo eje vertical que aparecía en la versión anterior.
        target_chart = LineChart()
        target_chart.visible_cells_only = False
        target_data = Reference(
            ws,
            min_col=17,
            min_row=1,
            max_row=8,
        )
        target_chart.add_data(target_data, titles_from_data=True)
        target_chart.set_categories(categorias)
        target_chart.series[0].tx = SeriesLabel(v="Target")
        target_chart.series[0].val.numRef.numCache = NumData(
            formatCode="0%",
            ptCount=7,
            pt=[NumVal(idx=indice, v=0.85) for indice in range(7)],
        )
        target_chart.series[0].graphicalProperties.line.solidFill = "4F81BD"
        target_chart.series[0].graphicalProperties.line.prstDash = "dash"
        target_chart.series[0].graphicalProperties.line.width = 22225
        target_chart.series[0].marker.symbol = "none"
        target_chart.x_axis.axId = chart.x_axis.axId
        target_chart.y_axis.axId = chart.y_axis.axId
        target_chart.y_axis.title = None
        target_chart.x_axis.title = None
        target_chart.x_axis.delete = True
        target_chart.y_axis.delete = True

        chart += target_chart

        # Área interna del gráfico. Los dos primeros gráficos poseen
        # ajustes ligeramente distintos en el archivo de referencia.
        if clave == "TM1":
            chart.layout = Layout(
                manualLayout=ManualLayout(
                    layoutTarget="inner",
                    xMode="edge",
                    yMode="edge",
                    x=0.0754470505,
                    y=0.2985221576,
                    w=0.9098901360,
                    h=0.5962449842,
                )
            )
        elif clave == "TM2":
            chart.layout = Layout(
                manualLayout=ManualLayout(
                    layoutTarget="inner",
                    xMode="edge",
                    yMode="edge",
                    x=0.0885002013,
                    y=0.2532549190,
                    w=0.9044311103,
                    h=0.6453989123,
                )
            )
        elif clave == "COMBINADO":
            chart.layout = Layout(
                manualLayout=ManualLayout(
                    layoutTarget="inner",
                    xMode="edge",
                    yMode="edge",
                    x=0.100,
                    y=0.2532549190,
                    w=0.885,
                    h=0.6453989123,
                )
            )

        # Anclajes exactos de los tres gráficos visibles del reporte.
        anclajes_quimico = {
            "TM1": (
                AnchorMarker(col=8, colOff=1761016, row=7, rowOff=168004),
                AnchorMarker(col=12, colOff=1074579, row=20, rowOff=125697),
            ),
            "TM2": (
                AnchorMarker(col=8, colOff=1787486, row=21, rowOff=63262),
                AnchorMarker(col=12, colOff=1095969, row=34, rowOff=25940),
            ),
            "COMBINADO": (
                AnchorMarker(col=8, colOff=1798841, row=34, rowOff=96617),
                AnchorMarker(col=12, colOff=1090637, row=47, rowOff=58082),
            ),
        }
        anclajes_fisico = {
            "TM1": (
                AnchorMarker(col=8, colOff=1856513, row=7, rowOff=83409),
                AnchorMarker(col=12, colOff=1238983, row=20, rowOff=96459),
            ),
            "TM2": (
                AnchorMarker(col=8, colOff=1862862, row=21, rowOff=9405),
                AnchorMarker(col=12, colOff=1249142, row=34, rowOff=13565),
            ),
            "COMBINADO": (
                AnchorMarker(col=8, colOff=1860322, row=34, rowOff=118566),
                AnchorMarker(col=12, colOff=1246602, row=47, rowOff=123996),
            ),
        }
        anclajes = (
            anclajes_quimico
            if tipo.lower() == "quimico"
            else anclajes_fisico
        )
        desde, hasta = anclajes[clave]
        chart.anchor = TwoCellAnchor(
            editAs="twoCell",
            _from=desde,
            to=hasta,
        )
        ws.add_chart(chart)

    # ------------------------------------------------------------
    # Detalle turno a turno
    # ------------------------------------------------------------
    ws.merge_cells("C53:M53")
    ws["C53"] = (
        "5.- Detalle turno a turno de mineral apilado entre toma de muestras, "
        "muestras representativas y comentarios sobre muestras no representativas."
    )
    ws["C53"].font = font_header
    ws["C53"].alignment = left
    _aplicar_subrayado(53, 3, 13)

    ws.merge_cells("G55:I55")
    ws["G55"] = "Torre de muestreo #1"
    ws.merge_cells("J55:L55")
    ws["J55"] = "Torre de muestreo #2"

    for celda in ["G55", "J55"]:
        ws[celda].fill = azul_grupo
        ws[celda].font = font_header
        ws[celda].alignment = center
        ws[celda].border = border_grupo

    headers_detalle = [
        "Semana",
        "Fecha",
        "Pad",
        "Turno",
        "TMH\nCV-08",
        "Muestra representativa CV-08",
        "Comentarios",
        "TMH\nCV-108",
        "Muestra representativa CV-108",
        "Comentarios",
        "Representatividad Turno\n(árbol de decisión)",
    ]

    for col, valor in enumerate(headers_detalle, start=3):
        cell = ws.cell(56, col, valor)
        cell.fill = azul_header
        cell.font = font_header
        cell.alignment = center
        cell.border = border_grupo

    # Tablas auxiliares de auditoría: reemplazan los conteos ocultos y
    # fórmulas COUNTIFS del archivo histórico.
    auditorias = [
        ("TM1", 55, "Auditoría TM1"),
        ("TM2", 66, "Auditoría TM2"),
        ("COMBINADO", 77, "Auditoría TM1 + TM2"),
    ]

    for clave, fila_inicio_auditoria, titulo_auditoria in auditorias:
        ws.merge_cells(
            start_row=fila_inicio_auditoria,
            start_column=15,
            end_row=fila_inicio_auditoria,
            end_column=18,
        )
        ws.cell(fila_inicio_auditoria, 15, titulo_auditoria)
        ws.cell(fila_inicio_auditoria, 15).fill = amarillo
        ws.cell(fila_inicio_auditoria, 15).font = font_header
        ws.cell(fila_inicio_auditoria, 15).alignment = center

        encabezados_auditoria = [
            "Periodo",
            "Turnos activos",
            "Representativos",
            "No representativos",
        ]
        for col, valor in enumerate(encabezados_auditoria, start=15):
            cell = ws.cell(fila_inicio_auditoria + 1, col, valor)
            cell.fill = amarillo
            cell.font = font_header
            cell.alignment = center
            cell.border = border

        for offset, fila_resumen in enumerate(resumen[clave], start=2):
            fila_excel = fila_inicio_auditoria + offset
            valores_auditoria = [
                fila_resumen["Periodo"],
                fila_resumen["Turnos_Activos"],
                fila_resumen["Representativos"],
                fila_resumen["No_Representativos"],
            ]
            for col, valor in enumerate(valores_auditoria, start=15):
                cell = ws.cell(fila_excel, col, valor)
                cell.fill = amarillo
                cell.font = font_normal
                cell.alignment = center
                cell.border = border

            if fila_resumen["Periodo"] == "MTD":
                for col in range(15, 19):
                    ws.cell(fila_excel, col).font = Font(
                        name="Arial",
                        bold=True,
                        color="476475",
                        size=10,
                    )

    fila_datos = 57
    for indice, (_, fila) in enumerate(detalle.iterrows()):
        row_excel = fila_datos + indice

        valores = [
            fila["Semana"],
            fila["Fecha"].to_pydatetime(),
            fila["Pad"],
            fila["Turno"],
            fila["TMH_CV08"] if fila["TM1_Activo"] else None,
            fila["Rep_TM1"] if fila["TM1_Activo"] else None,
            fila["Comentario_TM1"],
            fila["TMH_CV108"] if fila["TM2_Activo"] else None,
            fila["Rep_TM2"] if fila["TM2_Activo"] else None,
            fila["Comentario_TM2"],
            fila["Rep_Turno"],
        ]

        for col, valor in enumerate(valores, start=3):
            cell = ws.cell(row_excel, col, valor)
            cell.font = font_normal
            cell.alignment = center if col not in [9, 12] else left
            cell.border = border

            if indice % 2 == 1:
                cell.fill = azul_alt

        ws.cell(row_excel, 4).number_format = "dd-mm-yyyy"
        ws.cell(row_excel, 7).number_format = "#,##0.0"
        ws.cell(row_excel, 10).number_format = "#,##0.0"

        for col in [8, 11, 13]:
            valor = ws.cell(row_excel, col).value
            _aplicar_semaforo(
                ws.cell(row_excel, col),
                valor,
                center,
            )

        if fila["Pad"] == "Sin clasificar":
            ws.cell(row_excel, 5).fill = gris

    ultima_fila = fila_datos + len(detalle) - 1

    # Bordes del detalle: contorno oscuro, divisiones internas finas y
    # grupos de torres claramente delimitados.
    _aplicar_bordes_tabla(
        56,
        3,
        ultima_fila,
        13,
        borde_exterior=medium,
        borde_interior=thin,
    )
    _aplicar_bordes_tabla(55, 7, 55, 9, borde_exterior=medium)
    _aplicar_bordes_tabla(55, 10, 55, 12, borde_exterior=medium)

    # Cada tabla de auditoría mantiene una grilla completa y un contorno
    # visible para que no quede como un bloque suelto sin terminación.
    for _, fila_inicio_auditoria, _ in auditorias:
        _aplicar_bordes_tabla(
            fila_inicio_auditoria,
            15,
            fila_inicio_auditoria + 8,
            18,
            borde_exterior=thin,
            borde_interior=thin,
        )

    gestion_fy_normalizada = _normalizar_gestion_fy(
        df_gestion_fy,
        fecha_base,
    )
    if incluir_grafico_fy:
        if gestion_fy_normalizada.empty:
            raise RuntimeError(
                f"La gestión FY {tipo.lower()} no entregó resultados "
                "para construir el gráfico."
            )

        # En el formato mensual de julio la sección FY comienza en la fila
        # 122. Si el detalle creciera, conserva al menos tres filas completas
        # entre la última fila de datos y el título de la sección.
        fila_grafico = max(122, ultima_fila + 4)
        _agregar_grafico_gestion_fy(
            ws=ws,
            df_gestion_fy=gestion_fy_normalizada,
            tipo=tipo,
            fecha_base=fecha_base,
            fila_inicio=fila_grafico,
        )
    elif gestion_fy_normalizada.empty:
        raise RuntimeError(
            f"La gestión FY {tipo.lower()} no entregó resultados "
            "para construir el gráfico."
        )

    ws.auto_filter.ref = f"C56:M{ultima_fila}"
    ws.freeze_panes = None

    # Dimensiones replicadas desde las hojas oficiales. Estas medidas
    # controlan tanto la lectura de las tablas como el tamaño real de los
    # gráficos, porque estos utilizan anclajes de dos celdas.
    if tipo.lower() == "quimico":
        anchos = {
            "A": 4.08203125,
            "B": 1.5,
            "C": 15.08203125,
            "D": 15.5,
            "E": 16.5,
            "F": 15.5,
            "G": 10.08203125,
            "H": 13.5,
            "I": 42.9140625,
            "J": 9.5,
            "K": 13.5,
            "L": 44.0,
            "M": 19.9140625,
            "N": 3.5,
        }
    else:
        anchos = {
            "A": 4.9140625,
            "B": 1.5,
            "C": 12.9140625,
            "D": 15.5,
            "E": 16.5,
            "F": 15.5,
            "G": 9.0,
            "H": 13.5,
            "I": 44.6640625,
            "J": 9.5,
            "K": 13.5,
            "L": 47.08203125,
            "M": 19.9140625,
            "N": 1.5,
        }

    # Las columnas de auditoría quedan fuera del cuerpo principal y con
    # ancho suficiente para que sus encabezados no se recorten.
    anchos.update({
        "O": 15.0,
        "P": 18.0,
        "Q": 18.0,
        "R": 18.0,
    })

    # En A3 vertical la altura de las 142 filas determina la escala. Ampliar
    # sólo C:M aprovecha mejor el ancho disponible sin alterar alturas,
    # fuentes, datos ni las columnas auxiliares fuera del área de impresión.
    columnas_visibles_pdf = set("CDEFGHIJKLM")
    factor_ancho_pdf = 1.12
    for columna, ancho in anchos.items():
        ws.column_dimensions[columna].width = (
            ancho * factor_ancho_pdf
            if columna in columnas_visibles_pdf
            else ancho
        )

    # N funciona como separación visual entre el reporte y la auditoría.
    ws.column_dimensions["N"].hidden = True

    alturas = {
        2: 14.25,
        3: 14.5,
        4: 14.5,
        5: 14.5,
        6: 14.5,
        7: 14.5,
        9: 32.0,
        10: 18.0,
        16: 32.0,
        17: 37.5,
        27: 32.0,
        28: 37.5,
        38: 32.0,
        39: 37.5,
        53: 20.0,
        55: 15.0,
        56: 39.5,
    }
    for fila, altura in alturas.items():
        ws.row_dimensions[fila].height = altura

    # Encabezados de las tablas auxiliares de auditoría.
    for fila in [56, 67, 78]:
        ws.row_dimensions[fila].height = 39.5
    for fila in [55, 66, 77]:
        ws.row_dimensions[fila].height = 18.0

    ws.sheet_view.zoomScale = 85
    ws.sheet_view.zoomScaleNormal = 85

    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    _fijar_escala_impresion(ws, _ESCALA_PDF_TORRES)
    ws.print_options.horizontalCentered = True
    ws.print_options.verticalCentered = False
    ws.page_margins.left = 0.15
    ws.page_margins.right = 0.15
    ws.page_margins.top = 0.20
    ws.page_margins.bottom = 0.20
    ws.page_margins.header = 0.0
    ws.page_margins.footer = 0.0

    if not incluir_grafico_fy:
        ws.print_area = f"A1:M{ultima_fila}"

    return nombre_hoja


def _fetch_fuentes_mensuales_torres(
    fecha_fin,
    fecha_corte_operacional=None,
) -> dict:
    """
    Consulta las fuentes necesarias para las hojas mensuales RN-046
    (Químico y Físico) del mes evaluado.
    """
    fin_d = pd.to_datetime(fecha_fin).date()
    corte_d = pd.to_datetime(
        fecha_corte_operacional or fin_d
    ).date()
    rango_fy = _obtener_rango_fiscal_hasta_mes(corte_d)

    fecha_inicio_mes = fin_d.replace(day=1)
    fecha_fin_mes = fin_d
    fecha_corte_exclusiva = (
        pd.Timestamp(corte_d) + pd.Timedelta(days=1)
    ).date()

    df_bd_ton_mes = fetch_bd_ton_report(
        start_date=fecha_inicio_mes,
        end_date=corte_d,
    )
    if df_bd_ton_mes.empty:
        raise RuntimeError(
            "BD Ton no entregó datos para el mes evaluado."
        )

    try:
        df_turno_mes = fetch_estado_apilado_turno_representatividad(
            start_date=fecha_inicio_mes,
            end_date=fecha_corte_exclusiva,
        )
    except Exception as material_error:
        raise RuntimeError(
            "No fue posible obtener el estado de apilado por turno "
            "necesario para aplicar RN-046."
        ) from material_error

    if df_turno_mes.empty:
        raise RuntimeError(
            "El estado de apilado por turno no entregó datos para el mes "
            "evaluado; no es posible determinar la "
            "evaluabilidad oficial de los turnos."
        )

    df_gestion_fy_quimico = fetch_gestion_representatividad_fy(
        anio_fiscal=rango_fy["anio_fiscal"],
        tipo="QUIMICO",
        alcance="COMBINADO",
        objetivo=0.85,
        fecha_corte=corte_d,
    )
    if df_gestion_fy_quimico.empty:
        raise RuntimeError(
            "La gestión FY química no entregó resultados."
        )

    df_gestion_fy_fisico = fetch_gestion_representatividad_fy(
        anio_fiscal=rango_fy["anio_fiscal"],
        tipo="FISICO",
        alcance="COMBINADO",
        objetivo=0.85,
        fecha_corte=corte_d,
    )
    if df_gestion_fy_fisico.empty:
        raise RuntimeError(
            "La gestión FY física no entregó resultados."
        )

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


def _build_xlsx_pdf_desde_excel(
    xlsx_bytes: bytes,
    tipo_analisis: str,
    fecha_fin,
) -> tuple[bytes, str]:
    """
    Extrae del mismo Excel descargable la hoja Quimico o Fisico y la prepara
    como una pagina A3. De esta forma PDF y Excel comparten exactamente los
    mismos valores, semaforos, tablas y graficos.
    """
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(xlsx_bytes))
    fecha = pd.Timestamp(fecha_fin)
    tipo_norm = str(tipo_analisis).lower()
    sufijo = {"quimico": "Quimico", "fisico": "Fisico", "srr": "SRR"}.get(tipo_norm)
    if sufijo is None:
        raise ValueError(f"Tipo de PDF no soportado: {tipo_analisis}")
    esperado = (
        f"01_{_MESES_ABR_TORRES[fecha.month]}_"
        f"{str(fecha.year)[-2:]} {sufijo}"
    )
    candidatos = [
        nombre for nombre in wb.sheetnames
        if nombre == esperado or nombre.endswith(f" {sufijo}")
    ]
    if not candidatos:
        raise RuntimeError(
            f"El Excel no contiene la hoja mensual {sufijo}."
        )

    nombre = candidatos[0]
    ws = wb[nombre]
    # LibreOffice (Linux) exporta TODAS las hojas al convertir a PDF e ignora
    # el sheet_state oculto, por lo que el PDF salia con Quimica y Fisica juntas.
    # Los graficos de la hoja mensual referencian solo celdas de su propia hoja,
    # asi que se eliminan las demas y queda un libro de una sola hoja. Esto tambien
    # funciona en Windows (Excel COM) porque no quedan referencias colgantes.
    for nombre_otro in list(wb.sheetnames):
        if nombre_otro != nombre:
            wb.remove(wb[nombre_otro])
    wb.active = 0

    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    # fitToWidth=1/fitToHeight=0 no sirve aca: LibreOffice pagina por celdas,
    # no por objetos. Las filas caben en una pagina, asi que no trocea nada y
    # el grafico que se sale lo aplasta igual contra el borde; encima sube la
    # escala (medido: 48,9% -> 51,3%) y lo empeora.
    _fijar_escala_impresion(
        ws,
        _ESCALA_PDF_SRR if tipo_norm == "srr" else _ESCALA_PDF_TORRES,
    )
    # PDF determinista entre ambientes: evita depender del "printer default".
    ws.page_setup.horizontalDpi = 600
    ws.page_setup.verticalDpi = 600
    ws.print_options.horizontalCentered = True
    ws.print_options.verticalCentered = False
    if tipo_norm != "srr":
        ws.page_margins.left = 0.15
        ws.page_margins.right = 0.15
        # Verticales en 0: al apilar las paginas, un margen se convierte en
        # una banda blanca en medio del reporte (medida: 41 pt).
        ws.page_margins.top = 0.0
        ws.page_margins.bottom = 0.0
        ws.page_margins.header = 0.0
        ws.page_margins.footer = 0.0
    ws.sheet_view.showGridLines = False
    if not ws.print_area:
        ws.print_area = f"A1:M{ws.max_row}"
    _forzar_alturas_pdf_deterministas(ws)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue(), nombre


def _motor_pdf() -> str:
    """Motor de render: "python" (por defecto) o "libreoffice" (legacy).

    El camino LibreOffice queda disponible por si hay que volver atrás, pero no
    es reproducible entre versiones: decide alto de fila, escala de impresión y
    posición de los objetos anclados por su cuenta, y por eso el gráfico FY se
    montaba sobre la tabla en el servidor y no en Windows.
    """
    return os.getenv("PDF_ENGINE", "python").strip().lower()


def _datos_pdf_torres(
    paquete: dict,
    tipo: str,
    fecha_fin,
    mapa_comentarios: dict | None = None,
) -> dict:
    """Reúne para el mes del reporte lo mismo que consume la hoja del Excel."""
    if mapa_comentarios is None:
        mapa_comentarios = paquete.get("mapa_comentarios")
    bd = paquete["bd_ton_mes"].copy()
    bd["Fecha"] = pd.to_datetime(bd["Fecha"], errors="coerce").dt.normalize()
    bd = bd[bd["Fecha"].notna()]
    if bd.empty:
        raise RuntimeError("BD Ton del mes sin fechas válidas.")

    objetivo = pd.Timestamp(fecha_fin).to_period("M")
    periodos = bd["Fecha"].dt.to_period("M")
    bd_mes = bd[periodos == objetivo]
    if bd_mes.empty:
        # El período pedido puede no coincidir con el del snapshot guardado.
        bd_mes = bd[periodos == periodos.max()]

    material = _preparar_material_por_turno(paquete["turno_mes"])
    if not material.empty:
        material = material[
            material["Fecha"].dt.to_period("M")
            == bd_mes["Fecha"].dt.to_period("M").iloc[0]
        ].copy()

    fecha_corte = paquete.get("fecha_corte_operacional")
    if fecha_corte is not None and not isinstance(fecha_corte, date):
        fecha_corte = pd.to_datetime(fecha_corte).date()

    detalle = _preparar_detalle_mensual_torres(
        df_bd_ton=bd_mes,
        tipo=tipo,
        df_material_turno=material,
        fecha_inicio_mes=paquete.get("fecha_inicio_mes"),
        fecha_fin_mes=paquete.get("fecha_fin_mes"),
        fecha_corte_operacional=fecha_corte,
        mapa_comentarios=mapa_comentarios,
    )
    if detalle.empty:
        raise RuntimeError(f"El detalle mensual {tipo} quedó vacío.")

    fecha_base = pd.to_datetime(detalle["Fecha"].min())
    gestion_fy = paquete[
        "gestion_fy_quimico" if tipo.lower() == "quimico"
        else "gestion_fy_fisico"
    ]
    return {
        "tipo": tipo,
        "fecha_base": fecha_base,
        "detalle": detalle,
        "resumen": _calcular_resumen_mensual_torres(detalle),
        "tonelaje": _calcular_tonelaje_por_material_torres(detalle),
        "gestion_fy": _normalizar_gestion_fy(gestion_fy, fecha_base),
        "anio_fiscal": _obtener_rango_fiscal_hasta_mes(
            fecha_base
        )["anio_fiscal"],
    }


def _datos_pdf_srr(
    paquete: dict,
    fecha_fin,
    mapa_comentarios: dict | None = None,
) -> dict:
    """Igual que _datos_pdf_torres, pero cruzando químico y físico para TM3."""
    quimico = _datos_pdf_torres(paquete, "quimico", fecha_fin, mapa_comentarios)
    fisico = _datos_pdf_torres(paquete, "fisico", fecha_fin, mapa_comentarios)
    detalle = _merge_detalle_srr(quimico["detalle"], fisico["detalle"])
    return {
        "fecha_base": quimico["fecha_base"],
        "detalle": detalle,
        "rep_turno": [
            _rep_turno_srr(
                fila.get("Rep_TM3_Quimico"), fila.get("Rep_TM3_Fisico")
            )
            for _, fila in detalle.iterrows()
        ],
        "resumen_quimico": _resumen_srr(quimico["detalle"]),
        "resumen_fisico": _resumen_srr(fisico["detalle"]),
        "mineral": _mineral_srr(detalle),
    }


def _nombre_pdf_representatividad(tipo_norm: str, fecha_corte, fecha_fin) -> str:
    # El nombre oficial usa la última fecha operacional válida mostrada en
    # el detalle, no el fin del período seleccionado (por ejemplo, 31 del mes).
    fecha_nombre = pd.to_datetime(fecha_corte, errors="coerce")
    if pd.isna(fecha_nombre):
        fecha_nombre = pd.Timestamp(fecha_fin)
    fecha_texto = fecha_nombre.strftime("%d-%m-%Y")
    if tipo_norm == "srr":
        return f"Representatividad Muestras SRR Torre {fecha_texto}.pdf"
    analisis_titulo = "Química" if tipo_norm == "quimico" else "Física"
    return (
        f"Representatividad Muestra {analisis_titulo} Torre {fecha_texto}.pdf"
    )


def _pdf_representatividad_desde_xlsx(
    xlsx_bytes: bytes,
    tipo_analisis: str,
    fecha_fin,
    fecha_corte=None,
    paquete: dict | None = None,
    mapa_comentarios: dict | None = None,
) -> tuple[bytes, str]:
    """Convierte Excel de representatividad a PDF A3 (hoja Químico o Físico)."""
    tipo_norm = str(tipo_analisis).lower()
    if _motor_pdf() == "python" and paquete is not None:
        from report_export.pdf_torres import render_srr, render_torres

        if tipo_norm == "srr":
            datos = _datos_pdf_srr(paquete, fecha_fin, mapa_comentarios)
            pdf_bytes = render_srr(datos)
        else:
            datos = _datos_pdf_torres(
                paquete, tipo_norm, fecha_fin, mapa_comentarios
            )
            pdf_bytes = render_torres(datos)
        print(
            "[PDF PYTHON]",
            {"tipo": tipo_norm, "filas_detalle": len(datos["detalle"])},
        )
        return (
            pdf_bytes,
            _nombre_pdf_representatividad(tipo_norm, fecha_corte, fecha_fin),
        )

    metricas = (
        _validar_workbook_representatividad(
            xlsx_bytes,
            fecha_fin,
            fecha_corte,
        )
        if fecha_corte is not None
        else _inspeccionar_workbook_representatividad(xlsx_bytes, fecha_fin)
    )
    print(
        "[PDF PREVALIDACION]",
        {
            "tipo": str(tipo_analisis).lower(),
            "fecha_fin": str(fecha_fin),
            "fecha_corte": str(fecha_corte),
            "metricas": metricas,
        },
    )
    xlsx_filtrado, nombre_hoja = _build_xlsx_pdf_desde_excel(
        xlsx_bytes,
        tipo_analisis,
        fecha_fin,
    )
    pdf_bytes = convert_xlsx_bytes_to_pdf(xlsx_filtrado)
    pdf_bytes = normalize_single_page_to_a3(pdf_bytes)
    return pdf_bytes, _nombre_pdf_representatividad(
        tipo_norm, fecha_corte, fecha_fin
    )


def _build_xlsx_pdf_reporte_torre(
    xlsx_bytes: bytes,
    nombre_hoja: str,
) -> bytes:
    """Deja una sola hoja del reporte de torres lista para convertir a PDF."""
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(xlsx_bytes))
    if nombre_hoja not in wb.sheetnames:
        raise RuntimeError(f"El Excel no contiene la hoja '{nombre_hoja}'.")

    for nombre_otro in list(wb.sheetnames):
        if nombre_otro != nombre_hoja:
            wb.remove(wb[nombre_otro])

    ws = wb[nombre_hoja]
    wb.active = 0
    ws.sheet_state = "visible"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.horizontalDpi = 600
    ws.page_setup.verticalDpi = 600
    ws.print_options.horizontalCentered = True
    ws.sheet_view.showGridLines = False

    # La tabla completa se reduce al ancho A3. Los bordes grises finos del
    # Excel se suavizan demasiado durante esa reducción, por lo que la copia
    # exclusiva para PDF usa líneas negras sólidas y encabezados reforzados.
    from openpyxl.styles import Border, Side

    if nombre_hoja == "Generador Reporte":
        fila_header_ini, fila_data = 18, 22
    else:
        fila_header_ini, fila_data = 19, 23

    ultima_fila_data = fila_data - 1
    for fila in range(ws.max_row, fila_data - 1, -1):
        if ws.cell(fila, 3).value not in (None, ""):
            ultima_fila_data = fila
            break

    lado_fino = Side(style="thin", color="000000")
    lado_medio = Side(style="medium", color="000000")
    borde_cuerpo = Border(
        left=lado_fino,
        right=lado_fino,
        top=lado_fino,
        bottom=lado_fino,
    )
    borde_header = Border(
        left=lado_medio,
        right=lado_medio,
        top=lado_medio,
        bottom=lado_medio,
    )
    for fila in range(fila_header_ini, ultima_fila_data + 1):
        borde = borde_header if fila < fila_data else borde_cuerpo
        for columna in range(3, 42):  # C:AO
            ws.cell(fila, columna).border = borde

    # B:AP contiene todo el marco oficial; A solo era espacio en blanco y
    # provocaba un desplazamiento perceptible al escalar el PDF.
    fila_fin_impresion = max(ultima_fila_data + 2, fila_data)
    ws.print_area = f"B1:AP{fila_fin_impresion}"
    ws.page_margins.left = 0.12
    ws.page_margins.right = 0.12
    ws.page_margins.top = 0.15
    ws.page_margins.bottom = 0.15
    ws.page_margins.header = 0.0
    ws.page_margins.footer = 0.0

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def _prefijo_mes_desde_nombres_hojas(nombres: list[str]) -> str:
    """Extrae '01_Ene_26' desde '01_Ene_26 Quimico'."""
    if not nombres:
        return "mes"
    primera = nombres[0]
    if " " in primera:
        return primera.split(" ", 1)[0]
    return primera[:31]


def _agregar_hoja_mensual_srr_legacy(
    wb,
    detalle_quimico: pd.DataFrame,
    detalle_fisico: pd.DataFrame,
    fecha_base,
) -> str:
    """Crea la hoja complementaria de TM3/SRR sin mezclar CV-001 con TM1/TM2."""
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    fecha_base = pd.Timestamp(fecha_base)
    nombre = f"01_{_MESES_ABR_TORRES[fecha_base.month]}_{str(fecha_base.year)[-2:]} SRR"
    if nombre in wb.sheetnames:
        del wb[nombre]
    ws = wb.create_sheet(nombre)
    ws.sheet_view.showGridLines = False

    azul = PatternFill("solid", fgColor="D7E1E7")
    verde = PatternFill("solid", fgColor="E2F0D9")
    rojo = PatternFill("solid", fgColor="FCE4D6")
    gris = PatternFill("solid", fgColor="F2F2F2")
    side = Side(style="thin", color="A6A6A6")
    borde = Border(left=side, right=side, top=side, bottom=side)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.merge_cells("A1:H2")
    ws["A1"] = (
        "REPRESENTATIVIDAD TORRE DE MUESTREO #3 / SRR - "
        f"{_MESES_NOMBRE_TORRES[fecha_base.month].upper()} {fecha_base.year}"
    )
    ws["A1"].font = Font(name="Arial", bold=True, size=16, color="476475")
    ws["A1"].alignment = centro
    ws["A1"].fill = azul

    def _resumen(detalle):
        filas = []
        for semana in range(1, 7):
            parte = detalle[detalle["Semana_Num"] == semana]
            activos = int((parte["TM3_Activo"] == 1).sum())
            reps = int(((parte["TM3_Activo"] == 1) & (parte["Rep_TM3"] == 1)).sum())
            filas.append((f"Semana {semana}", activos, reps, reps / activos if activos else None))
        activos = int((detalle["TM3_Activo"] == 1).sum())
        reps = int(((detalle["TM3_Activo"] == 1) & (detalle["Rep_TM3"] == 1)).sum())
        filas.append(("MTD", activos, reps, reps / activos if activos else None))
        return filas

    for col_ini, titulo, detalle in [
        (1, "Resumen químico TM3 / SRR", detalle_quimico),
        (6, "Resumen físico TM3 / SRR", detalle_fisico),
    ]:
        ws.merge_cells(start_row=4, start_column=col_ini, end_row=4, end_column=col_ini + 3)
        ws.cell(4, col_ini, titulo)
        encabezados = ["Periodo", "Turnos activos", "Representativos", "Resultado"]
        for j, valor in enumerate(encabezados, col_ini):
            ws.cell(5, j, valor)
        for i, fila in enumerate(_resumen(detalle), 6):
            for j, valor in enumerate(fila, col_ini):
                ws.cell(i, j, valor)
            ws.cell(i, col_ini + 3).number_format = "0.0%"
        for fila in ws.iter_rows(min_row=4, max_row=12, min_col=col_ini, max_col=col_ini + 3):
            for celda in fila:
                celda.border = borde
                celda.alignment = centro
        for celda in ws[4] + ws[5]:
            if col_ini <= celda.column <= col_ini + 3:
                celda.fill = azul
                celda.font = Font(name="Arial", bold=True, color="476475")

        # Target visible y serie ligada a las mismas filas del resumen.
        ws.cell(5, col_ini + 4, "Target")
        for i in range(6, 13):
            ws.cell(i, col_ini + 4, 0.85).number_format = "0%"
        grafico = BarChart()
        grafico.type = "col"
        grafico.style = 10
        grafico.title = titulo
        grafico.y_axis.numFmt = "0%"
        grafico.y_axis.scaling.max = 1
        datos = Reference(ws, min_col=col_ini + 3, min_row=5, max_row=12)
        categorias = Reference(ws, min_col=col_ini, min_row=6, max_row=12)
        grafico.add_data(datos, titles_from_data=True)
        grafico.set_categories(categorias)
        target = LineChart()
        target.add_data(Reference(ws, min_col=col_ini + 4, min_row=5, max_row=12), titles_from_data=True)
        grafico += target
        grafico.height, grafico.width = 7.0, 11.5
        ws.add_chart(grafico, "A14" if col_ini == 1 else "H14")

    q = detalle_quimico[["Fecha", "Turno", "TMH_CV01", "TM3_Activo", "Rep_TM3", "Comentario_TM3"]].copy()
    q = q.rename(columns={"Rep_TM3": "Rep_TM3_Quimico", "Comentario_TM3": "Comentario_TM3_Quimico"})
    f = detalle_fisico[["Fecha", "Turno", "Rep_TM3", "Comentario_TM3"]].copy()
    f = f.rename(columns={"Rep_TM3": "Rep_TM3_Fisico", "Comentario_TM3": "Comentario_TM3_Fisico"})
    detalle = q.merge(f, on=["Fecha", "Turno"], how="outer").sort_values(["Fecha", "Turno"])
    fila_detalle = 31
    headers = ["Fecha", "Turno", "TMH CV-01", "TM3 activo", "Químico TM3", "Comentario químico", "Físico TM3", "Comentario físico"]
    for col, valor in enumerate(headers, 1):
        ws.cell(fila_detalle, col, valor)
    for i, (_, fila) in enumerate(detalle.iterrows(), fila_detalle + 1):
        valores = [fila["Fecha"], fila["Turno"], fila["TMH_CV01"], fila["TM3_Activo"],
                   fila["Rep_TM3_Quimico"], fila["Comentario_TM3_Quimico"],
                   fila["Rep_TM3_Fisico"], fila["Comentario_TM3_Fisico"]]
        for col, valor in enumerate(valores, 1):
            celda = ws.cell(i, col, None if pd.isna(valor) else valor)
            celda.border, celda.alignment = borde, centro
            if col == 1:
                celda.number_format = "dd-mm-yyyy"
            elif col == 3:
                celda.number_format = "#,##0.0"
            elif col in (4, 5, 7):
                celda.number_format = "0"
            if col in (5, 7) and celda.value is not None:
                celda.fill = verde if int(celda.value) == 1 else rojo
        if i % 2 == 0:
            for col in range(1, 9):
                if col not in (5, 7) or ws.cell(i, col).value is None:
                    ws.cell(i, col).fill = gris

    for col in range(1, 9):
        ws.cell(fila_detalle, col).fill = azul
        ws.cell(fila_detalle, col).font = Font(name="Arial", bold=True, color="476475")
        ws.cell(fila_detalle, col).border = borde
        ws.cell(fila_detalle, col).alignment = centro
    anchos = [14, 10, 14, 12, 16, 32, 16, 32]
    from openpyxl.utils import get_column_letter
    for col, ancho in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(col)].width = ancho
    ws.auto_filter.ref = f"A{fila_detalle}:H{fila_detalle + len(detalle)}"
    ws.freeze_panes = f"A{fila_detalle + 1}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.print_area = f"A1:N{fila_detalle + len(detalle)}"
    return nombre


# Reglas de la hoja SRR/TM3. Viven acá y no dentro del constructor del Excel
# porque el PDF en Python las necesita idénticas; si se duplicaran, los dos
# formatos podrían empezar a informar números distintos.

def _merge_detalle_srr(
    detalle_quimico: pd.DataFrame,
    detalle_fisico: pd.DataFrame,
) -> pd.DataFrame:
    """Cruza químico y físico por Fecha + Turno para el detalle de TM3."""
    q = detalle_quimico[[
        "Semana", "Fecha", "Pad", "Turno", "TMH_CV01", "TM3_Activo",
        "Rep_TM3", "Comentario_TM3",
    ]].copy().rename(columns={
        "Rep_TM3": "Rep_TM3_Quimico",
        "Comentario_TM3": "Comentario_TM3_Quimico",
    })
    f = detalle_fisico[["Fecha", "Turno", "Rep_TM3", "Comentario_TM3"]].copy()
    f = f.rename(columns={
        "Rep_TM3": "Rep_TM3_Fisico",
        "Comentario_TM3": "Comentario_TM3_Fisico",
    })
    return q.merge(f, on=["Fecha", "Turno"], how="outer").sort_values(
        ["Fecha", "Turno"]
    )


def _rep_turno_srr(rep_quimico, rep_fisico):
    """Basta con que una de las dos muestras sea representativa."""
    if (
        pd.to_numeric(rep_quimico, errors="coerce") == 1
        or pd.to_numeric(rep_fisico, errors="coerce") == 1
    ):
        return 1
    if pd.isna(rep_quimico) and pd.isna(rep_fisico):
        return None
    return 0


def _resumen_srr(detalle: pd.DataFrame) -> list[dict]:
    """Semanas 1..6 y MTD sobre los turnos con TM3 activa."""
    filas = []

    def _fila(parte, etiqueta):
        activos = int((parte["TM3_Activo"] == 1).sum())
        reps = int(
            ((parte["TM3_Activo"] == 1) & (parte["Rep_TM3"] == 1)).sum()
        )
        no_reps = max(activos - reps, 0)
        filas.append({
            "Periodo": etiqueta,
            "Turnos_Activos": activos,
            "Representativos": reps,
            "No_Representativos": no_reps,
            "Pct_Representativos": reps / activos if activos else None,
            "Pct_No_Representativos": no_reps / activos if activos else None,
            "Total": 1.0 if activos else None,
        })

    for semana in range(1, 7):
        _fila(detalle[detalle["Semana_Num"] == semana], f"Semana {semana}")
    _fila(detalle, "MTD")
    return filas


def _mineral_srr(detalle: pd.DataFrame) -> list[dict]:
    """Tonelaje con y sin torre por material, sobre el detalle ya cruzado."""
    resultados = []
    for pad in ["Óxido", "Sulfuro"]:
        parte = detalle[(detalle["Pad"] == pad) & (detalle["TM3_Activo"] == 1)]
        rep_any = (
            (parte["Rep_TM3_Quimico"] == 1) | (parte["Rep_TM3_Fisico"] == 1)
        )
        con = float(
            pd.to_numeric(parte.loc[rep_any, "TMH_CV01"], errors="coerce").sum()
        )
        sin = float(
            pd.to_numeric(
                parte.loc[~rep_any, "TMH_CV01"], errors="coerce"
            ).sum()
        )
        total = con + sin
        resultados.extend([
            {"Pad": pad, "Estado": "Con Torre", "Tonelaje": con,
             "Distribucion": con / total if total else None},
            {"Pad": pad, "Estado": "Sin Torre", "Tonelaje": sin,
             "Distribucion": sin / total if total else None},
        ])
    return resultados


def _agregar_hoja_mensual_srr(
    wb,
    detalle_quimico: pd.DataFrame,
    detalle_fisico: pd.DataFrame,
    fecha_base,
) -> str:
    """Diseña la hoja mensual profesional de TM3/SRR sin alterar sus reglas."""
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.chart.axis import ChartLines
    from openpyxl.chart.data_source import NumData, NumFmt, NumVal
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.layout import Layout, ManualLayout
    from openpyxl.chart.series import SeriesLabel
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.geometry import PresetGeometry2D
    from openpyxl.drawing.image import Image as OpenpyxlImage
    from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, TwoCellAnchor
    from openpyxl.drawing.text import (
        CharacterProperties,
        Paragraph,
        ParagraphProperties,
        RichTextProperties,
    )
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    fecha_base = pd.Timestamp(fecha_base)
    nombre = f"01_{_MESES_ABR_TORRES[fecha_base.month]}_{str(fecha_base.year)[-2:]} SRR"
    if nombre in wb.sheetnames:
        del wb[nombre]
    ws = wb.create_sheet(nombre)
    ws.sheet_view.showGridLines = False

    azul = PatternFill("solid", fgColor="D7E1E7")
    blanco = PatternFill("solid", fgColor="FFFFFF")
    gris = PatternFill("solid", fgColor="F2F2F2")
    thin = Side(style="thin", color="595959")
    medium = Side(style="medium", color="404040")
    borde = Border(left=thin, right=thin, top=thin, bottom=thin)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)
    izquierda = Alignment(horizontal="left", vertical="center", wrap_text=True)
    izquierda_sin_wrap = Alignment(
        horizontal="left", vertical="center", wrap_text=False,
    )
    font_header = Font(name="Arial", bold=True, color="476475", size=10)
    font_normal = Font(name="Arial", color="476475", size=10)
    font_titulo = Font(name="Arial", bold=True, color="476475", size=12)

    def _contorno(fila_ini, col_ini, fila_fin, col_fin):
        for fila in range(fila_ini, fila_fin + 1):
            for col in range(col_ini, col_fin + 1):
                celda = ws.cell(fila, col)
                celda.border = Border(
                    left=medium if col == col_ini else thin,
                    right=medium if col == col_fin else thin,
                    top=medium if fila == fila_ini else thin,
                    bottom=medium if fila == fila_fin else thin,
                )

    def _subrayar(fila, col_ini, col_fin):
        for col in range(col_ini, col_fin + 1):
            ws.cell(fila, col).border = Border(bottom=thin)

    def _estilo_tabla_resumen_oficial(fila_encabezado, fila_mtd):
        """Replica la tabla oficial: fondo blanco y separaciones verticales."""
        for fila in range(fila_encabezado, fila_mtd + 1):
            for col in range(3, 7):
                ws.cell(fila, col).fill = blanco
        _aplicar_bordes_tabla_limpia(
            ws,
            fila_ini=fila_encabezado,
            fila_fin=fila_mtd,
            col_ini=3,
            col_fin=6,
            fila_header=fila_encabezado,
            fila_mtd=fila_mtd,
            columnas_separadoras=(3, 4, 5),
            lado_exterior=thin,
            lado_estructura=thin,
            lado_mtd=medium,
        )

    def _estilo_tabla_mineral_oficial():
        for fila in range(10, 15):
            for col in range(3, 7):
                ws.cell(fila, col).fill = blanco
        _aplicar_bordes_tabla_limpia(
            ws,
            fila_ini=10,
            fila_fin=14,
            col_ini=3,
            col_fin=6,
            fila_header=10,
            columnas_separadoras=(3, 4, 5),
            filas_separadoras=(12,),
            lado_exterior=thin,
            lado_estructura=thin,
            lado_mtd=medium,
        )

    def _semaforo(celda, valor):
        if pd.isna(valor):
            celda.value = None
            return
        celda.value = "●"
        celda.font = Font(
            name="Arial", bold=True,
            color="70AD47" if int(valor) == 1 else "C55A11", size=16,
        )
        celda.alignment = centro

    def _estado_activo(celda, valor):
        if pd.isna(valor):
            celda.value = None
            return
        celda.value = "●"
        celda.font = Font(
            name="Arial", bold=True,
            color="70AD47" if int(valor) == 1 else "A6A6A6", size=16,
        )
        celda.alignment = centro

    def _resumen(detalle):
        return [
            (
                fila["Periodo"],
                fila["Pct_Representativos"],
                fila["Pct_No_Representativos"],
                fila["Total"],
            )
            for fila in _resumen_srr(detalle)
        ]

    detalle = _merge_detalle_srr(detalle_quimico, detalle_fisico)

    ws.merge_cells("C5:M7")
    ws["C5"] = (
        "Muestras representativas de Torre de Muestreo #3 / SRR - "
        "Muestra Física y Química - "
        f"{_MESES_NOMBRE_TORRES[fecha_base.month].lower()}, {fecha_base.year}"
    )
    ws["C5"].font, ws["C5"].alignment = font_titulo, centro
    ws.merge_cells("K2:M4")
    ws["K2"] = (
        "Superintendencia de Medición y Reconciliación\n"
        "Gerencia Planificación Integrada"
    )
    ws["K2"].font, ws["K2"].alignment = font_header, centro
    logo_path = os.path.join(os.path.dirname(_REPORT_EXPORT_DIR), "assets", "logoBHP.png")
    if os.path.isfile(logo_path):
        logo = OpenpyxlImage(logo_path)
        logo.anchor = TwoCellAnchor(
            editAs="twoCell",
            _from=AnchorMarker(
                col=12, colOff=317500, row=1, rowOff=101600,
            ),
            to=AnchorMarker(
                col=12, colOff=1203180, row=4, rowOff=1275,
            ),
        )
        ws.add_image(logo)

    ws["C9"] = (
        "1.- Mineral apilado y caracterizado con información física y química "
        "de Torre de Muestreo #3 / SRR."
    )
    ws["C9"].font, ws["C9"].alignment = font_header, izquierda_sin_wrap
    _subrayar(9, 3, 8)
    ws.merge_cells("D10:F10")
    for col, valor in {3: "Pad", 4: "Mineral Apilado (ton)"}.items():
        celda = ws.cell(10, col, valor)
        celda.fill, celda.font, celda.alignment, celda.border = blanco, font_header, centro, borde
    filas_mineral = [
        (f["Pad"], f["Estado"], f["Tonelaje"], f["Distribucion"])
        for f in _mineral_srr(detalle)
    ]
    for fila_excel, valores in enumerate(filas_mineral, 11):
        for col, valor in zip((3, 4, 5, 6), valores):
            celda = ws.cell(fila_excel, col, valor)
            celda.font, celda.alignment, celda.border = font_normal, centro, borde
        ws.cell(fila_excel, 5).number_format = "#,##0.0"
        ws.cell(fila_excel, 6).number_format = "0.0%"
    ws.merge_cells("C11:C12")
    ws.merge_cells("C13:C14")
    for fila in (11, 13):
        ws.cell(fila, 3).font = font_header
    for fila in range(11, 15):
        ws.cell(fila, 4).font = font_normal
    _estilo_tabla_mineral_oficial()

    # Datos exclusivos de gráficos, lejos del reporte visible y fuera de impresión.
    for columna in ("X", "Y", "Z", "AA"):
        ws.column_dimensions[columna].hidden = True

    def _agregar_resumen_y_grafico(
        fila_inicio, titulo, detalle_tipo, desde, hasta, fila_aux,
    ):
        ws.cell(fila_inicio, 3, titulo)
        ws.cell(fila_inicio, 3).font = font_header
        ws.cell(fila_inicio, 3).alignment = izquierda_sin_wrap
        _subrayar(fila_inicio, 3, 8)
        encabezados = [
            f"{_MESES_NOMBRE_TORRES[fecha_base.month].lower()} {str(fecha_base.year)[-2:]}",
            "Muestras representativas TM SRR",
            "Muestras perdidas por Falla TM 3", "Total TM3",
        ]
        if "Física" in titulo:
            encabezados[1] = "Muestras representativas TM3"
        for col, valor in enumerate(encabezados, 3):
            celda = ws.cell(fila_inicio + 1, col, valor)
            celda.fill, celda.font, celda.alignment, celda.border = blanco, font_normal, centro, borde
        resumen = _resumen(detalle_tipo)
        for offset, valores in enumerate(resumen, 2):
            for col, valor in enumerate(valores, 3):
                celda = ws.cell(fila_inicio + offset, col, valor)
                celda.font, celda.alignment, celda.border = font_normal, centro, borde
            for col in range(4, 7):
                ws.cell(fila_inicio + offset, col).number_format = "0.0%"
        _estilo_tabla_resumen_oficial(fila_inicio + 1, fila_inicio + 8)
        ws.cell(fila_inicio + 9, 4, "Target de muestras representativas: 85%")
        ws.cell(fila_inicio + 9, 4).font = font_header
        ws.cell(fila_inicio + 9, 4).alignment = izquierda_sin_wrap

        es_quimico = "Química" in titulo
        nombre_representativas = (
            "Muestras representativas TM SRR"
            if es_quimico else "Muestras representativas TM3"
        )
        nombre_perdidas = "Muestras perdidas por Falla TM 3"
        ws.cell(fila_aux, 24, "Periodo")
        ws.cell(fila_aux, 25, nombre_representativas)
        ws.cell(fila_aux, 26, nombre_perdidas)
        ws.cell(fila_aux, 27, "Target")
        for indice, valores in enumerate(resumen, 1):
            ws.cell(fila_aux + indice, 24, valores[0])
            ws.cell(fila_aux + indice, 25, 0.0 if valores[1] is None else valores[1])
            ws.cell(fila_aux + indice, 26, 0.0 if valores[2] is None else valores[2])
            ws.cell(fila_aux + indice, 27, 0.85)
            for col_aux in (25, 26, 27):
                ws.cell(fila_aux + indice, col_aux).number_format = "0.0%"

        chart = BarChart()
        chart.type, chart.grouping, chart.overlap = "col", "percentStacked", 100
        chart.visible_cells_only = False
        chart.gapWidth, chart.varyColors = 150, False
        chart.title = (
            "Muestra Química Torre #3"
            if es_quimico else "Muestra Física Torre #3"
        )
        chart.title.overlay = False
        chart.height, chart.width = 7.2, 20.5
        chart.roundedCorners = False
        chart.graphical_properties = GraphicalProperties(solidFill="FFFFFF")
        chart.graphical_properties.prstGeom = PresetGeometry2D(prst="rect")
        chart.graphical_properties.line.solidFill = "7F8F9B"
        chart.graphical_properties.line.width = 9525
        chart.layout = Layout(manualLayout=ManualLayout(
            layoutTarget="inner",
            xMode="edge", yMode="edge",
            wMode="factor", hMode="factor",
            x=0.07544705050210952,
            y=0.2985221576338519,
            w=0.9098901359569239,
            h=0.5962449841774051,
        ))
        chart.legend.position, chart.legend.overlay = "t", False
        chart.x_axis.delete = False
        chart.y_axis.delete = False
        chart.x_axis.axPos = "b"
        chart.x_axis.tickLblPos = "nextTo"
        chart.y_axis.tickLblPos = "nextTo"
        chart.y_axis.scaling.min, chart.y_axis.scaling.max = 0, 1
        chart.y_axis.numFmt = NumFmt(formatCode="0%", sourceLinked=True)
        chart.y_axis.majorUnit = None
        chart.y_axis.title = "Muestras representativas"
        chart.x_axis.spPr = GraphicalProperties()
        chart.x_axis.spPr.line.solidFill = "476475"
        chart.x_axis.spPr.line.width = 19050
        chart.y_axis.spPr = GraphicalProperties()
        chart.y_axis.spPr.line.noFill = True
        chart.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties())
        chart.y_axis.majorGridlines.spPr.line.solidFill = "476475"
        chart.y_axis.majorGridlines.spPr.line.width = 3175
        data = Reference(ws, min_col=25, max_col=26, min_row=fila_aux, max_row=fila_aux + 7)
        categorias = Reference(ws, min_col=24, min_row=fila_aux + 1, max_row=fila_aux + 7)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categorias)
        chart.series[0].tx = SeriesLabel(v=nombre_representativas)
        chart.series[1].tx = SeriesLabel(v=nombre_perdidas)
        chart.series[0].graphicalProperties.solidFill = "476475"
        chart.series[1].graphicalProperties.solidFill = "E65400"
        valores_cache = [
            [0.0 if v[1] is None else v[1] for v in resumen],
            [0.0 if v[2] is None else v[2] for v in resumen],
        ]
        for indice, valores in enumerate(valores_cache):
            chart.series[indice].val.numRef.numCache = NumData(
                formatCode="0.0%", ptCount=7,
                pt=[NumVal(idx=i, v=float(v)) for i, v in enumerate(valores)],
            )
        chart.dLbls = DataLabelList()
        chart.dLbls.showVal, chart.dLbls.showSerName = False, False
        chart.dLbls.showCatName = False
        chart.dLbls.showLegendKey = False
        chart.dLbls.showPercent = False
        chart.dLbls.showLeaderLines = False
        for serie in chart.series:
            serie.dLbls = DataLabelList()
            serie.dLbls.numFmt = "0.0%"
            serie.dLbls.showVal = True
            serie.dLbls.showLegendKey = False
            serie.dLbls.showCatName = False
            serie.dLbls.showSerName = False
            serie.dLbls.showPercent = False
            serie.dLbls.showLeaderLines = False
            serie.dLbls.spPr = GraphicalProperties(noFill=True)
            serie.dLbls.spPr.line.noFill = True
            serie.dLbls.txPr = RichText(
                bodyPr=RichTextProperties(anchor="ctr", spAutoFit=True),
                p=[Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(
                            sz=1050, solidFill="FFFFFF",
                        )
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )],
            )
        chart.legend.txPr = RichText(
            bodyPr=RichTextProperties(),
            p=[Paragraph(
                pPr=ParagraphProperties(
                    defRPr=CharacterProperties(sz=900, solidFill="476475")
                ),
                endParaRPr=CharacterProperties(lang="es-CL"),
            )],
        )
        chart.title.tx.rich.p[0].pPr.defRPr = CharacterProperties(
            sz=1200, b=True, solidFill="476475",
        )
        texto_eje = RichText(
            bodyPr=RichTextProperties(),
            p=[Paragraph(
                pPr=ParagraphProperties(
                    defRPr=CharacterProperties(sz=1000, solidFill="476475")
                ),
                endParaRPr=CharacterProperties(lang="es-CL"),
            )],
        )
        chart.x_axis.txPr = texto_eje
        chart.y_axis.txPr = texto_eje
        chart.y_axis.title.tx.rich.p[0].pPr.defRPr = CharacterProperties(
            sz=1000, b=True, solidFill="476475",
        )
        target = LineChart()
        target.visible_cells_only = False
        target.add_data(Reference(ws, min_col=27, min_row=fila_aux, max_row=fila_aux + 7), titles_from_data=True)
        target.set_categories(categorias)
        target.series[0].tx = SeriesLabel(v="Target")
        target.series[0].val.numRef.numCache = NumData(
            formatCode="0%", ptCount=7,
            pt=[NumVal(idx=i, v=0.85) for i in range(7)],
        )
        target.series[0].graphicalProperties.line.solidFill = "4F81BD"
        target.series[0].graphicalProperties.line.prstDash = "dash"
        target.series[0].graphicalProperties.line.width = 22225
        target.series[0].marker.symbol = "none"
        target.x_axis.axId, target.y_axis.axId = chart.x_axis.axId, chart.y_axis.axId
        # Comparten los IDs del gráfico principal: no se deben marcar como
        # eliminados, porque eso también ocultaría Semana 1..6/MTD y el eje Y.
        target.x_axis.delete, target.y_axis.delete = False, False
        chart += target
        chart.anchor = TwoCellAnchor(editAs="twoCell", _from=desde, to=hasta)
        ws.add_chart(chart)

    _agregar_resumen_y_grafico(
        16,
        "2.- Muestra Química Torre de muestreo #3: Distribución porcentual de muestras obtenidas y no representativas.",
        detalle_quimico,
        AnchorMarker(col=8, colOff=1743364, row=8, rowOff=103910),
        AnchorMarker(col=12, colOff=1010380, row=21, rowOff=116961),
        2,
    )
    _agregar_resumen_y_grafico(
        27,
        "3.- Muestra Física Torre de muestreo #3: Distribución porcentual de muestras obtenidas y no representativas.",
        detalle_fisico,
        AnchorMarker(col=8, colOff=1749713, row=22, rowOff=29906),
        AnchorMarker(col=12, colOff=1020539, row=35, rowOff=34066),
        12,
    )

    ws.merge_cells("C40:M40")
    ws["C40"] = (
        "4.- Detalle turno a turno de mineral apilado entre toma de muestras, "
        "muestras representativas y comentarios sobre muestras no representativas."
    )
    ws["C40"].font, ws["C40"].alignment = font_header, izquierda_sin_wrap
    _subrayar(40, 3, 13)
    grupos = [
        (7, 9, "Muestra química"),
        (10, 12, "Muestra física"),
    ]
    for col_inicio, col_fin, texto in grupos:
        for col in range(col_inicio, col_fin + 1):
            celda = ws.cell(42, col)
            celda.value = texto if col == col_inicio else None
            celda.fill = azul
            celda.font = font_header
            celda.alignment = Alignment(
                horizontal="centerContinuous",
                vertical="center",
            )
            celda.border = Border(
                left=medium if col == col_inicio else Side(),
                right=medium if col == col_fin else Side(),
                top=medium,
                bottom=medium,
            )
    headers = [
        "Semana", "Fecha", "Pad", "Turno",
        "TMH\nCV-01", "Muestra representativa CV-01", "Comentarios",
        "TMH\nCV-01", "Muestra representativa CV-01", "Comentarios",
        "Representatividad Turno\n(árbol de decisión)",
    ]
    for col, valor in enumerate(headers, 3):
        celda = ws.cell(43, col, valor)
        celda.fill, celda.font, celda.alignment, celda.border = azul, font_header, centro, borde
    fila_datos = 44
    for indice, (_, fila) in enumerate(detalle.iterrows()):
        fila_excel = fila_datos + indice
        es_futura = pd.isna(fila.get("Pad"))
        rep_quimico = fila.get("Rep_TM3_Quimico")
        rep_fisico = fila.get("Rep_TM3_Fisico")
        rep_turno_srr = _rep_turno_srr(rep_quimico, rep_fisico)
        valores = [
            None if es_futura else fila.get("Semana"),
            None if es_futura else fila.get("Fecha"),
            None if es_futura else fila.get("Pad"), None if es_futura else fila.get("Turno"),
            None if es_futura else fila.get("TMH_CV01"),
            None if es_futura else rep_quimico,
            None if es_futura else fila.get("Comentario_TM3_Quimico"),
            None if es_futura else fila.get("TMH_CV01"),
            None if es_futura else rep_fisico,
            None if es_futura else fila.get("Comentario_TM3_Fisico"),
            None if es_futura else rep_turno_srr,
        ]
        for col, valor in enumerate(valores, 3):
            valor = None if pd.isna(valor) else valor
            celda = ws.cell(fila_excel, col, valor)
            celda.font, celda.border = font_normal, borde
            celda.alignment = izquierda if col in (9, 12) else centro
            if indice % 2 == 1:
                celda.fill = azul
        ws.cell(fila_excel, 4).number_format = "dd-mm-yyyy"
        ws.cell(fila_excel, 7).number_format = "#,##0.0"
        ws.cell(fila_excel, 10).number_format = "#,##0.0"
        _semaforo(ws.cell(fila_excel, 8), valores[5])
        _semaforo(ws.cell(fila_excel, 11), valores[8])
        _semaforo(ws.cell(fila_excel, 13), valores[10])
        if fila.get("Pad") == "Sin clasificar" and not es_futura:
            ws.cell(fila_excel, 5).fill = gris
    ultima_fila = fila_datos + len(detalle) - 1
    _contorno(43, 3, ultima_fila, 13)
    ws.auto_filter.ref = None
    ws.freeze_panes = None

    anchos = {
        "A": 4.75, "B": 1.50, "C": 12.75, "D": 15.50,
        "E": 16.50, "F": 15.50, "G": 9.00, "H": 13.50,
        "I": 43.75, "J": 9.50, "K": 13.50, "L": 44.25,
        "M": 19.75, "N": 1.50, "O": 1.50,
    }
    for columna, ancho in anchos.items():
        ws.column_dimensions[columna].width = ancho
    for fila, altura in {
        2: 14.25, 5: 14.5, 6: 14.5, 7: 14.5,
        17: 37.5, 28: 37.5, 42: 14.5, 43: 39.5,
    }.items():
        ws.row_dimensions[fila].height = altura
    for fila in range(fila_datos, ultima_fila + 1):
        es_futura = all(ws.cell(fila, col).value is None for col in range(3, 14))
        ws.row_dimensions[fila].height = 13.5 if es_futura else 15.0
    ws.sheet_view.zoomScale = 75
    ws.sheet_view.zoomScaleNormal = 75
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    _fijar_escala_impresion(ws, _ESCALA_PDF_SRR)
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.25
    ws.page_margins.top = ws.page_margins.bottom = 0.4
    ws.print_area = f"A1:M{ultima_fila}"
    return nombre


def _agregar_hojas_mensuales_torres(
    wb,
    df_bd_ton: pd.DataFrame,
    df_turno: pd.DataFrame | None = None,
    df_gestion_fy_quimico: pd.DataFrame | None = None,
    df_gestion_fy_fisico: pd.DataFrame | None = None,
    grafico_fy_en_hoja_aparte: bool = False,
    fecha_inicio_mes=None,
    fecha_fin_mes=None,
    fecha_corte_operacional=None,
    mapa_comentarios: dict | None = None,
) -> list[str]:
    """Crea un par Químico/Físico por cada mes incluido en BD Ton."""
    if df_bd_ton is None or df_bd_ton.empty or "Fecha" not in df_bd_ton.columns:
        return []

    bd = df_bd_ton.copy()
    bd["Fecha"] = pd.to_datetime(bd["Fecha"], errors="coerce").dt.normalize()
    bd = bd[bd["Fecha"].notna()].copy()

    if bd.empty:
        return []

    material_turno = _preparar_material_por_turno(df_turno)
    nombres = []

    for periodo, bd_mes in bd.groupby(bd["Fecha"].dt.to_period("M"), sort=True):
        material_mes = material_turno
        if not material_turno.empty:
            material_mes = material_turno[
                material_turno["Fecha"].dt.to_period("M") == periodo
            ].copy()

        for tipo in ["Quimico", "Fisico"]:
            df_gestion_tipo = (
                df_gestion_fy_quimico
                if tipo == "Quimico"
                else df_gestion_fy_fisico
            )
            nombre = _agregar_hoja_mensual_torres(
                wb=wb,
                df_bd_ton_mes=bd_mes,
                tipo=tipo,
                df_material_turno_mes=material_mes,
                df_gestion_fy=df_gestion_tipo,
                incluir_grafico_fy=not grafico_fy_en_hoja_aparte,
                fecha_inicio_mes=fecha_inicio_mes,
                fecha_fin_mes=fecha_fin_mes,
                fecha_corte_operacional=fecha_corte_operacional,
                mapa_comentarios=mapa_comentarios,
            )
            if nombre:
                nombres.append(nombre)

            if grafico_fy_en_hoja_aparte:
                fecha_base = pd.to_datetime(bd_mes["Fecha"].min())
                nombre_fy = _agregar_hoja_grafico_gestion_fy(
                    wb=wb,
                    df_gestion_fy=df_gestion_tipo,
                    tipo=tipo,
                    fecha_base=fecha_base,
                )
                if nombre_fy:
                    nombres.append(nombre_fy)

        detalle_quimico = _preparar_detalle_mensual_torres(
            bd_mes, "quimico", material_mes, fecha_inicio_mes,
            fecha_fin_mes, fecha_corte_operacional, mapa_comentarios,
        )
        detalle_fisico = _preparar_detalle_mensual_torres(
            bd_mes, "fisico", material_mes, fecha_inicio_mes,
            fecha_fin_mes, fecha_corte_operacional, mapa_comentarios,
        )
        nombre_srr = _agregar_hoja_mensual_srr(
            wb, detalle_quimico, detalle_fisico,
            pd.to_datetime(bd_mes["Fecha"].min()),
        )
        if nombre_srr:
            nombres.append(nombre_srr)

    return nombres


def _agregar_hoja_trazabilidad_pesos(wb, df_pesos_turno) -> None:
    """Agrega una vista ancha por Fecha/Turno sin alterar el DataFrame fuente."""
    if df_pesos_turno is None or df_pesos_turno.empty:
        return

    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    df = validar_pesos_representatividad(df_pesos_turno)
    campos = (
        ("PesoTeo_Quimico", "Peso teórico químico [kg]", "0.000", 22),
        ("PesoReal_Quimico", "Peso real químico [kg]", "0.000", 20),
        ("Representatividad_Quimica", "Representatividad química", "0.0%", 21),
        ("PesoTeo_Fisico", "Peso teórico físico [kg]", "0.000", 21),
        ("PesoReal_Fisico", "Peso real físico [kg]", "0.000", 19),
        ("Representatividad_Fisica", "Representatividad física", "0.0%", 20),
        ("Horas_Reales", "Horas reales", "0.000", 14),
        ("Factor_Masa", "Factor masa", "0.000", 14),
        ("fecha_carga", "Fecha de carga", "dd-mm-yyyy hh:mm", 19),
    )
    torres = (
        ("T1", "Torre de muestreo #1"),
        ("T2", "Torre de muestreo #2"),
        ("SRR", "Torre de muestreo #3 / SRR"),
    )
    filas = []
    for (fecha, turno), grupo in df.groupby(["Fecha", "Turno"], sort=False):
        por_torre = {fila["Torre"]: fila for _, fila in grupo.iterrows()}
        salida = {"Fecha": fecha, "Turno": turno}
        for torre, _ in torres:
            origen = por_torre.get(torre)
            for campo, _, _, _ in campos:
                salida[(torre, campo)] = None if origen is None else origen.get(campo)
        filas.append(salida)

    ws = wb.create_sheet("Trazabilidad Pesos")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A3"

    color_header, color_texto = "D7E1E7", "476475"
    fino = Side(style="thin", color="A6A6A6")
    medio = Side(style="medium", color=color_texto)
    borde = Border(left=fino, right=fino, top=fino, bottom=fino)
    borde_header = Border(left=medio, right=medio, top=medio, bottom=medio)
    encabezado = PatternFill("solid", fgColor=color_header)
    alterna = PatternFill("solid", fgColor=color_header)
    blanco = PatternFill("solid", fgColor="FFFFFF")
    fuente = Font(name="Arial", color=color_texto, size=10)
    fuente_baja = Font(name="Arial", bold=True, color="C00000", size=10)
    fuente_header = Font(name="Arial", bold=True, color=color_texto, size=11)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.merge_cells("A1:A2")
    ws.merge_cells("B1:B2")
    ws["A1"], ws["B1"] = "Fecha", "Turno"
    ws.column_dimensions["A"].width = 13
    ws.column_dimensions["B"].width = 10
    for col_idx in (1, 2):
        celda = ws.cell(1, col_idx)
        celda.fill, celda.font = encabezado, fuente_header
        celda.alignment, celda.border = centro, borde_header

    for bloque_idx, (_, titulo_torre) in enumerate(torres):
        inicio = 3 + bloque_idx * len(campos)
        fin = inicio + len(campos) - 1
        ws.merge_cells(start_row=1, start_column=inicio, end_row=1, end_column=fin)
        celda = ws.cell(1, inicio, titulo_torre)
        celda.fill, celda.font = encabezado, fuente_header
        celda.alignment, celda.border = centro, borde_header
        for offset, (_, titulo, _, ancho) in enumerate(campos):
            col_idx = inicio + offset
            subheader = ws.cell(2, col_idx, titulo)
            subheader.fill, subheader.font = encabezado, fuente_header
            subheader.alignment, subheader.border = centro, borde_header
            ws.column_dimensions[get_column_letter(col_idx)].width = ancho

    for fila_idx, fila in enumerate(filas, 3):
        fill = alterna if (fila_idx - 3) % 2 else blanco
        generales = ((fila["Fecha"], "dd-mm-yyyy"), (fila["Turno"], "General"))
        for col_idx, (valor, formato) in enumerate(generales, 1):
            celda = ws.cell(fila_idx, col_idx)
            if pd.notna(valor):
                celda.value = (
                    pd.to_datetime(valor).to_pydatetime()
                    if col_idx == 1 else valor
                )
            celda.number_format = formato
            celda.fill, celda.font = fill, fuente
            celda.alignment, celda.border = centro, borde

        for bloque_idx, (torre, _) in enumerate(torres):
            inicio = 3 + bloque_idx * len(campos)
            for offset, (origen, _, formato, _) in enumerate(campos):
                valor = fila[(torre, origen)]
                celda = ws.cell(fila_idx, inicio + offset)
                if pd.notna(valor):
                    if origen == "fecha_carga":
                        valor = pd.to_datetime(valor).to_pydatetime()
                    else:
                        valor = float(valor)
                    celda.value = valor
                celda.number_format = formato
                celda.fill, celda.font = fill, fuente
                celda.alignment, celda.border = centro, borde
                if origen in {
                    "Representatividad_Quimica", "Representatividad_Fisica"
                } and pd.notna(valor):
                    celda.font = fuente_baja if float(valor) < 0.75 else fuente

    ultima_fila = len(filas) + 2
    for inicio, fin in ((1, 2), (3, 11), (12, 20), (21, 29)):
        for fila_idx in range(1, ultima_fila + 1):
            for col_idx in range(inicio, fin + 1):
                celda = ws.cell(fila_idx, col_idx)
                actual = celda.border
                celda.border = Border(
                    left=medio if col_idx == inicio else actual.left,
                    right=medio if col_idx == fin else actual.right,
                    top=medio if fila_idx == 1 else actual.top,
                    bottom=medio if fila_idx == ultima_fila else actual.bottom,
                )

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 46
    for fila_idx in range(3, ultima_fila + 1):
        ws.row_dimensions[fila_idx].height = 21
    ws.auto_filter.ref = f"A2:AC{ultima_fila}"


def _export_representatividad_torres_to_excel(
    df: pd.DataFrame,
    df_bd_ton_fy: pd.DataFrame,
    df_bd_ton_mes: pd.DataFrame,
    df_turno_mes: pd.DataFrame | None = None,
    df_gestion_fy_quimico: pd.DataFrame | None = None,
    df_gestion_fy_fisico: pd.DataFrame | None = None,
    fecha_inicio_mes=None,
    fecha_fin_mes=None,
    fecha_corte_operacional=None,
    mapa_comentarios: dict | None = None,
    df_pesos_turno: pd.DataFrame | None = None,
) -> bytes:
    """
    Exporta el reporte de Representatividad Torres a Excel.

    Las hojas Representatividad Torres y BD Ton utilizan la estética
    del bloque AT:BM de Reporte Diario: fondo blanco, encabezados
    jerárquicos, bordes completos y desplazamiento libre.
    """
    from openpyxl import Workbook
    from openpyxl.styles import (
        Font,
        Alignment,
        PatternFill,
        Border,
        Side,
    )
    from openpyxl.cell.cell import MergedCell

    df = df.copy()

    columnas_pct = [
        "TM1_TurnoA_Quimico",
        "TM1_TurnoA_Fisico",
        "TM1_TurnoB_Quimico",
        "TM1_TurnoB_Fisico",
        "TM2_TurnoA_Quimico",
        "TM2_TurnoA_Fisico",
        "TM2_TurnoB_Quimico",
        "TM2_TurnoB_Fisico",
        "SRR_TurnoA_Quimico",
        "SRR_TurnoA_Fisico",
        "SRR_TurnoB_Quimico",
        "SRR_TurnoB_Fisico",
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Representatividad Torres"
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = None

    # Paleta equivalente a Reporte Diario, columnas AT:BM.
    color_header = "D7E1E7"
    color_texto = "476475"
    color_borde = "476475"
    color_borde_interno = "A6A6A6"
    color_subtitulo = "666666"

    fill_blanco = PatternFill("solid", fgColor="FFFFFF")
    fill_header = PatternFill("solid", fgColor=color_header)
    fill_alt = PatternFill("solid", fgColor=color_header)

    font_titulo = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=14,
    )
    font_subtitulo = Font(
        name="Arial",
        italic=True,
        color=color_subtitulo,
        size=9,
    )
    font_header = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=11,
    )
    font_normal = Font(
        name="Arial",
        color=color_texto,
        size=10,
    )
    font_fecha = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=10,
    )
    font_bajo = Font(
        name="Arial",
        bold=True,
        color="C00000",
        size=10,
    )
    thin = Side(style="thin", color=color_borde_interno)
    thin_header = Side(style="thin", color=color_borde)
    medium = Side(style="medium", color=color_borde)

    border_datos = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin,
    )
    border_header = Border(
        left=thin_header,
        right=thin_header,
        top=thin_header,
        bottom=thin_header,
    )

    center = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )

    def _aplicar_contorno(
        fila_ini: int,
        col_ini: int,
        fila_fin: int,
        col_fin: int,
        estilo=medium,
    ) -> None:
        """Refuerza el contorno del bloque sin perder las líneas internas."""
        for fila in range(fila_ini, fila_fin + 1):
            for col in range(col_ini, col_fin + 1):
                celda = ws.cell(fila, col)
                borde_actual = celda.border
                celda.border = Border(
                    left=estilo if col == col_ini else borde_actual.left,
                    right=estilo if col == col_fin else borde_actual.right,
                    top=estilo if fila == fila_ini else borde_actual.top,
                    bottom=estilo if fila == fila_fin else borde_actual.bottom,
                )

    # ------------------------------------------------------------
    # Título y subtítulo
    # ------------------------------------------------------------
    ws.merge_cells("A1:M1")
    ws["A1"] = "Representatividad diaria de torres de muestreo"
    ws["A1"].font = font_titulo
    ws["A1"].alignment = center
    ws["A1"].fill = fill_blanco

    ws.merge_cells("A2:M2")
    ws["A2"] = (
        "Valores expresados en porcentaje. Los valores menores a 75% "
        "se destacan en rojo."
    )
    ws["A2"].font = font_subtitulo
    ws["A2"].alignment = center
    ws["A2"].fill = fill_blanco

    # ------------------------------------------------------------
    # Encabezados jerárquicos
    # ------------------------------------------------------------
    ws.merge_cells("A4:A6")
    ws.merge_cells("B4:E4")
    ws.merge_cells("F4:I4")
    ws.merge_cells("J4:M4")
    ws.merge_cells("B5:C5")
    ws.merge_cells("D5:E5")
    ws.merge_cells("F5:G5")
    ws.merge_cells("H5:I5")
    ws.merge_cells("J5:K5")
    ws.merge_cells("L5:M5")

    ws["A4"] = "Día"
    ws["B4"] = "Representatividad TM1"
    ws["F4"] = "Representatividad TM2"
    ws["J4"] = "Representatividad TM3 / SRR"
    ws["B5"] = "Turno A"
    ws["D5"] = "Turno B"
    ws["F5"] = "Turno A"
    ws["H5"] = "Turno B"
    ws["J5"] = "Turno A"
    ws["L5"] = "Turno B"

    headers_fila_6 = [
        "Químico",
        "Físico",
        "Químico",
        "Físico",
        "Químico",
        "Físico",
        "Químico",
        "Físico",
        "Químico",
        "Físico",
        "Químico",
        "Físico",
    ]
    for col, header in enumerate(headers_fila_6, start=2):
        ws.cell(6, col, header)

    for fila in range(4, 7):
        for col in range(1, 14):
            celda = ws.cell(fila, col)
            if isinstance(celda, MergedCell):
                continue
            celda.fill = fill_header
            celda.font = font_header
            celda.alignment = center
            celda.border = border_header

    # ------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------
    fila_inicio = 7

    for fila_excel, (_, fila_df) in enumerate(
        df.iterrows(),
        start=fila_inicio,
    ):
        es_alterna = (fila_excel - fila_inicio) % 2 == 1
        fill_fila = fill_alt if es_alterna else fill_blanco

        fecha = pd.to_datetime(
            fila_df.get("Dia"),
            errors="coerce",
        )
        celda_fecha = ws.cell(fila_excel, 1)
        celda_fecha.value = (
            fecha.to_pydatetime()
            if pd.notna(fecha)
            else None
        )
        celda_fecha.number_format = "dd-mm-yyyy"
        celda_fecha.fill = fill_fila
        celda_fecha.font = font_fecha
        celda_fecha.alignment = center
        celda_fecha.border = border_datos

        for col_excel, nombre_columna in enumerate(
            columnas_pct,
            start=2,
        ):
            celda = ws.cell(fila_excel, col_excel)
            valor = pd.to_numeric(
                fila_df.get(nombre_columna),
                errors="coerce",
            )

            celda.fill = fill_fila
            celda.alignment = center
            celda.border = border_datos

            es_futura = (
                fecha_corte_operacional is not None
                and pd.notna(fecha)
                and fecha.date() > fecha_corte_operacional
            )
            if es_futura:
                celda.value = None
                celda.font = font_normal
            elif pd.isna(valor):
                celda.value = "Tambor detenido"
                celda.font = Font(
                    name="Arial",
                    italic=True,
                    color=color_texto,
                    size=10,
                )
            else:
                celda.value = float(valor)
                celda.number_format = "0.0%"
                celda.font = (
                    font_bajo
                    if float(valor) < 0.75
                    else font_normal
                )

    ultima_fila = max(fila_inicio + len(df) - 1, fila_inicio)

    # Contornos funcionales: Día, TM1 y TM2.
    for col_ini, col_fin in [
        (1, 1),
        (2, 5),
        (6, 9),
        (10, 13),
    ]:
        _aplicar_contorno(4, col_ini, ultima_fila, col_fin)

    # Las celdas combinadas de los títulos requieren un contorno propio.
    # Aplicarlo a todo el rango evita los cortes que Excel puede producir en
    # el borde inferior de una celda combinada.
    _aplicar_contorno(4, 2, 4, 5)
    _aplicar_contorno(4, 6, 4, 9)
    _aplicar_contorno(4, 10, 4, 13)
    for referencia in ("B4", "F4", "J4"):
        # Excel reconstruye el borde exterior de una celda combinada desde
        # su celda ancla; por eso los cuatro lados deben quedar definidos.
        ws[referencia].border = Border(
            left=medium,
            right=medium,
            top=medium,
            bottom=medium,
        )

    # Dimensiones equivalentes al bloque AT:BM.
    ws.column_dimensions["A"].width = 15
    for columna in ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]:
        ws.column_dimensions[columna].width = 15

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 24
    ws.row_dimensions[6].height = 24
    for fila in range(fila_inicio, ultima_fila + 1):
        ws.row_dimensions[fila].height = 21

    if len(df) > 0:
        ws.auto_filter.ref = f"A6:M{ultima_fila}"

    # Segunda hoja: BD Ton con la misma identidad visual.
    _agregar_hoja_bd_ton(
        wb=wb,
        df_bd_ton=df_bd_ton_fy,
    )

    # Hojas mensuales Químico y Físico: solo el mes evaluado.
    _agregar_hojas_mensuales_torres(
        wb=wb,
        df_bd_ton=df_bd_ton_mes,
        df_turno=df_turno_mes,
        df_gestion_fy_quimico=df_gestion_fy_quimico,
        df_gestion_fy_fisico=df_gestion_fy_fisico,
        fecha_inicio_mes=fecha_inicio_mes,
        fecha_fin_mes=fecha_fin_mes,
        fecha_corte_operacional=fecha_corte_operacional,
        mapa_comentarios=mapa_comentarios,
    )

    _agregar_hoja_trazabilidad_pesos(wb, df_pesos_turno)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return output.getvalue()


def _export_representatividad_desde_paquete(
    paquete: dict,
    mapa_comentarios: dict | None = None,
) -> bytes:
    """Arma Excel desde snapshot guardado (sin SP ni consultas pesadas)."""
    if not paquete or "rep_torres" not in paquete:
        raise RuntimeError("Paquete de snapshot incompleto.")

    fecha_corte = paquete.get("fecha_corte_operacional")
    if fecha_corte is not None and not isinstance(fecha_corte, date):
        fecha_corte = pd.to_datetime(fecha_corte).date()

    return _export_representatividad_torres_to_excel(
        df=paquete["rep_torres"],
        df_bd_ton_fy=paquete["bd_ton_fy"],
        df_bd_ton_mes=paquete["bd_ton_mes"],
        df_turno_mes=paquete["turno_mes"],
        df_gestion_fy_quimico=paquete["gestion_fy_quimico"],
        df_gestion_fy_fisico=paquete["gestion_fy_fisico"],
        fecha_inicio_mes=paquete.get("fecha_inicio_mes"),
        fecha_fin_mes=paquete.get("fecha_fin_mes"),
        fecha_corte_operacional=fecha_corte,
        mapa_comentarios=mapa_comentarios,
        df_pesos_turno=paquete.get("pesos_turno", pd.DataFrame()),
    )


def _inspeccionar_workbook_representatividad(
    xlsx_bytes: bytes,
    fecha_fin,
) -> dict:
    """Lee del XLSX final el corte, filas e indicadores usados por los PDF."""
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
    fecha = pd.Timestamp(fecha_fin)
    prefijo = (
        f"01_{_MESES_ABR_TORRES[fecha.month]}_"
        f"{str(fecha.year)[-2:]}"
    )

    def _hoja(sufijo: str):
        esperado = f"{prefijo} {sufijo}"
        candidatos = [
            nombre for nombre in wb.sheetnames
            if nombre == esperado or nombre.endswith(f" {sufijo}")
        ]
        if not candidatos:
            raise RuntimeError(f"El workbook no contiene la hoja {sufijo}.")
        return wb[candidatos[0]]

    def _valor_periodo(ws, fila_inicio: int, periodo: str) -> float:
        for fila in range(fila_inicio + 2, fila_inicio + 9):
            if str(ws.cell(fila, 3).value or "").strip() == periodo:
                return float(ws.cell(fila, 4).value or 0.0)
        raise RuntimeError(
            f"No se encontró {periodo} desde la fila {fila_inicio}."
        )

    def _detalle(ws, fila_inicio: int, fila_fin: int) -> tuple[date | None, int]:
        fechas = []
        filas = 0
        for fila in range(fila_inicio, fila_fin + 1):
            # La fecha calendario puede existir en filas futuras; Pad distingue
            # las filas que realmente contienen detalle operacional.
            if ws.cell(fila, 5).value in (None, ""):
                continue
            fecha_valor = pd.to_datetime(
                ws.cell(fila, 4).value,
                errors="coerce",
            )
            if pd.notna(fecha_valor):
                fechas.append(fecha_valor.date())
                filas += 1
        return (max(fechas) if fechas else None, filas)

    resultado = {}
    for tipo, sufijo in (("quimico", "Quimico"), ("fisico", "Fisico")):
        ws = _hoja(sufijo)
        fecha_max, filas_detalle = _detalle(ws, 57, 121)
        fy = {}
        for fila in range(1, ws.max_row + 1):
            etiqueta = str(ws.cell(fila, 20).value or "").strip()
            if etiqueta and etiqueta != "Periodo":
                valor = ws.cell(fila, 23).value
                if isinstance(valor, (int, float)):
                    fy[etiqueta] = float(valor)
        resultado[tipo] = {
            "tm2_semana_2": _valor_periodo(ws, 27, "Semana 2"),
            "tm2_mtd": _valor_periodo(ws, 27, "MTD"),
            "combinado_semana_2": _valor_periodo(ws, 38, "Semana 2"),
            "combinado_mtd": _valor_periodo(ws, 38, "MTD"),
            "fy": fy,
            "fecha_max_detalle": fecha_max,
            "filas_detalle": filas_detalle,
            "print_area": str(ws.print_area),
        }

    ws_srr = _hoja("SRR")
    fecha_max_srr, filas_srr = _detalle(ws_srr, 44, ws_srr.max_row)
    tonelaje_sulfuro_sin_torre = None
    for fila in range(11, 15):
        if str(ws_srr.cell(fila, 4).value or "").strip() == "Sin Torre":
            # Las filas 13:14 corresponden a Sulfuro (C13:C14 combinado).
            if fila >= 13:
                tonelaje_sulfuro_sin_torre = float(
                    ws_srr.cell(fila, 5).value or 0.0
                )
                break
    resultado["srr"] = {
        "sulfuro_sin_torre": tonelaje_sulfuro_sin_torre,
        "fecha_max_detalle": fecha_max_srr,
        "filas_detalle": filas_srr,
        "print_area": str(ws_srr.print_area),
    }
    return resultado


class WorkbookRepresentatividadInconsistenteError(RuntimeError):
    """El XLSX de representatividad no pasó la validación previa a exportar."""

    def __init__(self, mensaje_tecnico: str, *, tipo: str, detalle: str):
        super().__init__(mensaje_tecnico)
        self.tipo = tipo
        self.detalle = detalle


def _etiqueta_tipo_rep(tipo: str) -> str:
    return {
        "quimico": "Químico",
        "fisico": "Físico",
        "srr": "SRR",
    }.get(str(tipo).lower(), str(tipo))


def _fmt_pct_rep(valor) -> str:
    if valor is None:
        return "sin valor"
    return f"{float(valor) * 100:.2f}%"


def _contenido_modal_workbook_inconsistente(
    exc: WorkbookRepresentatividadInconsistenteError,
):
    """Mensaje legible para el modal de error de exportación."""
    return [
        html.P(
            "No se pudo generar el reporte "
            f"{_etiqueta_tipo_rep(exc.tipo)} porque los indicadores del "
            "libro Excel no son consistentes entre sí.",
            className="mb-3",
        ),
        html.P(exc.detalle, className="mb-3"),
        html.P(
            "Vuelva a refrescar o publicar el período, o revise los datos "
            "de origen, y reintente la exportación.",
            className="mb-0 text-muted",
        ),
    ]


def _validar_workbook_representatividad(
    xlsx_bytes: bytes,
    fecha_fin,
    fecha_corte,
) -> dict:
    """Impide convertir un workbook cuyo detalle no corresponda al corte."""
    metricas = _inspeccionar_workbook_representatividad(xlsx_bytes, fecha_fin)
    corte = pd.to_datetime(fecha_corte).date()
    for tipo in ("quimico", "fisico", "srr"):
        fecha_max = metricas[tipo]["fecha_max_detalle"]
        if fecha_max != corte:
            raise WorkbookRepresentatividadInconsistenteError(
                f"Workbook inconsistente para {tipo}: corte={corte}, "
                f"fecha máxima del detalle={fecha_max}. No se convertirá PDF.",
                tipo=tipo,
                detalle=(
                    f"La fecha de corte operacional es {corte.strftime('%d-%m-%Y')}, "
                    "pero el detalle del reporte llega hasta "
                    f"{fecha_max.strftime('%d-%m-%Y') if fecha_max else 'sin fecha'}."
                ),
            )

    # En el mes actual del FY, la barra mensual FY debe coincidir con el MTD
    # combinado. La YTD se conserva y se reporta por separado.
    etiqueta_mes = f"{_MESES_ABR_TORRES[pd.Timestamp(fecha_fin).month]}-"
    etiqueta_mes += str(pd.Timestamp(fecha_fin).year)[-2:]
    for tipo in ("quimico", "fisico"):
        fy_mes = metricas[tipo]["fy"].get(etiqueta_mes)
        combinado_mtd = metricas[tipo]["combinado_mtd"]
        if fy_mes is None or abs(fy_mes - combinado_mtd) > 1e-9:
            raise WorkbookRepresentatividadInconsistenteError(
                f"Workbook inconsistente para {tipo}: FY {etiqueta_mes}="
                f"{fy_mes}, combinado MTD={combinado_mtd}. No se convertirá PDF.",
                tipo=tipo,
                detalle=(
                    f"En {etiqueta_mes}, el indicador FY "
                    f"({_fmt_pct_rep(fy_mes)}) no coincide con el MTD "
                    f"combinado ({_fmt_pct_rep(combinado_mtd)})."
                ),
            )
    return metricas


def _construir_fuente_unica_representatividad(
    fecha_inicio,
    fecha_fin,
    mapa_comentarios: dict | None = None,
) -> tuple[dict, bytes, dict]:
    """Construye una vez paquete vivo + workbook para XLSX y los tres PDF."""
    if mapa_comentarios is None:
        try:
            guardado = fetch_comentarios_representatividad_periodo(
                fecha_inicio,
                fecha_fin,
            )
            if not guardado.empty:
                mapa_comentarios = comentarios_mapa_desde_dataframe(guardado)
        except Exception:
            mapa_comentarios = None

    paquete = armar_paquete_reporte_torre_oficial(
        pd.to_datetime(fecha_inicio).date(),
        pd.to_datetime(fecha_fin).date(),
    )
    xlsx_bytes = _export_representatividad_desde_paquete(
        paquete,
        mapa_comentarios=mapa_comentarios,
    )
    # El PDF en Python arma el detalle por su cuenta desde el paquete, así que
    # necesita el mismo mapa que se usó acá; sin esto perdería los comentarios
    # y el Pad ajustado en el editor.
    paquete["mapa_comentarios"] = mapa_comentarios
    metricas = _validar_workbook_representatividad(
        xlsx_bytes,
        fecha_fin,
        paquete["fecha_corte_operacional"],
    )
    print(
        "[RTO FUENTE UNICA]",
        {
            "fecha_inicio": str(fecha_inicio),
            "fecha_fin": str(fecha_fin),
            "fecha_corte": str(paquete["fecha_corte_operacional"]),
            "filas_rep": len(paquete["rep_torres"]),
            "filas_bd_ton_mes": len(paquete["bd_ton_mes"]),
            "filas_turno_mes": len(paquete["turno_mes"]),
            "workbook_bytes": len(xlsx_bytes),
            "metricas": metricas,
        },
    )
    return paquete, xlsx_bytes, metricas


def _generar_excel_representatividad_completo(
    fecha_inicio,
    fecha_fin,
    mapa_comentarios: dict | None = None,
) -> bytes:
    """Construye una unica fuente Excel para las descargas XLSX y PDF."""
    _, xlsx_bytes, _ = _construir_fuente_unica_representatividad(
        fecha_inicio,
        fecha_fin,
        mapa_comentarios=mapa_comentarios,
    )
    return xlsx_bytes


def _export_dataframe_simple_to_excel(df: pd.DataFrame, sheet_name: str = "Reporte") -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

    output.seek(0)
    return output.getvalue()

def _preparar_reporte_turno_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ordena las columnas del reporte por turno en el mismo orden visual del formato BHP
    y reemplaza valores vacíos:
      - columnas numéricas: NULL/NaN -> 0
      - columnas de texto: NULL/NaN -> "-"
    Además redondea valores numéricos para visualización y exportación.
    """
    df = df.copy()

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.strftime("%d-%m-%Y")
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
    columnas_ordenadas = [
        "Fecha",
        "Campania",
        "Material",
        "Modulo",
        "Avance",
        "Turno",

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
        "CuFe_Plan_Semanal",
        "CuFe_Plan_Mensual",

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

    columnas_ordenadas = [c for c in columnas_ordenadas if c in df.columns]
    df = df[columnas_ordenadas]

    columnas_texto = [
        "Fecha",
        "Turno",
        "Campania",
        "Material",
        "Modulo",
        "Fuente_Info_Quimica",
        "Fuente_Info_Fisica",
        "Malla_Menos_1_2_Plan_Semanal",  # puede venir como "<75%"
    ]

    columnas_texto = [c for c in columnas_texto if c in df.columns]
    columnas_numericas = [c for c in df.columns if c not in columnas_texto]

    for col in columnas_numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Avance viene desde SQL/cache en escala 0-1.
    # Para visualización se muestra en escala 0-100.
    if "Avance" in df.columns:
        df["Avance"] = pd.to_numeric(df["Avance"], errors="coerce") * 100

    # STOCK, MINA y SRR ya vienen desde SQL/cache en escala 0-100.
    # No multiplicar ni dividir.
    for col in ["STOCK", "MINA", "SRR"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Solubilidad es razón CuS/CuT, no porcentaje.
    # No multiplicar por 100.
    for col in ["Solubilidad_Real", "Solubilidad_Plan_Semanal", "Solubilidad_Plan_Mensual"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Limpiar objetivo granulométrico.
    if "Malla_Menos_1_2_Plan_Semanal" in df.columns:
        df["Malla_Menos_1_2_Plan_Semanal"] = (
            df["Malla_Menos_1_2_Plan_Semanal"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .replace({"nan": "", "None": "", "NULL": ""})
        )

    cols_0_dec = [
        "Apilado_TMS_Real",
        "Apilado_TMS_Plan_Mensual",
    ]

    cols_2_dec = [
        "Avance",
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
        "CuFe_Plan_Semanal",
        "CuFe_Plan_Mensual",

        "FeT_Real",
        "FeS_Real",
        "ConsH_Real",

        "Malla_Menos_1_2_Real",
        "Malla_Menos_100_Real",
        "Malla_Menos_100_Plan_Semanal",
        "Malla_Menos_100_Plan_Mensual",

        "CaolBeta_Real",
        "CaolBeta_Plan_Semanal",
        "CaolBeta_Plan_Mensual",

        "Dosis_Acido_Ideal_TM",
        "Dosis_Acido_Programa_Semanal",
    ]

    for col in cols_0_dec:
        if col in df.columns:
            df[col] = df[col].round(0)

    for col in cols_2_dec:
        if col in df.columns:
            df[col] = df[col].round(2)

    for col in columnas_texto:
        df[col] = df[col].fillna("-")

    return df


def _tabla_reporte_turno(df: pd.DataFrame):
    df = _preparar_reporte_turno_df(df)

    # Encabezados agrupados tipo BHP
    column_headers = {
    "Fecha": ["", "Fecha"],
    "Campania": ["", "Campaña"],
    "Material": ["", "Material"],
    "Modulo": ["", "Módulo"],
    "Avance": ["", "Avance (%)"],
    "Turno": ["", "Turno"],

    "Apilado_TMS_Real": ["Apilado TMS", "Real"],
    "Apilado_TMS_Plan_Mensual": ["Apilado TMS", "Plan"],

    "STOCK": ["Distribución origen", "Stock (%)"],
    "MINA": ["Distribución origen", "Mina (%)"],
    "SRR": ["Distribución origen", "SRR (%)"],

    "CuT_Real": ["Análisis Químicos", "CuT Real (%)"],
    "CuT_Plan_Semanal": ["Análisis Químicos", "CuT Programa (%)"],
    "CuT_Plan_Mensual": ["Análisis Químicos", "CuT Plan (%)"],

    "CuS_Real": ["Análisis Químicos", "CuS Real (%)"],
    "CuS_Plan_Semanal": ["Análisis Químicos", "CuS Programa (%)"],
    "CuS_Plan_Mensual": ["Análisis Químicos", "CuS Plan (%)"],

    "Solubilidad_Real": ["Análisis Químicos", "Solubilidad Real"],
    "Solubilidad_Plan_Semanal": ["Análisis Químicos", "Solubilidad Programa"],
    "Solubilidad_Plan_Mensual": ["Análisis Químicos", "Solubilidad Plan"],

    "CO3_Real": ["Análisis Químicos", "CO3 Real (%)"],
    "CO3_Plan_Semanal": ["Análisis Químicos", "CO3 Programa (%)"],
    "CO3_Plan_Mensual": ["Análisis Químicos", "CO3 Plan (%)"],

    "CuFe_Real": ["Análisis Químicos", "CuFe Real (%)"],
    "CuFe_Plan_Semanal": ["Análisis Químicos", "CuFe Programa (%)"],
    "CuFe_Plan_Mensual": ["Análisis Químicos", "CuFe Plan (%)"],

    "FeT_Real": ["Análisis Químicos", "FeT Real (%)"],
    "FeS_Real": ["Análisis Químicos", "FeS Real (%)"],

    "ConsH_Real": ["Análisis Químicos", "Consumo de Ácido (kg/ton)"],

    "Malla_Menos_1_2_Real": ["Granulometrías", "-1/2 Real (%)"],
    "Malla_Menos_1_2_Plan_Semanal": ["Granulometrías", "-1/2 Plan (%)"],

    "Malla_Menos_100_Real": ["Granulometrías", "-100#Ty Real (%)"],
    "Malla_Menos_100_Plan_Semanal": ["Granulometrías", "-100#Ty Programa (%)"],
    "Malla_Menos_100_Plan_Mensual": ["Granulometrías", "-100#Ty Plan (%)"],

    "CaolBeta_Real": ["NIR", "CaolBeta Real (%)"],
    "CaolBeta_Plan_Semanal": ["NIR", "CaolBeta Programa (%)"],
    "CaolBeta_Plan_Mensual": ["NIR", "CaolBeta Plan (%)"],

    "Dosis_Acido_Ideal_TM": ["Dosis de ácido (kg/ton)", "Ideal TM"],
    "Dosis_Acido_Programa_Semanal": ["Dosis de ácido (kg/ton)", "Programa"],

    "Fuente_Info_Quimica": ["Fuentes de información", "Muestra química"],
    "Fuente_Info_Fisica": ["Fuentes de información", "Muestra física"],
 }

    columnas_texto = [
    "Fecha",
    "Turno",
    "Campania",
    "Material",
    "Modulo",
    "Fuente_Info_Quimica",
    "Fuente_Info_Fisica",
    "Malla_Menos_1_2_Plan_Semanal",
 ]
    columnas_numericas = [c for c in df.columns if c not in columnas_texto]

    return dash_table.DataTable(
        id="tabla-reporte-turno",
        columns=[
            {
                "name": column_headers.get(c, ["", c]),
                "id": c,
                "type": "numeric" if c in columnas_numericas else "text",
            }
            for c in df.columns
        ],
        data=df.to_dict("records"),
        merge_duplicate_headers=True,
        page_size=20,
        sort_action="native",
        filter_action="none",
        fixed_rows={"headers": True},
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "650px",
            "width": "100%",
            "maxWidth": "100%",
            "border": "1px solid #d0d0d0",
        },
        style_cell={
            "textAlign": "center",
            "fontFamily": "Arial",
            "fontSize": "11px",
            "padding": "5px",
            "minWidth": "90px",
            "width": "105px",
            "maxWidth": "140px",
            "whiteSpace": "normal",
            "height": "auto",
            "border": "1px solid #d9d9d9",
        },
        style_header={
            "backgroundColor": "#9DC3E6",
            "fontWeight": "bold",
            "color": "#1f4e79",
            "textAlign": "center",
            "border": "1px solid #7f9db9",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f7f3ef"},
            {"if": {"column_id": "Fecha"}, "backgroundColor": "#d9eaf7", "fontWeight": "bold"},
            {"if": {"column_id": "Turno"}, "backgroundColor": "#f2f2f2", "fontWeight": "bold"},
        ],
        style_cell_conditional=[
            {
                "if": {"column_id": "ConsH_Real"},
                "minWidth": "150px",
                "width": "160px",
                "maxWidth": "180px",
            },
            {
                "if": {"column_id": "Dosis_Acido_Ideal_TM"},
                "minWidth": "130px",
                "width": "140px",
                "maxWidth": "160px",
            },
            {
                "if": {"column_id": "Dosis_Acido_Programa_Semanal"},
                "minWidth": "130px",
                "width": "140px",
                "maxWidth": "160px",
            },

        ],
    )



def _export_reporte_turno_formateado(df: pd.DataFrame) -> bytes:
    """
    Exporta el reporte por turno con formato tipo BHP:
    encabezados agrupados, mismo orden de columnas de la visualización y reemplazo de vacíos por cero.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    df = _preparar_reporte_turno_df(df)

    wb = Workbook()
    ws = wb.active
    ws.title = "Analisis Turno"

    # Estilos
    azul = PatternFill("solid", fgColor="9DC3E6")
    celeste = PatternFill("solid", fgColor="D9EAF7")
    gris = PatternFill("solid", fgColor="F2F2F2")
    beige = PatternFill("solid", fgColor="F7F3EF")
    blanco = PatternFill("solid", fgColor="FFFFFF")

    font_bhp = Font(bold=True, size=28, color="E97132")
    font_titulo = Font(bold=True, size=14, color="1F4E79")
    font_header = Font(bold=True, color="1F4E79")
    font_normal = Font(color="404040")

    thin = Side(style="thin", color="B8B8B8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    max_col = len(df.columns)
    last_col = get_column_letter(max_col)

    # Encabezado superior
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    ws["A1"] = "BHP"
    ws["A1"].font = font_bhp
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=max_col)
    ws["A3"] = "Análisis de las Torres de Muestreo por Turno"
    ws["A3"].font = font_titulo
    ws["A3"].alignment = center

    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=max_col)
    ws["A4"] = "Superintendencia de Medición y Reconciliación - Gerencia de Planificación de la Producción"
    ws["A4"].font = Font(size=10, color="404040")
    ws["A4"].alignment = center

    row_group = 7
    row_header = 8
    row_data = 9

    # Nombres visibles
    headers = {
        "Fecha": "Fecha",
        "Campania": "Campaña",
        "Material": "Material",
        "Modulo": "Módulo",
        "Avance": "Avance",
        "Turno": "Turno",

        "Apilado_TMS_Real": "Real",
        "Apilado_TMS_Plan_Mensual": "Plan",

        "STOCK": "Stock",
        "MINA": "Mina",
        "SRR": "SRR",

        "CuT_Real": "Real",
        "CuT_Plan_Mensual": "Programa",
        "CuT_Plan_Semanal": "Plan",

        "CuS_Real": "Real",
        "CuS_Plan_Mensual": "Programa",
        "CuS_Plan_Semanal": "Plan",

        "Solubilidad_Real": "Real",
        "Solubilidad_Plan_Mensual": "Programa",
        "Solubilidad_Plan_Semanal": "Plan",

        "CO3_Real": "Real",
        "CO3_Plan_Mensual": "Programa",
        "CO3_Plan_Semanal": "Plan",

        "CuFe_Real": "Real",
        "CuFe_Plan_Mensual": "Programa",
        "CuFe_Plan_Semanal": "Plan",

        "FeT_Real": "Real",
        "FeS_Real": "Real",
        "ConsH_Real": "Consumo ácido kg/t",

        "Malla_Menos_1_2_Real": "Real",
        "Malla_Menos_1_2_Plan_Semanal": "Plan",

        "Malla_Menos_100_Real": "Real",
        "Malla_Menos_100_Plan_Mensual": "Programa",
        "Malla_Menos_100_Plan_Semanal": "Plan",

        "CaolBeta_Real": "Real",
        "CaolBeta_Plan_Mensual": "Programa",
        "CaolBeta_Plan_Semanal": "Plan",

        "Dosis_Acido_Ideal_TM": "Ideal TM",
        "Dosis_Acido_Programa_Semanal": "Programa semanal",

        "Fuente_Info_Quimica": "Muestra química",
        "Fuente_Info_Fisica": "Muestra física",
    }

    for idx, col in enumerate(df.columns, start=1):
        cell = ws.cell(row=row_header, column=idx)
        cell.value = headers.get(col, col)
        cell.fill = celeste
        cell.font = font_header
        cell.alignment = center
        cell.border = border

    # Grupos por rangos según el orden de columnas
    def col_pos(col_name):
        try:
            return list(df.columns).index(col_name) + 1
        except ValueError:
            return None

    grupos = []

    # General: Fecha a Turno
    if col_pos("Fecha") and col_pos("Turno"):
        grupos.append(("", col_pos("Fecha"), col_pos("Turno")))

    if col_pos("Apilado_TMS_Real") and col_pos("Apilado_TMS_Plan_Mensual"):
        grupos.append(("Apilado TMS", col_pos("Apilado_TMS_Real"), col_pos("Apilado_TMS_Plan_Mensual")))

    if col_pos("STOCK") and col_pos("SRR"):
        grupos.append(("Distribución origen", col_pos("STOCK"), col_pos("SRR")))

    if col_pos("CuT_Real") and col_pos("ConsH_Real"):
        grupos.append(("Análisis Químicos", col_pos("CuT_Real"), col_pos("ConsH_Real")))

    if col_pos("Malla_Menos_1_2_Real") and col_pos("Malla_Menos_100_Plan_Semanal"):
        grupos.append(("Granulometrías", col_pos("Malla_Menos_1_2_Real"), col_pos("Malla_Menos_100_Plan_Semanal")))

    if col_pos("CaolBeta_Real") and col_pos("CaolBeta_Plan_Semanal"):
        grupos.append(("NIR", col_pos("CaolBeta_Real"), col_pos("CaolBeta_Plan_Semanal")))

    if col_pos("Dosis_Acido_Ideal_TM") and col_pos("Dosis_Acido_Programa_Semanal"):
        grupos.append(("Dosis de ácido", col_pos("Dosis_Acido_Ideal_TM"), col_pos("Dosis_Acido_Programa_Semanal")))

    if col_pos("Fuente_Info_Quimica") and col_pos("Fuente_Info_Fisica"):
        grupos.append(("Fuentes de información", col_pos("Fuente_Info_Quimica"), col_pos("Fuente_Info_Fisica")))

    for titulo, c_ini, c_fin in grupos:
        if c_ini is None or c_fin is None:
            continue
        ws.merge_cells(start_row=row_group, start_column=c_ini, end_row=row_group, end_column=c_fin)
        cell = ws.cell(row=row_group, column=c_ini)
        cell.value = titulo
        cell.fill = azul if titulo else blanco
        cell.font = font_header
        cell.alignment = center
        cell.border = border
        for c in range(c_ini, c_fin + 1):
            ws.cell(row=row_group, column=c).fill = azul if titulo else blanco
            ws.cell(row=row_group, column=c).border = border

    # Datos
    for r_idx, (_, row) in enumerate(df.iterrows(), start=row_data):
        for c_idx, col in enumerate(df.columns, start=1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.value = row[col]
            cell.font = font_normal
            cell.alignment = center
            cell.border = border

            if (r_idx - row_data) % 2 == 1:
                cell.fill = beige

            if col == "Fecha":
                cell.fill = celeste
            elif col in ["Campania", "Material", "Modulo", "Avance", "Turno"]:
                cell.fill = gris

            if isinstance(cell.value, float):
                cell.number_format = "0.00"

    # Anchos y filtros
    for c_idx, col in enumerate(df.columns, start=1):
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = 15

    ws.freeze_panes = "G9"
    ws.auto_filter.ref = f"A8:{last_col}{ws.max_row}"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


@callback(
    Output("report-historial", "children"),
    Input("report-subtabs", "value"),
    prevent_initial_call=False,
)
def cargar_historial_representatividad_torres(subtab):
    """Muestra el historial al abrir Reportes Diarios, sin pulsar Editar comentarios."""
    if subtab != "tab-diarios":
        return html.Div()
    try:
        df_hist = fetch_historial_reporte_torre_oficial()
    except Exception:
        df_hist = pd.DataFrame()
    return _tabla_historial_representatividad(df_hist)


# Espeja los pasos de refrescar_representatividad_para_exportacion
# (report_export.py): si cambian alla, cambian aca.
_AVISO_REFRESCO_EDITOR = html.Div(
    [
        html.Strong("Actualizando datos antes de abrir el editor…"),
        html.Ol(
            [
                html.Li("Apilado por turno (evaluabilidad RN-046)"),
                html.Li("Peso de torres (totalizador de 10 s)"),
                html.Li("Representatividad por torre"),
                html.Li("BD Ton"),
            ],
            className="mb-0 mt-2",
        ),
    ],
    className="text-muted small",
)


@callback(
    Output("report-grafico", "children"),
    Output("report-tabla", "children"),
    Output("report-historial", "children", allow_duplicate=True),
    Output("rep-comentarios-store", "data", allow_duplicate=True),
    Output("rep-tab-activo-store", "data", allow_duplicate=True),
    Output("rep-periodo-store", "data", allow_duplicate=True),
    Input({"type": "report-gen-btn", "tipo": ALL}, "n_clicks"),
    State("report-fecha-inicio", "date"),
    State("report-fecha-final", "date"),
    State("report-fecha-modo", "value"),
    prevent_initial_call=True,
    running=[
        # Abrir el editor dejo de ser instantaneo: refresca cuatro capas antes
        # de leer. Sin este aviso la espera no tiene explicacion en pantalla.
        (Output("report-progress", "children"), _AVISO_REFRESCO_EDITOR, ""),
        # Ademas evita el doble clic: el segundo refresco no corrompe nada
        # (sp_getapplock lo serializa, ver
        # agents/FIX_refresco_representatividad_concurrencia.md) pero abortaria
        # con "otro proceso esta actualizando" en la cara del usuario.
        (
            Output({"type": "report-gen-btn", "tipo": MATCH}, "disabled"),
            True,
            False,
        ),
    ],
)
def generar_reporte(n_clicks_list, f_ini, f_fin, modo_fecha):
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update, no_update, no_update, no_update, no_update
    if not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update, no_update, no_update, no_update

    tipo = triggered["tipo"]

    if not f_ini or not f_fin:
        return (
            dbc.Alert("⚠️ Debe seleccionar rango de fechas.", color="warning"),
            html.Div(),
            no_update,
            no_update,
            no_update,
            no_update,
        )

    ini = pd.to_datetime(f_ini).date()
    fin = pd.to_datetime(f_fin).date()
    # El SP usa fecha final exclusiva: Fecha >= inicio AND Fecha < fin
    fin_sql_exclusivo = (pd.to_datetime(f_fin) + pd.Timedelta(days=1)).date()

    # ------------------------------------------------------------
    # REPORTE REPRESENTATIVIDAD TORRES
    # ------------------------------------------------------------
    if tipo == "representatividad_torres":
        try:
            periodo_store = _periodo_store_desde_fechas(ini, fin, modo_fecha)
            puede_publicar = periodo_store.get("modo") == "mes" and bool(
                periodo_store.get("periodo_mes")
            )
            detalle, _ = _cargar_detalle_representatividad_periodo(
                ini,
                fin,
                periodo_mes=periodo_store.get("periodo_mes"),
            )
            if detalle.empty:
                return (
                    dbc.Alert("Sin detalle para comentarios en el rango.", color="info"),
                    html.Div(),
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            registros = detalle.copy()
            registros["Fecha"] = pd.to_datetime(
                registros["Fecha"], errors="coerce"
            ).dt.strftime("%Y-%m-%d")
            registros = registros.astype(object).where(pd.notna(registros), None)
            registros_store = registros.to_dict("records")

            es_republicacion = (
                puede_publicar
                and bool(periodo_store.get("periodo_mes"))
                and mes_tiene_reporte_activo(str(periodo_store["periodo_mes"]))
            )
            editor = _editor_comentarios_representatividad(
                detalle,
                tab_activo="quimico",
                registros_store=registros_store,
                periodo_store=periodo_store,
                puede_publicar=puede_publicar,
                es_republicacion=es_republicacion,
            )

            try:
                df_hist = fetch_historial_reporte_torre_oficial()
            except Exception:
                df_hist = pd.DataFrame()

            historial = _tabla_historial_representatividad(df_hist)
            return (
                html.Div(),
                editor,
                historial,
                registros_store,
                "quimico",
                periodo_store,
            )
        except Exception as e:
            return (
                dbc.Alert(f"Error al cargar editor de comentarios: {e}", color="danger"),
                html.Div(),
                no_update,
                no_update,
                no_update,
                no_update,
            )

    # ------------------------------------------------------------
    # REPORTE POR TURNO
    # ------------------------------------------------------------
    if tipo == "reporte_turno":
        print("ENTRÓ A REPORTE TURNO")
        print("fecha fin SQL exclusiva:", fin_sql_exclusivo)
        try:
            fecha_fin_factor = fin_sql_exclusivo - pd.Timedelta(days=1)
            actualizar_factor_ajuste_camiones_v2_report(
                start_date=ini,
                end_date=fecha_fin_factor,
                dias_reproceso=0,
            )
            actualizar_reporte_turno_cache_emision(
                start_date=ini,
                end_date=fin_sql_exclusivo,
            )
            df_turno = fetch_reporte_turno_cache_emision(
                start_date=ini,
                end_date=fin_sql_exclusivo
            )
            print("Columnas reporte turno:", df_turno.columns.tolist())
            print("Filas reporte turno:", len(df_turno))
        except Exception as e:
            return (
                dbc.Alert(f"Error al consultar reporte por turno: {e}", color="danger"),
                html.Div(),
                html.Div(),
                no_update,
                no_update,
                no_update,
            )

        if df_turno.empty:
            return (
                dbc.Alert("Sin datos para el reporte por turno en el rango seleccionado.", color="info"),
                html.Div(),
                html.Div(),
                no_update,
                no_update,
                no_update,
            )

        tabla = html.Div([
            html.H5("Análisis de las Torres de Muestreo por Turno", className="mb-2"),
            html.P(
                "Vista preliminar del reporte. Puede desplazarse horizontalmente para revisar todas las variables.",
                className="text-muted mb-3"
            ),
            _tabla_reporte_turno(df_turno)
        ])

        historial = dbc.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Fecha"),
                        html.Th("Tipo"),
                        html.Th("Usuario")
                    ]),
                    style={"backgroundColor": "#FEEBC8"}
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(pd.Timestamp.now().strftime("%d-%m-%Y")),
                       html.Td("Análisis de las Torres de Muestreo por Turno"),
                        html.Td("usuario_actual")
                    ]),
                ])
            ],
            bordered=True,
            hover=True
        )

        return html.Div(), tabla, historial, no_update, no_update, no_update

    # ------------------------------------------------------------
    # PRODUCCION DIARIA / DATOS CONCILIADOS DE EMISION
    # ------------------------------------------------------------
    if tipo == "prod":
        ini_d = pd.to_datetime(f_ini).date()
        fin_d = pd.to_datetime(f_fin).date()
        try:
            print(f"[PREVIEW][DATOS_CONCILIADOS_EMISION] Actualizando {ini_d} -> {fin_d}")
            _refrescar_dependencias_datos_conciliados(
                ini_d=ini_d,
                fin_d=fin_d,
                fin_sql_exclusivo=fin_sql_exclusivo,
            )
            df = fetch_datos_conciliados_emision_report(ini_d, fin_d)
            print(f"[PREVIEW][DATOS_CONCILIADOS_EMISION] rows={len(df)}")
        except Exception as exc:
            return (
                dbc.Alert(f"Error al consultar Datos Conciliados de emision: {exc}", color="danger"),
                html.Div(), html.Div(), no_update, no_update, no_update,
            )
        if df.empty:
            return (
                dbc.Alert("Sin datos en el rango seleccionado.", color="info"),
                html.Div(), html.Div(), no_update, no_update, no_update,
            )
        ycol = next((c for c in [
            "Produccion_Catodos_Real", "ProducciÃ³n_CÃ¡todos_Real", "prod_catodos_real"
        ] if c in df.columns), None)
        if ycol is None:
            return (
                dbc.Alert("No se encuentra la columna 'Produccion_Catodos_Real' en la tabla.", color="danger"),
                html.Div(), html.Div(), no_update, no_update, no_update,
            )
        fig = px.line(
            df.sort_values("Fecha"), x="Fecha", y=ycol, markers=True,
            title="ProducciÃ³n Diaria (CÃ¡todos)",
        )
        tabla = _style_table(df.sort_values("Fecha", ascending=False).head(10))
        historial = dbc.Table(
            [
                html.Thead(
                    html.Tr([html.Th("Fecha"), html.Th("Tipo"), html.Th("Usuario")]),
                    style={"backgroundColor": "#FEEBC8"},
                ),
                html.Tbody([html.Tr([
                    html.Td(pd.Timestamp.now().strftime("%d-%m-%Y")),
                    html.Td("ProducciÃ³n Diaria"), html.Td("usuario_actual"),
                ])]),
            ], bordered=True, hover=True,
        )
        return html.Div(), tabla, historial, no_update, no_update, no_update

    # ------------------------------------------------------------
    # REPORTES ANTIGUOS
    # ------------------------------------------------------------
    fecha_hasta = f_fin
    end_date = pd.to_datetime(fecha_hasta).date()

    df = fetch_report_data(end_date=end_date)

    if df.empty:
        return (
            dbc.Alert("Sin datos en el rango seleccionado.", color="info"),
            html.Div(),
            html.Div(),
            no_update,
            no_update,
            no_update,
        )

    if tipo == "balance":
        ycol = "Produccion_Catodos_Real" if "Produccion_Catodos_Real" in df.columns else None

        if ycol:
            df["Semana"] = pd.to_datetime(df["Fecha"]).dt.isocalendar().week
            agg = df.groupby("Semana", as_index=False)[ycol].mean()
            fig = px.bar(agg, x="Semana", y=ycol, title="Balance Semanal (Promedio Producción)")
            grafico = dcc.Graph(figure=fig)
        else:
            grafico = dbc.Alert("Balance: no se encontró columna Produccion_Catodos_Real.", color="warning")

        table_df = df.sort_values("Fecha", ascending=False).head(10)
        tabla = _style_table(table_df)

    else:
        ycol = "Produccion_Catodos_Real" if "Produccion_Catodos_Real" in df.columns else None

        if ycol:
            df["Mes"] = pd.to_datetime(df["Fecha"]).dt.to_period("M").astype(str)
            agg = df.groupby("Mes", as_index=False)[ycol].sum()
            fig = px.bar(agg, x="Mes", y=ycol, title="Conciliación Mensual (Suma Producción)")
            grafico = dcc.Graph(figure=fig)
        else:
            grafico = dbc.Alert("Conciliación: no se encontró columna Produccion_Catodos_Real.", color="warning")

        table_df = df.sort_values("Fecha", ascending=False).head(10)
        tabla = _style_table(table_df)

    nombres_tipo = {
        "prod": "Producción Diaria",
        "balance": "Balance Semanal",
        "conciliacion": "Conciliación Mensual",
    }

    historial = dbc.Table(
        [
            html.Thead(
                html.Tr([
                    html.Th("Fecha"),
                    html.Th("Tipo"),
                    html.Th("Usuario")
                ]),
                style={"backgroundColor": "#FEEBC8"}
            ),
            html.Tbody([
                html.Tr([
                    html.Td(pd.Timestamp.now().strftime("%d-%m-%Y")),
                    html.Td(nombres_tipo.get(tipo, tipo)),
                    html.Td("usuario_actual")
                ]),
            ])
        ],
        bordered=True,
        hover=True
    )

    return html.Div(), tabla, historial, no_update, no_update, no_update


@callback(
    Output("report-download-xlsx", "data"),
    Output("report-status", "children", allow_duplicate=True),
    Output("report-progress", "children", allow_duplicate=True),
    Output("report-error-modal", "is_open", allow_duplicate=True),
    Output("report-error-modal-body", "children", allow_duplicate=True),
    Input({"type": "report-export-btn", "tipo": ALL}, "n_clicks"),
    State("report-fecha-inicio", "date"),
    State("report-fecha-final", "date"),
    State("report-fecha-modo", "value"),
    State("report-balance-caso", "value"),
    prevent_initial_call=True,
    running=[
        (
            Output({"type": "report-export-btn", "tipo": MATCH}, "disabled"),
            True,
            False,
        ),
    ],
)
def exportar_excel(
    n_clicks_list, f_ini, f_fin, modo_fecha=None, balance_caso_id=None
):
    triggered = ctx.triggered_id
    print("[RTO] Callback generación Excel disparado")
    print(f"[RTO] n_clicks={n_clicks_list}")
    print(f"[RTO] trigger={triggered}")
    print(f"[RTO] periodo_inicio={f_ini}")
    print(f"[RTO] periodo_fin={f_fin}")
    print("[RTO] modo=descargar")
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update, no_update, False, no_update
    if not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update, False, no_update

    tipo = triggered["tipo"]
    _done = html.Div()

    print(f"[EXCEL] tipo={tipo} | ini={f_ini} | fin={f_fin}")

    if not f_ini or not f_fin:
        print("[EXCEL] Sin fechas - abortando")
        return no_update, "Debe seleccionar rango de fechas.", _done, False, no_update

    ini_d = pd.to_datetime(f_ini).date()
    fin_d = pd.to_datetime(f_fin).date()
    # El SP usa fecha final exclusiva: Fecha >= inicio AND Fecha < fin
    fin_sql_exclusivo = (pd.to_datetime(f_fin) + pd.Timedelta(days=1)).date()

    try:
        # ------------------------------------------------------------
        # REPORTE REPRESENTATIVIDAD TORRES
        # ------------------------------------------------------------
        if tipo == "representatividad_torres":
            log_db_destino_reporte_torre()
            print(
                "[RTO] Flujo solo descarga/exportación; "
                "no publica snapshot oficial."
            )
            activo = _reporte_oficial_activo_para_periodo(ini_d, fin_d)
            if not activo:
                return (
                    no_update,
                    "No existe un reporte oficial activo para descargar "
                    "en el período seleccionado.",
                    _done,
                    False,
                    no_update,
                )
            id_reporte = int(activo["id_reporte"])
            fecha_corte_operacional = pd.to_datetime(
                activo["fecha_corte_operacional"]
            ).date()
            print(
                "[RTO] Descargando reporte oficial activo "
                f"id_reporte={id_reporte}, "
                f"corte operacional={fecha_corte_operacional}"
            )
            paquete = fetch_reporte_torre_oficial_snapshot(id_reporte)
            df_detalle = fetch_reporte_torre_oficial_detalle(
                id_reporte=id_reporte,
            )
            mapa = comentarios_mapa_desde_dataframe(df_detalle)
            xbytes = _export_representatividad_desde_paquete(
                paquete,
                mapa_comentarios=mapa,
            )

            filename = (
                f"Reporte_Representatividad_Torres_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )

            status = (
                f"Descargado reporte oficial activo id_reporte={id_reporte} "
                f"— corte operacional {fecha_corte_operacional} — {filename}"
            )

            return (
                _enviar_descarga(xbytes, filename),
                status,
                _done,
                False,
                no_update,
            )

            
        # ------------------------------------------------------------
        # REPORTE POR TURNO + GENERADOR REPORTE
        # ------------------------------------------------------------
        if tipo == "reporte_turno":
            # ------------------------------------------------------------
            # Instrumentacion temporal de tiempo por etapa (diagnostico de
            # exportacion lenta). Cada etapa imprime su propio [EXCEL-T]
            # con segundos transcurridos, para ver cual paso concentra el
            # tiempo total (no solo el SP de reporte_turno). Quitar cuando
            # ya no se necesite el diagnostico.
            # ------------------------------------------------------------
            _t_export_ini = time.perf_counter()

            fecha_fin_factor = fin_sql_exclusivo - pd.Timedelta(days=1)

            _t0 = time.perf_counter()
            actualizar_apilado_tmh_v2_report(
                start_date=ini_d,
                end_date=fecha_fin_factor,
                dias_reproceso=7,
            )
            print(f"[EXCEL-T] sp_mantiene_apilado_tmh_v2_test: {time.perf_counter() - _t0:.2f}s")

            _t0 = time.perf_counter()
            actualizar_factor_ajuste_camiones_v2_report(
                start_date=ini_d,
                end_date=fecha_fin_factor,
                dias_reproceso=0,
            )
            print(f"[EXCEL-T] sp_mantiene_factor_ajuste_camiones_v2_test: {time.perf_counter() - _t0:.2f}s")

            _t0 = time.perf_counter()
            actualizar_reporte_turno_cache_emision(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )
            print(f"[EXCEL-T] actualizar_reporte_turno_cache_emision (clays_cufe + sp_actualizar_reporte_turno_cache_emision_test): {time.perf_counter() - _t0:.2f}s")

            print(f"[EXCEL] Fetching reporte_turno {ini_d} -> {fin_sql_exclusivo}")
            _t0 = time.perf_counter()
            df_turno = fetch_reporte_turno_cache_emision(start_date=ini_d, end_date=fin_sql_exclusivo)
            print(f"[EXCEL-T] SELECT reporte_turno_cache_emision_test: {time.perf_counter() - _t0:.2f}s")
            print(f"[EXCEL] reporte_turno rows={len(df_turno)}")

            if df_turno.empty:
                return no_update, "Sin datos para el rango seleccionado.", _done, False, no_update

            df_clays_cufe = fetch_clays_cufe_report(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )
            print(f"[EXCEL] Clays-CuFe rows={len(df_clays_cufe)}")

            df_trazabilidad_analitos = fetch_trazabilidad_analitos_report(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )
            print(
                f"[EXCEL] Trazabilidad Analitos rows="
                f"{len(df_trazabilidad_analitos)}"
            )

            df_curva_granulometrica = fetch_curva_granulometrica_report(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )
            print(
                f"[EXCEL] Curva Granulométrica rows="
                f"{len(df_curva_granulometrica)}"
            )

            print(f"[EXCEL] Fetching generador_reporte_diario {ini_d} -> {fin_sql_exclusivo}")
            _t0 = time.perf_counter()
            df_generador = fetch_generador_reporte_diario_emision(start_date=ini_d, end_date=fin_sql_exclusivo)
            print(f"[EXCEL-T] sp_generador_reporte_diario_emision_test: {time.perf_counter() - _t0:.2f}s")
            print(f"[EXCEL] generador rows={len(df_generador)}")

            inicio_mes_resumen = ini_d.replace(day=1)
            if inicio_mes_resumen < ini_d:
                print(
                    f"[EXCEL] Fetching generador resumen mensual "
                    f"{inicio_mes_resumen} -> {fin_sql_exclusivo}"
                )
                df_generador_resumen = fetch_generador_reporte_diario_emision(
                    start_date=inicio_mes_resumen,
                    end_date=fin_sql_exclusivo,
                )
            else:
                df_generador_resumen = df_generador

            _t0 = time.perf_counter()
            output = io.BytesIO()
            export_reporte_turno_estilo_leyes_finos(
                df=df_turno,
                output=output,
                df_generador=df_generador,
                df_generador_resumen=df_generador_resumen,
                df_clays_cufe=df_clays_cufe,
                df_trazabilidad_analitos=df_trazabilidad_analitos,
                df_curva_granulometrica=df_curva_granulometrica,
                periodo_inicio=ini_d,
                periodo_fin=fin_d,
            )
            output.seek(0)
            xbytes = output.getvalue()
            print(f"[EXCEL-T] formateo openpyxl (export_reporte_turno_estilo_leyes_finos): {time.perf_counter() - _t0:.2f}s")
            print(f"[EXCEL] reporte_turno excel size={len(xbytes)} bytes")
            print(f"[EXCEL-T] TOTAL exportar_excel(reporte_turno): {time.perf_counter() - _t_export_ini:.2f}s")

            filename = (
                f"Analisis_Torres_de_Muestreo_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )
            status = f"Exportado: {filename} (turno={len(df_turno)}, generador={len(df_generador)})"
            return _enviar_descarga(xbytes, filename), status, _done, False, no_update

        # ------------------------------------------------------------
        # PRODUCCIÓN DIARIA / DATOS CONCILIADOS
        # ------------------------------------------------------------
        if tipo == "prod":
            print(
                f"[EXCEL][DATOS_CONCILIADOS_EMISION] "
                f"Actualizando {ini_d} -> {fin_d}"
            )
            _refrescar_dependencias_datos_conciliados(
                ini_d=ini_d,
                fin_d=fin_d,
                fin_sql_exclusivo=fin_sql_exclusivo,
            )
            df = fetch_datos_conciliados_emision_report(
                start_date=ini_d,
                end_date=fin_d
            )
            fecha_inicio_mtd = fin_d.replace(day=1)
            if ini_d <= fecha_inicio_mtd:
                df_mtd = df
            else:
                df_mtd = fetch_datos_conciliados_emision_report(
                    start_date=fecha_inicio_mtd,
                    end_date=fin_d,
                )
            df_factor = fetch_factor_ajuste_camiones_report(
                start_date=ini_d,
                end_date=fin_d,
            )
            df_balance_chancado = fetch_balance_chancado_report(
                start_date=ini_d,
                end_date=fin_d,
            )
            print(
                "[EXCEL][BALANCE_CHANCADO] "
                f"rows={len(df_balance_chancado)}"
            )
            print(f"[EXCEL][DATOS_CONCILIADOS_EMISION] rows={len(df)}")

            columnas_control = [
                columna for columna in [
                    "Fecha", "Chancado_TMS_Real", "Apilado_TMS_Real", "Ley_CuT_Real_srr"
                ] if columna in df.columns
            ]
            if "Fecha" in columnas_control:
                print(df.loc[
                    pd.to_datetime(df["Fecha"]).dt.date.isin(
                        [date(2026, 7, 14), date(2026, 7, 21)]
                    ),
                    columnas_control,
                ].to_string(index=False))

            if df.empty:
                return no_update, "Sin datos para exportar en el rango seleccionado.", _done, False, no_update

            template_path = (
                TEMPLATE_XLSX_PATH
                if os.path.isfile(TEMPLATE_XLSX_PATH)
                else _find_plantilla_propuesta()
            )
            if os.path.isfile(template_path):
                xbytes = export_datos_conciliados_to_template(
                    df,
                    template_path,
                    df_factor_ajuste=df_factor,
                    df_balance_chancado=df_balance_chancado,
                    rango_personalizado=modo_fecha == "rango",
                    df_resumen_mtd=df_mtd,
                )
            else:
                xbytes = _export_dataframe_simple_to_excel(
                    df, sheet_name="Generador Reporte Diario"
                )

            filename = (
                f"Reporte_DatosConciliados_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )

            status = f"Exportado: {filename} — Registros: {len(df)}"
            return _enviar_descarga(xbytes, filename), status, _done, False, no_update

        # ------------------------------------------------------------
        # BALANCE PLANTA HIDROMETALURGIA - CASO/RUN OFICIAL
        # ------------------------------------------------------------
        if tipo == "balance":
            if balance_caso_id is None:
                raise BalanceReportError(
                    "Debe seleccionar un Caso oficial para generar el Balance."
                )
            df_periodo, df_acumulado, metadata = build_balance_official_report(
                int(balance_caso_id)
            )
            identity = build_balance_report_identity(metadata)
            print(
                "[BALANCE EXPORT] "
                f"caso_id={identity['caso_id']} "
                f"run_id={identity['run_id']} "
                f"periodo={identity['fecha_inicio']}..{identity['fecha_fin']} "
                f"mtd={identity['mtd_fecha_inicio']}..{identity['mtd_fecha_fin']} "
                f"mtd_casos={metadata.get('casos_mtd', [])}"
            )
            print("[BALANCE] exportando template...")
            xbytes = export_balance_reconciliacion_to_template(
                df_periodo,
                df_acumulado,
                metadata,
                BALANCE_TEMPLATE_XLSX_PATH,
            )
            filename = identity["filename"]
            print(f"[BALANCE EXPORT] output={filename}")
            status = (
                "Balance generado correctamente | "
                f"{identity['caso_label']} | {identity['run_label']} | "
                f"{identity['periodo_label']} | {identity['mtd_label']}"
            )
            return (
                _enviar_descarga(xbytes, filename), status, _done, False, no_update
            )

        # ------------------------------------------------------------
        # CONCILIACIÓN U OTROS REPORTES ANTIGUOS
        # ------------------------------------------------------------
        print(f"[EXCEL] Fetching report_data tipo={tipo} end={fin_d}")
        df = fetch_report_data(end_date=fin_d)
        df = df[
            (pd.to_datetime(df["Fecha"]).dt.date >= ini_d) &
            (pd.to_datetime(df["Fecha"]).dt.date <= fin_d)
        ].copy()
        print(f"[EXCEL] report_data rows={len(df)}")

        if df.empty:
            return no_update, "Sin datos para exportar en el rango seleccionado.", _done, False, no_update

        xbytes = export_dataframe_with_template(df, TEMPLATE_XLSX_PATH)
        print(f"[EXCEL] {tipo} excel size={len(xbytes)} bytes")

        filename = (
            f"Reporte_{tipo}_"
            f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
            f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
        )
        return _enviar_descarga(xbytes, filename), f"Exportado: {filename} ({len(df)} registros)", _done, False, no_update

    except BalanceReportError as exc:
        import traceback
        traceback.print_exc()
        return (
            no_update,
            f"No se genero el Balance: {exc}",
            html.Div(),
            True,
            html.P(str(exc), className="mb-0"),
        )

    except DependenciaDatosExportError as exc:
        import traceback
        traceback.print_exc()
        fecha = pd.to_datetime(exc.fecha, errors="coerce")
        contenido = [
            html.P(
                "No fue posible generar el Excel porque faltan datos "
                "necesarios para completar el reporte.",
                className="mb-3",
            ),
        ]
        if pd.notna(fecha):
            contenido.append(html.P([
                html.Strong("Datos disponibles hasta: "),
                fecha.strftime("%d-%m-%Y"),
            ], className="mb-2"))
        if exc.campos:
            contenido.extend([
                html.P("Campos pendientes:", className="fw-semibold mb-1"),
                html.Ul(
                    [
                        html.Li(_ETIQUETAS_DEPENDENCIAS_DATOS.get(campo, campo))
                        for campo in exc.campos
                    ],
                    className="mb-3",
                ),
            ])
        contenido.append(html.P(
            "Complete o actualice los datos de origen y vuelva a intentar "
            "la exportación.",
            className="mb-0 text-muted",
        ))
        return (
            no_update,
            "No se generó el Excel: existen datos de origen incompletos.",
            html.Div(),
            True,
            contenido,
        )

    except WorkbookRepresentatividadInconsistenteError as e:
        import traceback
        traceback.print_exc()
        return (
            no_update,
            (
                f"No se generó el Excel {_etiqueta_tipo_rep(e.tipo)}: "
                "indicadores inconsistentes en el reporte."
            ),
            html.Div(),
            True,
            _contenido_modal_workbook_inconsistente(e),
        )

    except Exception as e:
        import traceback
        traceback.print_exc()

        return (
            no_update,
            f"❌ Error al exportar: {e}",
            html.Div(),
            False,
            no_update,
        )


@callback(
    Output("report-error-modal", "is_open", allow_duplicate=True),
    Input("report-error-modal-close", "n_clicks"),
    prevent_initial_call=True,
)
def cerrar_modal_error_exportacion(n_clicks):
    return False if n_clicks else no_update

# Clear the progress bar once report-grafico updates (covers the generar_reporte callback)
@callback(
    Output("report-progress", "children", allow_duplicate=True),
    Input("report-grafico", "children"),
    prevent_initial_call=True,
)
def _clear_progress_on_viz(_):
    return html.Div()


@callback(
    Output("report-download-pdf", "data"),
    Output("report-status", "children", allow_duplicate=True),
    Output("report-progress", "children", allow_duplicate=True),
    Output("report-error-modal", "is_open", allow_duplicate=True),
    Output("report-error-modal-body", "children", allow_duplicate=True),
    Input({"type": "report-pdf-btn", "tipo": ALL}, "n_clicks"),
    State("report-fecha-inicio", "date"),
    State("report-fecha-final", "date"),
    prevent_initial_call=True,
    running=[
        (
            Output({"type": "report-pdf-btn", "tipo": MATCH}, "disabled"),
            True,
            False,
        ),
    ],
)
def generar_pdf(n_clicks_list, f_ini, f_fin):
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update, no_update, False, no_update
    if not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update, False, no_update

    tipo = triggered["tipo"]
    _done = html.Div()

    print(f"[PDF] tipo={tipo} | ini={f_ini} | fin={f_fin}")

    if not f_ini or not f_fin:
        print("[PDF] Sin fechas - abortando")
        return (
            no_update,
            "Debe seleccionar rango de fechas.",
            _done,
            False,
            no_update,
        )

    ini_d = pd.to_datetime(f_ini).date()
    fin_d = pd.to_datetime(f_fin).date()
    fin_sql_exclusivo = (pd.to_datetime(f_fin) + pd.Timedelta(days=1)).date()

    try:
        # ── REPRESENTATIVIDAD TORRES ──────────────────────────────────
        if tipo in {
            "representatividad_torres",
            "representatividad_torres_quimico",
            "representatividad_torres_fisico",
            "representatividad_torres_srr",
        }:
            analisis = (
                "quimico" if tipo.endswith("_quimico")
                else "srr" if tipo.endswith("_srr")
                else "fisico"
            )
            print(
                f"[PDF] Generando PDF {analisis} RN-046 "
                f"{ini_d} -> {fin_d}"
            )

            paquete, excel_base, metricas = (
                _construir_fuente_unica_representatividad(
                    ini_d,
                    fin_d,
                )
            )
            fecha_corte_operacional = paquete["fecha_corte_operacional"]

            pdf_bytes, filename = _pdf_representatividad_desde_xlsx(
                excel_base,
                analisis,
                fin_d,
                fecha_corte=fecha_corte_operacional,
                paquete=paquete,
            )
            print(f"[PDF] representatividad_torres pdf size={len(pdf_bytes)} bytes")
            return (
                _enviar_descarga(pdf_bytes, filename),
                f"PDF generado: {filename} - corte "
                f"{fecha_corte_operacional} - "
                f"{metricas[analisis]['filas_detalle']} filas - "
                "PDF A3 sin solapamientos",
                _done,
                False,
                no_update,
            )

        # ── REPORTE POR TURNO ─────────────────────────────────────────
        if tipo in {"reporte_turno", "reporte_turno_turno", "reporte_turno_generador"}:
            fecha_fin_factor = fin_sql_exclusivo - pd.Timedelta(days=1)
            actualizar_factor_ajuste_camiones_v2_report(
                start_date=ini_d,
                end_date=fecha_fin_factor,
                dias_reproceso=0,
            )
            actualizar_reporte_turno_cache_emision(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )
            print(f"[PDF] Fetching reporte_turno {ini_d} -> {fin_sql_exclusivo}")
            df_turno = fetch_reporte_turno_cache_emision(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )
            print(f"[PDF] reporte_turno rows={len(df_turno)}")
            if df_turno.empty:
                return (
                    no_update,
                    "Sin datos para el rango seleccionado.",
                    _done,
                    False,
                    no_update,
                )

            df_generador = fetch_generador_reporte_diario_emision(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )
            print(f"[PDF] generador rows={len(df_generador)}")

            output = io.BytesIO()
            export_reporte_turno_estilo_leyes_finos(
                df=df_turno,
                output=output,
                df_generador=df_generador,
            )
            nombre_hoja = (
                "Generador Reporte"
                if tipo == "reporte_turno_generador"
                else "Reporte por Turno"
            )
            xlsx_hoja = _build_xlsx_pdf_reporte_torre(
                output.getvalue(),
                nombre_hoja,
            )
            pdf_bytes = convert_xlsx_bytes_to_pdf(xlsx_hoja)
            pdf_bytes = normalize_pages_to_a3_landscape(pdf_bytes)
            print(f"[PDF] {nombre_hoja} pdf size={len(pdf_bytes)} bytes")
            sufijo = (
                "Generador_Reporte"
                if nombre_hoja == "Generador Reporte"
                else "Reporte_por_Turno"
            )
            filename = (
                f"Analisis_Torres_{sufijo}_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.pdf"
            )
            status = (
                f"PDF generado: {filename} "
                f"(turno={len(df_turno)}, generador={len(df_generador)})"
            )
            return (
                _enviar_descarga(pdf_bytes, filename),
                status,
                _done,
                False,
                no_update,
            )

        # ── PRODUCCIÓN DIARIA / DATOS CONCILIADOS ─────────────────────
        if tipo == "prod":
            print(
                f"[PDF][DATOS_CONCILIADOS_EMISION] "
                f"Actualizando {ini_d} -> {fin_d}"
            )
            _refrescar_dependencias_datos_conciliados(
                ini_d=ini_d,
                fin_d=fin_d,
                fin_sql_exclusivo=fin_sql_exclusivo,
            )
            df = fetch_datos_conciliados_emision_report(
                start_date=ini_d,
                end_date=fin_d,
            )
            print(f"[PDF][DATOS_CONCILIADOS_EMISION] rows={len(df)}")
            if df.empty:
                return (
                    no_update,
                    "Sin datos para generar PDF.",
                    _done,
                    False,
                    no_update,
                )

            pdf_bytes = generar_pdf_datos_conciliados(df, f_ini, f_fin)
            print(f"[PDF] prod pdf size={len(pdf_bytes)} bytes")
            filename = (
                f"Produccion_Diaria_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.pdf"
            )
            return (
                _enviar_descarga(pdf_bytes, filename),
                f"PDF generado: {filename} ({len(df)} registros)",
                _done,
                False,
                no_update,
            )

        # ── BALANCE / CONCILIACIÓN ────────────────────────────────────
        print(f"[PDF] Fetching report_data tipo={tipo} end={fin_d}")
        df = fetch_report_data(end_date=fin_d)
        df = df[
            (pd.to_datetime(df["Fecha"]).dt.date >= ini_d) &
            (pd.to_datetime(df["Fecha"]).dt.date <= fin_d)
        ].copy()
        print(f"[PDF] report_data rows={len(df)}")

        if df.empty:
            return (
                no_update,
                "Sin datos para generar PDF.",
                _done,
                False,
                no_update,
            )

        pdf_bytes = generar_pdf_datos_conciliados(df, f_ini, f_fin)
        print(f"[PDF] {tipo} pdf size={len(pdf_bytes)} bytes")
        filename = (
            f"Reporte_{tipo}_"
            f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
            f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.pdf"
        )
        return (
            _enviar_descarga(pdf_bytes, filename),
            f"PDF generado: {filename} ({len(df)} registros)",
            _done,
            False,
            no_update,
        )

    except WorkbookRepresentatividadInconsistenteError as e:
        import traceback
        print(f"[PDF ERROR] tipo={tipo}: {e}")
        traceback.print_exc()
        return (
            no_update,
            (
                f"No se generó el PDF {_etiqueta_tipo_rep(e.tipo)}: "
                "indicadores inconsistentes en el reporte."
            ),
            _done,
            True,
            _contenido_modal_workbook_inconsistente(e),
        )
    except Exception as e:
        import traceback
        print(f"[PDF ERROR] tipo={tipo}: {e}")
        traceback.print_exc()
        return (
            no_update,
            f"Error al generar PDF ({tipo}): {e}",
            _done,
            False,
            no_update,
        )


def _alternar_pad(valor: str | None) -> str:
    """Rota entre los valores válidos; "Sin clasificar" entra por el primero."""
    actual = _texto_comentario_rep(valor)
    otros = [v for v in _PAD_VALORES_VALIDOS if v != actual]
    return otros[0] if otros else _PAD_VALORES_VALIDOS[0]


@callback(
    Output("rep-comentarios-grid", "data", allow_duplicate=True),
    Output("rep-comentarios-grid", "tooltip_data", allow_duplicate=True),
    Output("rep-comentarios-grid", "active_cell"),
    Input("rep-comentarios-grid", "active_cell"),
    State("rep-comentarios-grid", "data"),
    prevent_initial_call=True,
)
def alternar_pad_rep(active_cell, grid_data):
    """
    Clic en la celda Pad alterna el valor.

    Reemplaza al dropdown: el menú de DataTable se dibuja dentro del
    contenedor con scroll y queda recortado, sin CSS que lo evite mientras
    la grilla necesite scroll horizontal.
    """
    if not active_cell or active_cell.get("column_id") != "Pad":
        return no_update, no_update, no_update

    fila_id = active_cell.get("row_id")
    filas = [f for f in (grid_data or []) if f.get("id") == fila_id]
    if not filas:
        return no_update, no_update, no_update

    fila = filas[0]
    # Sin Pad_Original la fila es futura o sin apilado: nada que clasificar.
    if not _texto_comentario_rep(fila.get("Pad_Original")):
        return no_update, no_update, None

    fila["Pad"] = _alternar_pad(fila.get("Pad"))
    # El tooltip se recalcula: la fila recien ajustada tiene que mostrar su
    # valor anterior, y la que vuelve al calculado tiene que perderlo.
    tooltips = [_tooltip_pad_rep(f) for f in grid_data]
    # active_cell a None para que el siguiente clic en la misma celda
    # vuelva a disparar el callback.
    return grid_data, tooltips, None


@callback(
    Output("rep-comentarios-store", "data", allow_duplicate=True),
    Input("rep-comentarios-grid", "data"),
    State("rep-comentarios-store", "data"),
    State("rep-tab-activo-store", "data"),
    prevent_initial_call=True,
)
def sincronizar_comentarios_desde_grilla(grid_data, registros, tab_activo):
    if not registros or grid_data is None:
        return no_update
    tab = str(tab_activo or "quimico").lower()
    fusionados = _fusionar_comentarios_grilla(registros, grid_data, tab)
    # Sin cambio real no tocar el store: evita roundtrips y re-renders.
    if fusionados == registros:
        return no_update
    return fusionados


@callback(
    Output("rep-tab-quimico", "outline"),
    Output("rep-tab-fisico", "outline"),
    Output("rep-tab-activo-store", "data"),
    Output("rep-comentarios-store", "data", allow_duplicate=True),
    Output("rep-comentarios-grid", "data", allow_duplicate=True),
    Output("rep-comentarios-grid", "tooltip_data", allow_duplicate=True),
    Input("rep-tab-quimico", "n_clicks"),
    Input("rep-tab-fisico", "n_clicks"),
    State("rep-comentarios-store", "data"),
    State("rep-tab-activo-store", "data"),
    State("rep-periodo-store", "data"),
    State("rep-comentarios-grid", "data"),
    prevent_initial_call=True,
)
def cambiar_tab_comentarios_rep(n_q, n_f, registros, tab_activo, periodo, grid_data):
    """Cambia Químico/Físico sin remountar el editor (evita pestañeo)."""
    triggered = ctx.triggered_id
    if not registros:
        return no_update, no_update, no_update, no_update, no_update, no_update

    registros = _fusionar_comentarios_grilla(registros, grid_data, tab_activo)

    if triggered == "rep-tab-fisico":
        tab = "fisico"
        outline_q, outline_f = True, False
    else:
        tab = "quimico"
        outline_q, outline_f = False, True

    df = pd.DataFrame(registros)
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    grilla_data, tooltips = _registros_tooltips_grilla_rep(df, tab)
    return outline_q, outline_f, tab, registros, grilla_data, tooltips


clientside_callback(
    """
    function(n) {
        if (!n) return window.dash_clientside.no_update;

        // El Pad se confirma al clic; el comentario vive en <input> y solo
        // entra a `data` al perder el foco. Si publicamos en el mismo tick,
        // el State de la grilla llega sin el texto nuevo.
        const grid = document.getElementById('rep-comentarios-grid');
        const active = document.activeElement;
        if (
            grid
            && active
            && grid.contains(active)
            && active.tagName === 'INPUT'
        ) {
            active.blur();
        }

        const btn = document.getElementById('rep-generar-final-btn');
        if (btn) btn.disabled = true;

        setTimeout(function() {
            if (window.dash_clientside && window.dash_clientside.set_props) {
                window.dash_clientside.set_props(
                    'rep-publicar-trigger',
                    {data: Date.now()}
                );
            }
        }, 120);

        // El modal solo se abre aca. Cerrarlo es cosa del callback de
        // publicacion (running=), que tarda lo que tarden los 4 SP de
        // refresco mas la escritura del snapshot. Antes se cerraba con un
        // setTimeout de 1 s y el spinner mentia sobre el progreso real.
        return true;
    }
    """,
    Output("rep-publicar-modal", "is_open"),
    Input("rep-generar-final-btn", "n_clicks"),
    prevent_initial_call=True,
)


@callback(
    Output("rep-publicar-status", "children"),
    Output("report-historial", "children", allow_duplicate=True),
    Output("rep-comentarios-store", "data", allow_duplicate=True),
    Output("report-tabla", "children", allow_duplicate=True),
    Input("rep-publicar-trigger", "data"),
    State("rep-comentarios-store", "data"),
    State("rep-periodo-store", "data"),
    State("rep-tab-activo-store", "data"),
    State("rep-comentarios-grid", "data"),
    State("report-fecha-modo", "value"),
    prevent_initial_call=True,
    running=[
        (Output("rep-generar-final-btn", "disabled"), True, False),
        # Cierra el modal "Publicando…" al terminar, exito o error. Con un
        # Output normal una excepcion dejaria el spinner girando para siempre.
        (
            Output("rep-publicar-modal", "is_open", allow_duplicate=True),
            True,
            False,
        ),
    ],
)
def publicar_reporte_representatividad(
    trigger, registros, periodo, tab_activo, grid_data, modo_fecha,
):
    if not trigger:
        return no_update, no_update, no_update, no_update

    if not registros or not periodo:
        return (
            "Debe cargar el detalle antes de publicar.",
            no_update,
            no_update,
            no_update,
        )

    modo = str(modo_fecha or periodo.get("modo") or "mes").lower()
    if modo != "mes":
        return (
            "Solo se guardan reportes en modo Mes completo. "
            "Use exportacion XLSX/PDF para rangos personalizados.",
            no_update,
            no_update,
            no_update,
        )

    registros = _fusionar_comentarios_grilla(registros, grid_data, tab_activo)

    ini = pd.to_datetime(periodo.get("inicio")).date()
    fin = pd.to_datetime(periodo.get("fin")).date()
    usuario = _usuario_sesion()

    try:
        print("[RTO] Publicando reporte oficial...")
        ini, fin, periodo_mes = normalizar_periodo_mes(ini, fin)
        es_republicacion = mes_tiene_reporte_activo(periodo_mes)
        log_db_destino_reporte_torre()
        paquete = armar_paquete_reporte_torre_oficial(ini, fin)
        print(
            "[RTO] Fecha corte operacional: "
            f"{paquete['fecha_corte_operacional']}"
        )

        # La grilla nunca es fuente de tonelajes, actividad ni
        # representatividad. Se reconstruye el detalle vivo y se incorporan
        # exclusivamente los seis comentarios editables por Fecha + Turno.
        detalle_vivo, _ = _cargar_detalle_representatividad_periodo(
            ini,
            fin,
            periodo_mes=periodo_mes,
            paquete=paquete,
        )
        df_final = _fusionar_solo_comentarios_en_detalle_vivo(
            detalle_vivo,
            registros,
        )
        print(f"[RTO] Filas df_detalle: {len(df_final)}")
        resumen_tm3 = _validar_detalle_publicacion_rep(df_final)
        print(f"[RTO] Detalle vivo antes del escritor TM3: {resumen_tm3}")

        print("[RTO] Llamando write_reporte_torre_oficial...")
        id_reporte = write_reporte_torre_oficial(
            df_detalle=df_final,
            periodo_inicio=ini,
            periodo_fin=fin,
            usuario=usuario,
            paquete=paquete,
        )
        print(f"[RTO] Reporte oficial guardado: id_reporte={id_reporte}")
        df_hist = fetch_historial_reporte_torre_oficial()
        historial = _tabla_historial_representatividad(df_hist)
        etiqueta = _etiqueta_mes_periodo(periodo_mes)
        if es_republicacion:
            mensaje = f"Cambios de {etiqueta} confirmados."
        else:
            mensaje = f"Reporte de {etiqueta} generado."

        # Se relee lo guardado y se rearma el editor: sin esto la grilla
        # sigue mostrando el estado previo al INSERT y un Pad recien
        # ajustado queda sin su autor en pantalla.
        guardado = fetch_reporte_torre_oficial_detalle(periodo_mes=periodo_mes)
        if guardado.empty:
            return mensaje, historial, registros, no_update

        registros = (
            guardado.astype(object)
            .where(pd.notna(guardado), None)
            .to_dict("records")
        )
        editor = _editor_comentarios_representatividad(
            guardado,
            tab_activo=str(tab_activo or "quimico").lower(),
            registros_store=registros,
            periodo_store=periodo,
            puede_publicar=True,
            es_republicacion=True,
        )
        return mensaje, historial, registros, editor
    except Exception as exc:
        return f"Error al publicar: {exc}", no_update, registros, no_update


@callback(
    Output("rep-eliminar-modal", "is_open"),
    Output("rep-eliminar-id-store", "data"),
    Output("rep-eliminar-texto", "value"),
    Input({"type": "rep-hist-del", "id_reporte": ALL}, "n_clicks"),
    Input("rep-eliminar-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def abrir_cerrar_modal_eliminar_rep(n_clicks_list, cancel_clicks):
    triggered = ctx.triggered_id
    if triggered == "rep-eliminar-cancel-btn":
        return False, no_update, ""
    if not isinstance(triggered, dict) or triggered.get("type") != "rep-hist-del":
        return no_update, no_update, no_update
    if not any(n_clicks_list):
        return no_update, no_update, no_update
    return True, triggered.get("id_reporte"), ""


@callback(
    Output("rep-eliminar-confirm-btn", "disabled"),
    Input("rep-eliminar-texto", "value"),
)
def validar_texto_eliminar_rep(texto):
    return str(texto or "").strip().lower() != _TEXTO_CONFIRMACION_BORRADO


@callback(
    Output("rep-eliminar-modal", "is_open", allow_duplicate=True),
    Output("report-historial", "children", allow_duplicate=True),
    Output("report-status", "children", allow_duplicate=True),
    Output("rep-eliminar-texto", "value", allow_duplicate=True),
    Input("rep-eliminar-confirm-btn", "n_clicks"),
    State("rep-eliminar-id-store", "data"),
    State("rep-eliminar-texto", "value"),
    prevent_initial_call=True,
)
def eliminar_reporte_representatividad(n_clicks, id_reporte, texto):
    if not n_clicks:
        return no_update, no_update, no_update, no_update
    if str(texto or "").strip().lower() != _TEXTO_CONFIRMACION_BORRADO:
        return (
            no_update,
            no_update,
            f'Debe escribir "{_TEXTO_CONFIRMACION_BORRADO}" para eliminar.',
            no_update,
        )
    if id_reporte is None:
        return no_update, no_update, no_update, no_update
    try:
        soft_delete_reporte_torre_oficial(
            int(id_reporte),
            _usuario_sesion(),
        )
        df_hist = fetch_historial_reporte_torre_oficial()
        return (
            False,
            _tabla_historial_representatividad(df_hist),
            "Reporte eliminado del historial.",
            "",
        )
    except Exception as exc:
        return no_update, no_update, f"Error al eliminar: {exc}", no_update


@callback(
    Output("report-tabla", "children", allow_duplicate=True),
    Output("report-historial", "children", allow_duplicate=True),
    Output("report-status", "children", allow_duplicate=True),
    Output("rep-comentarios-store", "data", allow_duplicate=True),
    Output("rep-tab-activo-store", "data", allow_duplicate=True),
    Output("rep-periodo-store", "data", allow_duplicate=True),
    Input({"type": "rep-hist-reabrir", "id_reporte": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def reabrir_reporte_representatividad(n_clicks_list):
    if not any(n_clicks_list):
        return no_update, no_update, no_update, no_update, no_update, no_update
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update, no_update, no_update, no_update, no_update

    id_reporte = int(triggered["id_reporte"])
    try:
        df = fetch_reporte_torre_oficial_detalle(id_reporte=id_reporte)
        if df.empty:
            return (
                dbc.Alert("Reporte no encontrado.", color="warning"),
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )
        registros = df.copy()
        registros["Fecha"] = pd.to_datetime(
            registros["Fecha"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        registros = registros.astype(object).where(
            pd.notna(registros),
            None,
        )
        registros_store = registros.to_dict("records")
        detalle = df.copy()
        periodo = {
            "inicio": str(df["periodo_inicio"].iloc[0]),
            "fin": str(df["periodo_fin"].iloc[0]),
            "modo": "mes",
            "periodo_mes": str(df["periodo_mes"].iloc[0])
            if "periodo_mes" in df.columns and pd.notna(df["periodo_mes"].iloc[0])
            else None,
        }
        editor = _editor_comentarios_representatividad(
            detalle,
            tab_activo="quimico",
            registros_store=registros_store,
            periodo_store=periodo,
            puede_publicar=True,
            es_republicacion=True,
        )
        df_hist = fetch_historial_reporte_torre_oficial()
        return (
            editor,
            _tabla_historial_representatividad(df_hist),
            "Reporte reabierto desde historial.",
            registros_store,
            "quimico",
            periodo,
        )
    except Exception as exc:
        return (
            dbc.Alert(f"Error al reabrir: {exc}", color="danger"),
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )


@callback(
    Output("report-download-xlsx", "data", allow_duplicate=True),
    Output("report-status", "children", allow_duplicate=True),
    Input({"type": "rep-hist-xlsx", "id_reporte": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def descargar_historial_xlsx_representatividad(n_clicks_list):
    if not any(n_clicks_list):
        return no_update, no_update
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update

    id_reporte = int(triggered["id_reporte"])
    try:
        paquete = fetch_reporte_torre_oficial_snapshot(id_reporte)
        if not paquete or paquete.get("rep_torres") is None or paquete["rep_torres"].empty:
            return no_update, "Reporte no encontrado."
        df_detalle = fetch_reporte_torre_oficial_detalle(id_reporte=id_reporte)
        mapa = comentarios_mapa_desde_dataframe(df_detalle)
        xbytes = _export_representatividad_desde_paquete(paquete, mapa_comentarios=mapa)
        ini = pd.to_datetime(paquete.get("periodo_inicio")).date()
        fin = pd.to_datetime(paquete.get("periodo_fin")).date()
        filename = (
            f"Reporte_Representatividad_Torres_{ini.strftime('%Y%m%d')}_"
            f"{fin.strftime('%Y%m%d')}.xlsx"
        )
        return _enviar_descarga(xbytes, filename), f"XLSX generado desde reporte guardado."
    except Exception as exc:
        return no_update, f"Error al exportar historial: {exc}"


@callback(
    Output("report-download-pdf", "data", allow_duplicate=True),
    Output("report-status", "children", allow_duplicate=True),
    Input({"type": "rep-hist-pdf", "id_reporte": ALL, "subtipo": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def descargar_historial_pdf_representatividad(n_clicks_list):
    if not any(n_clicks_list):
        return no_update, no_update
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update

    id_reporte = int(triggered["id_reporte"])
    subtipo = str(triggered.get("subtipo") or "quimico").lower()
    try:
        paquete = fetch_reporte_torre_oficial_snapshot(id_reporte)
        if not paquete or paquete.get("rep_torres") is None or paquete["rep_torres"].empty:
            return no_update, "Reporte no encontrado."
        df_detalle = fetch_reporte_torre_oficial_detalle(id_reporte=id_reporte)
        mapa = comentarios_mapa_desde_dataframe(df_detalle)
        xbytes = _export_representatividad_desde_paquete(paquete, mapa_comentarios=mapa)
        fin = pd.to_datetime(paquete.get("periodo_fin")).date()
        pdf_bytes, filename = _pdf_representatividad_desde_xlsx(
            xbytes,
            subtipo,
            fin,
            fecha_corte=paquete.get("fecha_corte_operacional"),
            paquete=paquete,
            mapa_comentarios=mapa,
        )
        return (
            _enviar_descarga(pdf_bytes, filename),
            f"PDF {subtipo} generado desde reporte guardado.",
        )
    except Exception as exc:
        return no_update, f"Error al generar PDF historial: {exc}"
