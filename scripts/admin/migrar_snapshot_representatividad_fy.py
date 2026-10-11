"""Recalcula solamente los bloques FY de un snapshot historico de torres.

El modo normal es de solo lectura. Para escribir se exige ``--apply`` y
``--confirm-dev``. No crea reportes ni modifica cabecera o detalle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

import pandas as pd
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from report_export.report_export import (  # noqa: E402
    RTO_CAB_TABLE,
    RTO_DETALLE_TABLE,
    RTO_SNAPSHOT_TABLE,
    _dataframe_a_snapshot_json,
    _get_engine,
    _snapshot_json_a_dataframe,
    fetch_gestion_representatividad_fy,
)


BLOQUES = ("gestion_fy_quimico", "gestion_fy_fisico")
COLUMNAS_FY = {
    "Etiqueta",
    "Turnos_Evaluables",
    "Turnos_Representativos",
    "Representatividad",
}
MESES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


@dataclass(frozen=True)
class MetadataReporte:
    id_reporte: int
    periodo_mes: str
    periodo_inicio: object
    periodo_fin: object
    fecha_corte_operacional: object
    anio_fiscal: int
    activo: object
    estado: object
    usuario: object


def _scalar(valor):
    if hasattr(valor, "item"):
        try:
            return valor.item()
        except (TypeError, ValueError):
            pass
    return valor


def _json_default(valor):
    valor = _scalar(valor)
    if isinstance(valor, (date, datetime, pd.Timestamp)):
        return valor.isoformat()
    raise TypeError(f"No serializable: {type(valor).__name__}")


def _fila_mapping(resultado):
    fila = resultado.mappings().one_or_none()
    return None if fila is None else dict(fila)


def leer_estado(engine, id_reporte: int):
    sql_cab = text(f"""
        SELECT id_reporte, periodo_mes, periodo_inicio, periodo_fin,
               fecha_corte_operacional, anio_fiscal, activo, estado, usuario
        FROM {RTO_CAB_TABLE}
        WHERE id_reporte = :id_reporte
    """)
    sql_snap = text(f"""
        SELECT bloque, payload, filas
        FROM {RTO_SNAPSHOT_TABLE}
        WHERE id_reporte = :id_reporte
          AND bloque IN (:bloque_q, :bloque_f)
    """)
    with engine.connect() as conn:
        cab = _fila_mapping(conn.execute(sql_cab, {"id_reporte": id_reporte}))
        filas = conn.execute(
            sql_snap,
            {"id_reporte": id_reporte, "bloque_q": BLOQUES[0], "bloque_f": BLOQUES[1]},
        ).mappings().all()
    if cab is None:
        raise RuntimeError(f"No existe id_reporte={id_reporte}.")
    if cab["fecha_corte_operacional"] is None:
        raise RuntimeError("La cabecera no tiene fecha_corte_operacional.")
    if cab["anio_fiscal"] is None:
        raise RuntimeError("La cabecera no tiene anio_fiscal.")
    if len(filas) != 2 or {str(f["bloque"]) for f in filas} != set(BLOQUES):
        raise RuntimeError("Deben existir exactamente los dos bloques FY actuales.")
    metadata = MetadataReporte(**{k: _scalar(cab[k]) for k in MetadataReporte.__annotations__})
    actuales = {str(f["bloque"]): {"payload": f["payload"], "filas": int(f["filas"])} for f in filas}
    return metadata, actuales


def identificar_destino(engine) -> dict:
    with engine.connect() as conn:
        fila = _fila_mapping(conn.execute(text("""
            SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name,
                   SUSER_SNAME() AS login_name
        """)))
    fila["entorno"] = os.getenv("ENTORNO")
    return fila


def exigir_dev(destino: dict, confirmado: bool) -> None:
    if not confirmado:
        raise RuntimeError("--apply exige --confirm-dev.")
    valores = " ".join(str(destino.get(k) or "") for k in ("server_name", "database_name", "entorno")).lower()
    if any(token in valores for token in ("prod", "produccion", "production")):
        raise RuntimeError("Destino identificado como PROD; este script solo permite DEV.")
    if str(destino.get("entorno") or "").strip() == "2":
        raise RuntimeError("ENTORNO=2 corresponde a produccion; aplicacion abortada.")


def recalcular(metadata: MetadataReporte, fetch_fn: Callable = fetch_gestion_representatividad_fy) -> dict:
    corte = pd.to_datetime(metadata.fecha_corte_operacional).date()
    salida = {}
    for tipo, bloque in (("QUIMICO", BLOQUES[0]), ("FISICO", BLOQUES[1])):
        salida[bloque] = fetch_fn(
            anio_fiscal=int(metadata.anio_fiscal), tipo=tipo, alcance="COMBINADO",
            objetivo=0.85, fecha_corte=corte,
        )
    return salida


def _buscar_fila(df: pd.DataFrame, etiqueta: str) -> pd.Series:
    coincidencias = df[df["Etiqueta"].astype(str).str.casefold() == etiqueta.casefold()]
    if len(coincidencias) != 1:
        raise RuntimeError(f"Se esperaba una fila unica para Etiqueta={etiqueta!r}.")
    return coincidencias.iloc[0]


def validar_recalculo(metadata: MetadataReporte, nuevos: dict) -> None:
    mes = pd.to_datetime(metadata.periodo_inicio)
    etiqueta_mes = f"{MESES[mes.month - 1]}-{str(mes.year)[2:]}"
    for bloque in BLOQUES:
        df = nuevos.get(bloque)
        if df is None or df.empty:
            raise RuntimeError(f"El recalculo de {bloque} esta vacio.")
        faltantes = COLUMNAS_FY - set(df.columns)
        if faltantes:
            raise RuntimeError(f"{bloque} no contiene columnas requeridas: {sorted(faltantes)}")
        _buscar_fila(df, etiqueta_mes)

    if metadata.id_reporte == 110:
        esperados = {
            BLOQUES[0]: {"Jul-26": (114, 14, 14 / 114), etiqueta_mes: (88, 14, 14 / 88), "YTD": (202, 28, 28 / 202)},
            BLOQUES[1]: {"Jul-26": (114, 5, 5 / 114), etiqueta_mes: (88, 8, 8 / 88), "YTD": (202, 13, 13 / 202)},
        }
        for bloque, filas in esperados.items():
            for etiqueta, (evaluables, representativos, rep) in filas.items():
                fila = _buscar_fila(nuevos[bloque], etiqueta)
                observado = (int(fila["Turnos_Evaluables"]), int(fila["Turnos_Representativos"]))
                if observado != (evaluables, representativos) or abs(float(fila["Representatividad"]) - rep) > 1e-10:
                    raise RuntimeError(f"Aceptacion piloto fallida en {bloque}/{etiqueta}: {observado}.")


def serializar(nuevos: dict, serializer: Callable = _dataframe_a_snapshot_json) -> dict:
    return {b: {"payload": serializer(nuevos[b]), "filas": len(nuevos[b])} for b in BLOQUES}


def huella_detalle(engine, id_reporte: int) -> dict:
    sql = text(f"""
        SELECT COUNT_BIG(*) AS filas,
               CHECKSUM_AGG(BINARY_CHECKSUM(*)) AS checksum
        FROM {RTO_DETALLE_TABLE}
        WHERE id_reporte = :id_reporte
    """)
    with engine.connect() as conn:
        return _fila_mapping(conn.execute(sql, {"id_reporte": id_reporte}))


def validar_detalle_piloto(engine, id_reporte: int) -> None:
    if id_reporte != 110:
        return
    sql = text(f"""
        SELECT Fecha, Turno, TM1_Activo, TM2_Activo
        FROM {RTO_DETALLE_TABLE}
        WHERE id_reporte = :id_reporte
          AND Fecha IN ('2026-08-05', '2026-08-21', '2026-08-22')
          AND Turno = 'TB'
        ORDER BY Fecha
    """)
    with engine.connect() as conn:
        filas = conn.execute(sql, {"id_reporte": id_reporte}).mappings().all()
    observados = {
        pd.to_datetime(f["Fecha"]).date(): (int(f["TM1_Activo"]), int(f["TM2_Activo"]))
        for f in filas
    }
    esperados = {
        date(2026, 8, 5): (1, 0),
        date(2026, 8, 21): (0, 1),
        date(2026, 8, 22): (1, 1),
    }
    if observados != esperados:
        raise RuntimeError(f"Detalle piloto inesperado: {observados}.")


def crear_backup(metadata: MetadataReporte, actuales: dict, directorio: Path) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ruta = directorio / f"reporte_torre_{metadata.id_reporte}_fy_antes_{stamp}.json"
    contenido = {
        "id_reporte": metadata.id_reporte,
        "timestamp": datetime.now().astimezone().isoformat(),
        "metadata": asdict(metadata),
        "bloques": actuales,
    }
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    return ruta


def aplicar(engine, id_reporte: int, serializados: dict) -> None:
    sql = text(f"""
        UPDATE {RTO_SNAPSHOT_TABLE}
        SET payload = :payload, filas = :filas
        WHERE id_reporte = :id_reporte AND bloque = :bloque
    """)
    with engine.begin() as conn:
        for bloque in BLOQUES:
            resultado = conn.execute(sql, {"id_reporte": id_reporte, "bloque": bloque, **serializados[bloque]})
            if resultado.rowcount != 1:
                raise RuntimeError(f"UPDATE de {bloque} afecto {resultado.rowcount} filas; rollback.")


def restaurar_backup(engine, ruta: Path) -> int:
    data = json.loads(ruta.read_text(encoding="utf-8"))
    id_reporte = int(data["id_reporte"])
    bloques = data["bloques"]
    if set(bloques) != set(BLOQUES):
        raise RuntimeError("El backup no contiene exactamente los dos bloques FY.")
    aplicar(engine, id_reporte, bloques)
    return id_reporte


def _resumen_fila(df: pd.DataFrame, etiqueta: str) -> str:
    f = _buscar_fila(df, etiqueta)
    return f"{int(f['Turnos_Evaluables'])} / {int(f['Turnos_Representativos'])} = {float(f['Representatividad']):.15f}"


def imprimir_comparacion(metadata, actuales, nuevos) -> None:
    mes = pd.to_datetime(metadata.periodo_inicio)
    etiqueta_mes = f"{MESES[mes.month - 1]}-{str(mes.year)[2:]}"
    for bloque in BLOQUES:
        anterior = _snapshot_json_a_dataframe(actuales[bloque]["payload"])
        print(f"\n{bloque}")
        for etiqueta in (etiqueta_mes, "YTD"):
            print(f"  {etiqueta}: antes  {_resumen_fila(anterior, etiqueta)}")
            print(f"           despues {_resumen_fila(nuevos[bloque], etiqueta)}")


def ejecutar(id_reporte: int, apply: bool = False, confirm_dev: bool = False,
             backup_dir: Path = PROJECT_ROOT / "backups", engine=None,
             fetch_fn: Callable = fetch_gestion_representatividad_fy,
             serializer: Callable = _dataframe_a_snapshot_json) -> None:
    engine = engine or _get_engine()
    destino = identificar_destino(engine)
    print("DB destino:", json.dumps(destino, ensure_ascii=False, default=str))
    metadata, actuales = leer_estado(engine, id_reporte)
    print("Cabecera:", json.dumps(asdict(metadata), ensure_ascii=False, default=_json_default))
    nuevos = recalcular(metadata, fetch_fn)
    validar_recalculo(metadata, nuevos)
    serializados = serializar(nuevos, serializer)
    imprimir_comparacion(metadata, actuales, nuevos)
    if not apply:
        print("\nDRY-RUN: no se realizaron cambios.")
        return

    exigir_dev(destino, confirm_dev)
    detalle_antes = huella_detalle(engine, id_reporte)
    if int(detalle_antes["filas"]) != 62 and id_reporte == 110:
        raise RuntimeError(f"El detalle 110 debe tener 62 filas; tiene {detalle_antes['filas']}.")
    validar_detalle_piloto(engine, id_reporte)
    backup = crear_backup(metadata, actuales, backup_dir)
    print(f"Backup creado: {backup}")
    aplicar(engine, id_reporte, serializados)
    metadata_post, actuales_post = leer_estado(engine, id_reporte)
    detalle_despues = huella_detalle(engine, id_reporte)
    if metadata_post != metadata or detalle_despues != detalle_antes:
        raise RuntimeError("La cabecera o el detalle cambiaron durante la migracion; revisar y restaurar backup.")
    validar_detalle_piloto(engine, id_reporte)
    for bloque in BLOQUES:
        if actuales_post[bloque] != serializados[bloque]:
            raise RuntimeError(f"Validacion post-update fallida para {bloque}.")
    validar_recalculo(metadata_post, {b: _snapshot_json_a_dataframe(actuales_post[b]["payload"]) for b in BLOQUES})
    print("APPLY completado: 2 bloques FY actualizados; cabecera y detalle sin cambios.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id-reporte", type=int)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--apply", action="store_true")
    modo.add_argument("--rollback-backup", type=Path)
    modo.add_argument("--dry-run", action="store_true", help="Explicito; es tambien el modo por defecto.")
    parser.add_argument("--confirm-dev", action="store_true", help="Confirmacion obligatoria para cualquier escritura.")
    parser.add_argument("--backup-dir", type=Path, default=PROJECT_ROOT / "backups")
    args = parser.parse_args(argv)
    try:
        engine = _get_engine()
        if args.rollback_backup:
            destino = identificar_destino(engine)
            print("DB destino:", json.dumps(destino, ensure_ascii=False, default=str))
            exigir_dev(destino, args.confirm_dev)
            restaurado = restaurar_backup(engine, args.rollback_backup)
            print(f"Rollback completado para id_reporte={restaurado}; solo payload y filas FY.")
        else:
            if args.id_reporte is None:
                parser.error("--id-reporte es obligatorio salvo con --rollback-backup")
            ejecutar(args.id_reporte, args.apply, args.confirm_dev, args.backup_dir, engine)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
