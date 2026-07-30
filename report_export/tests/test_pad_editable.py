"""
Pad editable: Pad = valor efectivo, Pad_Original = valor derivado.

Cubre el ciclo completo del override — grilla -> store -> detalle vivo ->
publicacion -> republicacion — porque un Pad ajustado cambia cifras del
reporte oficial (tabla "Mineral apilado por Pad").
"""
import unittest

import pandas as pd

from report_export import report_export as repo
from report_export.callbacks import reportabilidad_cb as cb


def _registros_detalle():
    """Detalle vivo recien calculado: sin ajustes, Pad == Pad_Original."""
    return [
        {
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Semana": "Semana 1",
            "Pad": "Sulfuro",
            "Pad_Original": "Sulfuro",
            "Comentario_TM1_Quimico": None,
            "Comentario_TM2_Quimico": None,
            "Comentario_TM3_Quimico": None,
            "Comentario_TM1_Fisico": None,
            "Comentario_TM2_Fisico": None,
            "Comentario_TM3_Fisico": None,
        },
        {
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TB",
            "Semana": "Semana 1",
            "Pad": "Sin clasificar",
            "Pad_Original": "Sin clasificar",
            "Comentario_TM1_Quimico": None,
            "Comentario_TM2_Quimico": None,
            "Comentario_TM3_Quimico": None,
            "Comentario_TM1_Fisico": None,
            "Comentario_TM2_Fisico": None,
            "Comentario_TM3_Fisico": None,
        },
    ]


def _fila_grilla(fecha, turno, pad, pad_original):
    return {
        "Fecha": fecha,
        "Turno": turno,
        "Pad": pad,
        "Pad_Original": pad_original,
        "Comentario_TM1": "",
        "Comentario_TM2": "",
        "Comentario_TM3": "",
    }


class TestPadEditable(unittest.TestCase):

    def test_edicion_en_grilla_llega_al_store(self):
        registros = _registros_detalle()
        grid = [
            _fila_grilla("01-07-2026", "TA", "Sulfuro", "Sulfuro"),
            # El operador corrige el turno B a Óxido.
            _fila_grilla("01-07-2026", "TB", "Óxido", "Sin clasificar"),
        ]
        salida = cb._fusionar_comentarios_grilla(registros, grid, "quimico")
        por_turno = {f["Turno"]: f for f in salida}

        self.assertEqual(por_turno["TB"]["Pad"], "Óxido")
        # El derivado nunca se toca: es la evidencia de que hubo ajuste.
        self.assertEqual(por_turno["TB"]["Pad_Original"], "Sin clasificar")
        self.assertEqual(por_turno["TA"]["Pad"], "Sulfuro")

    def test_valor_fuera_de_lista_se_ignora(self):
        registros = _registros_detalle()
        grid = [_fila_grilla("01-07-2026", "TA", "Test", "Sulfuro")]
        salida = cb._fusionar_comentarios_grilla(registros, grid, "quimico")

        self.assertEqual(salida[0]["Pad"], "Sulfuro")

    def test_fila_futura_no_se_puede_clasificar(self):
        """Sin Pad_Original la fila no tiene apilado: no hay nada que ajustar."""
        registros = _registros_detalle()
        registros[0]["Pad"] = None
        registros[0]["Pad_Original"] = None
        grid = [_fila_grilla("01-07-2026", "TA", "Óxido", None)]

        salida = cb._fusionar_comentarios_grilla(registros, grid, "quimico")

        self.assertIsNone(salida[0]["Pad"])

    def test_sin_clasificar_no_es_ajuste_elegible(self):
        """Solo Óxido y Sulfuro; "Sin clasificar" existe pero no se elige."""
        self.assertEqual(cb._PAD_VALORES_VALIDOS, ("Óxido", "Sulfuro"))

        registros = _registros_detalle()
        grid = [_fila_grilla("01-07-2026", "TA", "Sin clasificar", "Sulfuro")]
        salida = cb._fusionar_comentarios_grilla(registros, grid, "quimico")

        self.assertEqual(salida[0]["Pad"], "Sulfuro")

    def test_override_del_editor_gana_sobre_el_detalle_vivo(self):
        vivo = pd.DataFrame(_registros_detalle())
        editor = _registros_detalle()
        editor[1]["Pad"] = "Óxido"

        salida = cb._fusionar_solo_comentarios_en_detalle_vivo(vivo, editor)

        self.assertEqual(list(salida["Pad"]), ["Sulfuro", "Óxido"])
        self.assertEqual(
            list(salida["Pad_Original"]), ["Sulfuro", "Sin clasificar"]
        )

    def test_sin_ajuste_el_detalle_vivo_manda(self):
        """El derivado cambia entre versiones y no hay override: gana el nuevo."""
        vivo = pd.DataFrame(_registros_detalle())
        vivo.loc[1, "Pad"] = "Sulfuro"
        vivo.loc[1, "Pad_Original"] = "Sulfuro"

        salida = cb._fusionar_solo_comentarios_en_detalle_vivo(
            vivo, _registros_detalle()
        )

        self.assertEqual(salida.loc[1, "Pad"], "Sulfuro")

    def test_republicar_arrastra_el_override_guardado(self):
        """Regenerar el mes no debe perder un Pad ajustado en la version previa."""
        detalle_nuevo = pd.DataFrame(_registros_detalle())
        guardado = pd.DataFrame([
            {
                "Fecha": pd.Timestamp("2026-07-01"),
                "Turno": "TB",
                "Pad": "Óxido",
                "Pad_Original": "Sin clasificar",
            }
        ])
        previos = repo.comentarios_mapa_desde_dataframe(guardado)

        salida = repo._merge_comentarios_representatividad(detalle_nuevo, previos)

        self.assertEqual(list(salida["Pad"]), ["Sulfuro", "Óxido"])

    def test_republicar_sin_override_usa_el_derivado_fresco(self):
        detalle_nuevo = pd.DataFrame(_registros_detalle())
        detalle_nuevo.loc[1, "Pad"] = "Sulfuro"
        detalle_nuevo.loc[1, "Pad_Original"] = "Sulfuro"
        guardado = pd.DataFrame([
            {
                "Fecha": pd.Timestamp("2026-07-01"),
                "Turno": "TB",
                "Pad": "Sin clasificar",
                "Pad_Original": "Sin clasificar",
            }
        ])
        previos = repo.comentarios_mapa_desde_dataframe(guardado)

        salida = repo._merge_comentarios_representatividad(detalle_nuevo, previos)

        self.assertEqual(salida.loc[1, "Pad"], "Sulfuro")

    def test_pad_original_se_persiste(self):
        self.assertIn("Pad_Original", repo.RTO_DETALLE_COLUMNAS)
        registros = repo._registros_detalle_torre_oficial(
            pd.DataFrame(_registros_detalle())
        )
        self.assertEqual(registros[1]["Pad_Original"], "Sin clasificar")


class TestPadAutoria(unittest.TestCase):

    def test_ajuste_nuevo_sella_al_usuario_que_publica(self):
        detalle = pd.DataFrame(_registros_detalle())
        detalle.loc[1, "Pad"] = "Óxido"

        salida = repo._merge_comentarios_representatividad(
            detalle, {}, usuario="cramos",
        )

        self.assertEqual(salida.loc[1, "Pad_Ajustado_Por"], "cramos")
        # La fila sin ajuste no queda con autor.
        self.assertIsNone(salida.loc[0, "Pad_Ajustado_Por"])

    def test_republicar_conserva_al_autor_original(self):
        detalle = pd.DataFrame(_registros_detalle())
        detalle.loc[1, "Pad"] = "Óxido"
        guardado = pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TB",
            "Pad": "Óxido",
            "Pad_Original": "Sin clasificar",
            "Pad_Ajustado_Por": "jperez",
        }])
        previos = repo.comentarios_mapa_desde_dataframe(guardado)

        salida = repo._merge_comentarios_representatividad(
            detalle, previos, usuario="cramos",
        )

        self.assertEqual(salida.loc[1, "Pad_Ajustado_Por"], "jperez")

    def test_cambiar_el_ajuste_resella_al_autor(self):
        detalle = pd.DataFrame(_registros_detalle())
        detalle.loc[1, "Pad"] = "Sulfuro"
        guardado = pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TB",
            "Pad": "Óxido",
            "Pad_Original": "Sin clasificar",
            "Pad_Ajustado_Por": "jperez",
        }])
        previos = repo.comentarios_mapa_desde_dataframe(guardado)

        salida = repo._merge_comentarios_representatividad(
            detalle, previos, usuario="cramos",
        )

        self.assertEqual(salida.loc[1, "Pad"], "Sulfuro")
        self.assertEqual(salida.loc[1, "Pad_Ajustado_Por"], "cramos")

    def test_editar_en_sesion_borra_el_autor_hasta_publicar(self):
        vivo = pd.DataFrame(_registros_detalle())
        vivo.loc[1, "Pad"] = "Óxido"
        vivo.loc[1, "Pad_Ajustado_Por"] = "jperez"

        editor = _registros_detalle()
        editor[1]["Pad"] = "Sulfuro"

        salida = cb._fusionar_solo_comentarios_en_detalle_vivo(vivo, editor)

        self.assertEqual(salida.loc[1, "Pad"], "Sulfuro")
        # pandas deja NaN en columna object; lo que importa es que el autor
        # viejo desaparezca y que el INSERT lo mande como NULL.
        self.assertTrue(pd.isna(salida.loc[1, "Pad_Ajustado_Por"]))
        registros = repo._registros_detalle_torre_oficial(salida)
        self.assertIsNone(registros[1]["Pad_Ajustado_Por"])


class TestPadLlegaAlExport(unittest.TestCase):
    """
    El Excel se arma desde el snapshot y recalcula el Pad; el ajuste solo
    llega por ``mapa_comentarios``. Sin esto la tabla "Mineral apilado por
    Pad" ignora la edicion.
    """

    def _mapa(self, pad, original):
        return repo.comentarios_mapa_desde_dataframe(pd.DataFrame([{
            "Fecha": pd.Timestamp("2026-07-01"),
            "Turno": "TA",
            "Pad": pad,
            "Pad_Original": original,
        }]))

    def test_ajuste_viaja_al_export(self):
        mapa = self._mapa("Óxido", "Sulfuro")
        self.assertEqual(
            repo.pad_ajustado_para(mapa, pd.Timestamp("2026-07-01"), "TA"),
            "Óxido",
        )

    def test_sin_ajuste_no_pisa_al_derivado(self):
        mapa = self._mapa("Sulfuro", "Sulfuro")
        self.assertIsNone(
            repo.pad_ajustado_para(mapa, pd.Timestamp("2026-07-01"), "TA")
        )

    def test_turno_o_fecha_sin_registro_no_ajusta(self):
        mapa = self._mapa("Óxido", "Sulfuro")
        self.assertIsNone(
            repo.pad_ajustado_para(mapa, pd.Timestamp("2026-07-01"), "TB")
        )
        self.assertIsNone(
            repo.pad_ajustado_para(mapa, pd.Timestamp("2026-07-02"), "TA")
        )

    def test_historico_sin_pad_original_no_ajusta(self):
        """Filas previas al backfill: Pad_Original NULL no es un ajuste."""
        mapa = self._mapa("Sulfuro", None)
        self.assertIsNone(
            repo.pad_ajustado_para(mapa, pd.Timestamp("2026-07-01"), "TA")
        )


class TestTogglePad(unittest.TestCase):

    def test_alterna_entre_los_dos_validos(self):
        self.assertEqual(cb._alternar_pad("Óxido"), "Sulfuro")
        self.assertEqual(cb._alternar_pad("Sulfuro"), "Óxido")

    def test_sin_clasificar_entra_por_el_primero(self):
        self.assertEqual(cb._alternar_pad("Sin clasificar"), "Óxido")
        self.assertEqual(cb._alternar_pad(None), "Óxido")

    def test_ida_y_vuelta_deja_el_valor_calculado(self):
        """El toggle es su propio deshacer: dos clics vuelven al original."""
        original = "Sulfuro"
        self.assertEqual(cb._alternar_pad(cb._alternar_pad(original)), original)


class TestTooltipPad(unittest.TestCase):

    def test_sin_ajuste_no_hay_tooltip(self):
        fila = {"Pad": "Sulfuro", "Pad_Original": "Sulfuro"}
        self.assertEqual(cb._tooltip_pad_rep(fila), {})

    def test_tooltip_muestra_valor_anterior_y_autor(self):
        fila = {
            "Pad": "Óxido",
            "Pad_Original": "Sin clasificar",
            "Pad_Ajustado_Por": "jperez",
        }
        texto = cb._tooltip_pad_rep(fila)["Pad"]["value"]

        self.assertIn("Sin clasificar", texto)
        self.assertIn("jperez", texto)

    def test_tooltip_marca_el_ajuste_sin_publicar(self):
        fila = {"Pad": "Óxido", "Pad_Original": "Sulfuro", "Pad_Ajustado_Por": None}
        texto = cb._tooltip_pad_rep(fila)["Pad"]["value"]

        self.assertIn("Sulfuro", texto)
        self.assertIn("sin publicar", texto)


if __name__ == "__main__":
    unittest.main()
