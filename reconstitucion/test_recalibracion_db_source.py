from datetime import date
from types import SimpleNamespace

import recalibracion_db_source as source


class _Mappings:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return _Mappings(self.rows)


class _Connection:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params):
        self.engine.calls.append((str(statement), dict(params)))
        return _Result(self.engine.rows)


class _Engine:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []

    def connect(self):
        return _Connection(self)


def _dbs(engine):
    return SimpleNamespace(
        SCHEMA="inventar_SpcHidr.inventar_SpcHidr",
        get_engine=lambda: engine,
    )


def test_campaign_history_anchors_identity_and_bounds_shared_history(monkeypatch):
    engine = _Engine([{"pad_id": 2, "campana_id": 13, "modulo_id": 72}])
    monkeypatch.setattr(source, "_db_source", lambda: _dbs(engine))

    rows = source.load_campaign_history(
        date(2026, 10, 12), scopes=[(2, 13, 12)], engine=engine
    )

    assert rows == [{"pad_id": 2, "campana_id": 13, "modulo_id": 72}]
    sql, params = engine.calls[0]
    assert "WITH bounds AS" in sql
    assert "anchor.[campaña_id] = :anchor_campaign_0" in sql
    assert "anchor.[campaña] = :anchor_visible_0" in sql
    assert "cad.fecha >= b.fecha_inicio" in sql
    assert "cad.pad_id IN" not in sql
    assert "LEFT JOIN [inventar_SpcHidr].[inventar_SpcHidr].modulo AS md" in sql
    assert params["anchor_pad_0"] == 2
    assert params["anchor_campaign_0"] == 13
    assert params["anchor_visible_0"] == 12
    assert params["cutoff"] == date(2026, 10, 12)
    assert "volumen_acumulado_final_apilado_m3 AS vol_acum_final" in sql


def test_fixed_modules_reads_direct_wet_tonnage_for_exact_identity(monkeypatch):
    engine = _Engine([{"campana_id": 13, "modulo_id": 72, "campana": 12,
                       "tmh_apilado": None, "fecha_cierre": None}])
    monkeypatch.setattr(source, "_db_source", lambda: _dbs(engine))

    rows = source.load_fixed_modules(
        date(2026, 10, 12), scopes=[(2, 13, 12)], engine=engine
    )

    assert rows[0]["tmh_apilado"] is None
    assert rows[0]["fecha_cierre"] is None
    sql, params = engine.calls[0]
    assert "vb.estado_congelamiento = 'CONGELADO'" in sql
    assert "vb.fecha_congelamiento IS NULL OR" in sql
    assert "vb.fecha_cierre IS NULL OR" in sql
    assert sql.count("DATEADD(day, 1, CAST(:cutoff AS date))") == 2
    assert "dr.tmh_apilado AS tmh_apilado" in sql
    assert "dr.[campaña] AS campana" in sql
    assert "dr.[campaña_id] = vb.[campaña_id]" in sql
    assert "dr.modulo_id = vb.modulo_id" in sql
    assert "dr.pad_id = vb.pad_id" in sql
    assert "LEFT JOIN [inventar_SpcHidr].[inventar_SpcHidr].disponible_rotopalas" in sql
    assert "vb.[campaña_id] = :campaign_0" in sql
    assert "AND ((vb.pad_id = :pad_0 AND vb.[campaña_id] = :campaign_0 AND dr.[campaña] = :visible_0))" in sql
    assert "OR dr.[campaña] IS NULL" not in sql
    assert "humedad" not in sql.lower()
    assert params["cutoff"] == date(2026, 10, 12)
    assert params["pad_0"] == 2
    assert params["campaign_0"] == 13
    assert params["visible_0"] == 12


def test_scope_identity_uses_internal_ids_and_visible_campaign_as_anchor():
    assert source.scope_campaign_identity({
        "pad_id": 2, "campana_id": 13, "campana": 12
    }) == (2, 13)
    assert source._scope_anchor((1, 17, 8)) == (1, 17, 8)
    assert source._scope_anchor((1, 17)) == (1, 17, None)
