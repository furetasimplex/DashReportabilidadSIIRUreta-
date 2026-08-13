"""Chequeo de arranque: DB conectada + objetos SQL requeridos por seccion.

Se ejecuta al importar main (tambien via wsgi). Por defecto solo reporta;
con DB_STARTUP_CHECK_STRICT=1 aborta si falta algo critico.
Desactivar: DB_STARTUP_CHECK=0.

Segun SQLSERVER_DB elige el ambiente de dependencias cross-DB:
  inventar_SpcHidr_PROD -> espera PROD_SIIR (prohibe DEV_SIIR en modulos)
  inventar_SpcHidr      -> espera DEV_SIIR  (prohibe PROD_SIIR en modulos)
Override: HIDRO_SIIR_DB=PROD_SIIR|DEV_SIIR.

Ademas, si el ambiente es DEV y existe inventar_SpcHidr_PROD, chequea el
peer via OBJECT_ID de tres partes. En PROD no se revisa la otra inventar_*.
Fallos del peer son avisos por defecto; DB_STARTUP_CHECK_PEER_STRICT=1 los
trata como requeridos. Omitir peer: DB_STARTUP_CHECK_BOTH_INVENTAR=0.
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

# Par de bases de negocio en el mismo servidor.
INVENTAR_DB_DEV = "inventar_SpcHidr"
INVENTAR_DB_PROD = "inventar_SpcHidr_PROD"
INVENTAR_DBS = (INVENTAR_DB_DEV, INVENTAR_DB_PROD)

# Dependencias cross-DB (schema.hidro) que los SP/vistas de inventar_* referencian.
# El prefijo de base (DEV_SIIR / PROD_SIIR) se elige segun SQLSERVER_DB.
CROSS_DB_HIDRO_OBJECTS = (
    "hidro.imp_csv",
    "hidro.v_imp_chancado_normalizado",
    "hidro.v_imp_conciliacion_chancado",
)


@dataclass(frozen=True)
class AmbientePerfil:
    """Perfil de referencias esperado segun la DB de conexion."""

    nombre: str
    sqlserver_db: str
    siir_db: str  # base Django/hidro esperada en los modulos SQL
    siir_db_prohibida: str  # no debe aparecer en defs si este ambiente esta activo
    login_db_esperada: str  # prefijo tipico de LOGIN_DATABASE


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


def _resolver_ambiente(db_efectiva: str | None) -> AmbientePerfil:
    """Elige el perfil de dependencias segun SQLSERVER_DB / DB_NAME().

    Override opcional: HIDRO_SIIR_DB=PROD_SIIR|DEV_SIIR fuerza la base hidro
    sin cambiar el resto del perfil.
    """
    nombre = (db_efectiva or "").strip()
    override = (os.getenv("HIDRO_SIIR_DB") or "").strip()

    if nombre.endswith("_PROD") or nombre == "inventar_SpcHidr_PROD":
        perfil = AmbientePerfil(
            nombre="prod",
            sqlserver_db=nombre or "inventar_SpcHidr_PROD",
            siir_db="PROD_SIIR",
            siir_db_prohibida="DEV_SIIR",
            login_db_esperada="PROD_SIIR",
        )
    else:
        # inventar_SpcHidr (sin sufijo) u otras = ambiente de desarrollo.
        perfil = AmbientePerfil(
            nombre="dev",
            sqlserver_db=nombre or "inventar_SpcHidr",
            siir_db="DEV_SIIR",
            siir_db_prohibida="PROD_SIIR",
            login_db_esperada="DEV_SIIR",
        )

    if override in {"DEV_SIIR", "PROD_SIIR"}:
        prohibida = "PROD_SIIR" if override == "DEV_SIIR" else "DEV_SIIR"
        perfil = AmbientePerfil(
            nombre=perfil.nombre,
            sqlserver_db=perfil.sqlserver_db,
            siir_db=override,
            siir_db_prohibida=prohibida,
            login_db_esperada=override,
        )
    return perfil


def _modulos_con_patron(conn, patron: str) -> list[str]:
    """Objetos cuyo texto SQL contiene el patron (p.ej. DEV_SIIR / PROD_SIIR)."""
    rows = conn.execute(
        text(
            """
            SELECT s.name + '.' + o.name AS fqn
            FROM sys.sql_modules AS m
            JOIN sys.objects AS o ON o.object_id = m.object_id
            JOIN sys.schemas AS s ON s.schema_id = o.schema_id
            WHERE m.definition LIKE :patron
            ORDER BY 1
            """
        ),
        {"patron": f"%{patron}%"},
    ).scalars().all()
    return list(rows)


def _cross_db_objeto_existe(conn, fqn_tres_partes: str) -> bool:
    """OBJECT_ID de un objeto en otra base del mismo servidor (db.schema.objeto)."""
    oid = conn.execute(
        text("SELECT OBJECT_ID(:fqn)"),
        {"fqn": fqn_tres_partes},
    ).scalar()
    return oid is not None


def _db_existe(conn, database: str) -> bool:
    return conn.execute(
        text("SELECT DB_ID(:db)"),
        {"db": database},
    ).scalar() is not None


def _peer_inventar_db(db_actual: str | None) -> str | None:
    """La otra base inventar_* del par dev/prod, si aplica."""
    nombre = (db_actual or "").strip()
    if nombre == INVENTAR_DB_PROD:
        return INVENTAR_DB_DEV
    if nombre == INVENTAR_DB_DEV:
        return INVENTAR_DB_PROD
    return None


def _objetos_requeridos_unicos() -> list[DbObject]:
    """Lista deduplicada de objetos required (sin opcionales)."""
    vistos: set[str] = set()
    out: list[DbObject] = []
    for objetos in SECCIONES.values():
        for obj in objetos:
            if not obj.required or obj.fqn in vistos:
                continue
            vistos.add(obj.fqn)
            out.append(obj)
    return out


def _modulos_con_patron_en_db(conn, database: str, patron: str) -> list[str]:
    """Igual que _modulos_con_patron pero contra sys.sql_modules de otra DB."""
    # Identificadores de catalogo no se parametrizan; database viene de constante.
    if database not in INVENTAR_DBS:
        raise ValueError(f"DB no permitida para scan de modulos: {database}")
    rows = conn.execute(
        text(
            f"""
            SELECT s.name + '.' + o.name AS fqn
            FROM [{database}].sys.sql_modules AS m
            JOIN [{database}].sys.objects AS o ON o.object_id = m.object_id
            JOIN [{database}].sys.schemas AS s ON s.schema_id = o.schema_id
            WHERE m.definition LIKE :patron
            ORDER BY 1
            """
        ),
        {"patron": f"%{patron}%"},
    ).scalars().all()
    return list(rows)


def _chequear_peer_inventar(
    conn,
    peer_db: str,
    *,
    lineas: list[str],
    faltantes_required: list[str],
    faltantes_optional: list[str],
    peer_strict: bool,
) -> None:
    """Inventario + deps cross-DB + refs SIIR sobre la otra inventar_*."""
    destino = "required" if peer_strict else "optional"
    bucket = faltantes_required if peer_strict else faltantes_optional

    lineas.append("-" * 72)
    lineas.append(
        f"Seccion: Peer inventar ({peer_db}) "
        f"[{'STRICT' if peer_strict else 'aviso'}]"
    )

    if not _db_existe(conn, peer_db):
        lineas.append(f"  [FALTA] base {peer_db} no existe en el servidor")
        bucket.append(f"peer:{peer_db} (DB inexistente)")
        return

    lineas.append(f"  [OK] base {peer_db} existe")

    # Schemas
    for schema in (SCHEMA_HIDRO, SCHEMA_RECLAMO):
        # SCHEMA_ID es de la DB actual; usar OBJECT_ID de un objeto tipico no.
        # Comprobar via catalogo de la peer.
        ok = conn.execute(
            text(
                f"""
                SELECT 1
                FROM [{peer_db}].sys.schemas
                WHERE name = :schema
                """
            ),
            {"schema": schema},
        ).scalar() is not None
        marca = "OK" if ok else "FALTA"
        lineas.append(f"  [{marca}] schema {peer_db}.{schema}")
        if not ok:
            bucket.append(f"peer:{peer_db}.{schema}")

    perfil_peer = _resolver_ambiente(peer_db)
    lineas.append(
        f"  Ambiente peer={perfil_peer.nombre} | "
        f"hidro esperado={perfil_peer.siir_db} | "
        f"prohibido={perfil_peer.siir_db_prohibida}"
    )

    faltan_objs: list[str] = []
    for obj in _objetos_requeridos_unicos():
        fqn3 = f"{peer_db}.{obj.fqn}"
        if not _cross_db_objeto_existe(conn, fqn3):
            faltan_objs.append(fqn3)
            bucket.append(f"peer:{fqn3}")
    total_req = len(_objetos_requeridos_unicos())
    if not faltan_objs:
        lineas.append(f"  [OK] {total_req} objetos requeridos presentes")
    else:
        lineas.append(
            f"  [FALTA] {len(faltan_objs)}/{total_req} objetos requeridos "
            f"ausentes en {peer_db}"
        )
        for fqn3 in faltan_objs[:12]:
            lineas.append(f"  [FALTA] {fqn3}")
        if len(faltan_objs) > 12:
            lineas.append(f"  ... y {len(faltan_objs) - 12} mas")

    # Cross-DB hidro del peer
    for relativo in CROSS_DB_HIDRO_OBJECTS:
        fqn = f"{perfil_peer.siir_db}.{relativo}"
        ok = _cross_db_objeto_existe(conn, fqn)
        marca = "OK" if ok else "FALTA"
        lineas.append(f"  [{marca}] dep {fqn}")
        if not ok:
            bucket.append(f"peer-cross-db:{fqn}")

    # Modulos con SIIR prohibido en el peer
    try:
        mods_mal = _modulos_con_patron_en_db(
            conn, peer_db, perfil_peer.siir_db_prohibida
        )
    except Exception as exc:
        lineas.append(f"  [AVISO] no se pudo leer modulos de {peer_db}: {exc}")
        faltantes_optional.append(f"peer-modulos:{peer_db}")
        return

    if not mods_mal:
        lineas.append(
            f"  [OK] ningun modulo en {peer_db} contiene "
            f"{perfil_peer.siir_db_prohibida}"
        )
    else:
        lineas.append(
            f"  [FALTA] {len(mods_mal)} modulo(s) en {peer_db} apuntan a "
            f"{perfil_peer.siir_db_prohibida}"
        )
        for fqn in mods_mal[:8]:
            lineas.append(f"  [FALTA] {peer_db}.{fqn}")
            bucket.append(
                f"peer:{peer_db}.{fqn} ({perfil_peer.siir_db_prohibida})"
            )
        if len(mods_mal) > 8:
            lineas.append(f"  ... y {len(mods_mal) - 8} mas")


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
            perfil = _resolver_ambiente(db_actual)
            lineas.append(
                f"  Ambiente={perfil.nombre} | hidro/SIIR esperado={perfil.siir_db} "
                f"| prohibido en modulos={perfil.siir_db_prohibida}"
            )
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
                login_db, _, _ = _parse_login_fqn(login_database)
                if login_db and login_db != perfil.login_db_esperada:
                    lineas.append(
                        f"  [AVISO] LOGIN_DATABASE apunta a {login_db}, "
                        f"pero el ambiente {perfil.nombre} espera "
                        f"{perfil.login_db_esperada}.*"
                    )
                    faltantes_optional.append(
                        f"LOGIN_DATABASE={login_db} "
                        f"(esperado {perfil.login_db_esperada})"
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

            # --- Dependencias cross-DB segun ambiente ---
            lineas.append("-" * 72)
            lineas.append(
                f"Seccion: Dependencias cross-DB ({perfil.siir_db})"
            )
            for relativo in CROSS_DB_HIDRO_OBJECTS:
                fqn = f"{perfil.siir_db}.{relativo}"
                ok = _cross_db_objeto_existe(conn, fqn)
                marca = "OK" if ok else "FALTA"
                lineas.append(f"  [{marca}] {fqn}")
                if not ok:
                    faltantes_required.append(f"cross-db:{fqn}")

            # Texto SQL: no debe apuntar a la base SIIR del otro ambiente.
            lineas.append("-" * 72)
            lineas.append(
                f"Seccion: Referencias en modulos SQL "
                f"(esperado {perfil.siir_db}, prohibido {perfil.siir_db_prohibida})"
            )
            mods_ok = _modulos_con_patron(conn, perfil.siir_db)
            mods_mal = _modulos_con_patron(conn, perfil.siir_db_prohibida)
            if mods_ok:
                lineas.append(
                    f"  [OK] {len(mods_ok)} modulo(s) referencian {perfil.siir_db}"
                )
            else:
                lineas.append(
                    f"  [AVISO] ningun modulo menciona {perfil.siir_db} "
                    "(puede ser normal si no hay cruces en texto)"
                )
            if not mods_mal:
                lineas.append(
                    f"  [OK] ningun modulo contiene {perfil.siir_db_prohibida}"
                )
            else:
                lineas.append(
                    f"  [FALTA] {len(mods_mal)} modulo(s) apuntan a "
                    f"{perfil.siir_db_prohibida} (ambiente {perfil.nombre} "
                    f"requiere {perfil.siir_db}; ver "
                    "docs/migrations/patch_dev_siir_to_prod_siir.sql)"
                )
                for fqn in mods_mal:
                    lineas.append(f"  [FALTA] {fqn}")
                    faltantes_required.append(
                        f"{perfil.siir_db_prohibida} en {fqn}"
                    )

            # --- Peer inventar_* (solo desde DEV; en PROD no se revisa la otra base) ---
            check_both = os.getenv(
                "DB_STARTUP_CHECK_BOTH_INVENTAR", "1"
            ).strip().lower() not in {"0", "false", "no"}
            peer_strict = os.getenv(
                "DB_STARTUP_CHECK_PEER_STRICT", "0"
            ).strip().lower() in {"1", "true", "yes"}
            peer_db = _peer_inventar_db(db_actual)
            if perfil.nombre == "prod":
                lineas.append("-" * 72)
                lineas.append(
                    "Seccion: Peer inventar (omitido: ambiente prod "
                    "no revisa inventar_SpcHidr)"
                )
            elif check_both and peer_db:
                _chequear_peer_inventar(
                    conn,
                    peer_db,
                    lineas=lineas,
                    faltantes_required=faltantes_required,
                    faltantes_optional=faltantes_optional,
                    peer_strict=peer_strict,
                )
            elif check_both and not peer_db:
                lineas.append("-" * 72)
                lineas.append(
                    "Seccion: Peer inventar (omitido: DB actual no es "
                    f"{INVENTAR_DB_DEV} ni {INVENTAR_DB_PROD})"
                )
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
