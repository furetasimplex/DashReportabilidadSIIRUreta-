"""Invalidaci?n de corridas previas a cambios del m?todo de reconciliaci?n."""
import pickle

import pandas as pd

from . import pad_dashboard as dashboard


def test_raw_nuevo_se_puede_cargar(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, '_RECON_RAW_DIR', str(tmp_path))
    caso = {'id': 10013}
    token = dashboard._save_recon_raw({'piles': []}, caso,
                                      pd.Timestamp('2026-08-01'),
                                      pd.Timestamp('2026-08-03'))

    raw, _ = dashboard._load_recon_raw(token, 10013)

    assert raw['payload_version'] == dashboard._RECON_RAW_PAYLOAD_VERSION
    assert raw['caso'] == caso


def test_raw_legacy_del_mismo_caso_se_rechaza(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, '_RECON_RAW_DIR', str(tmp_path))
    caso = {'id': 10013}
    token = dashboard._save_recon_raw({'piles': []}, caso,
                                      pd.Timestamp('2026-08-01'),
                                      pd.Timestamp('2026-08-03'))
    path = dashboard._recon_raw_path(token)
    with open(path, 'wb') as fh:
        # Payload legacy con identidad de Caso válida, pero sin versión.
        pickle.dump(dict(res={'piles': []}, caso=caso,
                         ws=pd.Timestamp('2026-08-01'),
                         we=pd.Timestamp('2026-08-03')), fh)

    raw, returned_path = dashboard._load_recon_raw(token, 10013)

    assert raw is None
    assert returned_path == path


def test_raw_de_otra_version_se_rechaza(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, '_RECON_RAW_DIR', str(tmp_path))
    caso = {'id': 10013}
    token = dashboard._save_recon_raw({'piles': []}, caso,
                                      pd.Timestamp('2026-08-01'),
                                      pd.Timestamp('2026-08-03'))
    path = dashboard._recon_raw_path(token)
    with open(path, 'rb') as fh:
        raw = pickle.load(fh)
    raw['payload_version'] += 1
    with open(path, 'wb') as fh:
        pickle.dump(raw, fh)

    loaded, returned_path = dashboard._load_recon_raw(token, 10013)

    assert loaded is None
    assert returned_path == path
