"""
Prueba funcional reversible DEV - Fase 2A.1 límites KOM/CAT.

Ejecutar desde la raíz del repo:
    python scripts/test_factor_limites_dev_reversible.py

Requisitos:
- SQLSERVER_DB=inventar_SpcHidr
- SIIR_DEV_SQLSERVER_HOST configurado con la máquina DEV real.
- Fase 2A desplegada en DEV.
- Configuración oficial inicial: KOM=380 / CAT=265 desde 2026-07-01.

La prueba usa una transacción externa y reemplaza temporalmente _engine_dev()
por un proxy que reutiliza la misma conexión. Así, incluso las funciones que
internamente usan .begin()/.connect() participan en la misma transacción.
Al final SIEMPRE ejecuta ROLLBACK.
"""

from contextlib import AbstractContextManager
from datetime import date, timedelta
import sys
import traceback

import pandas as pd
from flask import Flask, session
from pandas.testing import assert_frame_equal

from db_connection import get_engine
from monitor_pi_tum import db
from monitor_pi_tum import limites_camiones_panel as ui


USUARIO_PRUEBA = "PRUEBA_FASE_2A1_REVERSIBLE"
VALOR_PRUEBA_FUTURO = 350
VALOR_PRUEBA_RETRO = 351
FECHA_RETRO = date(2026, 9, 20)

TABLA_VIGENCIAS = "inventar_SpcHidr.factor_camiones_parametro_vigencia_test"
TABLA_CONTROL = "inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test"


class _ReuseConnection(AbstractContextManager):
    """Context manager que NO commit/rollback/close la conexión externa."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class _TransactionalEngineProxy:
    """Expone connect()/begin() reutilizando una transacción ya abierta."""

    def __init__(self, conn, real_engine):
        self._conn = conn
        self.url = real_engine.url

    def connect(self):
        return _ReuseConnection(self._conn)

    def begin(self):
        return _ReuseConnection(self._conn)


def _read_sql(conn, sql, **params):
    return pd.read_sql(db.text(sql), conn, params=params or None)


def snapshot_vigencias(conn):
    return _read_sql(
        conn,
        f"""
        SELECT *
        FROM {TABLA_VIGENCIAS}
        ORDER BY flota, parametro, vigencia_desde, id;
        """,
    )


def snapshot_control(conn):
    return _read_sql(
        conn,
        f"""
        SELECT *
        FROM {TABLA_CONTROL}
        ORDER BY Fecha;
        """,
    )


def limites_en_fecha(fecha_iso):
    frame = db.obtener_limites_factor_vigentes(fecha_iso)
    return {
        str(r["flota"]): float(r["valor"])
        for r in frame.to_dict("records")
    }


def assert_config_oficial(conn):
    actual = snapshot_vigencias(conn)
    activos = actual[
        (actual["activo"].astype(bool))
        & (actual["parametro"] == "LIMITE_CARGA_AJUSTE")
    ].copy()

    abiertas = activos[activos["vigencia_hasta"].isna()]
    if len(abiertas) != 2:
        raise AssertionError(
            f"Se esperaban 2 vigencias abiertas oficiales y hay {len(abiertas)}."
        )

    mapa = {str(r["flota"]): float(r["valor"]) for r in abiertas.to_dict("records")}
    if mapa != {"KOM": 380.0, "CAT": 265.0}:
        raise AssertionError(f"Configuración oficial inesperada: {mapa}")

    fechas = {
        str(r["flota"]): pd.Timestamp(r["vigencia_desde"]).date()
        for r in abiertas.to_dict("records")
    }
    esperado = date(2026, 7, 1)
    if fechas != {"KOM": esperado, "CAT": esperado}:
        raise AssertionError(f"Fecha inicial oficial inesperada: {fechas}")


def run_in_rollback(real_engine, nombre, fn):
    print(f"\n{'=' * 78}\n{nombre}\n{'=' * 78}")
    with real_engine.connect() as conn:
        # Abrir primero la transacción explícita. En SQLAlchemy 2.x,
        # _assert_dev_connection() ejecuta SELECTs y activa autobegin;
        # si se llama antes, un conn.begin() posterior falla con
        # InvalidRequestError.
        tx = conn.begin()
        original_engine_dev = db._engine_dev
        try:
            db._assert_dev_connection(conn)
            proxy = _TransactionalEngineProxy(conn, real_engine)
            db._engine_dev = lambda: proxy
            fn(conn)
            print("[OK] Validaciones dentro de la transacción.")
        finally:
            db._engine_dev = original_engine_dev
            if tx.is_active:
                tx.rollback()
            print("[ROLLBACK] Ejecutado.")

    with real_engine.connect() as verify:
        db._assert_dev_connection(verify)
        assert_config_oficial(verify)
    print("[OK] Configuración oficial restaurada tras ROLLBACK.")


def prueba_futuro(conn):
    antes_vigencias = snapshot_vigencias(conn)
    antes_control = snapshot_control(conn)

    fecha_futura = date.today() + timedelta(days=30)

    print(
        f"Prueba futura: KOM={VALOR_PRUEBA_FUTURO} "
        f"desde {fecha_futura:%Y-%m-%d}"
    )

    app = Flask(__name__)
    app.secret_key = "fase-2a1-test-only"

    with app.test_request_context("/"):
        session["user"] = USUARIO_PRUEBA

        token, _, retro = ui.preparar_confirmacion(
            "KOM",
            VALOR_PRUEBA_FUTURO,
            fecha_futura.isoformat(),
            "PRUEBA REVERSIBLE FASE 2A.1 - FUTURO",
        )
        if retro:
            raise AssertionError("La prueba futura fue clasificada como retroactiva.")

        anterior = fecha_futura - timedelta(days=1)
        if limites_en_fecha(anterior.isoformat())["KOM"] != 380.0:
            raise AssertionError("KOM dejó de ser 380 antes de la fecha futura.")

        resultado = ui.confirmar_registro(token, False)
        print("Resultado UI:", str(resultado)[:500])

        hoy = limites_en_fecha(date.today().isoformat())
        if hoy["KOM"] != 380.0 or hoy["CAT"] != 265.0:
            raise AssertionError(f"Límites vigentes hoy cambiaron indebidamente: {hoy}")

        en_d = limites_en_fecha(fecha_futura.isoformat())
        if en_d["KOM"] != float(VALOR_PRUEBA_FUTURO):
            raise AssertionError(f"KOM en D no resolvió {VALOR_PRUEBA_FUTURO}: {en_d}")
        if en_d["CAT"] != 265.0:
            raise AssertionError(f"CAT cambió indebidamente en la prueba futura: {en_d}")

        despues_control = snapshot_control(conn)
        assert_frame_equal(
            antes_control.reset_index(drop=True),
            despues_control.reset_index(drop=True),
            check_dtype=True,
            check_exact=True,
        )

        despues_vigencias = snapshot_vigencias(conn)
        if len(despues_vigencias) <= len(antes_vigencias):
            raise AssertionError("La nueva vigencia futura no fue registrada.")

        pendientes = db.obtener_pendientes_limites_factor()
        if not pendientes.empty:
            futuras = pendientes[
                pd.to_datetime(pendientes["Fecha"]).dt.date >= fecha_futura
            ]
            if not futuras.empty:
                raise AssertionError(
                    "Aparecieron pendientes materializados en/tras la fecha futura."
                )

    print("[OK] Futuro: vigente actual 380, D=350, CAT=265, Control V2 intacto.")


def prueba_retroactiva(conn):
    antes_control = snapshot_control(conn)

    if FECHA_RETRO >= date.today():
        raise AssertionError(
            f"FECHA_RETRO={FECHA_RETRO} debe ser anterior a hoy={date.today()}."
        )

    print(
        f"Prueba retroactiva: KOM={VALOR_PRUEBA_RETRO} "
        f"desde {FECHA_RETRO:%Y-%m-%d}"
    )

    app = Flask(__name__)
    app.secret_key = "fase-2a1-test-only"

    with app.test_request_context("/"):
        session["user"] = USUARIO_PRUEBA

        token, _, retro = ui.preparar_confirmacion(
            "KOM",
            VALOR_PRUEBA_RETRO,
            FECHA_RETRO.isoformat(),
            "PRUEBA REVERSIBLE FASE 2A.1 - RETROACTIVO",
        )
        if not retro:
            raise AssertionError("La prueba retroactiva no fue detectada como retroactiva.")

        try:
            ui.confirmar_registro(token, False)
        except ValueError as exc:
            if "retroactivo" not in str(exc).lower():
                raise
        else:
            raise AssertionError("Se aceptó un cambio retroactivo sin checkbox.")

        token, _, retro = ui.preparar_confirmacion(
            "KOM",
            VALOR_PRUEBA_RETRO,
            FECHA_RETRO.isoformat(),
            "PRUEBA REVERSIBLE FASE 2A.1 - RETROACTIVO",
        )
        if not retro:
            raise AssertionError("La segunda preparación perdió el estado retroactivo.")

        resultado = ui.confirmar_registro(token, True)
        salida = str(resultado)
        print("Resultado UI:", salida[:700])
        if "PENDIENTE DE REPROCESO" not in salida:
            raise AssertionError("La UI no informó PENDIENTE DE REPROCESO.")

        anterior = FECHA_RETRO - timedelta(days=1)
        limites_pre = limites_en_fecha(anterior.isoformat())
        limites_d = limites_en_fecha(FECHA_RETRO.isoformat())

        if limites_pre["KOM"] != 380.0:
            raise AssertionError(
                f"KOM anterior a D cambió indebidamente: {limites_pre}"
            )
        if limites_d["KOM"] != float(VALOR_PRUEBA_RETRO):
            raise AssertionError(
                f"KOM en D no tomó {VALOR_PRUEBA_RETRO}: {limites_d}"
            )
        if limites_d["CAT"] != 265.0:
            raise AssertionError(f"CAT cambió indebidamente: {limites_d}")

        despues_control = snapshot_control(conn)
        assert_frame_equal(
            antes_control.reset_index(drop=True),
            despues_control.reset_index(drop=True),
            check_dtype=True,
            check_exact=True,
        )

        pendientes = db.obtener_pendientes_limites_factor()
        kom = pendientes[
            (pendientes["flota"] == "KOM")
            & (pd.to_datetime(pendientes["Fecha"]).dt.date >= FECHA_RETRO)
        ]
        if kom.empty:
            raise AssertionError(
                "No se detectó ninguna diferencia configuración vs límite materializado."
            )

        if not (
            (kom["limite_configurado"].astype(float) == float(VALOR_PRUEBA_RETRO))
            & (kom["limite_utilizado"].astype(float) == 380.0)
        ).any():
            raise AssertionError(
                "No se encontró el contraste esperado configurado="
                f"{VALOR_PRUEBA_RETRO} vs utilizado=380."
            )

    print(
        "[OK] Retroactivo: D-1=380, D=nuevo valor, CAT=265, "
        "pendiente visible y Control V2 intacto."
    )


def main():
    real_engine = get_engine()
    if real_engine is None:
        raise RuntimeError("get_engine() no devolvió una conexión.")

    print("Servidor/base objetivo:", real_engine.url)

    with real_engine.connect() as conn:
        db._assert_dev_connection(conn)
        assert_config_oficial(conn)

    print("[OK] Guard DEV y configuración oficial inicial confirmados.")

    run_in_rollback(
        real_engine,
        "PRUEBA 1 - CAMBIO FUTURO REVERSIBLE",
        prueba_futuro,
    )
    run_in_rollback(
        real_engine,
        "PRUEBA 2 - CAMBIO RETROACTIVO REVERSIBLE",
        prueba_retroactiva,
    )

    with real_engine.connect() as conn:
        db._assert_dev_connection(conn)
        assert_config_oficial(conn)

    print("\n" + "=" * 78)
    print("RESULTADO FINAL")
    print("=" * 78)
    print("OK - Ambas pruebas terminaron con ROLLBACK.")
    print("OK - Configuración final oficial: KOM=380 / CAT=265 desde 2026-07-01.")
    print("OK - Ningún valor provisional quedó persistido.")
    print("OK - El registro de vigencias no modificó Control V2.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        print("\nFALLO - Revisar la evidencia anterior. No asumir que DEV quedó modificado.")
        sys.exit(1)
