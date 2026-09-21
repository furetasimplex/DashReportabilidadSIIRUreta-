"""Contratos de fechas, secuencia y frescura; sin conexiones SQL reales."""
import ast
from datetime import date, datetime, timedelta
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from report_export import report_export as repo


class OrquestacionTurnoTests(unittest.TestCase):
    def test_periodos_y_orden(self):
        casos = [
            (date(2026, 9, 1), date(2026, 9, 30), date(2026, 9, 13), date(2026, 9, 7)),
            (date(2026, 8, 1), date(2026, 8, 31), date(2026, 8, 31), date(2026, 8, 25)),
            (date(2026, 9, 5), date(2026, 9, 10), date(2026, 9, 10), date(2026, 9, 5)),
            (date(2026, 9, 1), date(2026, 9, 30), date(2026, 9, 10), date(2026, 9, 4)),
        ]
        for inicio, fin, corte, ventana in casos:
            with self.subTest(corte=corte, inicio=inicio):
                momento = datetime(2026, 10, 1)
                engine = MagicMock()
                conn = engine.connect.return_value.__enter__.return_value
                conn.execute.return_value.scalar.return_value = momento
                conn.execute.return_value.mappings.return_value.all.side_effect = [
                    [{"Fecha": corte, "Turno": t, "Fecha_Actualizacion": momento} for t in ("A", "B")],
                    [{"Fecha": corte, "Fecha_Calculo": momento}],
                ]
                llamadas = []
                def registrar(nombre):
                    return lambda *a, **kw: llamadas.append((nombre, a, kw))
                with patch.object(repo, "_get_engine", return_value=engine), \
                     patch.object(repo, "fetch_fecha_corte_apilado_tmh_report", return_value=corte), \
                     patch.object(repo, "actualizar_apilado_tmh_v2_report", side_effect=registrar("apilado")), \
                     patch.object(repo, "actualizar_factor_ajuste_camiones_v2_report", side_effect=registrar("factor")), \
                     patch.object(repo, "actualizar_reporte_turno_cache_emision", side_effect=registrar("cache")):
                    resultado = repo.refrescar_dependencias_reporte_turno_emision(inicio, fin)
                self.assertEqual(resultado["inicio_ventana"], ventana)
                self.assertEqual(resultado["fin_solicitada"], fin)
                self.assertEqual(llamadas, [
                    ("apilado", (inicio, corte, 7), {}),
                    ("factor", (inicio, fin), {"dias_reproceso": 0}),
                    ("cache", (inicio, fin + timedelta(days=1)), {}),
                ])

    def test_sin_corte_no_escribe(self):
        with patch.object(repo, "fetch_fecha_corte_apilado_tmh_report", return_value=None), \
             patch.object(repo, "actualizar_apilado_tmh_v2_report") as apilado:
            with self.assertRaisesRegex(RuntimeError, "No existe una fecha operacional"):
                repo.refrescar_dependencias_reporte_turno_emision(date(2026, 9, 1), date(2026, 9, 30))
            apilado.assert_not_called()

    def test_cache_incompleto_obsoleto_y_duplicado(self):
        corte = date(2026, 9, 13)
        momento = datetime(2026, 9, 14)
        filas = [{"Fecha": corte, "Turno": t, "Fecha_Actualizacion": momento} for t in ("A", "B")]
        args = (date(2026, 9, 1), date(2026, 10, 1), corte, momento)
        repo._validar_frescura_cache_turno(filas, *args)
        for invalido in ([], filas[:1], filas + filas[:1],
                         [dict(f, Fecha_Actualizacion=momento - timedelta(seconds=1)) for f in filas]):
            with self.subTest(filas=invalido), self.assertRaises(RuntimeError):
                repo._validar_frescura_cache_turno(invalido, *args)

    def test_clays_precede_cache_y_respeta_fin_exclusivo(self):
        engine = MagicMock()
        conn = engine.begin.return_value.__enter__.return_value
        with patch.object(repo, "_get_engine", return_value=engine):
            repo.actualizar_reporte_turno_cache_emision(date(2026, 9, 1), date(2026, 10, 1))
        llamadas = conn.execute.call_args_list
        self.assertEqual(len(llamadas), 2)
        self.assertIn("sp_refrescar_clays_cufe", str(llamadas[0].args[0]))
        self.assertEqual(llamadas[0].args[1]["fecha_fin"], date(2026, 9, 30))
        self.assertIn("sp_actualizar_reporte_turno_cache", str(llamadas[1].args[0]))
        self.assertEqual(llamadas[1].args[1]["fecha_fin"], date(2026, 10, 1))

    def test_consumidores_comparten_orquestacion(self):
        path = Path(repo.__file__).parent / "callbacks/reportabilidad_cb.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        consumidores = []
        for fn in tree.body:
            if not isinstance(fn, ast.FunctionDef):
                continue
            calls = [n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
            if "refrescar_dependencias_reporte_turno_emision" in calls:
                consumidores.append(fn.name)
                self.assertNotIn("actualizar_apilado_tmh_v2_report", calls)
                self.assertNotIn("actualizar_factor_ajuste_camiones_v2_report", calls)
        self.assertIn("generar_reporte", consumidores)
        self.assertIn("exportar_excel", consumidores)
        self.assertEqual(len(consumidores), 3)  # Preview, Excel y PDF.


if __name__ == "__main__":
    unittest.main()
