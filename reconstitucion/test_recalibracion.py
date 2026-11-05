"""Reconstitucion por densidad humeda recalibrada: invariantes de la especificacion.

docs/METODOLOGIA_RECONSTITUCION_DENSIDAD_RECALIBRADA.md (secciones 8-14).
Sin SQL: todas las fuentes se simulan y Engine.connect queda bloqueado.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    from . import (recalibracion as rc, recalibracion_caso as rcc, recalibracion_db as rdb,
                   engine, modelo_flujos as mf, db_source, panel, informe_modulos as im,
                   presentacion)
except ImportError:  # pragma: no cover
    from reconstitucion import (recalibracion as rc, recalibracion_caso as rcc,
                                recalibracion_db as rdb, engine, modelo_flujos as mf,
                                db_source, panel, informe_modulos as im, presentacion)

MR = APP / "test_fixtures" / "referencias" / "Control_MR_septiembre.xlsx"


# ------------------------------------------------------------- seccion 8

def test_densidad_formula_y_casos_particulares():
    assert rc.densidad_recalibrada(1480960.0, 0.0, 800692.806) == pytest.approx(
        1.8495982341, rel=1e-9)                       # Caso 10013, seccion 15
    assert rc.densidad_recalibrada(1000., 400., 300.) == pytest.approx(2.0)
    assert rc.densidad_recalibrada(1000., 1000., 0.) is None   # todo fijado y cierra
    assert rc.densidad_recalibrada(0., 0., 500.) == 0.0         # cero conservado
    assert rc.densidad_recalibrada(0., 0., 0.) == 0.0
    with pytest.raises(rc.RecalibracionError, match="mayor que la masa global"):
        rc.densidad_recalibrada(100., 150., 10.)
    with pytest.raises(rc.RecalibracionError, match="volumen ajustable es nulo"):
        rc.densidad_recalibrada(100., 40., 0.)
    for malo in (float("nan"), -1.0, None):
        with pytest.raises(rc.RecalibracionError):
            rc.densidad_recalibrada(malo, 0., 10.)


def test_metas_humedas():
    metas = rc.metas_humedas(1.5, [100., np.nan, 0.])
    assert metas.iloc[0] == pytest.approx(150.) and np.isnan(metas.iloc[1]) and metas.iloc[2] == 0.
    assert rc.metas_humedas(None, [1., 2.]).isna().all()


# ------------------------------------------------------------- seccion 10

def _turnos(rows):
    return pd.DataFrame([dict(fecha=pd.Timestamp("2026-10-01") + pd.Timedelta(days=i // 2),
                              turno="AB"[i % 2], tmh=w, tms=d) for i, (w, d) in enumerate(rows)])


def test_ejemplo_didactico_40_tmh_38_tms():
    turnos = _turnos([(40., 38.)])
    mods = pd.DataFrame(dict(clave=["m1", "m2"], meta_tmh=[10., np.nan], abierto=[False, True]))
    asig, resid, resumen = rc.asignar_secuencial(turnos, mods)
    a = asig.set_index("clave")
    assert a.loc["m1", "tmh"] == pytest.approx(10.) and a.loc["m1", "tms"] == pytest.approx(9.5)
    assert a.loc["m2", "tmh"] == pytest.approx(30.) and a.loc["m2", "tms"] == pytest.approx(28.5)
    assert a.tmh.sum() == pytest.approx(40.) and a.tms.sum() == pytest.approx(38.)
    assert resid.empty
    assert a.loc["m1", "fraccion_turno"] == pytest.approx(0.25)     # S del modulo que cierra
    s = resumen.set_index("clave")
    assert s.loc["m1", "fraccion_traspaso"] == pytest.approx(0.25)
    assert s.loc["m2", "fraccion_traspaso"] == 1.0                   # ultimo abierto


def test_residual_pasa_al_siguiente_dentro_del_mismo_turno_y_conserva_por_turno():
    turnos = _turnos([(40., 38.), (100., 90.), (60., 50.)])
    mods = pd.DataFrame(dict(clave=[1, 2, 3], meta_tmh=[70., 55., np.nan],
                             abierto=[False, False, True]))
    asig, resid, _ = rc.asignar_secuencial(turnos, mods)
    cons = rc.conservacion_por_turno(turnos, asig, resid, exigir=True)
    assert cons.ok.all()
    por_modulo = asig.groupby("clave").tmh.sum()
    assert por_modulo[1] == pytest.approx(70.) and por_modulo[2] == pytest.approx(55.)
    assert por_modulo[3] == pytest.approx(75.)          # el abierto no usa meta
    segundo = asig[(asig.fecha == turnos.fecha[1]) & (asig.turno == "B")].sort_values("orden")
    assert list(segundo.clave) == [1, 2, 3]              # cierre y traspasos dentro del mismo turno
    assert list(segundo.tmh) == pytest.approx([30., 55., 15.])


def test_ultimo_abierto_ignora_cualquier_meta_futura():
    turnos = _turnos([(100., 95.), (100., 95.)])
    base = pd.DataFrame(dict(clave=[1, 2], meta_tmh=[50., 1.], abierto=[False, True]))
    otra = base.assign(meta_tmh=[50., 1e9])
    a1, _, _ = rc.asignar_secuencial(turnos, base)
    a2, _, _ = rc.asignar_secuencial(turnos, otra)
    pd.testing.assert_frame_equal(a1, a2)
    assert a1.groupby("clave").tmh.sum()[2] == pytest.approx(150.)


def test_metas_agotadas_reporta_residual_y_no_lo_hace_desaparecer():
    turnos = _turnos([(100., 90.)])
    mods = pd.DataFrame(dict(clave=[1], meta_tmh=[60.], abierto=[False]))
    asig, resid, _ = rc.asignar_secuencial(turnos, mods)
    assert asig.tmh.sum() == pytest.approx(60.)
    assert resid.tmh.sum() == pytest.approx(40.) and resid.tms.sum() == pytest.approx(36.)
    assert resid.motivo.iloc[0] == "metas_agotadas"
    assert rc.conservacion_por_turno(turnos, asig, resid, exigir=True).ok.all()
    with pytest.raises(rc.RecalibracionError):          # sin el residual no cierra
        rc.conservacion_por_turno(turnos, asig, None, exigir=True)


def test_ceros_ausencias_y_errores_de_la_secuencia():
    mods = pd.DataFrame(dict(clave=[1, 2], meta_tmh=[10., np.nan], abierto=[False, True]))
    # TMH y TMS cero: se conserva el cero, no hay filas ni material nuevo
    asig, resid, _ = rc.asignar_secuencial(_turnos([(0., 0.), (20., 18.)]), mods)
    assert asig.tmh.sum() == pytest.approx(20.) and resid.empty
    # TMH positiva con TMS ausente: la TMS no se inventa
    asig, _, _ = rc.asignar_secuencial(_turnos([(20., np.nan)]), mods)
    assert asig.tms.isna().all() and asig.tmh.sum() == pytest.approx(20.)
    with pytest.raises(rc.RecalibracionError):          # TMH ausente: no se completa
        rc.asignar_secuencial(_turnos([(np.nan, 1.)]), mods)
    with pytest.raises(rc.RecalibracionError):          # TMS con TMH cero es imposible
        rc.asignar_secuencial(_turnos([(0., 5.)]), mods)
    with pytest.raises(rc.RecalibracionError, match="duplicada"):
        rc.asignar_secuencial(_turnos([(5., 4.)]),
                              pd.DataFrame(dict(clave=[1, 1], meta_tmh=[1., 1.])))
    with pytest.raises(rc.RecalibracionError, match="meta TMH utilizable"):
        rc.asignar_secuencial(_turnos([(5., 4.)]),
                              pd.DataFrame(dict(clave=[1, 2], meta_tmh=[np.nan, np.nan],
                                                abierto=[False, True])))


def test_modulos_fijados_se_preservan_y_la_incompatibilidad_bloquea():
    turnos = _turnos([(60., 57.), (60., 57.)])
    mods = pd.DataFrame(dict(clave=["fijo", "aj", "abierto"], meta_tmh=[45., 30., np.nan],
                             abierto=[False, False, True]))
    asig, resid, res = rc.asignar_secuencial(turnos, mods)
    rc.verificar_fijados(res, {"fijo": 45.}, tms_conformado={"fijo": 42.75})
    assert res.set_index("clave").loc["fijo", "tmh_asignada"] == pytest.approx(45.)
    with pytest.raises(rc.RecalibracionError, match="incompatible"):
        rc.verificar_fijados(res, {"fijo": 50.})
    with pytest.raises(rc.RecalibracionError, match="TMS conformada"):
        rc.verificar_fijados(res, {"fijo": 45.}, tms_conformado={"fijo": 99.})
    # suministro que no alcanza a cubrir al fijado: incompatible
    pocos = _turnos([(10., 9.)])
    _, _, res2 = rc.asignar_secuencial(pocos, mods)
    with pytest.raises(rc.RecalibracionError, match="incompatible"):
        rc.verificar_fijados(res2, {"fijo": 45.})


# ------------------------------------------------- referencia M&R (sec. 4)

def _bloques_mr():
    openpyxl = pytest.importorskip("openpyxl")
    if not MR.exists():
        pytest.skip("referencia M&R no disponible")
    ws = openpyxl.load_workbook(MR, data_only=True)["Septiembre"]
    # Bloques de ~63 filas desde la fila 4 (modulo 131..135): la fila 'TMH' esta 4 filas
    # bajo la cabecera (la cabecera de algunos bloques lleva una fila extra, por lo que
    # se ubica por rotulo). El sexto bloque es el resumen y se excluye.
    filas = [r for r in range(4, ws.max_row)
             if ws.cell(r, 2).value == "TMH" and ws.cell(r, 3).value == "[TMH]"
             and isinstance(ws.cell(r, 18).value, (int, float))
             and isinstance(ws.cell(r, 19).value, (int, float))][:5]
    bloques = []
    for r in filas:
        def fila(off):
            return [ws.cell(r + off, c).value or 0.0 for c in range(4, 17)]   # D..P
        tmh, tms, cut = fila(0), fila(1), fila(3)                              # TMH +0, TMS +1, CuT +3
        last = max(i for i, x in enumerate(tmh) if x > 0)
        bloques.append(dict(tmh=tmh[:last + 1], tms=tms[:last + 1], cut=cut[:last + 1],
                            meta=ws.cell(r, 18).value, S=ws.cell(r, 19).value,
                            cu_fino=ws.cell(r + 1, 18).value))
    return bloques


def test_estructura_control_mr_septiembre_reproduce_asignacion_S_y_cu_fino():
    bloques = _bloques_mr()
    assert len(bloques) == 5
    # Suministro por turno = suma de las partes de los modulos en el turno de traspaso.
    suministro, inicio = {}, 0
    for b in bloques:
        for j, (w, d) in enumerate(zip(b["tmh"], b["tms"])):
            ant = suministro.get(inicio + j, (0.0, 0.0))
            suministro[inicio + j] = (ant[0] + w, ant[1] + d)
        inicio += len(b["tmh"]) - 1
    turnos = pd.DataFrame([dict(fecha=pd.Timestamp("2026-09-01") + pd.Timedelta(days=t // 2),
                                turno="AB"[t % 2], tmh=w, tms=d)
                           for t, (w, d) in sorted(suministro.items())])
    mods = pd.DataFrame(dict(clave=range(5), meta_tmh=[b["meta"] for b in bloques],
                             abierto=[False] * 4 + [True]))
    asig, resid, resumen = rc.asignar_secuencial(turnos, mods)
    assert resid.empty
    assert rc.conservacion_por_turno(turnos, asig, resid, exigir=True).ok.all()
    esperado_S = [0.6437, 0.5861, 0.5978, 0.4720, 1.0]
    esperado_cu = [865.41, 810.21, 845.65, 764.63, 460.63]
    for k, b in enumerate(bloques):
        got = asig[asig.clave == k].sort_values(["fecha", "turno"]).reset_index(drop=True)
        assert len(got) == len(b["tmh"])
        np.testing.assert_allclose(got.tmh, b["tmh"], rtol=1e-9)
        np.testing.assert_allclose(got.tms, b["tms"], rtol=1e-8)
        s = resumen.set_index("clave").loc[k, "fraccion_traspaso"]
        assert s == pytest.approx(b["S"], rel=1e-9)
        assert round(s, 4) == esperado_S[k]
        cu_fino = float((got.tms.to_numpy() * np.array(b["cut"]) / 100.0).sum())
        assert cu_fino == pytest.approx(b["cu_fino"], rel=1e-8)
        assert round(cu_fino, 2) == esperado_cu[k]


# --------------------------------- reconstitucion de un Caso (sin SQL)

DIAS = pd.date_range("2026-09-28", "2026-10-03")
INICIO, FIN = pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-03")
OBJETIVO_TMS = 2200.0


def caso():
    return dict(id=10013, run_id=10145, nombre="fixture", fecha_inicio="2026-10-01",
                fecha_fin="2026-10-03", modelo_codigo="hidrometalurgia_125_v2",
                modelo_version="v2", total_flujos=125)


def apilado_sintetico(v_obj_ultimo=2500.0):
    vols = {1: [1000, 1000, 500, 0, 0, 0], 2: [0, 0, 500, 1000, 600, 0],
            3: [0, 0, 0, 0, 400, 1000]}
    rows = []
    for m, vs in vols.items():
        for d, x in zip(DIAS, vs):
            rows.append(dict(fecha=d, pad_id=2, campana=12, campana_id=13, modulo=m,
                             modulo_id=100 + m, vol_diario=float(x), avance=.5,
                             vol_total_est=v_obj_ultimo if m == 3 else 2500.,
                             vol_acum_final=0., altura_prom=8., grado_prom=1., id=1))
    return pd.DataFrame(rows)


def perfil_sintetico():
    return pd.DataFrame([dict(fecha=d, turno=t, tm=tm, tmh=w / 2, humedad=4., fuente="PI")
                         for d in DIAS for t, w in (("A", 400.), ("B", 380.))
                         for tm in ("TM1", "TM2")])


def fuentes(ap=None, fijados=None, perfil=None):
    ap = apilado_sintetico() if ap is None else ap

    def load_apilado(desde=None, hasta=None, engine=None):
        r = ap
        if desde is not None:
            r = r[r.fecha >= pd.Timestamp(desde)]
        if hasta is not None:
            r = r[r.fecha <= pd.Timestamp(hasta)]
        return r.copy()

    def load_profile(desde, hasta, engine=None):
        p = perfil_sintetico() if perfil is None else perfil
        return p[(p.fecha >= pd.Timestamp(desde)) & (p.fecha <= pd.Timestamp(hasta))].copy()

    targets = {2: dict(flujo="F19", masa_medida=OBJETIVO_TMS, masa_reconciliada=OBJETIVO_TMS,
                       fino_cu_medido=10., fino_cu_reconciliado=10.),
               1: dict(flujo="F18", masa_medida=0., masa_reconciliada=0.,
                       fino_cu_medido=0., fino_cu_reconciliado=0.)}
    hours = pd.DataFrame({"fecha": list(DIAS[3:]), "H_op": [20.] * 3})
    fij = pd.DataFrame(columns=["campana_id", "pad_id", "parcela_id", "modulo_id",
                                "modulo_numero", "fecha_conformacion", "fecha_congelamiento",
                                "tms_conformado", "estado_congelamiento", "tmh_fijada"]) \
        if fijados is None else fijados
    return [
        patch.object(mf, "load_targets", return_value=targets),
        patch.object(mf, "load_profile", side_effect=load_profile),
        patch.object(mf, "load_hours", return_value=hours),
        patch.object(db_source, "load_apilado", side_effect=load_apilado),
        patch.object(rdb, "load_nacimientos", return_value=pd.DataFrame(
            {"pad_id": [2], "campana_id": [13], "nacimiento": [DIAS[0]]})),
        patch.object(rdb, "load_modulos", return_value=pd.DataFrame(
            {"modulo_id": [101, 102, 103], "modulo_numero": [1, 2, 3], "parcela_id": [7, 7, 7]})),
        patch.object(rdb, "load_modulos_fijados", return_value=fij),
        patch("sqlalchemy.engine.Engine.connect", side_effect=AssertionError("SQL prohibido")),
    ]


class Ctx:
    def __init__(self, patches):
        self.p = patches

    def __enter__(self):
        for p in self.p:
            p.start()

    def __exit__(self, *a):
        for p in reversed(self.p):
            p.stop()


def correr(**kw):
    with Ctx(fuentes(**kw)):
        return engine.analyze_db(fecha_min=INICIO, fecha_max=FIN, caso=caso(),
                                 caso_id=10013, use_intraday=True,
                                 metodo="recalibrada")


def test_caso_recalibrado_conserva_masa_y_usa_historia_desde_el_nacimiento():
    res = correr()
    st = res["shift_table"]
    assert res["metodo_reconstitucion"] == "recalibrada"
    assert res["historia_desde"] == DIAS[0]
    # Conservacion del Caso (14): sum D por PAD = TMS reconciliada F19
    assert st.loc[st.pad_id == 2, "masa_total"].sum() == pytest.approx(OBJETIVO_TMS, rel=1e-10)
    # Conservacion por turno: la TMH asignada reproduce el suministro de la ventana
    g = res["recalibracion_grupos"].iloc[0]
    # rho = (W_global campana hasta el corte - W_fijo) / V_real ajustable
    assert g.w_global_campana == pytest.approx(6 * 780.0)
    assert g.v_ajustable == pytest.approx(6000.0)
    assert g.rho_h == pytest.approx(6 * 780.0 / 6000.0)
    # El modulo 1 se lleno en la historia (meta = rho * vol_total_est): no se reinicia
    mods = res["recalibracion_modulos"].set_index("modulo")
    assert mods.loc[1, "meta_tmh"] == pytest.approx(g.rho_h * 2500.)
    assert mods.loc[1, "tmh_ventana"] == 0.0
    assert pd.isna(mods.loc[3, "meta_tmh"]) and bool(mods.loc[3, "abierto"])
    assert mods.loc[3, "fraccion_traspaso"] == 1.0
    sup = res["asignaciones"].groupby(["fecha", "turno"])[["tmh", "tms"]].sum()
    esperado = pd.Series({(f, t): w for f in DIAS[3:] for t, w in (("A", 400.), ("B", 380.))})
    np.testing.assert_allclose(sup.tmh.to_numpy(), esperado.to_numpy(), rtol=1e-10)
    assert res["sin_asignar"].empty
    assert res["cuadratura_pad"].masa_pendiente.abs().max() < 1e-8


def test_volumen_sin_masa_y_masa_sin_volumen_se_conservan():
    st = correr()["shift_table"]
    # 2026-10-02: el modulo 3 tiene volumen observado pero asignacion calculada cero
    fila = st[(st.fecha == pd.Timestamp("2026-10-02")) & (st.modulo == 3)].iloc[0]
    assert fila.vol_diario == 400. and fila.fila_volumetrica
    assert fila.tmh_total == 0.0 and fila.masa_total == 0.0
    assert st.loc[st.fecha.between(INICIO, FIN)].vol_diario.sum() == pytest.approx(
        apilado_sintetico().query("fecha >= '2026-10-01'").vol_diario.sum())
    # Masa asignada a un modulo sin fila volumetrica ese dia: se agrega la fila (vol 0)
    ap = apilado_sintetico()
    ap.loc[ap.modulo == 2, "vol_total_est"] = 6000.      # el modulo 2 sigue recibiendo masa el 10-03
    res = correr(ap=ap)
    st = res["shift_table"]
    sin_fila = st[~st.fila_volumetrica]
    assert len(sin_fila) == 1 and sin_fila.modulo.iloc[0] == 2
    assert sin_fila.fecha.iloc[0] == pd.Timestamp("2026-10-03")
    assert sin_fila.vol_diario.iloc[0] == 0 and sin_fila.tmh_total.iloc[0] > 0
    # el volumen del modulo 3 (sin masa) tampoco se pierde
    assert st.loc[st.modulo == 3, "vol_diario"].sum() == 1400.
    assert st.loc[st.pad_id == 2, "masa_total"].sum() == pytest.approx(OBJETIVO_TMS, rel=1e-10)


def test_ultimo_abierto_no_usa_volumen_objetivo_futuro():
    a = correr(ap=apilado_sintetico(v_obj_ultimo=2500.))["shift_table"]
    b = correr(ap=apilado_sintetico(v_obj_ultimo=99999.))["shift_table"]
    cols = ["fecha", "modulo", "tmh_turno1", "tmh_turno2", "masa_turno1", "masa_turno2"]
    pd.testing.assert_frame_equal(a[cols], b[cols])


def test_modulo_fijado_se_preserva_y_cambia_la_densidad():
    fijo = pd.DataFrame([dict(campana_id=13, pad_id=2, parcela_id=7, modulo_id=101,
                              modulo_numero=1, fecha_conformacion=DIAS[1],
                              fecha_congelamiento=DIAS[2], tms_conformado=1900. * .96,
                              estado_congelamiento="CONGELADO", tmh_fijada=1900.)])
    res = correr(fijados=fijo)
    g = res["recalibracion_grupos"].iloc[0]
    assert g.w_fijo == 1900. and g.v_ajustable == pytest.approx(3500.)
    assert g.rho_h == pytest.approx((6 * 780. - 1900.) / 3500.)
    m = res["recalibracion_modulos"].set_index("modulo")
    assert bool(m.loc[1, "fijado"]) and m.loc[1, "meta_tmh"] == 1900.
    assert m.loc[1, "tmh_hasta_corte"] == pytest.approx(1900.)
    # fijado incompatible con su TMS conformada: bloquea
    malo = fijo.assign(tms_conformado=500.)
    with pytest.raises(rc.RecalibracionError, match="TMS conformada"):
        correr(fijados=malo)
    # CONGELADO sin TMH directa: ajustable, con advertencia
    sin_tmh = fijo.assign(tmh_fijada=np.nan)
    res = correr(fijados=sin_tmh)
    assert not bool(res["recalibracion_modulos"].set_index("modulo").loc[1, "fijado"])
    assert any(a.codigo == "congelado_incompleto" for a in res["avisos"])


def test_identidad_ambigua_y_perfil_faltante_se_rechazan():
    ap = apilado_sintetico()
    ap.loc[(ap.modulo == 2), "modulo_id"] = np.where(ap.loc[(ap.modulo == 2)].fecha.eq(DIAS[2]), 999, 102)
    with pytest.raises(rc.RecalibracionError, match="Identidad ambigua"):
        correr(ap=ap)
    perfil = perfil_sintetico().iloc[1:]           # falta una correa en un turno con volumen
    with pytest.raises(mf.FlowCaseError):
        correr(perfil=perfil)


def test_grafico_tabla_detalle_e_informe_consumen_las_mismas_asignaciones():
    res = correr()
    res = dict(res, caso=caso())
    st, tl = res["shift_table"], res["module_timeline"]
    # grafico: horario desde las asignaciones, estimado con interpolacion uniforme de 12 h
    assert tl.mass_h.sum() == pytest.approx(st.tmh_total.sum())
    assert tl.mass_dry.sum() == pytest.approx(st.masa_total.sum())
    assert tl.resolucion.str.startswith("interpolacion_uniforme_12h").all()
    assert "estimacion" in tl.resolucion.iloc[0]
    for r in tl.itertuples():
        assert pd.Timestamp(r.fecha) + pd.Timedelta(hours=8) <= r.start < r.end <= \
            pd.Timestamp(r.fecha) + pd.Timedelta(hours=32)
    fig = panel.fig_gantt(res)
    assert len(fig.data) == 1
    # tabla y detalle: TMH/TMS por turno = asignacion secuencial, sin reparto posterior
    it = presentacion._itinerary_frame(res)
    visibles = it[it.tms_primera_fila]
    assert visibles.tmh_turno_asignada.sum() == pytest.approx(st.tmh_total.sum())
    assert visibles.masa_turno_asignada.sum() == pytest.approx(st.masa_total.sum())
    assert (it.loc[it.modulo == 3, "fecha"] == pd.Timestamp("2026-10-02")).any()   # vol sin masa
    # informe: meta, densidad, S y Cu fino = sum(TMS * CuT / 100) por turno
    cal = pd.DataFrame([dict(fecha=d, turno=t, CuT=c) for d in DIAS[3:]
                        for t, c in (("A", 1.0), ("B", 2.0))])
    frame = im.preparar_modulos_desde_resultado(res, 2, cal, INICIO, FIN)
    mod = res["recalibracion_modulos"].set_index("modulo")
    for r in frame.itertuples():
        assert r.TMH == pytest.approx(st.loc[st.modulo == r.modulo, "tmh_total"].sum())
        assert r.TMS == pytest.approx(st.loc[st.modulo == r.modulo, "masa_total"].sum())
        assert r.densidad_recalibrada == pytest.approx(res["recalibracion_grupos"].rho_h.iloc[0])
        if r.modulo != 3:
            assert r.meta_tmh == pytest.approx(mod.loc[r.modulo, "meta_tmh"])
        assert r.fraccion_traspaso == pytest.approx(mod.loc[r.modulo, "fraccion_traspaso"])
        sub = st[st.modulo == r.modulo]
        fino = (sub.masa_turno1.sum() * 1.0 + sub.masa_turno2.sum() * 2.0) / 100.0
        assert r.cu_fino == pytest.approx(fino)


def test_metodo_anterior_sigue_disponible_por_parametro():
    ap = apilado_sintetico().assign(vol_acum_final=1., vol_total_est=1.)
    with Ctx(fuentes(ap=ap)):
        res = engine.analyze_db(fecha_min=INICIO, fecha_max=FIN, caso=caso(),
                                caso_id=10013, metodo="volumen")
        with pytest.raises(ValueError, match="invalido"):
            engine.analyze_db(fecha_min=INICIO, fecha_max=FIN, caso=caso(),
                              caso_id=10013, metodo="otro")
    assert "metodo_reconstitucion" not in res and "tmh_turno1" not in res["shift_table"]
    assert res["shift_table"].masa_total.sum() == pytest.approx(OBJETIVO_TMS)


def test_cargar_resultado_caso_pasa_el_metodo_solo_si_se_pide():
    calls = []

    def loader(**kw):
        calls.append(kw)
        r = correr()
        return r
    panel.cargar_resultado_caso(caso(), loader)
    panel.cargar_resultado_caso(caso(), loader, metodo="volumen")
    assert "metodo" not in calls[0] and calls[1]["metodo"] == "volumen"


def test_panel_carga_recalibrada_solo_si_se_elige():
    """La metodologia vigente sigue por defecto; la recalibrada es opt-in."""
    from dash import Dash
    from reconstitucion import panel
    assert engine.METODO_DEFECTO == "volumen"
    calls = []
    def loader(**kwargs):
        calls.append(kwargs)
        return dict(masa=pd.DataFrame({"caso_id": [kwargs["caso_id"]]}))
    app = Dash(__name__, suppress_callback_exceptions=True)
    panel.register_callbacks(app, loader=loader, case_loader=lambda: [])
    fn = next(v["callback"].__wrapped__ for k, v in app.callback_map.items()
              if "reconstitucion-token.data" in k)
    case = dict(caso(), id=10013)
    fn(1, 10013, [case], "volumen")
    fn(1, 10013, [case], "recalibrada")
    assert "metodo" not in calls[0] and calls[1]["metodo"] == "recalibrada"
