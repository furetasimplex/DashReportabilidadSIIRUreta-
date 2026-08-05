from datetime import date
import unittest
from unittest.mock import patch

import pandas as pd

from report_export import report_export as repo
from report_export.callbacks import reportabilidad_cb as cb


class _Alto(Exception):
    """Corta la ejecucion apenas se llega al punto que interesa medir."""


class _Result:
    def __init__(self, valor):
        self.valor = valor

    def scalar(self):
        return self.valor


class _Contexto:
    def __init__(self, conexion):
        self.conexion = conexion

    def __enter__(self):
        return self.conexion

    def __exit__(self, exc_type, exc, tb):
        return False


class _Conexion:
    """Registra cada sentencia; devuelve rc para sp_getapplock."""

    def __init__(self, ejecuciones=None, falla_en=None, rc=0):
        self.ejecuciones = ejecuciones if ejecuciones is not None else []
        self.falla_en = falla_en
        self.rc = rc

    def execute(self, sentencia, parametros=None):
        sql = str(sentencia)
        if self.falla_en and self.falla_en in sql:
            raise Exception("fallo simulado")
        self.ejecuciones.append((sql, parametros))
        return _Result(self.rc if "sp_getapplock" in sql else None)

    def commit(self):
        pass

    def begin(self):
        return _Contexto(self)


class _Motor:
    def __init__(self, conexion=None):
        self.conexion = conexion or _Conexion()

    def connect(self):
        return _Contexto(self.conexion)

    def begin(self):
        return _Contexto(self.conexion)


def _sps_en(ejecuciones):
    """Ignora las sentencias de lock y deja solo los tres SP de refresco."""
    out = []
    for sql, params in ejecuciones:
        if "sp_getapplock" in sql or "sp_releaseapplock" in sql:
            continue
        if "EXEC " not in sql:
            continue
        out.append((sql.split("EXEC ", 1)[1].split()[0], params))
    return out


class RefrescoRepresentatividadTests(unittest.TestCase):
    def test_fecha_corte_usa_totalizador_y_bitacora_y_respeta_rango(self):
        esperado = date(2026, 7, 23)
        motor = _Motor()

        with (
            patch.object(repo, "_get_engine", return_value=motor),
            patch.object(
                repo.pd,
                "read_sql_query",
                return_value=pd.DataFrame(
                    {"Fecha_Maxima_Exportable": [pd.Timestamp(esperado)]}
                ),
            ) as leer,
        ):
            resultado = repo.fetch_fecha_corte_operacional_representatividad(
                date(2026, 7, 1),
                date(2026, 7, 31),
            )

        self.assertEqual(resultado, esperado)
        sql = str(leer.call_args.args[0])
        self.assertIn("inventar_SpcHidr.tot_TM", sql)
        self.assertIn("inventar_SpcHidr.v_bitacora_rangos_norm", sql)
        self.assertIn(
            "r.Max_ts_fin_dia <= mt.Max_Fecha_Totalizador",
            sql,
        )
        self.assertEqual(
            leer.call_args.kwargs["params"],
            {
                "start": date(2026, 7, 1),
                "end": date(2026, 7, 31),
            },
        )

    def test_refresco_ejecuta_los_sp_en_orden_con_corte_inclusivo(self):
        ejecuciones = []
        motor = _Motor(_Conexion(ejecuciones))
        inicio = date(2026, 7, 1)
        corte = date(2026, 7, 23)

        with (
            patch.object(
                repo,
                "fetch_fecha_corte_operacional_representatividad",
                return_value=corte,
            ),
            patch.object(repo, "_get_engine", return_value=motor),
        ):
            resultado = repo.refrescar_representatividad_para_exportacion(
                inicio,
                date(2026, 7, 31),
            )

        self.assertEqual(resultado, corte)
        sps = _sps_en(ejecuciones)
        self.assertEqual(
            [nombre for nombre, _ in sps],
            [
                # Primero el apilado: alimenta Turno_Evaluable, del que
                # dependen las tres capas siguientes para decidir que dias
                # son evaluables.
                "inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test",
                "inventar_SpcHidr.sp_calcular_resumen_intervalo_totTM",
                "inventar_SpcHidr.sp_refrescar_representatividad_torres",
                "inventar_SpcHidr.sp_sincronizar_bd_ton",
            ],
        )
        self.assertTrue(
            all(
                parametros == {"start": inicio, "end": corte}
                for _, parametros in sps
            )
        )

    def test_apilado_reprocesa_dias_ya_congelados(self):
        """Con @DiasReproceso=0 un dia congelado antes del cierre de turno
        se quedaria con Flag_Apilado_Valido=0 para siempre."""
        ejecuciones = []
        motor = _Motor(_Conexion(ejecuciones))

        with (
            patch.object(
                repo,
                "fetch_fecha_corte_operacional_representatividad",
                return_value=date(2026, 7, 23),
            ),
            patch.object(repo, "_get_engine", return_value=motor),
        ):
            repo.refrescar_representatividad_para_exportacion(
                date(2026, 7, 1),
                date(2026, 7, 31),
            )

        sql_apilado = next(
            sql for sql, _ in ejecuciones
            if "sp_mantiene_apilado_tmh_v2_test" in sql
        )
        self.assertIn("@DiasReproceso = 7", sql_apilado)

    def test_refresco_informa_si_no_hay_fecha_operacional_cerrada(self):
        with patch.object(
            repo,
            "fetch_fecha_corte_operacional_representatividad",
            return_value=None,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "No existe una fecha operacional cerrada",
            ):
                repo.refrescar_representatividad_para_exportacion(
                    date(2026, 7, 1),
                    date(2026, 7, 31),
                )

    def test_refresco_identifica_el_sp_que_falla(self):
        nombre = "inventar_SpcHidr.sp_refrescar_representatividad_torres"
        motor = _Motor(_Conexion(falla_en=nombre))

        with (
            patch.object(
                repo,
                "fetch_fecha_corte_operacional_representatividad",
                return_value=date(2026, 7, 23),
            ),
            patch.object(repo, "_get_engine", return_value=motor),
        ):
            with self.assertRaisesRegex(RuntimeError, nombre):
                repo.refrescar_representatividad_para_exportacion(
                    date(2026, 7, 1),
                    date(2026, 7, 31),
                )

    def test_toma_y_libera_el_applock_del_mes(self):
        ejecuciones = []
        motor = _Motor(_Conexion(ejecuciones))

        with (
            patch.object(
                repo,
                "fetch_fecha_corte_operacional_representatividad",
                return_value=date(2026, 7, 23),
            ),
            patch.object(repo, "_get_engine", return_value=motor),
        ):
            repo.refrescar_representatividad_para_exportacion(
                date(2026, 7, 1),
                date(2026, 7, 31),
            )

        self.assertIn("sp_getapplock", ejecuciones[0][0])
        self.assertEqual(
            ejecuciones[0][1],
            {
                "recurso": "rep_torres_refresco:2026-07",
                "timeout": repo.LOCK_REFRESCO_REP_TIMEOUT_MS,
            },
        )
        self.assertIn("@LockOwner = 'Session'", ejecuciones[0][0])
        self.assertIn("sp_releaseapplock", ejecuciones[-1][0])
        self.assertEqual(
            ejecuciones[-1][1],
            {"recurso": "rep_torres_refresco:2026-07"},
        )

    def test_lock_no_obtenido_aborta_sin_ejecutar_sp(self):
        ejecuciones = []
        motor = _Motor(_Conexion(ejecuciones, rc=-1))

        with (
            patch.object(
                repo,
                "fetch_fecha_corte_operacional_representatividad",
                return_value=date(2026, 7, 23),
            ),
            patch.object(repo, "_get_engine", return_value=motor),
        ):
            with self.assertRaisesRegex(RuntimeError, "2026-07"):
                repo.refrescar_representatividad_para_exportacion(
                    date(2026, 7, 1),
                    date(2026, 7, 31),
                )

        self.assertEqual(_sps_en(ejecuciones), [])
        self.assertEqual(len(ejecuciones), 1)
        self.assertIn("sp_getapplock", ejecuciones[0][0])

    def test_libera_el_lock_aunque_falle_un_sp(self):
        nombre = "inventar_SpcHidr.sp_refrescar_representatividad_torres"
        ejecuciones = []
        motor = _Motor(_Conexion(ejecuciones, falla_en=nombre))

        with (
            patch.object(
                repo,
                "fetch_fecha_corte_operacional_representatividad",
                return_value=date(2026, 7, 23),
            ),
            patch.object(repo, "_get_engine", return_value=motor),
        ):
            with self.assertRaisesRegex(RuntimeError, nombre):
                repo.refrescar_representatividad_para_exportacion(
                    date(2026, 7, 1),
                    date(2026, 7, 31),
                )

        self.assertTrue(
            any("sp_releaseapplock" in sql for sql, _ in ejecuciones)
        )


class GrillaRefrescaAlAbrirTests(unittest.TestCase):
    """La grilla dejo de leer el estado que dejo la ultima publicacion."""

    def test_abrir_la_grilla_refresca_el_mes_de_la_fecha_final(self):
        llamadas = []

        def _refresco(start_date, end_date):
            llamadas.append((start_date, end_date))
            return date(2026, 7, 23)

        def _corta(*args, **kwargs):
            raise _Alto

        with (
            patch.object(
                cb, "refrescar_representatividad_para_exportacion", _refresco
            ),
            patch.object(cb, "_fetch_fuentes_mensuales_torres", _corta),
        ):
            with self.assertRaises(_Alto):
                cb._cargar_detalle_representatividad_periodo(
                    date(2026, 7, 10),
                    date(2026, 7, 28),
                )

        # Rango = mes de `fin`, que es el que la grilla realmente muestra.
        self.assertEqual(llamadas, [(date(2026, 7, 1), date(2026, 7, 28))])

    def test_publicar_no_vuelve_a_refrescar(self):
        """Con paquete armado el refresco ya corrio: repetirlo es costo puro."""
        llamadas = []

        def _refresco(start_date, end_date):
            llamadas.append((start_date, end_date))
            return date(2026, 7, 23)

        def _corta(*args, **kwargs):
            raise _Alto

        paquete = {
            "fecha_corte_operacional": date(2026, 7, 23),
            "fecha_inicio_mes": date(2026, 7, 1),
            "fecha_fin_mes": date(2026, 7, 31),
            "bd_ton_mes": pd.DataFrame({"Fecha": [pd.Timestamp("2026-07-01")]}),
            "turno_mes": pd.DataFrame({"Fecha": [pd.Timestamp("2026-07-01")]}),
        }

        with (
            patch.object(
                cb, "refrescar_representatividad_para_exportacion", _refresco
            ),
            patch.object(cb, "_preparar_material_por_turno", _corta),
        ):
            with self.assertRaises(_Alto):
                cb._cargar_detalle_representatividad_periodo(
                    date(2026, 7, 1),
                    date(2026, 7, 31),
                    paquete=paquete,
                )

        self.assertEqual(llamadas, [])


if __name__ == "__main__":
    unittest.main()
