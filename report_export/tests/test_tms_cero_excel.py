"""Un cero de tonelaje no equivale a un analito evaluable ni a un NULL."""
import numpy as np
import pandas as pd
import pytest

from report_export.report_export import (
    preparar_df_generador_reporte_excel,
    preparar_df_reporte_turno_excel,
)


@pytest.mark.parametrize("diario", [False, True])
@pytest.mark.parametrize("fecha", ["2026-09-02", "2026-09-11"])
@pytest.mark.parametrize("tms", [0.0, np.nan])
def test_cero_y_null_con_analitos_no_evaluables(diario, fecha, tms):
    sufijo = "_Dia" if diario else ""
    dependientes = ["STOCK", "MINA", "SRR", "CuT_Real", "CuS_Real",
                   "Solubilidad_Real", "CO3_Real", "CuFe_Real", "FeT_Real",
                   "FeS_Real", "ConsH_Real", "Malla_Menos_1_2_Real",
                   "Malla_Menos_100_Real", "CaolBeta_Real"]
    dependientes = [c + sufijo for c in dependientes]
    dependientes.append("Dosis_Acido_Ideal_Dia" if diario else "Dosis_Acido_Ideal_TM")
    tonelaje = "Apilado_TMS_Real" + sufijo
    df = pd.DataFrame({"Fecha": [fecha, fecha], "Turno": ["A", "B"],
                       tonelaje: [tms, tms], **{c: [1.0, 2.0] for c in dependientes}})
    original = df.copy(deep=True)
    preparar = preparar_df_generador_reporte_excel if diario else preparar_df_reporte_turno_excel
    resultado = preparar(df)
    if pd.isna(tms):
        assert resultado[tonelaje].isna().all()
    else:
        assert resultado[tonelaje].eq(0).all()
    assert resultado[dependientes].isna().all().all()
    pd.testing.assert_frame_equal(df, original)


@pytest.mark.parametrize("diario", [False, True])
def test_produccion_del_10_no_cambia(diario):
    if diario:
        datos = {"Apilado_TMS_Real_Dia": [68184.771], "CuT_Real_Dia": [0.552221],
                 "MINA_Dia": [0.0]}
        preparar = preparar_df_generador_reporte_excel
    else:
        datos = {"Apilado_TMS_Real": [34092.869, 34091.902],
                 "CuT_Real": [0.531817, 0.572627], "MINA": [0.0, 0.0],
                 "Fuente_Info_Quimica": ["IMP", "IMP"],
                 "Fuente_Info_Fisica": ["IMP", "IMP"], "Turno": ["A", "B"]}
        preparar = preparar_df_reporte_turno_excel
    df = pd.DataFrame(datos).assign(Fecha=pd.Timestamp("2026-09-10"))
    resultado = preparar(df)
    for columna in datos:
        assert resultado[columna].tolist() == df[columna].tolist()
