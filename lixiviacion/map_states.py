"""Etiquetas y fases exclusivamente visuales; estado_operacional permanece intacto."""
FASES = {
    'APILADO': ('Apilado','stacked'),
    'CONFORMADO_PRE_RIEGO': ('Conformado / espera de riego','formed'),
    'CICLO_HIDRAULICO': ('Ciclo hidráulico','hydraulic'),
    'ESPERA_RECLAMO': ('Espera de reclamo','waiting'),
    'RECLAMO': ('Reclamo','reclaiming'),
    'RECLAMADO': ('Reclamado','reclaimed'),
    'MIXTO': ('Mixto','mixed'),
    'NO_EVALUABLE': ('Sin información / no evaluable','missing'),
}
ESTADOS = {
    'APILADO': ('APILADO','Apilado'),
    'CONFORMADO_PRE_RIEGO': ('CONFORMADO_PRE_RIEGO','Conformado / espera de riego'),
    'RIEGO': ('CICLO_HIDRAULICO','Riego'),
    'RIEGO_DRENAJE': ('CICLO_HIDRAULICO','Riego + drenaje'),
    'DRENAJE_CON_RIEGO_PAUSADO': ('CICLO_HIDRAULICO','Drenaje con riego pausado'),
    'PAUSA_HIDRAULICA': ('CICLO_HIDRAULICO','Pausa hidráulica'),
    'DRENAJE_RESIDUAL': ('CICLO_HIDRAULICO','Drenaje residual'),
    'REPOSO_PRE_RECLAMO': ('ESPERA_RECLAMO','Espera de reclamo'),
    'RECLAMO': ('RECLAMO','Reclamo'),
    'RECLAMADO': ('RECLAMADO','Reclamado'),
    'MIXTO': ('MIXTO','Mixto'),
    'SIN_INFORMACION': ('NO_EVALUABLE','Sin información'),
    'SIN_COBERTURA_HIDRAULICA': ('NO_EVALUABLE','Sin cobertura hidráulica'),
    'SIN_CLASIFICAR': ('NO_EVALUABLE','Sin clasificar'),
}
CALIDAD = {'EVALUABLE':'Evaluado', 'PARCIAL':'Información parcial',
           'NO_EVALUABLE':'No evaluable', 'SIN_INFORMACION':'Sin información'}


def fase_visual(estado_operacional):
    if estado_operacional not in ESTADOS:
        raise ValueError('Estado operacional SQL no soportado. Revisar contrato antes de representarlo.')
    return ESTADOS[estado_operacional][0]


def actividad(tiene_dato, activo):
    if tiene_dato != 1 or activo is None:
        return 'Sin dato'
    return {1:'Sí', 0:'No'}.get(activo, 'Sin dato')
