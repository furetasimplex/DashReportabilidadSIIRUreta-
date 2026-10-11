"""
Borrar un comentario debe persistir.

Tres capas fusionan comentarios entre la grilla y el INSERT, y cada una
tenia la regla "si viene vacio, conserva el anterior". Juntas hacian que un
comentario publicado fuera imborrable: la unica forma de cambiarlo era
escribir otro texto encima.
"""
import unittest

import pandas as pd

from report_export import report_export as repo
from report_export.callbacks import reportabilidad_cb as cb


def _registros_store():
    """Store del editor: ya trae el comentario publicado del mes."""
    return [
        {
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Pad": "Sulfuro",
            "Pad_Original": "Sulfuro",
            "Comentario_TM1_Quimico": "sonda tapada",
            "Comentario_TM2_Quimico": None,
            "Comentario_TM3_Quimico": None,
            "Comentario_TM1_Fisico": "muestreador detenido",
            "Comentario_TM2_Fisico": None,
            "Comentario_TM3_Fisico": None,
        },
    ]


class BorrarEnLaGrillaTests(unittest.TestCase):
    """Capa 1: grilla -> store."""

    def test_vaciar_la_celda_borra_el_comentario(self):
        grid = [{
            "Fecha": "01-07-2026",
            "Turno": "TA",
            "Comentario_TM1": "",
            "Comentario_TM2": "",
            "Comentario_TM3": "",
        }]

        fusionado = cb._fusionar_comentarios_grilla(
            _registros_store(), grid, "quimico",
        )

        self.assertIsNone(fusionado[0]["Comentario_TM1_Quimico"])

    def test_borrar_en_quimico_no_toca_fisico(self):
        grid = [{
            "Fecha": "01-07-2026",
            "Turno": "TA",
            "Comentario_TM1": "",
            "Comentario_TM2": "",
            "Comentario_TM3": "",
        }]

        fusionado = cb._fusionar_comentarios_grilla(
            _registros_store(), grid, "quimico",
        )

        self.assertEqual(
            fusionado[0]["Comentario_TM1_Fisico"], "muestreador detenido",
        )

    def test_una_fila_ausente_de_la_grilla_conserva_lo_suyo(self):
        # Solo se publica lo que la grilla muestra; el resto no se toca.
        fusionado = cb._fusionar_comentarios_grilla(
            _registros_store(), [], "quimico",
        )

        self.assertEqual(fusionado[0]["Comentario_TM1_Quimico"], "sonda tapada")


class BorrarEnElDetalleVivoTests(unittest.TestCase):
    """Capa 2: store -> detalle vivo recien calculado."""

    def test_el_store_vacio_no_revive_el_comentario_vivo(self):
        detalle_vivo = pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Pad": "Sulfuro",
            "Pad_Original": "Sulfuro",
            "Comentario_TM1_Quimico": "sonda tapada",
        }])
        store = _registros_store()
        store[0]["Comentario_TM1_Quimico"] = None

        resultado = cb._fusionar_solo_comentarios_en_detalle_vivo(
            detalle_vivo, store,
        )

        # pandas guarda NaN en columnas object; _valor_parametro_sql lo
        # convierte a None antes del INSERT.
        self.assertTrue(pd.isna(resultado.loc[0, "Comentario_TM1_Quimico"]))

    def test_columna_ausente_en_el_store_cae_al_valor_vivo(self):
        detalle_vivo = pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Comentario_TM1_Quimico": "sonda tapada",
        }])
        # Registro parcial: sin la clave, no hay intencion de borrar.
        store = [{"Fecha": pd.Timestamp("2026-07-01"), "Turno": "TA"}]

        resultado = cb._fusionar_solo_comentarios_en_detalle_vivo(
            detalle_vivo, store,
        )

        self.assertEqual(
            resultado.loc[0, "Comentario_TM1_Quimico"], "sonda tapada",
        )


class BorrarEnElWriterTests(unittest.TestCase):
    """Capa 3: detalle final -> INSERT, contra lo ya publicado en BD."""

    def _previos(self):
        return repo.comentarios_mapa_desde_dataframe(pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Pad": "Sulfuro",
            "Pad_Original": "Sulfuro",
            "Comentario_TM1_Quimico": "sonda tapada",
        }]))

    def test_publicar_vacio_borra_lo_guardado(self):
        df = pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Pad": "Sulfuro",
            "Pad_Original": "Sulfuro",
            "Comentario_TM1_Quimico": None,
        }])

        resultado = repo._merge_comentarios_representatividad(
            df, self._previos(), usuario="tester",
        )

        self.assertIsNone(resultado.loc[0, "Comentario_TM1_Quimico"])

    def test_publicar_con_texto_nuevo_lo_reemplaza(self):
        df = pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Pad": "Sulfuro",
            "Pad_Original": "Sulfuro",
            "Comentario_TM1_Quimico": "sonda operativa",
        }])

        resultado = repo._merge_comentarios_representatividad(
            df, self._previos(), usuario="tester",
        )

        self.assertEqual(
            resultado.loc[0, "Comentario_TM1_Quimico"], "sonda operativa",
        )


class CicloCompletoTests(unittest.TestCase):
    def test_borrar_en_la_grilla_llega_hasta_el_insert(self):
        grid = [{
            "Fecha": "01-07-2026",
            "Turno": "TA",
            "Comentario_TM1": "",
            "Comentario_TM2": "",
            "Comentario_TM3": "",
        }]
        store = cb._fusionar_comentarios_grilla(
            _registros_store(), grid, "quimico",
        )

        # Al publicar el detalle se recalcula y llega sin comentarios.
        detalle_vivo = pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Pad": "Sulfuro",
            "Pad_Original": "Sulfuro",
        }])
        df_final = cb._fusionar_solo_comentarios_en_detalle_vivo(
            detalle_vivo, store,
        )
        previos = repo.comentarios_mapa_desde_dataframe(pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Pad": "Sulfuro",
            "Pad_Original": "Sulfuro",
            "Comentario_TM1_Quimico": "sonda tapada",
        }]))
        df_guardar = repo._merge_comentarios_representatividad(
            df_final, previos, usuario="tester",
        )
        registros = repo._registros_detalle_torre_oficial(df_guardar)

        self.assertIsNone(registros[0]["Comentario_TM1_Quimico"])
        # El comentario de la otra pestaña sobrevive al borrado.
        self.assertEqual(
            registros[0]["Comentario_TM1_Fisico"], "muestreador detenido",
        )


if __name__ == "__main__":
    unittest.main()
