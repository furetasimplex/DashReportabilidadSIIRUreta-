"""Respaldo actual y recálculo V2 con ROLLBACK, antes de cambiar límites."""
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection

SCHEMA = "inventar_SpcHidr."
CONTROL = SCHEMA + "Control_Factor_Ajuste_Camiones_v2_test"
VIEW = SCHEMA + "v_ajuste_camiones_emision_test"


def save(path, value):
    path.write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def rows(conn, obj):
    return [dict(r) for r in conn.execute(text("SELECT * FROM " + obj + " ORDER BY Fecha")).mappings()]


def compare(before, after):
    a, b = ({r["Fecha"]: r for r in data} for data in (before, after))
    changes, maxima = [], {}
    for day in sorted(a.keys() | b.keys()):
        if day not in a or day not in b:
            changes.append({"Fecha": day, "fila_ausente": "antes" if day not in a else "despues"})
            continue
        for col, old in a[day].items():
            if col == "Fecha_Calculo":
                continue
            new = b[day][col]
            if isinstance(old, (int, float, Decimal)) and isinstance(new, (int, float, Decimal)):
                maxima[col] = max(maxima.get(col, 0), abs(float(new) - float(old)))
            if old != new:
                changes.append({"Fecha": day, "columna": col, "antes": old, "despues": new})
    return {"filas_antes": len(before), "filas_despues": len(after),
            "diferencias": changes, "diferencia_maxima_numerica": maxima}


def main():
    folder = Path("auditorias/archivo/docs/diagnosticos/factor_camiones_fase2a") / ("baseline_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    engine = _engine_dev()
    with engine.connect() as conn:
        _assert_dev_connection(conn)
        # No ejecutar mantenedores con triggers desconocidos sobre su destino.
        triggers = conn.execute(text("SELECT name FROM sys.triggers WHERE parent_id=OBJECT_ID(:n) AND is_disabled=0"), {"n": CONTROL}).scalars().all()
        if triggers:
            raise RuntimeError("Revisar triggers antes del recálculo: " + repr(triggers))
        folder.mkdir(parents=True, exist_ok=False)
        for name in ("sp_factor_ajuste_camiones_test", "sp_mantiene_factor_ajuste_camiones_v2_test", "v_ajuste_camiones_emision_test", "sp_mantiene_factor_ajuste_camiones_test"):
            definition = conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID(:n))"), {"n": SCHEMA + name}).scalar_one()
            (folder / (name + ".sql")).write_text(definition, encoding="utf-8")
        schema = [dict(r) for r in conn.execute(text("SELECT c.name, TYPE_NAME(c.user_type_id) tipo, c.max_length, c.precision, c.scale, c.is_nullable FROM sys.columns c WHERE object_id=OBJECT_ID(:n) ORDER BY column_id"), {"n": CONTROL}).mappings()]
        save(folder / "esquema_control.json", schema)
        control_before, view_before = rows(conn, CONTROL), rows(conn, VIEW)
        old_before = rows(conn, SCHEMA + "Control_Factor_Ajuste_Camiones")
        save(folder / "control_antes.json", control_before)
        save(folder / "vista_antes.json", view_before)
        save(folder / "cadena_antigua_antes.json", old_before)
        start, end = control_before[0]["Fecha"], control_before[-1]["Fecha"]
        if str(start) != "2026-07-01":
            raise RuntimeError("MIN(Fecha) cambió; revisar antes de continuar")
        conn.rollback()
        transaction = conn.begin()
        try:
            _assert_dev_connection(conn)
            conn.execute(text("EXEC inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test @FechaInicio=:inicio, @FechaFin=:fin, @DiasReproceso=0"), {"inicio": start, "fin": end})
            control_after, view_after = rows(conn, CONTROL), rows(conn, VIEW)
            save(folder / "control_recalculado_provisional.json", control_after)
            save(folder / "vista_recalculada_provisional.json", view_after)
            report = {"inicio": start, "fin": end, "control": compare(control_before, control_after), "vista": compare(view_before, view_after)}
        finally:
            transaction.rollback()
        report["rollback_control_identico"] = rows(conn, CONTROL) == control_before
        report["rollback_vista_identica"] = rows(conn, VIEW) == view_before
        report["cadena_antigua_identica"] = rows(conn, SCHEMA + "Control_Factor_Ajuste_Camiones") == old_before
        save(folder / "comparacion.json", report)
        assert report["rollback_control_identico"] and report["rollback_vista_identica"] and report["cadena_antigua_identica"]
        print("Evidencia:", folder)
        print("Rango:", start, end, "filas:", len(control_before))
        print("Diferencias control:", len(report["control"]["diferencias"]), "vista:", len(report["vista"]["diferencias"]))
        print("ROLLBACK confirmado. Cadena antigua intacta.")


if __name__ == "__main__":
    main()
