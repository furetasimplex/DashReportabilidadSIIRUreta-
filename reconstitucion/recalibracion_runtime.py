"""SELECT-only orchestration for the sequential method, from initial campaign data."""
import time

import numpy as np
import pandas as pd

from .modelo_flujos import FlowCaseError


def _sin_masa(caso, fuente, start=None, end=None):
    ventana = f" ({start:%Y-%m-%d} a {end:%Y-%m-%d})" if start is not None else ''
    if fuente == 'oficial':
        return (f"El Caso #{caso['id']} no tiene masa en Datos_conciliados_of_ver ni en los libros Excel{ventana}; "
                'no se reemplaza con Datos_conciliados_of.')
    return 'Falta masa conciliada de la campaña en DB.'


def _official_cuts(end):
    """Fechas de fin de los Casos oficiales hasta el corte; sin Casos futuros."""
    from curvas_recon.db_pipeline import load_casos
    return sorted({pd.Timestamp(c['fecha_fin']).normalize() for c in load_casos()
                   if pd.Timestamp(c['fecha_fin']).normalize() <= end})


def _window_profile(conciliado, start, end):
    """Perfil de la ventana con la masa conciliada, para horas y TMH diaria."""
    from .secuencia_campana import TMH_DIA_MAX
    acum = {}
    for row in conciliado.loc[conciliado.fecha.between(start, end)].itertuples(index=False):
        a, b = float(np.nan_to_num(row.tmh_a)), float(np.nan_to_num(row.tmh_b))
        wet = a + b
        if wet > TMH_DIA_MAX:
            a, b, wet = 0.0, 0.0, 0.0
        if wet > 0 and not np.isfinite(row.tms):
            raise FlowCaseError(f'{row.fecha:%Y-%m-%d}: TMH conciliada sin TMS.')
        dry_rate = float(row.tms) / wet if wet > 0 else 0.0
        # Un dia puede traer filas de ambos PAD (libro): se suman por fecha y turno.
        for turno, masa in (('A', a), ('B', b)):
            tmh, tms = acum.get((row.fecha, turno), (0.0, 0.0))
            acum[(row.fecha, turno)] = (tmh + masa, tms + masa * dry_rate)
    rows = [dict(fecha=f, turno=t, tmh=tmh, humedad=100.0 * (1.0 - tms / tmh) if tmh > 0 else 0.0)
            for (f, t), (tmh, tms) in sorted(acum.items())]
    return pd.DataFrame(rows, columns=['fecha', 'turno', 'tmh', 'humedad'])


def _aviso_excepciones(excepciones, start, end):
    """Avisos de la ventana: el resumen informativo y uno visible por factor fuera de tolerancia."""
    resumen = _resumen_excepciones(excepciones, start, end)
    if excepciones.empty:
        return [resumen]
    k = excepciones.loc[excepciones.tipo.eq('FACTOR_FLUJO_FUERA_TOLERANCIA')]
    from . import validacion as v
    return [resumen] + [v.Aviso('dato', 'factor_flujo_fuera_tolerancia', d) for d in k.detalle]


def _resumen_excepciones(excepciones, start, end):
    """Resume las excepciones de la ventana del Caso; la lista completa queda en el resultado."""
    from . import validacion as v
    ventana = excepciones.loc[excepciones.fecha.between(start, end)] if not excepciones.empty else excepciones
    if ventana.empty:
        return None
    resumen = ', '.join(f'{tipo}: {len(g)} día(s)' for tipo, g in ventana.groupby('tipo'))
    return v.Aviso('info', 'excepciones_reparto', f'Excepciones en la ventana del Caso. {resumen}.')


def load_runtime_recalibration(result, caso, targets, masa_fuente='oficial'):
    from .recalibracion_db_source import load_campaign_history, load_fixed_modules, load_masa_fuente
    from .recalibracion_adapter import apply_recalibrated_distribution
    from .recalibracion_mr import RecalibrationError

    if masa_fuente not in ('oficial', 'of'):
        raise FlowCaseError(f'Fuente de masa inválida: {masa_fuente!r}.')
    began = time.perf_counter()
    from . import masa_fuentes
    try:
        inicio = masa_fuentes.inicio_metodo_digital()
    except ValueError as exc:
        raise FlowCaseError(str(exc)) from exc
    start = pd.Timestamp(caso['fecha_inicio']).normalize()
    end = pd.Timestamp(caso['fecha_fin']).normalize()
    ap = result['apilado']
    positive_pads = [int(pad) for pad, value in targets.items()
                     if float(value['masa_reconciliada']) > 0]
    missing_id = {'pad_id', 'campana_id', 'campana'} - set(ap.columns)
    if missing_id:
        raise FlowCaseError(f'Falta identidad PAD/campaña para recalibrar la densidad: {sorted(missing_id)}.')
    active = ap.loc[ap.pad_id.isin(positive_pads) & ap.vol_diario.gt(0)]
    if active[['pad_id', 'campana_id', 'campana']].isna().any().any():
        raise FlowCaseError('Falta identidad PAD/campaña para recalibrar la densidad.')
    scopes = [tuple(int(x) for x in row) for row in active[
        ['pad_id', 'campana_id', 'campana']].drop_duplicates().itertuples(index=False, name=None)]
    if not scopes:
        raise FlowCaseError('No hay campaña activa con masa positiva para recalibrar.')
    history = load_campaign_history(end, scopes=scopes)
    hist = pd.DataFrame(history)
    if hist.empty or 'fecha' not in hist:
        raise FlowCaseError('Falta historia de campaña en DB para recalibrar la densidad.')
    first = pd.to_datetime(hist.fecha).min().normalize()
    # Regimen por Caso: previo (todo el Caso antes de la puesta en marcha) cierra con la fuente;
    # digital (fecha_fin >= puesta en marcha) cierra con el flujo. 'of' es testeo y escala como el digital.
    regimen = 'of' if masa_fuente == 'of' else ('previo' if end < inicio else 'digital')
    conciliado, excepciones_fuente = load_masa_fuente(first, end, fuente=masa_fuente, caso_id=caso['id'],
                                                      caso_inicio=start, inicio=inicio)
    if regimen == 'digital' and start < inicio:
        excepciones_fuente = pd.concat([excepciones_fuente, pd.DataFrame([dict(
            fecha=start, tipo='CASO_CRUZA_PUESTA_EN_MARCHA', tmh=0.0, tms=0.0,
            detalle=f"El Caso ({start:%Y-%m-%d} a {end:%Y-%m-%d}) cruza la puesta en marcha {inicio:%Y-%m-%d}: "
                    "régimen digital, cierra con el flujo.")])], ignore_index=True)
    conciliado = pd.DataFrame(conciliado)
    if conciliado.empty or 'fecha' not in conciliado:
        raise FlowCaseError(_sin_masa(caso, masa_fuente))
    conciliado['fecha'] = pd.to_datetime(conciliado.fecha).dt.normalize()
    if masa_fuente == 'oficial' and not conciliado.fecha.between(start, end).any():
        raise FlowCaseError(_sin_masa(caso, masa_fuente, start, end))
    for col in ('tmh_a', 'tmh_b', 'tms'):
        conciliado[col] = pd.to_numeric(conciliado[col], errors='coerce')
    # El libro no usa estados de congelamiento: se informan, no alteran el calculo.
    congelados = load_fixed_modules(end, scopes=scopes)
    cadena = dict(conciliado=conciliado, cortes=_official_cuts(end), fuente=masa_fuente, regimen=regimen,
                  excepciones_fuente=excepciones_fuente)
    try:
        updated = apply_recalibrated_distribution(
            result, history, _window_profile(conciliado, start, end), [], caso, cadena=cadena)
    except RecalibrationError as exc:
        raise FlowCaseError(str(exc)) from exc
    st = updated['shift_table']
    dates = pd.to_datetime(st.fecha)
    if not dates.between(start, end).all():
        raise FlowCaseError('La distribución contiene fechas fuera de la ventana del Caso.')
    cal = updated['recalibracion_mr'].drop_duplicates('pad_id').set_index('pad_id')
    for pad, target in targets.items():
        assigned = float(st.loc[st.pad_id.eq(int(pad)), 'masa_total'].sum())
        if regimen == 'previo':  # cierra con la fuente; la diferencia contra el flujo es pendiente visible
            expected = float(cal.tms_of_ventana.get(int(pad), 0.0))
            if not np.isclose(assigned, expected, rtol=1e-10, atol=1e-6):
                raise FlowCaseError(f'PAD {pad}: la distribución secuencial no cierra con la fuente de masa.')
            continue
        if not np.isclose(assigned, float(target['masa_reconciliada']), rtol=1e-10, atol=1e-6):
            raise FlowCaseError(f'PAD {pad}: la distribución secuencial no cierra con el Caso.')
    source = updated.get('fuente_modelo', {})
    if (int(source.get('id', -1)) != int(caso['id'])
            or str(source.get('run_id')) != str(caso['run_id'])):
        raise FlowCaseError('El Caso o run de la distribución no corresponde a la selección.')
    from . import validacion as v
    nuevos = [a for a in _aviso_excepciones(updated['excepciones_reparto'], start, end) if a is not None]
    ventana = conciliado.loc[conciliado.fecha.between(start, end)]
    por_fuente = ventana.groupby('fuente').fecha.nunique().to_dict()
    uso = ', '.join(f'{k} {n} día(s)' for k, n in sorted(por_fuente.items())) or 'sin masa en la ventana'
    en_libro = int(por_fuente.get('LIBRO_EXCEL', 0))
    flujo = {int(p): float(t['masa_reconciliada']) for p, t in targets.items()}
    tabla = st.groupby('pad_id').masa_total.sum().to_dict()
    pendiente = {p: flujo[p] - float(tabla.get(p, 0.0)) for p in flujo}
    resumen_k = ', '.join(f"PAD {int(p)}: k informado {r.factor_flujo_of:.6f}" for p, r in cal.iterrows()
                          if np.isfinite(r.factor_flujo_of))
    if regimen == 'previo':
        cierre = (f"Régimen previo (Caso anterior a la puesta en marcha {inicio:%Y-%m-%d}): la tabla cierra con la fuente, "
                  f"sin escalar al flujo; pendiente contra el flujo {sum(pendiente.values()):+.3f} TMS "
                  f"({'; '.join(f'PAD {p}: flujo {flujo[p]:.3f}, tabla {tabla.get(p, 0.0):.3f}' for p in flujo)}). {resumen_k}.")
    elif regimen == 'digital':
        cierre = f'Régimen digital: la tabla cierra con el flujo reconciliado. {resumen_k}.'
    else:
        cierre = f'La tabla se escala por PAD al flujo del Caso. {resumen_k}.'
    nota = (('MODO DE TESTEO, no oficial. ' if masa_fuente == 'of' else '') +
            f"Masa por turno ({'Datos_conciliados_of' if masa_fuente == 'of' else 'Datos_conciliados_of_ver y libros Excel'}): "
            f'{uso}. {cierre}')
    nuevos += ([v.Aviso('dato', 'masa_de_libro', f'{en_libro} día(s) de la ventana sin masa en ver: se usó la masa de los '
                f'libros Excel (anteriores a la puesta en marcha, CSV versionado), directa por PAD.', en_libro)]
               if en_libro else [])
    if regimen == 'previo' and any(abs(x) > 1e-6 for x in pendiente.values()):
        nuevos.append(v.Aviso('dato', 'flujo_pendiente_vs_fuente', cierre, 1))
    # La distribución previa al gancho usaba el perfil de correas: sus avisos ya no aplican.
    previos = [a for a in updated.get('avisos_entrada', []) if getattr(a, 'codigo', None) != 'perfil_caso_distribuido']
    updated['masa_fuente'] = masa_fuente
    updated['regimen_masa'] = regimen
    bal = updated['balance_flujos'].copy()
    bal['fuente_t'] = bal.pad_id.map(lambda p: float(cal.tms_of_ventana.get(int(p), 0.0)))
    bal['tabla_t'] = bal.pad_id.map(lambda p: float(tabla.get(int(p), 0.0)))
    bal['pendiente_t'] = bal.objetivo_t - bal.tabla_t
    bal['regimen'] = regimen
    updated['balance_flujos'] = bal
    marca = [v.Aviso('dato', 'masa_no_oficial', nota)] if masa_fuente != 'oficial' else [v.Aviso('info', 'masa_caso_secuencial', nota)]
    updated['avisos_entrada'] = previos + marca + nuevos
    revisados = [a for a in v.revisar_resultado(updated)
                 if not (regimen == 'previo' and a.codigo == 'masa_pendiente_sin_volumen')]
    updated['avisos'] = updated['avisos_entrada'] + revisados
    updated.setdefault('_phase_seconds', {})['recalibracion_db'] = time.perf_counter() - began
    updated['congelados_db'] = pd.DataFrame(congelados)
    updated.pop('_intraday_profile', None)
    return updated
