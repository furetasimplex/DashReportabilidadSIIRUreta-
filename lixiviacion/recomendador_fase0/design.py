"""Produce matriz documental, nunca ejecuta reglas ni asigna recomendaciones."""
from .audit import csvsave


def run():
    rows=[
    ('R01','Pausa hidráulica prolongada',"estado_operacional='PAUSA_HIDRAULICA'",'OP','Sí','Días consecutivos','B. REQUIERE_UMBRAL','Pausa prevista en estrategia de riego','MEDIO'),
    ('R02','Drenaje residual prolongado',"estado_operacional='DRENAJE_RESIDUAL'",'OP','Sí','Duración por etapa/campaña','B. REQUIERE_UMBRAL','Drenaje residual normal, sin caudal de drenaje medido','MEDIO'),
    ('R03','Drenaje con riego pausado prolongado',"estado_operacional='DRENAJE_CON_RIEGO_PAUSADO'",'OP','Sí','Duración y plan de pausas','B. REQUIERE_UMBRAL','Intermitencia de riego planificada','MEDIO'),
    ('R04','Conformado sin inicio de riego',"estado_operacional='CONFORMADO_PRE_RIEGO'",'OP','Sí para atención','Plazo desde conformado y fecha planificada','B. REQUIERE_UMBRAL','Espera normal; primer riego de campaña no necesariamente por módulo','MEDIO'),
    ('R05','Riego activo sin drenaje observable',"riego_activo=1 AND tiene_dato_drenaje=1 AND drenaje_activo=0",'OP','Sí para anomalía','Latencia esperada entre riego y señal Cu','C. REQUIERE_REGLA_NEGOCIO','Cu=0 no prueba ausencia de caudal de drenaje','MEDIO'),
    ('R06','Drenaje activo sin riego actual',"drenaje_activo=1 AND tiene_dato_riego=1 AND riego_activo=0",'OP','No para hecho','Ninguno para detección','A. DETECTABLE_HOY','Normal después de riego; actividad de drenaje es proxy químico','BAJO'),
    ('R07','Riego inactivo con cobertura',"tiene_dato_riego=1 AND riego_activo=0",'OP','No para hecho','Ninguno para detección','A. DETECTABLE_HOY','Normal en etapas sin riego; inactivo no significa caudal exactamente cero','BAJO'),
    ('R08','Drenaje inactivo con cobertura',"tiene_dato_drenaje=1 AND drenaje_activo=0",'OP','No para hecho','Ninguno para detección','A. DETECTABLE_HOY','No significa drenaje físico nulo','BAJO'),
    ('R09','Calidad PARCIAL prolongada',"calidad_estado='PARCIAL'",'OP','Sí','Días consecutivos y cobertura necesaria','B. REQUIERE_UMBRAL','Mixto con componente sin cobertura; no falla de toda parcela','MEDIO'),
    ('R10','No evaluable',"calidad_estado='NO_EVALUABLE'",'OP','No para hecho','Ninguno para detección','A. DETECTABLE_HOY','No implica inactividad ni anomalía metalúrgica','BAJO'),
    ('R11','Sin información hidráulica',"estado_operacional='SIN_COBERTURA_HIDRAULICA' OR riego_activo IS NULL OR drenaje_activo IS NULL",'OP','No para hecho','Ninguno para detección','A. DETECTABLE_HOY','Puede haber registros todos NULL; ausencia de campaña es otra condición','BAJO'),
    ('R12','Delta Cu negativo',"delta_cu_gl IS NOT NULL AND delta_cu_gl<0",'V2','No para hecho; sí posiblemente para atención','Persistencia/magnitud/flujo mínimo sin definir','A. DETECTABLE_HOY','Transitorio, desfase de muestras o flujo cero; no demuestra falla','BAJO'),
    ('R13','Transferencia Cu negativa',"transferencia_cu_t_d IS NOT NULL AND transferencia_cu_t_d<0",'V2','No para hecho; sí posiblemente para atención','Magnitud/flujo mínimo sin definir','A. DETECTABLE_HOY','Signo depende también del flujo y redondeo; no basta para intervenir','BAJO'),
    ('R14','Flujo positivo fuera de ventana',"flujo_m3_d>0 AND estado_asignacion='FUERA_VENTANA_RIEGO'",'V2','No para hecho','Ninguno para detección','A. DETECTABLE_HOY','Asignación hidráulica no equivale a inactividad operacional','BAJO'),
    ('R15','Mixto prolongado',"estado_operacional='MIXTO'",'OP','Sí','Coexistencias admitidas por módulos/campaña','C. REQUIERE_REGLA_NEGOCIO','Coexistencia normal de módulos; duración sola no vuelve anómalo MIXTO','MEDIO'),
    ('R16','Reposo pre reclamo prolongado',"estado_operacional='REPOSO_PRE_RECLAMO'",'OP','Sí','Plazo y programación de reclamo','B. REQUIERE_UMBRAL','Espera normal de recursos/plan; no prescribir reclamo','MEDIO'),
    ('R17','Apilado más allá del cierre esperado',"estado_operacional='APILADO'; falta fecha de cierre PLANIFICADA",'OP + plan no disponible','Sí','Fecha objetivo y tolerancia no disponibles','D. NO_RECOMENDABLE_AUN','fecha_conformado real no sustituye un plan de cierre','ALTO'),
    ('R18','Reclamo prolongado',"estado_operacional='RECLAMO'",'OP','Sí','Plazo esperado/pausas planificadas','B. REQUIERE_UMBRAL','Duración responde a plan; riesgo si induce cambiar reclamo','MEDIO')]
    out=[]
    for id,name,condition,source,duration,threshold,maturity,false,risk in rows:
        out.append({'ID regla':id,'Nombre':name,'Hecho detectable':condition,'Fuente':source,'Condición técnica':condition,
          'Grano':'PAD+parcela+fecha','Necesita duración':duration,'Umbral requerido':threshold,
          'Umbral definido hoy':'No; solo predicados de detección y umbrales heredados de clasificación SQL',
          'Prioridad definida':'REQUIERE DEFINICIÓN DE NEGOCIO','Acción definida':'REQUIERE DEFINICIÓN DE NEGOCIO',
          'Riesgo de falso positivo':false,'Dependencia de calidad':'OP: evaluar calidad y flags; V2: NULL/unidades/cobertura propia, calidad OP no certifica química',
          'Estado de madurez':maturity,'Riesgo automatización':risk})
    csvsave('matriz_reglas.csv',out)


if __name__=='__main__':run()
