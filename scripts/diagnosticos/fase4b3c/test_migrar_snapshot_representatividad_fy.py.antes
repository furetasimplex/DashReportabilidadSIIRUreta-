from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from scripts.admin import migrar_snapshot_representatividad_fy as sut


def _df(tipo="Q"):
    reps = (14, 28) if tipo == "Q" else (8, 13)
    return pd.DataFrame({
        "Etiqueta": ["Jul-26", "Ago-26", "YTD"],
        "Turnos_Evaluables": [114, 88, 202],
        "Turnos_Representativos": [14 if tipo == "Q" else 5, *reps],
        "Representatividad": [(14 if tipo == "Q" else 5) / 114, reps[0] / 88, reps[1] / 202],
    })


def _meta():
    return sut.MetadataReporte(110, "2026-08", date(2026, 8, 1), date(2026, 8, 31), date(2026, 8, 23), 2027, 1, "FINALIZADO", "tester")


def test_recalculo_usa_corte_historico_y_serializador_inyectado():
    fetch = Mock(side_effect=[_df("Q"), _df("F")])
    nuevos = sut.recalcular(_meta(), fetch)
    assert all(c.kwargs["fecha_corte"] == date(2026, 8, 23) for c in fetch.call_args_list)
    serializer = Mock(return_value="[]")
    sut.serializar(nuevos, serializer)
    assert serializer.call_count == 2


@pytest.mark.parametrize("nuevos", [{sut.BLOQUES[0]: pd.DataFrame(), sut.BLOQUES[1]: _df("F")}, {}])
def test_aborta_si_recalculo_vacio_o_faltante(nuevos):
    with pytest.raises(RuntimeError):
        sut.validar_recalculo(_meta(), nuevos)


class _Result:
    def __init__(self, rowcount): self.rowcount = rowcount


class _Tx:
    def __init__(self, rowcounts): self.rowcounts = iter(rowcounts); self.calls = []
    def __enter__(self): return self
    def __exit__(self, typ, value, tb): self.rolled_back = typ is not None
    def execute(self, _sql, params): self.calls.append(params); return _Result(next(self.rowcounts))


class _Engine:
    def __init__(self, rowcounts): self.tx = _Tx(rowcounts)
    def begin(self): return self.tx


def test_apply_actualiza_exactamente_dos_bloques():
    engine = _Engine([1, 1])
    sut.aplicar(engine, 110, {b: {"payload": "[]", "filas": 0} for b in sut.BLOQUES})
    assert [c["bloque"] for c in engine.tx.calls] == list(sut.BLOQUES)
    assert engine.tx.rolled_back is False


def test_rowcount_invalido_provoca_rollback():
    engine = _Engine([1, 0])
    with pytest.raises(RuntimeError):
        sut.aplicar(engine, 110, {b: {"payload": "[]", "filas": 0} for b in sut.BLOQUES})
    assert engine.tx.rolled_back is True


def test_dry_run_no_aplica(monkeypatch, capsys):
    monkeypatch.setattr(sut, "identificar_destino", lambda _e: {"server_name": "dev", "database_name": "dev", "login_name": "u", "entorno": "3"})
    anteriores = {b: {"payload": sut._dataframe_a_snapshot_json(_df("Q" if b.endswith("quimico") else "F")), "filas": 3} for b in sut.BLOQUES}
    monkeypatch.setattr(sut, "leer_estado", lambda _e, _id: (_meta(), anteriores))
    aplicar = Mock()
    monkeypatch.setattr(sut, "aplicar", aplicar)
    sut.ejecutar(110, engine=object(), fetch_fn=Mock(side_effect=[_df("Q"), _df("F")]))
    aplicar.assert_not_called()
    assert "DRY-RUN" in capsys.readouterr().out


def test_falta_bloque_aborta():
    class Result:
        def __init__(self, rows): self.rows = rows
        def mappings(self): return self
        def one_or_none(self): return self.rows
        def all(self): return self.rows
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def execute(self, sql, _params):
            if "FROM inventar_SpcHidr.reporte_torre_oficial_cab" in str(sql): return Result(_meta().__dict__)
            return Result([{"bloque": sut.BLOQUES[0], "payload": "[]", "filas": 0}])
    class Engine:
        def connect(self): return Conn()
    with pytest.raises(RuntimeError, match="exactamente"):
        sut.leer_estado(Engine(), 110)


def test_backup_no_contiene_credenciales(tmp_path: Path):
    actuales = {b: {"payload": "[]", "filas": 0} for b in sut.BLOQUES}
    ruta = sut.crear_backup(_meta(), actuales, tmp_path)
    texto = ruta.read_text(encoding="utf-8")
    assert "password" not in texto.lower()
    assert set(__import__("json").loads(texto)["bloques"]) == set(sut.BLOQUES)
