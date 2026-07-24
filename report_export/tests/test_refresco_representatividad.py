from datetime import date
import unittest
from unittest.mock import patch

import pandas as pd

from report_export import report_export as repo


class _Contexto:
    def __init__(self, conexion):
        self.conexion = conexion

    def __enter__(self):
        return self.conexion

    def __exit__(self, exc_type, exc, tb):
        return False


class _Conexion:
    def __init__(self, ejecuciones=None, falla_en=None):
        self.ejecuciones = ejecuciones if ejecuciones is not None else []
        self.falla_en = falla_en

    def execute(self, sentencia, parametros):
        sql = str(sentencia)
        if self.falla_en and self.falla_en in sql:
            raise Exception("fallo simulado")
        self.ejecuciones.append((sql, parametros))


class _Motor:
    def __init__(self, conexion=None):
        self.conexion = conexion or _Conexion()

    def connect(self):
        return _Contexto(self.conexion)

    def begin(self):
        return _Contexto(self.conexion)


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

    def test_refresco_ejecuta_los_tres_sp_en_orden_con_corte_inclusivo(self):
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
        self.assertEqual(
            [
                sql.split("EXEC ", 1)[1].split()[0]
                for sql, _ in ejecuciones
            ],
            [
                "inventar_SpcHidr.sp_calcular_resumen_intervalo_totTM",
                "inventar_SpcHidr.sp_refrescar_representatividad_torres",
                "inventar_SpcHidr.sp_sincronizar_bd_ton",
            ],
        )
        self.assertTrue(
            all(
                parametros == {"start": inicio, "end": corte}
                for _, parametros in ejecuciones
            )
        )

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


if __name__ == "__main__":
    unittest.main()
