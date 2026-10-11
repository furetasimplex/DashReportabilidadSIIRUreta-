from report_export.layouts.reportabilidad_page import _report_card


def _component_ids(component):
    ids = []
    component_id = getattr(component, "id", None)
    if component_id is not None:
        ids.append(component_id)
    children = getattr(component, "children", None)
    if children is None:
        return ids
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        if hasattr(child, "children") or getattr(child, "id", None) is not None:
            ids.extend(_component_ids(child))
    return ids


def test_representatividad_no_renderiza_descargas_vigentes():
    ids = _component_ids(
        _report_card("Torres", "Detalle", "representatividad_torres")
    )

    assert {"type": "report-gen-btn", "tipo": "representatividad_torres"} in ids
    assert not any(
        isinstance(component_id, dict)
        and component_id.get("type") in {"report-export-btn", "report-pdf-btn"}
        for component_id in ids
    )


def test_otros_reportes_conservan_botones_genericos():
    ids = _component_ids(_report_card("Balance", "Detalle", "balance"))

    assert {"type": "report-export-btn", "tipo": "balance"} in ids
    assert {"type": "report-pdf-btn", "tipo": "balance"} in ids
