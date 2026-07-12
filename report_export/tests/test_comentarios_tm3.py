import json
import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from report_export import report_export as repo
from report_export.callbacks import reportabilidad_cb as cb


COMENTARIOS = {
    "Comentario_TM1_Quimico": "hist q1",
    "Comentario_TM2_Quimico": "hist q2",
    "Comentario_TM3_Quimico": "hist q3",
    "Comentario_TM1_Fisico": "hist f1",
    "Comentario_TM2_Fisico": "hist f2",
    "Comentario_TM3_Fisico": "hist f3",
}


def _detalle_vivo() -> pd.DataFrame:
    filas = []
    for fecha, turno, base in (
        ("2026-07-01", "TA", 100.0),
        ("2026-07-01", "TB", 200.0),
    ):
        fila = {
            "Fecha": pd.Timestamp(fecha),
            "Turno": turno,
            "Semana": "Semana 1",
            "Pad": "Sulfuro",
            "TMH_CV08": base + 8,
            "TMH_CV108": base + 108,
            "TMH_CV01": base + 1,
            "TM1_Activo": 1,
            "TM2_Activo": 1,
            "TM3_Activo": 1,
            "Rep_TM1_Quimico": 0,
            "Rep_TM2_Quimico": 1,
            "Rep_TM3_Quimico": 0,
            "Rep_TM1_Fisico": 0,
            "Rep_TM2_Fisico": 0,
            "Rep_TM3_Fisico": 0,
            "Rep_Turno_Quimico": 1,
            "Rep_Turno_Fisico": 0,
        }
        fila.update(COMENTARIOS)
        filas.append(fila)
    return pd.DataFrame(filas)


def _detalle_julio_nullable() -> pd.DataFrame:
    filas = []
    for indice in range(62):
        fila = _detalle_vivo().iloc[0].to_dict()
        fila["Fecha"] = pd.Timestamp("2026-07-01") + pd.Timedelta(
            days=indice // 2
        )
        fila["Turno"] = "TA" if indice % 2 == 0 else "TB"
        fila["TMH_CV01"] = 100.0 if indice < 16 else None
        fila["TM3_Activo"] = (
            1 if indice < 15
            else 0 if indice < 20
            else pd.NA
        )
        fila["Rep_TM3_Quimico"] = 0 if indice < 15 else None
        fila["Rep_TM3_Fisico"] = 0 if indice < 15 else None
        filas.append(fila)
    return pd.DataFrame(filas)


class EditorComentariosTM3Tests(unittest.TestCase):
    def test_columnas_por_tab_incluyen_tm3(self):
        self.assertEqual(
            cb._rep_cols_por_tab("quimico")["rep_tm3"],
            "Rep_TM3_Quimico",
        )
        self.assertEqual(
            cb._rep_cols_por_tab("quimico")["com_tm3"],
            "Comentario_TM3_Quimico",
        )
        self.assertEqual(
            cb._rep_cols_por_tab("fisico")["rep_tm3"],
            "Rep_TM3_Fisico",
        )
        self.assertEqual(
            cb._rep_cols_por_tab("fisico")["com_tm3"],
            "Comentario_TM3_Fisico",
        )

    def test_grilla_tm3_cambia_con_pestana_y_no_convierte_null_en_cero(self):
        detalle = _detalle_vivo().iloc[[0]].copy()
        detalle.loc[detalle.index[0], "Rep_TM3_Quimico"] = 1
        detalle.loc[detalle.index[0], "Rep_TM3_Fisico"] = 0
        detalle.loc[detalle.index[0], "Comentario_TM3_Quimico"] = "químico"
        detalle.loc[detalle.index[0], "Comentario_TM3_Fisico"] = "físico"

        quimico = cb._df_a_grilla_rep(detalle, "quimico").iloc[0]
        fisico = cb._df_a_grilla_rep(detalle, "fisico").iloc[0]

        self.assertEqual(quimico["TMH_CV01"], 101.0)
        self.assertEqual(quimico["Rep_TM3"], "Representativo")
        self.assertEqual(quimico["Comentario_TM3"], "químico")
        self.assertEqual(fisico["Rep_TM3"], "No representativo")
        self.assertEqual(fisico["Comentario_TM3"], "físico")

        detalle.loc[detalle.index[0], "Rep_TM3_Fisico"] = None
        self.assertEqual(
            cb._df_a_grilla_rep(detalle, "fisico").iloc[0]["Rep_TM3"],
            "",
        )

    def test_grilla_visual_contiene_tercer_bloque_editable(self):
        componente = cb._grilla_comentarios_representatividad(
            cb._df_a_grilla_rep(_detalle_vivo(), "quimico")
        )
        columnas = {columna["id"]: columna for columna in componente.columns}

        self.assertEqual(
            columnas["TMH_CV01"]["name"][0],
            "Torre de muestreo #3 / SRR",
        )
        self.assertFalse(columnas["TMH_CV01"]["editable"])
        self.assertFalse(columnas["Rep_TM3"]["editable"])
        self.assertTrue(columnas["Comentario_TM3"]["editable"])

    def test_editor_conserva_tmh_cv01_no_evaluable_desde_fuente_viva(self):
        detalle = _detalle_vivo().iloc[[0]].copy()
        detalle.loc[detalle.index[0], "TM3_Activo"] = 0
        detalle.loc[detalle.index[0], "TMH_CV01"] = None
        fuente = pd.DataFrame(
            {
                "Fecha": [pd.Timestamp("2026-07-01")],
                "Apilado TMH CV-01 TA": [565.0],
                "Apilado TMH CV-01 TB": [None],
            }
        )

        completo = cb._completar_tm3_editor_desde_fuente_viva(
            detalle,
            fuente,
        )
        self.assertEqual(completo.iloc[0]["TMH_CV01"], 565.0)

    def test_preparacion_mantiene_tm3_activo_triestado(self):
        fuente = pd.DataFrame(
            {
                "Fecha": [pd.Timestamp("2026-07-01")],
                "Evaluable_TM3_TA": [0],
                "Evaluable_TM3_TB": [None],
                "Apilado TMH CV-01 TA": [565.0],
                "Apilado TMH CV-01 TB": [None],
            }
        )
        detalle = cb._preparar_detalle_mensual_torres(
            df_bd_ton=fuente,
            tipo="quimico",
            df_material_turno=pd.DataFrame(),
            fecha_inicio_mes=date(2026, 7, 1),
            fecha_fin_mes=date(2026, 7, 2),
            fecha_corte_operacional=date(2026, 7, 1),
        )

        self.assertEqual(len(detalle[detalle["TM3_Activo"] == 0]), 1)
        self.assertEqual(len(detalle[detalle["TM3_Activo"].isna()]), 3)
        self.assertEqual(len(detalle[detalle["TM3_Activo"] == 1]), 0)

    def test_cambio_de_pestana_conserva_ambos_comentarios_tm3(self):
        almacenado = _detalle_vivo().iloc[[0]].copy()
        almacenado["Fecha"] = almacenado["Fecha"].dt.strftime("%Y-%m-%d")
        registros = almacenado.to_dict("records")
        quimico = cb._df_a_grilla_rep(pd.DataFrame(registros), "quimico")
        quimico.loc[0, "Comentario_TM3"] = "edición química"
        registros = cb._fusionar_comentarios_grilla(
            registros,
            quimico.to_dict("records"),
            "quimico",
        )

        fisico = cb._df_a_grilla_rep(pd.DataFrame(registros), "fisico")
        self.assertEqual(fisico.loc[0, "Comentario_TM3"], "hist f3")
        fisico.loc[0, "Comentario_TM3"] = "edición física"
        registros = cb._fusionar_comentarios_grilla(
            registros,
            fisico.to_dict("records"),
            "fisico",
        )

        self.assertEqual(
            registros[0]["Comentario_TM3_Quimico"],
            "edición química",
        )
        self.assertEqual(
            registros[0]["Comentario_TM3_Fisico"],
            "edición física",
        )

    def test_comentario_vacio_no_borra_historico(self):
        registros = _detalle_vivo().iloc[[0]].to_dict("records")
        grilla = cb._df_a_grilla_rep(pd.DataFrame(registros), "quimico")
        grilla.loc[0, "Comentario_TM3"] = "   "
        fusionados = cb._fusionar_comentarios_grilla(
            registros,
            grilla.to_dict("records"),
            "quimico",
        )
        self.assertEqual(
            fusionados[0]["Comentario_TM3_Quimico"],
            "hist q3",
        )


class PublicacionSeguraTM3Tests(unittest.TestCase):
    def test_nullable_int_sql_convierte_solo_a_int_o_none(self):
        self.assertIsNone(repo._nullable_int_sql(None))
        self.assertIsNone(repo._nullable_int_sql(pd.NA))
        self.assertIsNone(repo._nullable_int_sql(float("nan")))
        self.assertEqual(repo._nullable_int_sql(0.0), 0)
        self.assertEqual(repo._nullable_int_sql(1.0), 1)
        self.assertIs(type(repo._nullable_int_sql(0.0)), int)
        self.assertIs(type(repo._nullable_int_sql(1.0)), int)

    def test_solo_comentarios_provienen_del_editor(self):
        vivo = _detalle_vivo()
        editor = vivo.copy()
        editor.loc[0, "TMH_CV01"] = 999999
        editor.loc[0, "TM3_Activo"] = 0
        editor.loc[0, "Rep_TM3_Quimico"] = 1
        editor.loc[0, "Comentario_TM3_Quimico"] = "nuevo q3"
        editor.loc[0, "Comentario_TM3_Fisico"] = "nuevo f3"

        final = cb._fusionar_solo_comentarios_en_detalle_vivo(vivo, editor)

        pd.testing.assert_frame_equal(
            final[list(cb._COLUMNAS_METRICAS_VIVAS_REP)],
            vivo[list(cb._COLUMNAS_METRICAS_VIVAS_REP)],
        )
        self.assertEqual(final.loc[0, "Comentario_TM3_Quimico"], "nuevo q3")
        self.assertEqual(final.loc[0, "Comentario_TM3_Fisico"], "nuevo f3")

    def test_validacion_julio_usa_conteos_calculados(self):
        julio = _detalle_julio_nullable()

        esperado = {
            "filas": 62,
            "TMH_CV01_no_nulo": 16,
            "TM3_Activo_1": 15,
            "TM3_Activo_0": 5,
            "TM3_Activo_NULL": 42,
            "Rep_TM3_Quimico_no_nulo": 15,
            "Rep_TM3_Fisico_no_nulo": 15,
        }
        self.assertEqual(cb._validar_detalle_publicacion_rep(julio), esperado)

        # Reproduce dcc.Store: pandas NA/NaN -> None -> JSON null.
        almacenado = julio.copy()
        almacenado["Fecha"] = almacenado["Fecha"].dt.strftime("%Y-%m-%d")
        records_store = (
            almacenado.astype(object)
            .where(pd.notna(almacenado), None)
            .to_dict("records")
        )
        records_store = json.loads(json.dumps(records_store))
        self.assertEqual(
            sum(fila["TM3_Activo"] is None for fila in records_store),
            42,
        )

        # El merge de comentarios conserva la semántica triestado.
        final = cb._fusionar_solo_comentarios_en_detalle_vivo(
            julio,
            records_store,
        )
        self.assertEqual(cb._validar_detalle_publicacion_rep(final), esperado)

        # Estos son exactamente los parámetros que recibe execute(insert_det).
        parametros = repo._registros_detalle_torre_oficial(final)
        self.assertEqual(repo._resumen_parametros_tm3(parametros), esperado)
        self.assertEqual(
            sum(fila["TM3_Activo"] is None for fila in parametros),
            42,
        )

    def test_writer_entrega_42_none_al_execute_insert_det(self):
        julio = _detalle_julio_nullable()
        capturados = []

        class ResultadoFalso:
            def scalar(self):
                return 1

        class ConexionFalsa:
            def execute(self, sentencia, parametros=None):
                if isinstance(parametros, dict) and "TM3_Activo" in parametros:
                    capturados.append(dict(parametros))
                return ResultadoFalso()

        class ContextoFalso:
            def __enter__(self):
                return ConexionFalsa()

            def __exit__(self, exc_type, exc, traceback):
                return False

        class MotorFalso:
            def begin(self):
                return ContextoFalso()

        paquete = {
            "fecha_corte_operacional": date(2026, 7, 10),
            "anio_fiscal": 2027,
        }
        with (
            patch.object(
                repo,
                "fetch_reporte_torre_oficial_detalle",
                return_value=pd.DataFrame(),
            ),
            patch.object(repo, "_get_engine", return_value=MotorFalso()),
            patch.object(repo, "_siguiente_id_reporte_torre_oficial", return_value=99),
        ):
            repo.write_reporte_torre_oficial(
                df_detalle=julio,
                periodo_inicio=date(2026, 7, 1),
                periodo_fin=date(2026, 7, 31),
                usuario="prueba",
                paquete=paquete,
            )

        esperado = {
            "filas": 62,
            "TMH_CV01_no_nulo": 16,
            "TM3_Activo_1": 15,
            "TM3_Activo_0": 5,
            "TM3_Activo_NULL": 42,
            "Rep_TM3_Quimico_no_nulo": 15,
            "Rep_TM3_Fisico_no_nulo": 15,
        }
        self.assertEqual(repo._resumen_parametros_tm3(capturados), esperado)
        self.assertEqual(
            {type(fila["TM3_Activo"]) for fila in capturados},
            {int, type(None)},
        )

    def test_publicar_reconstruye_fuente_viva_antes_del_writer(self):
        vivo = _detalle_vivo()
        registros = vivo.copy()
        registros.loc[0, "TMH_CV01"] = 999999
        registros.loc[0, "TM3_Activo"] = 0
        registros.loc[0, "Rep_TM3_Quimico"] = 1
        registros["Fecha"] = registros["Fecha"].dt.strftime("%Y-%m-%d")
        registros = registros.to_dict("records")
        grilla = cb._df_a_grilla_rep(pd.DataFrame(registros), "quimico")
        grilla.loc[0, "Comentario_TM3"] = "publicado q3"
        periodo = {
            "inicio": "2026-07-01",
            "fin": "2026-07-31",
            "modo": "mes",
            "periodo_mes": "2026-07",
        }

        with (
            patch.object(cb, "mes_tiene_reporte_activo", return_value=False),
            patch.object(
                cb,
                "armar_paquete_reporte_torre_oficial",
                return_value={"fecha_corte_operacional": date(2026, 7, 9)},
            ),
            patch.object(
                cb,
                "_cargar_detalle_representatividad_periodo",
                return_value=(vivo.copy(), date(2026, 7, 9)),
            ),
            patch.object(cb, "write_reporte_torre_oficial") as writer,
            patch.object(cb, "fetch_historial_reporte_torre_oficial", return_value=pd.DataFrame()),
        ):
            resultado = cb.publicar_reporte_representatividad(
                1,
                registros,
                periodo,
                "quimico",
                grilla.to_dict("records"),
                "mes",
            )

        self.assertIn("Reporte de Julio 2026 generado", resultado[0])
        guardado = writer.call_args.kwargs["df_detalle"]
        self.assertEqual(guardado.loc[0, "TMH_CV01"], vivo.loc[0, "TMH_CV01"])
        self.assertEqual(guardado.loc[0, "TM3_Activo"], vivo.loc[0, "TM3_Activo"])
        self.assertEqual(
            guardado.loc[0, "Rep_TM3_Quimico"],
            vivo.loc[0, "Rep_TM3_Quimico"],
        )
        self.assertEqual(
            guardado.loc[0, "Comentario_TM3_Quimico"],
            "publicado q3",
        )
        self.assertEqual(
            guardado.loc[0, "Comentario_TM3_Fisico"],
            "hist f3",
        )

    def test_writer_rechaza_columnas_tm3_faltantes_antes_de_bd(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "No se puede publicar: faltan columnas TM3",
        ):
            repo.write_reporte_torre_oficial(
                df_detalle=pd.DataFrame([{"Fecha": "2026-07-01", "Turno": "TA"}]),
                periodo_inicio=date(2026, 7, 1),
                periodo_fin=date(2026, 7, 31),
                usuario="prueba",
                paquete={"fecha_corte_operacional": date(2026, 7, 9)},
            )

    def test_merge_writer_preserva_historico_tm3(self):
        vivo = _detalle_vivo().iloc[[0]].copy()
        vivo.loc[vivo.index[0], "Comentario_TM3_Quimico"] = ""
        clave = (pd.Timestamp("2026-07-01"), "TA")
        final = repo._merge_comentarios_representatividad(
            vivo,
            {clave: {"Comentario_TM3_Quimico": "histórico BD"}},
        )
        self.assertEqual(
            final.iloc[0]["Comentario_TM3_Quimico"],
            "histórico BD",
        )

    def test_roundtrip_local_persistencia_y_reapertura_tm3(self):
        vivo = _detalle_vivo().iloc[[0]].copy()
        editor = vivo.copy()
        editor.loc[editor.index[0], "Comentario_TM3_Quimico"] = "persistido q"
        editor.loc[editor.index[0], "Comentario_TM3_Fisico"] = "persistido f"
        final = cb._fusionar_solo_comentarios_en_detalle_vivo(vivo, editor)

        registros_sql = repo._registros_detalle_torre_oficial(final)
        reabierto = pd.DataFrame(registros_sql)
        self.assertEqual(reabierto.loc[0, "TMH_CV01"], vivo.iloc[0]["TMH_CV01"])
        self.assertEqual(reabierto.loc[0, "TM3_Activo"], 1)
        self.assertEqual(reabierto.loc[0, "Rep_TM3_Quimico"], 0)
        self.assertEqual(reabierto.loc[0, "Rep_TM3_Fisico"], 0)
        self.assertEqual(
            reabierto.loc[0, "Comentario_TM3_Quimico"],
            "persistido q",
        )
        self.assertEqual(
            reabierto.loc[0, "Comentario_TM3_Fisico"],
            "persistido f",
        )

        mapa = repo.comentarios_mapa_desde_dataframe(reabierto)
        fresco = vivo.copy()
        fresco["Comentario_TM3_Quimico"] = None
        fresco["Comentario_TM3_Fisico"] = None
        recargado = repo._merge_comentarios_representatividad(fresco, mapa)
        self.assertEqual(
            cb._df_a_grilla_rep(recargado, "quimico").loc[0, "Comentario_TM3"],
            "persistido q",
        )
        self.assertEqual(
            cb._df_a_grilla_rep(recargado, "fisico").loc[0, "Comentario_TM3"],
            "persistido f",
        )


if __name__ == "__main__":
    unittest.main()
