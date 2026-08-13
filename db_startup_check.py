"""Chequeo de arranque: DB conectada + objetos SQL requeridos por seccion.

Se ejecuta al importar main (tambien via wsgi). Por defecto solo reporta;
con DB_STARTUP_CHECK_STRICT=1 aborta si falta algo critico.
Desactivar: DB_STARTUP_CHECK=0.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Schema de negocio hardcodeado en el SQL vivo (no es SQLSERVER_DB).
SCHEMA_HIDRO = "inventar_SpcHidr"
SCHEMA_RECLAMO = "reclamo"


@dataclass(frozen=True)
class DbObject:
    schema: str
    name: str
    kind: str  # table | view | procedure | function
    required: bool = True

    @property
    def fqn(self) -> str:
        return f"{self.schema}.{self.name}"


# Objetos que el codigo vivo toca (lectura/escritura/EXEC).
# kind se usa solo para el mensaje; OBJECT_ID no distingue bien todos.
SECCIONES: dict[str, list[DbObject]] = {
    "Reportabilidad / Datos Conciliados": [
        DbObject(SCHEMA_HIDRO, "Datos_conciliados_of", "table"),
        DbObject(SCHEMA_HIDRO, "sp_mantiene_datos_conciliados_emision_test", "procedure"),
        DbObject(SCHEMA_HIDRO, "sp_refrescar_historico_apilado_test", "procedure"),
        DbObject(SCHEMA_HIDRO, "v_ajuste_camiones_emision_test", "view"),
        DbObject(SCHEMA_HIDRO, "sp_refrescar_clays_cufe", "procedure"),
    ],
    "Reportabilidad / Representatividad Torres": [
        DbObject(SCHEMA_HIDRO, "tot_TM", "table"),
        DbObject(SCHEMA_HIDRO, "v_bitacora_rangos_norm", "view"),
        DbObject(SCHEMA_HIDRO, "v_datos_apilado_tmh_v2", "view"),
        DbObject(SCHEMA_HIDRO, "sp_mantiene_apilado_tmh_v2_test", "procedure"),
        DbObject(SCHEMA_HIDRO, "sp_calcular_resumen_intervalo_totTM", "procedure"),
        DbObject(SCHEMA_HIDRO, "Resumen_Intervalo_TotTM", "table"),
        DbObject(SCHEMA_HIDRO, "sp_refrescar_representatividad_torres", "procedure"),
        DbObject(SCHEMA_HIDRO, "sp_sincronizar_bd_ton", "procedure"),
        DbObject(SCHEMA_HIDRO, "v_bd_ton_reportabilidad", "view"),
        DbObject(SCHEMA_HIDRO, "v_estado_apilado_turno_representatividad", "view"),
        DbObject(SCHEMA_HIDRO, "v_reporte_turno_campania_modulo_test", "view"),
        DbObject(SCHEMA_HIDRO, "sp_gestion_representatividad_fy", "procedure"),
        DbObject(SCHEMA_HIDRO, "sp_reporte_representatividad_torres", "procedure"),
        DbObject(SCHEMA_HIDRO, "v_peso_teorico_turno_torre_excel", "view"),
        DbObject(SCHEMA_HIDRO, "peso_real_torre_turno", "table"),
        DbObject(SCHEMA_HIDRO, "reporte_torre_oficial_cab", "table"),
        DbObject(SCHEMA_HIDRO, "reporte_torre_oficial_snapshot", "table"),
        DbObject(SCHEMA_HIDRO, "reporte_torre_oficial_detalle", "table"),
    ],
    "Reportabilidad / Reporte por Turno": [
        DbObject(SCHEMA_HIDRO, "sp_reporte_turno_test", "procedure"),
        DbObject(SCHEMA_HIDRO, "sp_mantiene_factor_ajuste_camiones_v2_test", "procedure"),
        DbObject(SCHEMA_HIDRO, "sp_actualizar_reporte_turno_cache_emision_test", "procedure"),
        DbObject(SCHEMA_HIDRO, "reporte_turno_cache_emision_test", "table"),
        DbObject(SCHEMA_HIDRO, "sp_generador_reporte_diario_emision_test", "procedure"),
        DbObject(SCHEMA_HIDRO, "reporte_turno_cache", "table", required=False),
        DbObject(SCHEMA_HIDRO, "sp_generador_reporte_diario", "procedure", required=False),
        DbObject(SCHEMA_HIDRO, "sp_actualizar_reporte_turno_cache", "procedure", required=False),
    ],
    "Reclamo": [
        DbObject(SCHEMA_RECLAMO, "v_diferencia_cv25", "view"),
        DbObject(SCHEMA_RECLAMO, "v_rendimiento_rotopala", "view"),
        DbObject(SCHEMA_RECLAMO, "v_cuadratura_modulo", "view"),
        DbObject(SCHEMA_RECLAMO, "calculo_diario", "table"),
        DbObject(SCHEMA_RECLAMO, "v_reclamo_para_conciliados", "view"),
        DbObject(SCHEMA_RECLAMO, "ajuste_manual", "table"),
        DbObject(SCHEMA_RECLAMO, "v_modulo_base", "view"),
        DbObject(SCHEMA_RECLAMO, "modulo_congelado", "table"),
        DbObject(SCHEMA_RECLAMO, "secuencia_rotopala", "table"),
        DbObject(SCHEMA_RECLAMO, "rotopala_horas_turno", "table"),
        DbObject(SCHEMA_RECLAMO, "log_sincronizacion", "table"),
        DbObject(SCHEMA_RECLAMO, "log_automatizacion", "table"),
        DbObject(SCHEMA_RECLAMO, "log_ejecucion", "table"),
        DbObject(SCHEMA_RECLAMO, "fn_fecha_corte", "function"),
        DbObject(SCHEMA_RECLAMO, "sp_registrar_ajuste_manual", "procedure"),
        DbObject(SCHEMA_RECLAMO, "sp_actualizar_disponible_rotopala", "procedure"),
        DbObject(SCHEMA_RECLAMO, "sp_insertar_disponible_rotopala", "procedure"),
        DbObject(SCHEMA_RECLAMO, "sp_auto_mantener_secuencia", "procedure"),
        DbObject(SCHEMA_RECLAMO, "sp_sincronizar_desde_etl", "procedure"),
        DbObject(SCHEMA_RECLAMO, "sp_cargar_cv25_horas", "procedure"),
        DbObject(SCHEMA_RECLAMO, "sp_calcular_reclamo_diario", "procedure"),
        DbObject(SCHEMA_HIDRO, "disponible_rotopalas", "table"),
        DbObject(SCHEMA_HIDRO, "modulo", "table"),
        DbObject(SCHEMA_HIDRO, "parcela", "table"),
        DbObject(SCHEMA_HIDRO, "control_reclamo_diario", "table"),
        DbObject(SCHEMA_HIDRO, "sp_mantiene_datos_conciliados_emision_test", "procedure"),
    ],
    "PowerBI Camiones": [
        DbObject(SCHEMA_HIDRO, "mov_cam_powerbi", "table"),
        DbObject(SCHEMA_HIDRO, "mov_cam_powerbi_staging", "table"),
    ],
}


def _parse_login_fqn(login_database: str) -> tuple[str | None, str, str]:
    """Devuelve (database|None, schema, table) desde LOGIN_DATABASE."""
    parts = login_database.split(".")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return None, parts[0], parts[1]
    return None, "dbo", parts[0]


def _destino_conexion(conn) -> dict:
    fila = conn.execute(
        text(
            """
            SELECT
                @@SERVERNAME AS server_name,
                DB_NAME() AS database_name,
                SUSER_SNAME() AS login_name,
                SCHEMA_ID(:schema_hidro) AS schema_hidro_id,
                SCHEMA_ID(:schema_reclamo) AS schema_reclamo_id
            """
        ),
        {"schema_hidro": SCHEMA_HIDRO, "schema_reclamo": SCHEMA_RECLAMO},
    ).mappings().one()
    return dict(fila)


def _objeto_existe(conn, schema: str, name: str) -> bool:
    # OBJECT_ID acepta schema.name en la DB actual.
    oid = conn.execute(
        text("SELECT OBJECT_ID(:fqn)"),
        {"fqn": f"{schema}.{name}"},
    ).scalar()
    return oid is not None


def _login_tabla_existe(conn, login_database: str) -> tuple[bool, str]:
    db, schema, table = _parse_login_fqn(login_database)
    if db:
        # Cruces entre bases en el mismo servidor (PROD_SIIR / DEV_SIIR).
        oid = conn.execute(
            text("SELECT OBJECT_ID(:fqn)"),
            {"fqn": f"{db}.{schema}.{table}"},
        ).scalar()
        destino = f"{db}.{schema}.{table}"
    else:
        oid = conn.execute(
            text("SELECT OBJECT_ID(:fqn)"),
            {"fqn": f"{schema}.{table}"},
        ).scalar()
        destino = f"{schema}.{table} (DB actual)"
    return oid is not None, destino


def run_startup_db_check(*, strict: bool | None = None) -> bool:
    """Ejecuta el chequeo. True si todo lo required esta OK."""
    from dotenv import load_dotenv

    load_dotenv()

    if os.getenv("DB_STARTUP_CHECK", "1").strip() in {"0", "false", "no"}:
        logger.info("[DB-CHECK] Omitido (DB_STARTUP_CHECK=0)")
        return True

    if strict is None:
        strict = os.getenv("DB_STARTUP_CHECK_STRICT", "0").strip() in {
            "1",
            "true",
            "yes",
        }

    sqlserver_db_env = os.getenv("SQLSERVER_DB") or "(no definido)"
    login_database = os.getenv("LOGIN_DATABASE", "")

    try:
        from db_connection import get_engine

        engine = get_engine()
    except Exception as exc:
        msg = f"[DB-CHECK] No se pudo crear el engine: {exc}"
        logger.error(msg)
        print(msg)
        if strict:
            raise RuntimeError(msg) from exc
        return False

    if engine is None:
        msg = "[DB-CHECK] get_engine() devolvio None (revisar SQLSERVER_* / ENTORNO)"
        logger.error(msg)
        print(msg)
        if strict:
            raise RuntimeError(msg)
        return False

    faltantes_required: list[str] = []
    faltantes_optional: list[str] = []
    lineas: list[str] = []
    lineas.append("=" * 72)
    lineas.append("[DB-CHECK] Chequeo de arranque")
    lineas.append("=" * 72)

    try:
        with engine.connect() as conn:
            destino = _destino_conexion(conn)
            db_actual = destino.get("database_name")
            lineas.append(
                f"Conexion engine  = SQLSERVER_DB(.env)={sqlserver_db_env}"
            )
            lineas.append(
                f"DB efectiva      = {db_actual} @ {destino.get('server_name')} "
                f"(login={destino.get('login_name')})"
            )
            if sqlserver_db_env != "(no definido)" and db_actual != sqlserver_db_env:
                lineas.append(
                    "!! AVISO: SQLSERVER_DB del .env NO coincide con DB_NAME()"
                )

            hidro_ok = destino.get("schema_hidro_id") is not None
            reclamo_ok = destino.get("schema_reclamo_id") is not None
            lineas.append(
                f"Schemas en DB    = {SCHEMA_HIDRO}="
                f"{'OK' if hidro_ok else 'FALTA'} | "
                f"{SCHEMA_RECLAMO}={'OK' if reclamo_ok else 'FALTA'}"
            )
            if not hidro_ok:
                faltantes_required.append(f"schema {SCHEMA_HIDRO}")
            if not reclamo_ok:
                faltantes_required.append(f"schema {SCHEMA_RECLAMO}")

            # --- Auth (puede ser otra DB) ---
            lineas.append("-" * 72)
            lineas.append("Seccion: Auth / Login")
            if not login_database:
                lineas.append("  FALTA LOGIN_DATABASE en .env")
                faltantes_required.append("LOGIN_DATABASE")
            else:
                ok, destino_login = _login_tabla_existe(conn, login_database)
                estado = "OK" if ok else "FALTA"
                lineas.append(
                    f"  [{estado}] tabla={destino_login} "
                    f"(LOGIN_DATABASE={login_database})"
                )
                lineas.append(
                    "  Nota: Auth puede leer otra DB (DEV_SIIR/PROD_SIIR) "
                    "con el mismo engine; Reportabilidad/Reclamo/PowerBI "
                    f"usan la DB actual ({db_actual})."
                )
                if not ok:
                    faltantes_required.append(f"auth:{destino_login}")

            # --- Secciones de negocio (misma DB) ---
            for seccion, objetos in SECCIONES.items():
                lineas.append("-" * 72)
                lineas.append(f"Seccion: {seccion}")
                lineas.append(f"  DB usada: {db_actual} (schemas hardcodeados en SQL)")
                for obj in objetos:
                    ok = _objeto_existe(conn, obj.schema, obj.name)
                    marca = "OK" if ok else ("FALTA" if obj.required else "opcional-FALTA")
                    lineas.append(f"  [{marca}] {obj.kind:10} {obj.fqn}")
                    if not ok:
                        etiqueta = f"{seccion}: {obj.fqn}"
                        if obj.required:
                            faltantes_required.append(etiqueta)
                        else:
                            faltantes_optional.append(etiqueta)
    except Exception as exc:
        msg = f"[DB-CHECK] Error al consultar SQL Server: {exc}"
        logger.exception(msg)
        print(msg)
        if strict:
            raise RuntimeError(msg) from exc
        return False

    lineas.append("=" * 72)
    if faltantes_required:
        lineas.append(
            f"RESULTADO: FALTAN {len(faltantes_required)} objeto(s) requeridos"
        )
        for item in faltantes_required:
            lineas.append(f"  - {item}")
    else:
        lineas.append("RESULTADO: objetos requeridos OK")
    if faltantes_optional:
        lineas.append(
            f"Avisos opcionales ({len(faltantes_optional)}): "
            + ", ".join(faltantes_optional)
        )
    if strict and faltantes_required:
        lineas.append("Modo STRICT: abortando arranque.")
    lineas.append("=" * 72)

    reporte = "\n".join(lineas)
    print(reporte)
    if faltantes_required:
        logger.error(reporte)
    else:
        logger.info(reporte)

    if strict and faltantes_required:
        raise RuntimeError(
            "DB startup check fallo: faltan objetos requeridos. "
            "Ver log [DB-CHECK]. SQLSERVER_DB="
            f"{sqlserver_db_env}"
        )
    return not faltantes_required
