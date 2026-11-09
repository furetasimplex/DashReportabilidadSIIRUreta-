"""Base unica de masa (TMH y TMS de la fuente), cierre con el flujo y seleccion de fuente."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from reconstitucion import masa_fuentes, recalibracion_db_source as source
from reconstitucion.modelo_flujos import FlowCaseError
from reconstitucion.recalibracion_adapter import apply_recalibrated_distribution
from reconstitucion.recalibracion_mr import RecalibrationError
from reconstitucion.recalibracion_runtime import _window_profile, load_runtime_recalibration

CASO = dict(id=7, run_id="7", fecha_inicio="2026-10-01", fecha_fin="2026-10-02")
# dia: (TMH A, TMH B, TMS del dia); el 30-sep es previo a la ventana.
FUENTE = {"2026-09-30": (50.0, 50.0, 97.0), "2026-10-01": (40.0, 60.0, 96.0), "2026-10-02": (70.0, 30.0, 97.0)}
VENTANA_TMS = 193.0


def _conciliado(dias=FUENTE):
    return pd.DataFrame([dict(fecha=pd.Timestamp(d), etiqueta="Sulfuro", tmh_a=a, tmh_b=b, tms=s, caso_id=7)
                         for d, (a, b, s) in dias.items()])


def _historia():
    filas = [("2026-09-30", 1, 60, 100), ("2026-10-01", 1, 40, 100), ("2026-10-01", 2, 30, 120),
             ("2026-10-02", 2, 70, 120)]
    return [dict(fecha=pd.Timestamp(d), pad_id=2, campana_id=13, campana=12, parcela_id=1, modulo_id=m,
                 modulo=m, vol_diario=float(v), vol_total_est=float(e), vol_acum_final=0.0, avance=0.5)
            for d, m, v, e in filas]


def _resultado(flujo):
    hist = pd.DataFrame(_historia())
    ap = hist.loc[hist.fecha.ge("2026-10-01")].assign(estado="ACTIVO")
    dias = pd.to_datetime(["2026-10-01", "2026-10-02"])
    # Reparto previo con otra frontera de turnos: no debe influir en la tabla oficial.
    por_pad = pd.DataFrame(dict(fecha=dias, pad_id=2, TMS=flujo / 2, TMS_T1=flujo / 4, TMS_T2=flujo / 4,
                                H_op=20.0))
    por_pad.loc[:, "TMS_T1"] = [flujo / 2 * 0.3, flujo / 2 * 0.7]
    por_pad.loc[:, "TMS_T2"] = por_pad.TMS - por_pad.TMS_T1
    masa = por_pad.groupby("fecha", as_index=False)[["TMS", "TMS_T1", "TMS_T2", "H_op"]].sum()
    return dict(apilado=ap, masa=masa, masa_por_pad=por_pad, sem=None)


def _aplicar(flujo=VENTANA_TMS, dias=FUENTE, fuente="oficial", conc=None, regimen=None):
    conc = _conciliado(dias) if conc is None else conc
    perfil = _window_profile(conc, pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-02"))
    cadena = dict(conciliado=conc, cortes=[], fuente=fuente,
                  regimen=regimen or ("of" if fuente == "of" else "digital"))
    return apply_recalibrated_distribution(_resultado(flujo), _historia(), perfil, [], CASO, cadena=cadena)


def test_cierra_exacto_con_el_flujo_del_pad_y_no_hay_turno_con_tms_mayor_que_tmh():
    out = _aplicar()
    st = out["shift_table"]
    assert st.masa_total.sum() == pytest.approx(VENTANA_TMS, abs=1e-9)
    assert (st.masa_turno1 <= st.TMH_turno1 + 1e-9).all() and (st.masa_turno2 <= st.TMH_turno2 + 1e-9).all()
    assert out["recalibracion_mr"].factor_flujo_of.iloc[0] == pytest.approx(1.0)


def test_escalado_cierra_con_el_flujo_y_conserva_humedad_y_columnas_de_la_fuente():
    flujo = 200.0
    out = _aplicar(flujo, fuente="of")
    st = out["shift_table"]
    k = flujo / VENTANA_TMS
    assert out["recalibracion_mr"].factor_flujo_of.iloc[0] == pytest.approx(k)
    assert st.masa_total.sum() == pytest.approx(flujo, abs=1e-9)
    for turno, (tmh, tms) in (("1", ("TMH_of_turno1", "TMS_of_turno1")), ("2", ("TMH_of_turno2", "TMS_of_turno2"))):
        humedad_tabla = 1 - st[f"masa_turno{turno}"] / st[f"TMH_turno{turno}"].where(st[f"TMH_turno{turno}"] > 0)
        humedad_fuente = 1 - st[tms] / st[tmh].where(st[tmh] > 0)
        assert np.allclose(humedad_tabla.dropna(), humedad_fuente.dropna(), atol=1e-12)
        assert np.allclose(st[f"masa_turno{turno}"], st[tms] * k)
    # La fuente por dia y turno queda intacta.
    assert st.TMS_of_turno1.sum() + st.TMS_of_turno2.sum() == pytest.approx(VENTANA_TMS)
    assert st.TMH_of_turno1.sum() + st.TMH_of_turno2.sum() == pytest.approx(300 - 100)
    # No usa la frontera de turnos del reparto previo (30/70).
    assert st.groupby("fecha").masa_turno1.sum().iloc[0] != pytest.approx(flujo / 2 * 0.3)


def test_la_secuencia_no_depende_del_factor():
    a, b = _aplicar(200.0, fuente="of")["shift_table"], _aplicar(250.0, fuente="of")["shift_table"]
    cols = ["fecha", "modulo", "TMH_of_turno1", "TMH_of_turno2", "TMS_of_turno1", "TMS_of_turno2"]
    pd.testing.assert_frame_equal(a[cols].reset_index(drop=True), b[cols].reset_index(drop=True))


def test_intervalos_suman_12_horas_y_masas_del_timeline_son_las_oficiales():
    out = _aplicar(200.0, fuente="of")
    tl = out["module_timeline"]
    turno = (tl.start - tl.fecha).dt.total_seconds() >= 20 * 3600
    horas = (tl.end - tl.start).dt.total_seconds().div(3600).groupby([tl.fecha, turno]).sum()
    assert np.allclose(horas, 12.0)
    assert tl.mass_dry.sum() == pytest.approx(200.0)
    assert tl.mass_h.sum() == pytest.approx(out["shift_table"][["TMH_turno1", "TMH_turno2"]].sum().sum())


def test_totales_diarios_y_cuadratura_siguen_la_tabla_oficial():
    out = _aplicar(200.0, fuente="of")
    st = out["shift_table"]
    por_dia = st.groupby("fecha").masa_total.sum()
    assert np.allclose(st.TMS_dia, st.fecha.map(por_dia))
    assert out["cuadratura"].masa_pendiente.abs().max() < 1e-6
    assert out["cuadratura_pad"].masa_pendiente.abs().max() < 1e-6
    assert out["masa_por_pad"].TMS.sum() == pytest.approx(200.0)


def test_flujo_positivo_sin_tms_de_la_fuente_en_la_ventana_es_error():
    dias = {**FUENTE, "2026-10-01": (0.0, 0.0, 0.0), "2026-10-02": (0.0, 0.0, 0.0)}
    with pytest.raises(RecalibrationError, match="sin TMS conciliada"):
        _aplicar(50.0, dias=dias)


def test_flujo_cero_con_masa_de_la_fuente_deja_oficial_en_cero_y_registra_excepcion():
    out = _aplicar(0.0)
    st = out["shift_table"]
    assert st.masa_total.sum() == 0.0 and st.TMH_turno1.sum() + st.TMH_turno2.sum() == 0.0
    assert st.TMS_of_turno1.sum() + st.TMS_of_turno2.sum() == pytest.approx(VENTANA_TMS)
    exc = out["excepciones_reparto"]
    assert (exc.tipo == "FLUJO_CERO_CON_MASA_OF").sum() == 2


def test_control_de_k_oficial_registra_excepcion_visible_fuera_de_tolerancia():
    assert "FACTOR_FLUJO_FUERA_TOLERANCIA" not in set(_aplicar(VENTANA_TMS * (1 + 1e-6))["excepciones_reparto"].tipo)
    out = _aplicar(VENTANA_TMS * 1.01)
    fila = out["excepciones_reparto"].query("tipo == 'FACTOR_FLUJO_FUERA_TOLERANCIA'")
    assert len(fila) == 1 and "1.01" in fila.detalle.iloc[0]
    # La fuente 'of' (testeo) es comparacion: el escalado es el metodo, no una excepcion.
    assert "FACTOR_FLUJO_FUERA_TOLERANCIA" not in set(_aplicar(VENTANA_TMS * 1.01, fuente="of")["excepciones_reparto"].tipo)


@pytest.fixture
def tmp_path():
    """Directorio temporal propio: el predeterminado de pytest puede no ser escribible en esta maquina."""
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as carpeta:
        yield Path(carpeta)


class _Motor:
    def __init__(self):
        self.sql = []

    def connect(self):
        motor = self

        class Conexion:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def execute(self_, sentencia, params):
                motor.sql.append(str(sentencia))
                return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: []))
        return Conexion()


@pytest.fixture
def db_falsa(monkeypatch):
    dbs = SimpleNamespace(SCHEMA="dbo", MASA_VER_TABLE="Datos_conciliados_of_ver", get_engine=lambda: _Motor())
    monkeypatch.setattr(source, "_db_source", lambda: dbs)
    return dbs


def test_load_conciliado_usa_ver_por_defecto_con_el_criterio_de_load_masa(db_falsa):
    motor = _Motor()
    source.load_conciliado("2026-09-01", "2026-10-12", motor, caso_id=10013, caso_inicio="2026-10-01")
    sql = motor.sql[0]
    assert "Datos_conciliados_of_ver" in sql and "AJUSTE_REPORTE" in sql and "es_activa = 1" in sql
    assert "estado_validacion" in sql and "run_id" not in sql
    assert "Datos_conciliados_of " not in sql.replace("Datos_conciliados_of_ver", "")


def test_load_conciliado_of_solo_si_se_pide_y_ver_exige_caso(db_falsa):
    motor = _Motor()
    source.load_conciliado("2026-09-01", "2026-10-12", motor, fuente="of")
    assert "Datos_conciliados_of_ver" not in motor.sql[0] and "Datos_conciliados_of" in motor.sql[0]
    with pytest.raises(ValueError):
        source.load_conciliado("2026-09-01", "2026-10-12", motor)
    with pytest.raises(ValueError):
        source.load_conciliado("2026-09-01", "2026-10-12", motor, fuente="otra")


def test_runtime_sin_ver_ni_libro_falla_claro_y_nunca_pide_of(monkeypatch):
    pedidas = []
    ver_previo = _conciliado({"2026-09-30": (50.0, 50.0, 97.0)}).assign(caso_id=-1)

    def cargar(inicio, fin, *args, fuente="ver", **kw):
        pedidas.append(fuente)
        return ver_previo.to_dict("records") if fuente == "ver" else _conciliado().to_dict("records")

    monkeypatch.setattr(source, "load_conciliado", cargar)
    monkeypatch.setattr(masa_fuentes, "load_libros", lambda *a: _libros([]))
    monkeypatch.setattr(source, "load_campaign_history", lambda *a, **k: _historia())
    monkeypatch.setattr(source, "load_fixed_modules", lambda *a, **k: [])
    with pytest.raises(FlowCaseError, match="ni en los libros Excel"):
        load_runtime_recalibration(_resultado(VENTANA_TMS), CASO, {2: dict(masa_reconciliada=VENTANA_TMS)})
    assert pedidas == ["ver"]


def _libros(filas):
    """filas: (dia, pad, campana, tmh_a, tmh_b, tms_a, tms_b, libro)"""
    return pd.DataFrame([dict(fecha=pd.Timestamp(d), pad_id=p, campana=c, tmh_a=a, tmh_b=b, tms_a=sa, tms_b=sb, libro=l, sha256="x")
                         for d, p, c, a, b, sa, sb, l in filas],
                        columns=["fecha", "pad_id", "campana", "tmh_a", "tmh_b", "tms_a", "tms_b", "libro", "sha256"])


def _ver(filas):
    return pd.DataFrame([dict(fecha=pd.Timestamp(d), etiqueta="Sulfuro", tmh_a=a, tmh_b=b, tms=s, caso_id=7) for d, a, b, s in filas])


def test_precedencia_ver_sobre_libro_con_excepcion_de_la_diferencia():
    ver = _ver([("2026-09-29", 40, 60, 97)])
    lib = _libros([("2026-09-29", 2, 12, 50, 60, 48, 58, "L12")])
    out, exc = masa_fuentes.combinar_ver_libro(ver, lib, "2026-09-01", "2026-09-30")
    assert out.fuente.tolist() == ["VER"] and out.tmh_a.iloc[0] == 40
    assert exc.tipo.tolist() == ["LIBRO_DIFIERE_DE_VER"] and "dif -10.0" in exc.detalle.iloc[0]


def test_ver_completo_da_el_mismo_resultado_con_o_sin_libro():
    ver = _ver([("2026-09-29", 40, 60, 97)])
    lib = _libros([("2026-09-29", 2, 12, 40, 60, 38.8, 58.2, "L12")])
    con, exc = masa_fuentes.combinar_ver_libro(ver, lib, "2026-09-01", "2026-09-30")
    sin, _ = masa_fuentes.combinar_ver_libro(ver, _libros([]), "2026-09-01", "2026-09-30")
    pd.testing.assert_frame_equal(con.reset_index(drop=True), sin.reset_index(drop=True))
    assert exc.empty


def test_libro_solo_antes_del_inicio_digital_y_desde_el_1_de_octubre_no_se_rellena():
    lib = _libros([("2026-09-30", 2, 12, 10, 10, 9, 9, "L12"), ("2026-10-01", 2, 12, 10, 10, 9, 9, "L12"),
                   ("2026-10-02", 2, 12, 10, 10, 9, 9, "L12")])
    out, _ = masa_fuentes.combinar_ver_libro(_ver([]), lib, "2026-09-01", "2026-10-05", pd.Timestamp("2026-10-01"))
    assert out.fecha.dt.strftime("%Y-%m-%d").tolist() == ["2026-09-30"] and out.fuente.tolist() == ["LIBRO_EXCEL"]
    # Mover la fecha cambia el relleno sin tocar codigo.
    out, _ = masa_fuentes.combinar_ver_libro(_ver([]), lib, "2026-09-01", "2026-10-05", pd.Timestamp("2026-10-02"))
    assert out.fecha.dt.strftime("%Y-%m-%d").tolist() == ["2026-09-30", "2026-10-01"]


def test_dos_libros_distintos_en_el_mismo_dia_y_pad_no_se_eligen_en_silencio():
    lib = _libros([("2026-09-20", 2, 11, 10, 10, 9, 9, "L11"), ("2026-09-20", 2, 12, 12, 10, 9, 9, "L12"),
                   ("2026-09-21", 2, 11, 10, 10, 9, 9, "L11"), ("2026-09-21", 2, 12, 10, 10, 9, 9, "L12")])
    out, exc = masa_fuentes.combinar_ver_libro(_ver([]), lib, "2026-09-01", "2026-09-30")
    assert exc.tipo.tolist() == ["LIBROS_EN_CONFLICTO"]
    assert out.fecha.dt.strftime("%Y-%m-%d").tolist() == ["2026-09-21"]  # el identico se conserva una vez


def test_modo_oficial_no_lee_of_y_of_solo_si_se_pide(monkeypatch):
    pedidas = []

    def cargar(inicio, fin, engine=None, *, fuente="ver", **kw):
        pedidas.append(fuente)
        return _ver([("2026-10-01", 1, 1, 1.9)]).to_dict("records") if fuente == "ver" else _ver([("2026-10-01", 2, 2, 3.8)]).to_dict("records")

    monkeypatch.setattr(source, "load_conciliado", cargar)
    monkeypatch.setattr(masa_fuentes, "load_libros", lambda *a: _libros([]))
    masa, _ = source.load_masa_fuente("2026-09-01", "2026-10-12", caso_id=7, caso_inicio="2026-10-01")
    assert pedidas == ["ver"] and set(masa.fuente) == {"VER"}
    masa, _ = source.load_masa_fuente("2026-09-01", "2026-10-12", fuente="of")
    assert pedidas == ["ver", "of"] and set(masa.fuente) == {"OF"}
    with pytest.raises(ValueError):
        source.load_masa_fuente("2026-09-01", "2026-10-12", fuente="libro")


def test_libro_va_directo_a_su_pad_con_trazabilidad_y_cierra_con_el_flujo():
    # 30-sep, previo a la ventana: ver no tiene el dia y el libro trae el PAD 2 directo.
    ver = _ver([("2026-10-01", 40, 60, 96), ("2026-10-02", 70, 30, 97)])
    lib = _libros([("2026-09-30", 2, 12, 50, 50, 48.5, 48.5, "L12"), ("2026-09-30", 1, 18, 5, 5, 4.8, 4.8, "L18")])
    conc, exc = masa_fuentes.combinar_ver_libro(ver, lib, "2026-09-01", "2026-10-02")
    # El PAD 1 no tiene historia en el fixture: su fila se informa como sin destino, no se inventa.
    out = _aplicar(conc=conc, flujo=VENTANA_TMS)
    st = out["shift_table"]
    assert st.masa_total.sum() == pytest.approx(VENTANA_TMS, abs=1e-9)
    assert set(st.fuente_dato_turno1) <= {"VER"}
    assert "MASA_SIN_DESTINO" in set(out["excepciones_reparto"].tipo)
    from reconstitucion.secuencia_campana import despachar
    desp, _ = despachar(conc, pd.DataFrame(_historia()), "2026-10-02")
    assert set(desp.loc[desp.fecha.eq("2026-09-30"), "fuente"]) == {"LIBRO_EXCEL"}
    sep = desp.loc[desp.fecha.eq("2026-09-30") & desp.pad_id.eq(2)]
    assert sep.set_index("turno").tmh.to_dict() == {"A": 50.0, "B": 50.0}  # los turnos del libro, sin repartir por volumen


def _fecha_en(monkeypatch, tmp_path, texto):
    ruta = tmp_path / "puesta_en_marcha.json"
    ruta.unlink(missing_ok=True)
    if texto is not None:
        ruta.write_text(texto, encoding="utf8")
    monkeypatch.setattr(masa_fuentes, "RUTA_PUESTA_EN_MARCHA", ruta)


def test_la_fecha_de_puesta_en_marcha_se_lee_del_archivo_versionado_y_falla_si_falta(monkeypatch, tmp_path):
    assert masa_fuentes.inicio_metodo_digital() == pd.Timestamp("2026-10-01")  # archivo real del repositorio
    _fecha_en(monkeypatch, tmp_path, '{"fecha": "2026-11-15", "nota": "x"}')
    assert masa_fuentes.inicio_metodo_digital() == pd.Timestamp("2026-11-15")
    for texto in (None, "no es json", '{"nota": "sin fecha"}', '{"fecha": "ayer"}'):
        _fecha_en(monkeypatch, tmp_path, texto)
        with pytest.raises(ValueError, match="puesta en marcha"):
            masa_fuentes.inicio_metodo_digital()


def _runtime_con_fecha(monkeypatch, tmp_path, fecha, caso):
    """Corre el runtime con mocks; la fecha de puesta en marcha es la dada."""
    _fecha_en(monkeypatch, tmp_path, '{"fecha": "%s", "nota": "prueba"}' % fecha)
    ver = _ver([("2026-10-01", 40, 60, 96), ("2026-10-02", 70, 30, 97)])
    ver_previo = _ver([("2026-09-30", 50, 50, 97)])
    todo = pd.concat([ver_previo.assign(caso_id=-1), ver])
    monkeypatch.setattr(source, "load_conciliado", lambda *a, **k: todo.to_dict("records"))
    monkeypatch.setattr(masa_fuentes, "load_libros", lambda *a: _libros([]))
    monkeypatch.setattr(source, "load_campaign_history", lambda *a, **k: _historia())
    monkeypatch.setattr(source, "load_fixed_modules", lambda *a, **k: [])
    monkeypatch.setattr("reconstitucion.recalibracion_runtime._official_cuts", lambda end: [])
    resultado = _resultado(200.0)
    resultado.update(fuente_modelo=dict(caso), balance_flujos=pd.DataFrame([dict(pad_id=2, flujo="F19", objetivo_t=200.0)]),
                     avisos_entrada=[])
    return load_runtime_recalibration(resultado, caso, {2: dict(masa_reconciliada=200.0)})


def test_regimen_por_caso_segun_la_fecha_previo_digital_y_cruce(monkeypatch, tmp_path):
    antes = _runtime_con_fecha(monkeypatch, tmp_path, "2026-10-10", CASO)  # Caso entero antes: previo
    assert antes["regimen_masa"] == "previo"
    st = antes["shift_table"]
    assert st.masa_total.sum() == pytest.approx(VENTANA_TMS)                    # cierra con la fuente, k = 1
    mr = antes["recalibracion_mr"].iloc[0]
    assert mr.factor_aplicado == 1.0 and mr.factor_flujo_of == pytest.approx(200.0 / VENTANA_TMS)
    assert mr.pendiente_flujo_tms == pytest.approx(200.0 - VENTANA_TMS)
    assert antes["balance_flujos"].pendiente_t.iloc[0] == pytest.approx(200.0 - VENTANA_TMS)
    assert antes["cuadratura_pad"].masa_pendiente.sum() == pytest.approx(200.0 - VENTANA_TMS)
    tipos = set(antes["excepciones_reparto"].tipo)
    assert "FLUJO_PENDIENTE_VS_FUENTE" in tipos and "FACTOR_FLUJO_FUERA_TOLERANCIA" not in tipos
    assert any(a.codigo == "flujo_pendiente_vs_fuente" and a.nivel == "dato" for a in antes["avisos"])
    assert not any(a.codigo == "masa_pendiente_sin_volumen" for a in antes["avisos"])
    nota = next(a for a in antes["avisos"] if a.codigo == "masa_caso_secuencial").detalle
    assert "cierra con la fuente" in nota and "VER 2 día" in nota
    despues = _runtime_con_fecha(monkeypatch, tmp_path, "2026-10-01", CASO)  # fecha_fin >= fecha: digital
    assert despues["regimen_masa"] == "digital" and despues["shift_table"].masa_total.sum() == pytest.approx(200.0)
    assert "FACTOR_FLUJO_FUERA_TOLERANCIA" in set(despues["excepciones_reparto"].tipo)
    assert "CASO_CRUZA_PUESTA_EN_MARCHA" not in set(despues["excepciones_reparto"].tipo)
    cruza = _runtime_con_fecha(monkeypatch, tmp_path, "2026-10-02", CASO)  # inicio < fecha <= fin: digital + excepcion
    assert cruza["regimen_masa"] == "digital" and cruza["shift_table"].masa_total.sum() == pytest.approx(200.0)
    assert "CASO_CRUZA_PUESTA_EN_MARCHA" in set(cruza["excepciones_reparto"].tipo)


def test_regimen_previo_ver_sigue_ganando_al_libro():
    ver = _ver([("2026-09-30", 50, 50, 97)])
    lib = _libros([("2026-09-30", 2, 12, 60, 50, 58, 48, "L12")])
    out, exc = masa_fuentes.combinar_ver_libro(ver, lib, "2026-09-01", "2026-10-02", pd.Timestamp("2026-10-10"))
    assert out.fuente.tolist() == ["VER"] and "LIBRO_DIFIERE_DE_VER" in set(exc.tipo)


def test_libro_con_tms_mayor_que_tmh_no_fluye_como_masa():
    from reconstitucion.secuencia_campana import despachar
    lib = _libros([("2026-09-30", 2, 12, 0.0, 0.0, 40000.0, 100.0, "L12"),      # TMH=0 con TMS>0
                   ("2026-09-29", 2, 12, 100.0, 50.0, 90.0, 80.0, "L12"),       # TMS B > TMH B
                   ("2026-09-28", 2, 12, 100.0, 50.0, 95.0, 48.0, "L12")])      # valida
    conc, _ = masa_fuentes.combinar_ver_libro(_ver([]), lib, "2026-09-01", "2026-10-02", pd.Timestamp("2026-10-01"))
    desp, exc = despachar(conc, pd.DataFrame(_historia()), "2026-10-02")
    assert desp.fecha.dt.strftime("%Y-%m-%d").unique().tolist() == ["2026-09-28"]
    tipos = exc.groupby(exc.fecha.dt.strftime("%Y-%m-%d")).tipo.agg(set).to_dict()
    assert "TMS_SIN_TMH" in tipos["2026-09-30"] and "LIBRO_TMS_MAYOR_TMH" in tipos["2026-09-29"]
    assert desp.tmh.sum() == 150.0  # la TMH nunca se reconstruye


def test_masa_de_una_campana_no_entra_a_otra():
    from reconstitucion.secuencia_campana import despachar
    hist = pd.DataFrame(_historia() + [dict(fecha=pd.Timestamp("2026-09-30"), pad_id=2, campana_id=9, campana=11,
                                              parcela_id=1, modulo_id=9, modulo=9, vol_diario=5.0, vol_total_est=9.0)])
    lib = _libros([("2026-09-30", 2, 12, 10, 10, 9, 9, "L12"), ("2026-09-30", 2, 11, 3, 3, 2, 2, "L11")])
    conc, _ = masa_fuentes.combinar_ver_libro(_ver([]), lib, "2026-09-01", "2026-10-02", pd.Timestamp("2026-10-01"))
    # Dos libros distintos para el mismo dia y PAD no se mezclan ni se eligen: el dia queda sin masa de libro.
    assert conc.empty or set(conc.fuente) == {"LIBRO_EXCEL"}
    solo = _libros([("2026-09-30", 2, 11, 3, 3, 2, 2, "L11"), ("2026-09-29", 2, 12, 10, 10, 9, 9, "L12")])
    conc, _ = masa_fuentes.combinar_ver_libro(_ver([]), solo, "2026-09-01", "2026-10-02", pd.Timestamp("2026-10-01"))
    hist = pd.concat([hist, hist.iloc[[0]].assign(fecha=pd.Timestamp("2026-09-29"))], ignore_index=True)
    desp, _ = despachar(conc, hist, "2026-10-02")
    por = desp.groupby(["campana", "campana_id"]).tmh.sum().to_dict()
    assert por == {(12, 13): 20.0, (11, 9): 6.0}


def test_csv_versionado_no_mezcla_campanas_ni_conserva_filas_sin_campana_activa():
    libros = masa_fuentes.load_libros()
    assert {"campana_libro", "resolucion"} <= set(libros.columns)
    ox = libros[libros.libro.str.contains("Oxidos")]
    assert ox.fecha.min() >= pd.Timestamp("2025-07-01")             # 2024-07-28 a 2025-05-06 no tiene campana activa
    assert set(ox[ox.fecha < pd.Timestamp("2025-10-01")].campana) == {17}
    sul = libros[libros.libro.str.contains("Camp 11")]
    assert sul.fecha.min() >= pd.Timestamp("2025-05-31")             # inicio real de la campana 11


def test_acumulado_por_modulo_incluye_dias_previos_y_marca_el_parcial():
    out = _aplicar()
    a = out["modulos_acumulado"].set_index("modulo")
    # El 30-sep (previo a la ventana) pertenece al modulo 1: cruza el borde del Caso.
    assert a.loc[1, "parcial_ventana"] and a.loc[1, "TMH_previa"] > 0
    assert not a.loc[2, "parcial_ventana"] and a.loc[2, "TMH_previa"] == 0
    assert a.TMS_ventana.sum() == pytest.approx(VENTANA_TMS)
    assert (a.TMH_acumulado - a.TMH_ventana - a.TMH_previa).abs().max() < 1e-9
    assert a.TMS_previa.sum() == pytest.approx(97.0)
