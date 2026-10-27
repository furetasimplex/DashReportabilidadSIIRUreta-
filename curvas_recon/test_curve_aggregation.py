from curvas_recon.curve_aggregation import (
    combine_recovery_series, delete_local_group, restore_local_groups, save_local_group,
)


def test_weighted_two_piles_use_cu_and_calendar_dates():
    combined = combine_recovery_series([
        {'id': 'OX-P01', 'cu_tf_t': 100, 'series': {'xs': ['2026-01-01', '2026-01-03'], 'ys': [10, 30]}},
        {'id': 'SU-P02', 'cu_tf_t': 300, 'series': {'xs': ['2026-01-01', '2026-01-03'], 'ys': [20, 40]}},
    ])
    assert combined['xs'][0].isoformat() == '2026-01-01'
    assert combined['cu_tf_t'] == [400.0, 400.0, 400.0]
    assert combined['recovered_cu_t'] == [70.0, None, 150.0]
    assert combined['ys'] == [17.5, None, 37.5]


def test_missing_member_and_none_keep_explicit_gaps_and_no_false_blue_case():
    combined = combine_recovery_series([
        {'id': 'OX-P01', 'cu_tf_t': 100, 'series': {
            'xs': ['2026-01-01', '2026-01-02', '2026-01-04'],
            'ys': [10, None, 40],
            'sources': ['Reconciliado del Caso'] * 3,
        }},
        {'id': 'SU-P02', 'cu_tf_t': 100, 'series': {
            'xs': ['2026-01-01', '2026-01-03', '2026-01-04'],
            'ys': [20, 30, 50],
            'sources': ['Reconciliado del Caso', 'Medido', 'Reconciliado del Caso'],
        }},
    ])
    assert [d.isoformat() for d in combined['xs']] == [
        '2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04']
    assert combined['ys'] == [15.0, None, None, 45.0]
    assert combined['sources'] == ['Reconciliado del Caso', 'Medido', 'Medido', 'Reconciliado del Caso']


def test_local_group_create_edit_delete_restore_and_active_member_validation():
    active = {'rox-P01', 'rsu-P02'}
    groups, msg = save_local_group([], None, '  Sulfuros + óxidos ',
                                  ['rox-P01', 'rsu-P02', 'rox-P01'], active)
    assert msg.startswith('Grupo guardado')
    group_id = groups[0]['id']
    assert groups[0]['members'] == ['rox-P01', 'rsu-P02']
    edited, msg = save_local_group(groups, group_id, 'Actualizado',
                                  ['rox-P01', 'rsu-P02'], active)
    assert len(edited) == 1 and edited[0]['name'] == 'Actualizado'
    rejected, msg = save_local_group(edited, group_id, 'Inactivo',
                                    ['rox-P01', 'su-P99'], active)
    assert rejected == edited and 'activas' in msg
    assert delete_local_group(edited, group_id) == []
    assert restore_local_groups() == []
