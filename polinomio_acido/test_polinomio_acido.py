from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from unittest.mock import MagicMock, patch
import math

from flask import Flask, session
import pandas as pd
import pytest

from . import db, panel


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "docs/migrations/polinomio_acido/001_dosis_acido_configuracion.sql"
CONSUMER_MIGRATION = ROOT / "docs/migrations/polinomio_acido/002_integrar_consumidores_polinomio_acido.sql"


def valores():
    return {
        "umbral_mineral": "0.25", "umbral_co3": "0.25",
        "tasa_minima": "14", "tasa_base": "11", "factor_co3": "15.51",
        "factor_cus_co3_sobre_025": "8.182", "tasa_base_co3_sobre_025": "18.99",
        "factor_co3_co3_sobre_025": "15.51", "factor_cus_mineral_oxido": "8.182",
        "tasa_basal_mineral_oxido": "18.99", "factor_co3_mineral_oxido": "15.51",
    }


def calcular_referencia(solubilidad, co3, cus):
    p = {k: float(v) for k, v in valores().items()}
    sol = 0 if solubilidad is None else solubilidad
    carbonato = 0 if co3 is None else co3
    if sol < p["umbral_mineral"]:
        resultado = (p["tasa_minima"] if carbonato <= p["umbral_co3"]
                     else p["tasa_base"] + p["factor_co3"] * carbonato)
    elif cus is None or cus <= 0:
        resultado = 0
    else:
        prueba = (p["factor_cus_co3_sobre_025"] * math.log(cus)
                  + p["tasa_base_co3_sobre_025"]
                  + p["factor_co3_co3_sobre_025"] * carbonato)
        resultado = (p["tasa_minima"] if prueba < p["tasa_minima"]
                     else p["factor_cus_mineral_oxido"] * math.log(cus)
                     + p["tasa_basal_mineral_oxido"]
                     + p["factor_co3_mineral_oxido"] * carbonato)
    return float(Decimal(str(resultado)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def test_validacion_contrato_completo_y_precision():
    result = db.validar_configuracion(valores(), " operador ", " comentario ")
    assert result["umbral_mineral"] == Decimal("0.250000")
    assert result["usuario_submit"] == "operador"
    assert result["comentario"] == "comentario"
    for field, value in [
        ("umbral_mineral", "1.1"), ("umbral_co3", "-0.1"),
        ("factor_co3", "1.1234567"), ("tasa_base", "NaN"),
    ]:
        invalid = {**valores(), field: value}
        with pytest.raises(ValueError):
            db.validar_configuracion(invalid, "operador")
    incomplete = valores()
    incomplete.pop("factor_co3")
    with pytest.raises(ValueError, match="Faltan parametros"):
        db.validar_configuracion(incomplete, "operador")
    with pytest.raises(ValueError, match="usuario autenticado"):
        db.validar_configuracion(valores(), None)


def test_insercion_es_unica_y_parametrizada():
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    select_result = MagicMock()
    select_result.scalar.return_value = 7
    insert_result = MagicMock()
    insert_result.mappings.return_value.one.return_value = {
        "configuracion_id": 8, "fecha_submit": "2026-10-07",
        "usuario_submit": "operador", "comentario": None,
    }
    conn.execute.side_effect = [select_result, insert_result]
    with patch.object(db, "_engine", return_value=engine):
        result = db.insertar_configuracion(valores(), "operador", None, 7)
    assert result["configuracion_id"] == 8
    assert conn.execute.call_count == 2
    sql = " ".join(str(call.args[0]) for call in conn.execute.call_args_list).upper()
    assert sql.count("INSERT INTO") == 1
    assert "UPDATE " not in sql and "DELETE " not in sql
    assert ":UMBRAL_MINERAL" in sql


def test_version_obsoleta_se_rechaza_antes_del_insert():
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    conn.execute.return_value.scalar.return_value = 9
    with patch.object(db, "_engine", return_value=engine):
        with pytest.raises(ValueError, match="cambio desde la revision"):
            db.insertar_configuracion(valores(), "operador", None, 7)
    assert conn.execute.call_count == 1


def test_confirmacion_conserva_usuario_y_payload_revisado():
    app = Flask(__name__)
    app.secret_key = "test-only"
    with app.test_request_context(), patch.object(db, "insertar_configuracion", return_value={
        "configuracion_id": 2, "fecha_submit": "2026-10-07",
        "usuario_submit": "operador", "comentario": "Cambio",
    }) as write:
        session["user"] = "operador"
        token, resumen = panel.preparar_confirmacion(valores(), "Cambio", 1)
        assert "reemplazará globalmente" in str(resumen)
        result = panel.confirmar_configuracion(token)
        assert result["configuracion_id"] == 2
        assert write.call_args.args[1] == "operador"
        assert write.call_args.args[3] == 1
        with pytest.raises(ValueError, match="confirmación no está vigente"):
            panel.confirmar_configuracion(token)


def test_historial_expandible_muestra_todas_las_versiones():
    base = {**valores(), "fecha_submit": "2026-10-07 10:00", "usuario_submit": "u",
            "comentario": None}
    frame = pd.DataFrame([{**base, "configuracion_id": 2}, {**base, "configuracion_id": 1}])
    rendered = str(panel.mostrar_historial(frame))
    assert "Versión 2" in rendered and "Versión 1" in rendered
    for _, etiqueta, _ in db.PARAMETROS:
        assert etiqueta in rendered



def test_comentarios_renderizan_ausentes_numericos_y_texto_en_historial_y_estado():
    valores_comentario = [None, float("nan"), pd.NA, 12.5, "Texto preservado"]
    for comentario in valores_comentario:
        registro = {
            **valores(), "configuracion_id": 2, "fecha_submit": "2026-10-07 10:00",
            "usuario_submit": "u", "comentario": comentario,
        }
        historial = str(panel.mostrar_historial(pd.DataFrame([registro])))
        vigente = str(panel._estado_vigente(registro))
        if comentario is None or (isinstance(comentario, float) and math.isnan(comentario)) or comentario is pd.NA:
            esperado = "Sin comentario"
        else:
            esperado = str(comentario)
        assert f"Comentario: {esperado}" in historial
        assert f"Comentario: {esperado}" in vigente


def test_esquema_coloreado_representa_funcion_completa_sin_redondear():
    parametros = {k: Decimal(v) for k, v in valores().items()}
    parametros["factor_co3"] = Decimal("15.510123")
    esquema = str(panel.construir_esquema(parametros))
    for fragmento in ("Mineral Sulfuro", "Mineral Óxido", "Rs < ",
                       "CO3 ≤ ", "0,25", "Ln(CuS)", "devuelve 0 kg/t",
                       "sin redondeo visual", "15,510123", "factor_co3",
                       "polinomio-chip umbral", "polinomio-chip minimo",
                       "polinomio-chip base", "polinomio-chip cus", "polinomio-chip co3",
                       "Editar Factor CO3", "polinomio-acido-factor_co3",
                       "Edición guiada", "P01", "P03", "P11",
                       "polinomio-chip-posicion"):
        assert fragmento in esquema
    assert esquema.index("Mineral Sulfuro") < esquema.index("Para CO3 ≤")
    assert esquema.index("Para CO3 ≤") < esquema.index("Para CO3 >")
    assert esquema.index("Para CO3 >") < esquema.index("Mineral Óxido")
    assert panel.numero_exacto(Decimal("0.250000")) == "0,25"
    assert panel.numero_exacto(Decimal("8.182345")) == "8,182345"


def test_campos_y_formula_comparten_codigo_de_posicion():
    for indice, nombre in enumerate(db.NOMBRES_PARAMETROS, start=1):
        codigo = f"P{indice:02d}"
        assert panel.POSICIONES_PARAMETROS[nombre] == codigo
        assert codigo in str(panel._campo(nombre, panel.ETIQUETAS_PARAMETROS[nombre]))


def test_esquema_controla_configuracion_incompleta():
    alerta = panel.actualizar_vista_funcion(*([None] * len(db.NOMBRES_PARAMETROS)))
    assert "Complete los 11 parámetros" in str(alerta)


def test_migracion_y_funcion_cubren_contrato_y_ramas():
    sql = MIGRATION.read_text(encoding="utf-8")
    upper = sql.upper()
    assert "IF OBJECT_ID" in upper and "IF NOT EXISTS" in upper
    assert "CREATE OR ALTER FUNCTION [INVENTAR_SPCHIDR].[FN_CALCULAR_DOSIS_ACIDO]" in upper
    assert "ORDER BY CONFIGURACION_ID DESC" in upper
    assert "IF @CONFIGURACION_ID IS NULL RETURN NULL" in upper
    assert "WHEN @CUS IS NULL OR @CUS <= 0 THEN 0.0" in upper
    assert "MIGRACION_INICIAL" in upper
    for nombre in db.NOMBRES_PARAMETROS:
        assert nombre in sql

    assert calcular_referencia(None, None, None) == 14.00
    assert calcular_referencia(0.10, 0.50, 1) == 18.76
    assert calcular_referencia(0.50, 0.20, None) == 0.00
    assert calcular_referencia(0.50, 0.20, -1) == 0.00
    assert calcular_referencia(0.50, 0.00, 0.10) == 14.00
    assert calcular_referencia(0.50, 0.20, 1.00) == 22.09


def test_migracion_conecta_los_dos_consumidores_con_la_funcion_centralizada():
    sql = CONSUMER_MIGRATION.read_text(encoding="utf-8-sig")
    assert "USE [inventar_SpcHidr_PROD]" in sql
    assert "CREATE OR ALTER FUNCTION [inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]" in sql
    assert "CREATE OR ALTER PROCEDURE [inventar_SpcHidr].[sp_reporte_turno_emision_test]" in sql
    assert ");\nGO\n\n/****** Objeto: StoredProcedure" in sql.replace("\r\n", "\n")
    assert sql.count("[inventar_SpcHidr].[fn_calcular_dosis_acido]") == 6
    for alias in (
        "Dosis_Acido_Ideal_Dia",
        "Dosis_Acido_Ideal_TM",
        "Dosis_Acido_Programa_Semanal",
    ):
        assert alias in sql
    assert "CAST(pr.CuS_Programa / NULLIF(pr.CuT_Programa, 0) AS DECIMAL(18,6))" in sql
    assert "CAST(ISNULL(ps.Solubilidad_Plan_Semanal, 0) AS DECIMAL(18,6))" in sql


def test_sidebar_monta_modulo_sin_conectarlo_a_consumidores():
    layout_source = (ROOT / "layout.py").read_text(encoding="utf-8")
    assert "nav-polinomio-acido" in layout_source
    assert "subtabs-polinomio-acido" in layout_source
    for folder in ("report_export", "callbacks", "reclamo", "monitor_pi_tum", "lixiviacion"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix in {".py", ".sql"}:
                content = path.read_text(encoding="utf-8", errors="ignore")
                assert "fn_calcular_dosis_acido" not in content
                assert "dosis_acido_configuracion" not in content
