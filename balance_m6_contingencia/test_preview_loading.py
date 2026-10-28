from unittest.mock import patch
import pytest
from dash import no_update
from . import panel,service
from .test_presentation import auth,args,source,comparison,dump

@pytest.mark.parametrize('selected',[[],None,['outside-query']])
def test_invalid_selection_never_reads_or_simulates(auth,selected):
    a=args();a[9]=selected
    with patch.object(panel,'ctx') as ctx,patch.object(service,'load_rows') as read,patch.object(service,'preview') as preview,patch.object(service,'persist') as persist:
        ctx.triggered_id='m6ct-preview'
        result=panel.handle_action(*a)
        assert result[1] is None and result[4] is no_update
        assert 'Sin previsualización válida' in dump(result[0])
        read.assert_not_called();preview.assert_not_called();persist.assert_not_called()

@pytest.mark.parametrize('missing',['selection','motive','consent'])
def test_save_missing_requirement_never_persists_even_with_prior_preview(auth,missing):
    a=args()
    with patch.object(panel,'ctx') as ctx,patch.object(service,'load_rows',return_value=source()),patch.object(service,'preview',return_value=dict(comparacion=comparison(),huella_entradas='B'*64)),patch.object(service,'persist') as persist:
        ctx.triggered_id='m6ct-preview';a[13]=panel.act(*a)[1];a[14]=['SI']
        if missing=='selection':a[9]=[]
        elif missing=='motive':a[11]=' '
        else:a[14]=[]
        ctx.triggered_id='m6ct-guardar';result=panel.handle_action(*a)
        assert result[1] is None and result[4] is no_update
        persist.assert_not_called()

def test_failed_preview_clears_old_impact_and_can_retry(auth):
    a=args()
    with patch.object(panel,'ctx') as ctx,patch.object(service,'load_rows',return_value=source()),patch.object(service,'preview',side_effect=RuntimeError('private failure')) as preview,patch.object(service,'persist') as persist:
        ctx.triggered_id='m6ct-preview';failed=panel.handle_action(*a)
        assert failed[0] is not no_update and failed[1] is None
        assert 'No se completó la operación' in dump(failed[2]) and 'private failure' not in dump(failed[2])
        preview.side_effect=None;preview.return_value=dict(comparacion=comparison(),huella_entradas='B'*64)
        ok=panel.handle_action(*a)
        assert ok[1] and ok[3]==[] and ok[4] is no_update
        assert 'Previsualización completada' in dump(ok[2])
        persist.assert_not_called()
