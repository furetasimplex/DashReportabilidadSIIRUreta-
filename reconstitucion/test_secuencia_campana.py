"""Excepciones del reparto secuencial: una sola rotopala, datos faltantes y modulos detenidos."""
import numpy as np
import pandas as pd
import pytest

from reconstitucion.secuencia_campana import TMH_DIA_MAX, chain_targets, despachar

SU, OX = (2, 13, 12), (1, 18, 18)


def _hist(filas):
    """filas: (dia, destino, modulo, volumen, estimado)"""
    return pd.DataFrame([dict(fecha=pd.Timestamp(d), pad_id=t[0], campana_id=t[1], campana=t[2],
                              modulo_id=m, modulo=m, vol_diario=float(v), vol_total_est=float(e))
                         for d, t, m, v, e in filas])


def _conc(filas):
    """filas: (dia, etiqueta, A, B, TMS)"""
    return pd.DataFrame([dict(fecha=pd.Timestamp(d), etiqueta=e, tmh_a=a, tmh_b=b, tms=s)
                         for d, e, a, b, s in filas])


def _tipos(exc):
    return set(exc.tipo)


def test_una_rotopala_llena_turnos_en_orden_y_no_reparte_cada_turno():
    # Venia en SU, termina en OX: 75 % SU primero. No es 75/25 en cada turno.
    h = _hist([("2026-08-04", SU, 1, 100, 100), ("2026-08-05", SU, 1, 75, 100),
               ("2026-08-05", OX, 9, 25, 100), ("2026-08-06", OX, 9, 100, 100)])
    d = _conc([("2026-08-05", "Oxido", 50.0, 50.0, 95.0)])
    desp, exc = despachar(d, h, "2026-08-06")
    dia = desp.set_index(["turno", "pad_id"]).tmh
    assert dia[("A", 2)] == pytest.approx(50.0)
    assert dia[("B", 2)] == pytest.approx(25.0)
    assert dia[("B", 1)] == pytest.approx(25.0)
    assert ("A", 1) not in dia.index
    assert desp.tmh.sum() == pytest.approx(100.0)
    assert desp.tms.sum() == pytest.approx(95.0)
    assert "DIA_DOS_PAD" in _tipos(exc)


def test_orden_inverso_cuando_venia_en_oxido():
    h = _hist([("2026-08-04", OX, 9, 100, 100), ("2026-08-05", OX, 9, 25, 100),
               ("2026-08-05", SU, 1, 75, 100), ("2026-08-06", SU, 1, 100, 100)])
    desp, _ = despachar(_conc([("2026-08-05", "Sulfuro", 50.0, 50.0, 95.0)]), h, "2026-08-06")
    dia = desp.set_index(["turno", "pad_id"]).tmh
    assert dia[("A", 1)] == pytest.approx(25.0)
    assert dia[("A", 2)] == pytest.approx(25.0)
    assert dia[("B", 2)] == pytest.approx(50.0)


def test_masa_imposible_se_excluye_y_se_informa():
    h = _hist([("2026-01-07", SU, 1, 100, 100)])
    desp, exc = despachar(_conc([("2026-01-07", "Sulfuro", TMH_DIA_MAX + 1, 0.0, 0.0)]), h, "2026-01-07")
    assert desp.empty
    assert "MASA_IMPOSIBLE" in _tipos(exc)


def test_masa_sin_volumen_usa_etiqueta_y_sin_etiqueta_no_se_asigna():
    h = _hist([("2026-08-14", SU, 1, 100, 100), ("2026-08-14", OX, 9, 1, 100)])
    d = _conc([("2026-08-15", "Sulfuro", 10.0, 10.0, 19.0), ("2026-08-16", "", 7.0, 7.0, 13.0)])
    desp, exc = despachar(d, h, "2026-08-16")
    assert desp.pad_id.unique().tolist() == [2]
    assert desp.tmh.sum() == pytest.approx(20.0)
    sin = exc.loc[exc.tipo.eq("MASA_SIN_DESTINO")]
    assert sin.tmh.sum() == pytest.approx(14.0)
    assert "MASA_SIN_VOLUMEN" in _tipos(exc)


def test_ceros_y_ausencias_no_inventan_masa():
    h = _hist([("2026-08-01", SU, 1, 100, 100), ("2026-08-02", SU, 1, 50, 100)])
    d = _conc([("2026-08-01", "Sulfuro", np.nan, np.nan, 20.0)])
    desp, exc = despachar(d, h, "2026-08-02")
    assert desp.empty
    assert {"TMS_SIN_TMH", "VOLUMEN_SIN_MASA"} <= _tipos(exc)


def test_tmh_sin_tms_conserva_tmh_e_informa():
    h = _hist([("2026-08-01", SU, 1, 100, 100)])
    desp, exc = despachar(_conc([("2026-08-01", "Sulfuro", 10.0, 0.0, np.nan)]), h, "2026-08-01")
    assert desp.tmh.sum() == pytest.approx(10.0)
    assert desp.tms.sum() == 0.0
    assert "TMH_SIN_TMS" in _tipos(exc)


def _supply(filas):
    return pd.DataFrame([dict(fecha=pd.Timestamp(d), tmh=float(w)) for d, w in filas])


def test_abierto_usa_volumen_real_y_cerrado_el_estimado():
    h = _hist([("2026-09-01", SU, 1, 100, 100), ("2026-09-02", SU, 2, 50, 100)])
    fijo, abierto, log = chain_targets(_supply([("2026-09-01", 150), ("2026-09-02", 75)]), h, [], "2026-09-02")
    assert abierto == 2
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(225 / 150)
    assert fijo == {1: pytest.approx(150.0)}


def test_lo_fijado_en_un_corte_no_cambia_en_el_siguiente():
    h = _hist([("2026-09-01", SU, 1, 100, 100), ("2026-09-02", SU, 2, 50, 100),
               ("2026-09-08", SU, 2, 50, 100), ("2026-09-09", SU, 3, 40, 100)])
    s = _supply([("2026-09-01", 150), ("2026-09-02", 75), ("2026-09-08", 100), ("2026-09-09", 80)])
    fijo, abierto, log = chain_targets(s, h, ["2026-09-02"], "2026-09-09")
    assert fijo[1] == pytest.approx(150.0)
    assert abierto == 3
    assert log[-1]["density_tmh_per_m3"] == pytest.approx((405 - 150) / 140)


def test_estimado_posterior_al_corte_no_se_usa():
    h = _hist([("2026-09-01", SU, 1, 100, 100), ("2026-09-02", SU, 2, 50, 100),
               ("2026-09-20", SU, 1, 0, 400)])
    fijo, _, _ = chain_targets(_supply([("2026-09-01", 150), ("2026-09-02", 75)]), h, [], "2026-09-02")
    assert fijo[1] == pytest.approx(150.0)


def test_abierto_detenido_no_se_reprecia_al_reanudar_con_otro_modulo():
    # Caso M31/M33 de oxidos: M1 queda detenido; al reanudar, M2 se lleva solo su masa.
    h = _hist([("2026-05-05", OX, 1, 100, 200), ("2026-08-05", OX, 2, 40, 100)])
    s = _supply([("2026-05-05", 130), ("2026-08-05", 80)])
    fijo, abierto, log = chain_targets(s, h, ["2026-07-07"], "2026-08-05")
    assert fijo[1] == pytest.approx(130.0)
    assert abierto == 2
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(80 / 40)


def test_hueco_de_volumen_conserva_el_estimado_del_detenido():
    # Caso M129: su volumen faltante cae despues de su ultimo dia registrado.
    h = _hist([("2026-08-14", SU, 1, 50, 100), ("2026-08-19", SU, 2, 100, 100)])
    s = _supply([("2026-08-14", 90), ("2026-08-16", 90), ("2026-08-19", 180)])
    fijo, _, log = chain_targets(s, h, ["2026-08-14"], "2026-08-19", ["2026-08-16"])
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(360 / 200)
    assert fijo[1] == pytest.approx(180.0)


def test_modulo_abandonado_pesa_por_volumen_real():
    # Contrato R1: el cerrado sin volumen el dia del corte pesa por su volumen real (ya no hay umbral de abandono).
    h = _hist([("2026-05-01", SU, 1, 50, 100), ("2026-05-02", SU, 2, 100, 100), ("2026-05-20", SU, 3, 50, 100)])
    s = _supply([("2026-05-01", 90), ("2026-05-02", 180), ("2026-05-20", 90)])
    fijo, abierto, log = chain_targets(s, h, [], "2026-05-20")
    assert abierto == 3
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(360 / 200)
    assert fijo[1] == pytest.approx(90.0)
    assert fijo[2] == pytest.approx(180.0)


def test_dia_sin_masa_ni_volumen_se_informa_y_cero_explicito_no():
    h = _hist([("2026-08-01", SU, 1, 100, 100), ("2026-08-04", SU, 1, 50, 100)])
    d = _conc([("2026-08-01", "Sulfuro", 10.0, 10.0, 19.0), ("2026-08-02", "", 0.0, 0.0, 0.0),
               ("2026-08-04", "Sulfuro", 5.0, 5.0, 9.0)])
    desp, exc = despachar(d, h, "2026-08-04")
    dias = exc.loc[exc.tipo.eq("DIA_SIN_DATOS"), "fecha"].tolist()
    assert dias == [pd.Timestamp("2026-08-03")]
    assert desp.tmh.sum() == pytest.approx(30.0)


def test_volumen_sin_masa_sale_de_densidad_y_meta():
    # Falla de masa: 50 m3 de M1 sin masa. La densidad no se diluye con ese volumen.
    h = _hist([("2026-09-01", SU, 1, 50, 100), ("2026-09-02", SU, 1, 50, 100), ("2026-09-03", SU, 2, 40, 100)])
    s = _supply([("2026-09-01", 90), ("2026-09-03", 72)])
    fijo, _, log = chain_targets(s, h, [], "2026-09-03", (), ["2026-09-02"])
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(162 / 90)
    assert fijo[1] == pytest.approx(90.0)


def test_campana_sin_masa_ni_volumen_utilizable_falla_con_mensaje():
    h = _hist([("2026-09-01", SU, 1, 50, 100)])
    from reconstitucion.recalibracion_mr import RecalibrationError
    with pytest.raises(RecalibrationError, match="masa y volumen"):
        chain_targets(_supply([]).assign(fecha=pd.to_datetime([]), tmh=[]), h, [], "2026-09-01", (), ["2026-09-01"])


# --- regla de volumen R1 de los modulos cerrados (sin umbrales de abandono)

def test_r1_cerrado_sin_volumen_el_dia_del_corte_usa_el_real():
    h = _hist([("2026-09-01", SU, 1, 60, 100), ("2026-09-02", SU, 2, 50, 100)])
    fijo, _, log = chain_targets(_supply([("2026-09-01", 90), ("2026-09-02", 75)]), h, [], "2026-09-02")
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(165 / 110)   # 60 reales + 50 del abierto
    assert fijo[1] == pytest.approx(90.0)


def test_r1_en_curso_con_volumen_el_dia_del_corte_usa_el_estimado():
    h = _hist([("2026-09-01", SU, 1, 60, 100), ("2026-09-02", SU, 1, 10, 100), ("2026-09-02", SU, 2, 50, 100)])
    fijo, _, log = chain_targets(_supply([("2026-09-01", 90), ("2026-09-02", 75)]), h, [], "2026-09-02")
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(165 / 150)   # estimado 100 + 50 del abierto
    assert fijo[1] == pytest.approx(110.0)


def test_r1_hueco_de_topografia_entre_su_inicio_y_el_siguiente_usa_el_estimado():
    h = _hist([("2026-09-01", SU, 1, 60, 100), ("2026-09-03", SU, 2, 50, 100)])
    fijo, _, log = chain_targets(_supply([("2026-09-01", 90), ("2026-09-02", 30), ("2026-09-03", 45)]), h, [], "2026-09-03",
                                 ["2026-09-02"])
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(165 / 150)
    assert fijo[1] == pytest.approx(110.0)


def test_r1_no_tiene_umbrales_de_abandono():
    # Real 95 % del estimado y 10 dias detenido: antes (umbral 90 %) pesaba el estimado; ahora pesa el real.
    import reconstitucion.secuencia_campana as sc
    assert not hasattr(sc, "ABANDONO_DIAS") and not hasattr(sc, "ABANDONO_FRACCION")
    h = _hist([("2026-09-01", SU, 1, 95, 100), ("2026-09-12", SU, 2, 50, 100)])
    fijo, _, log = chain_targets(_supply([("2026-09-01", 190), ("2026-09-12", 100)]), h, [], "2026-09-12")
    assert log[-1]["density_tmh_per_m3"] == pytest.approx(290 / 145)
    assert fijo[1] == pytest.approx(190.0)
