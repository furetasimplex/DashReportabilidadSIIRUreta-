import ast
from pathlib import Path


def test_accumulated_rl_has_separate_lazy_callback_and_tab():
    source = Path(__file__).with_name('pad_dashboard.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == 'render_rl_acumulada_chart')
    source_fn = ast.get_source_segment(source, fn)
    assert "tab_value != 'tab-rl-acum'" in source_fn
    assert "accumulated=True" in source_fn
    assert "curvas-recon-chart-rl-acum" in source
    assert "value='tab-rl-acum'" in source


def test_existing_daily_rl_tab_keeps_its_own_callback_path():
    source = Path(__file__).with_name('pad_dashboard.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == 'render_rl_chart')
    source_fn = ast.get_source_segment(source, fn)
    assert "tab_value != 'tab-rl'" in source_fn
    assert 'accumulated=True' not in source_fn


def test_inactive_accumulated_callback_does_not_access_sql_or_metadata():
    source=Path(__file__).with_name('pad_dashboard.py')
    tree=ast.parse(source.read_text(encoding='utf8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render_rl_acumulada_chart')
    def forbidden(*args,**kwargs):
        raise AssertionError('Inactive tab must not read data')
    ns={'empty_figure':lambda *args:'not selected','_store_matches_case':forbidden,
        'ensure_full_data':forbidden,'_get_group_raw':forbidden,'_rl_tms_by_pile':forbidden}
    fn.decorator_list=[]
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),ns)
    assert ns[fn.name]('tab-rec',{},None,None,[],10013)=='not selected'


def test_accumulated_tab_visibility_does_not_show_another_chart():
    source=Path(__file__).with_name('pad_dashboard.py')
    tree=ast.parse(source.read_text(encoding='utf8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='switch_recon_pila_tab')
    ns={}
    fn.decorator_list=[]
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),ns)
    styles=ns[fn.name]('tab-rl-acum','some-group')
    assert len(styles)==7
    assert [i for i,s in enumerate(styles) if s.get('display')=='block']==[6]
