"""Prepara DDL y rollback DEV desde definiciones respaldadas, sin conectarse a SQL."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP = ROOT / 'backup'
DDL = ROOT / 'ddl'
DDL.mkdir(exist_ok=True)


def leer(nombre):
    return (BACKUP / (nombre + '.sql')).read_bytes().decode('utf-8').replace('\r\r\n', '\n').replace('\r\n', '\n')


def escribir(nombre, sql, nuevo=False):
    (DDL / (nombre + '.sql')).write_text(sql, encoding='utf-8')
    rollback = (f'DROP VIEW {nombre};' if nuevo else leer(nombre).replace('CREATE   VIEW', 'ALTER VIEW', 1)
                .replace('CREATE VIEW', 'ALTER VIEW', 1).replace('CREATE   PROCEDURE', 'ALTER PROCEDURE', 1)
                .replace('CREATE PROCEDURE', 'ALTER PROCEDURE', 1))
    (ROOT / ('rollback_' + nombre + '.sql')).write_text(rollback, encoding='utf-8')


RT = 'inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno'
RO = 'inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test'

# La variante de Balance lee RT solo en los bloques post-cutover de CV006,
# CV008/CV108 y SRR. La fuente y las fórmulas históricas permanecen intactas.
nombre = 'inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test'
sql = leer(nombre)
assert sql.count(RT + ' AS r') == 2
sql = sql.replace(RT + ' AS r', RO + ' AS r')

# F20 conserva exactamente su serie PI para días sin contingencia. En días
# afectados usa ambos turnos de RO; un turno pendiente bloquea el balance.
ancla = ';WITH CV025_Base AS'
assert sql.count(ancla) == 1
guardia = '''IF EXISTS (
    SELECT 1
    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test r
    WHERE r.equipo_codigo = 'RIPIOS_CV025'
      AND r.fecha_operacional BETWEEN @fecha_inicio AND @fecha_fin
    GROUP BY r.fecha_operacional
    HAVING MAX(CONVERT(int,r.contingencia_pi_activa)) = 1
       AND (COUNT(*) <> 2 OR SUM(CASE WHEN r.valor_final_resuelto IS NULL THEN 1 ELSE 0 END) > 0)
)
    THROW 51025, 'CV025 operacional pendiente: F20 no admite PI de respaldo ni cero fabricado.', 1;

'''
sql = sql.replace(ancla, guardia + ancla)
ancla = 'CV025_Validado AS\n('
assert sql.count(ancla) == 1
old = 'FROM CV025_Validado\n\nWHERE Fecha BETWEEN @fecha_inicio AND @fecha_fin;'
assert sql.count(old) == 1
new = '''FROM (
    SELECT COALESCE(v.Fecha,o.Fecha) AS Fecha,
           CASE WHEN o.Contingencia = 1 THEN o.TMH_Operacional
                ELSE v.CV025_TMH_Dia END AS CV025_TMH_Dia
    FROM CV025_Validado v
    FULL OUTER JOIN (
        SELECT fecha_operacional AS Fecha,
               MAX(CONVERT(int,contingencia_pi_activa)) AS Contingencia,
               SUM(CONVERT(float,valor_final_resuelto)) AS TMH_Operacional
        FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test
        WHERE equipo_codigo='RIPIOS_CV025'
          AND fecha_operacional BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY fecha_operacional
    ) o ON o.Fecha=v.Fecha
) cv
WHERE Fecha BETWEEN @fecha_inicio AND @fecha_fin;'''
sql = sql.replace(old,new)
sql = sql.replace('CREATE   PROCEDURE','ALTER PROCEDURE',1).replace('CREATE PROCEDURE','ALTER PROCEDURE',1)
escribir(nombre,sql)

# Reclamo conserva su tabla y vistas oficiales. Las variantes leen una capa
# CV025 por día que sustituye solo la fuente en días bajo contingencia.
origen = 'reclamo.v_cv25_diario'
nuevo = 'reclamo.v_cv25_diario_contingencia_test'
sql = leer(origen).replace('[reclamo].[v_cv25_diario]', '[reclamo].[v_cv25_diario_contingencia_test]', 1)
fuente = 'FROM [reclamo].[cv25_diario] cv'
assert sql.count(fuente) == 1
op = '''FROM (
    SELECT COALESCE(base.fecha,op.Fecha) AS fecha,
           CONVERT(decimal(30,12), CASE WHEN op.activa=1 THEN op.tmh ELSE base.tmh_dia END) AS tmh_dia,
           CONVERT(decimal(30,12), CASE WHEN op.activa=1 THEN op.tmh *
                (1.0 - COALESCE(base.humedad_pct,0) / 100.0)
                ELSE base.tms_dia END) AS tms_dia,
           base.tmh_cv025tot,base.tmh_cv025_tot,
           CASE WHEN op.activa=1 THEN 'RO_CV025' ELSE base.tag_utilizado END AS tag_utilizado,
           CASE WHEN op.activa=1 AND op.tmh IS NULL THEN 'PENDIENTE_TUM'
                WHEN op.activa=1 THEN 'OPERACIONAL_PI_TUM' ELSE base.flag END AS flag,
           CASE WHEN op.activa=1 AND op.tmh IS NULL THEN 1 ELSE 0 END AS pendiente
    FROM [reclamo].[cv25_diario] base
    FULL OUTER JOIN (
        SELECT fecha_operacional AS Fecha,
               MAX(CONVERT(int,contingencia_pi_activa)) AS activa,
               CASE WHEN COUNT(*)<>2 OR SUM(CASE WHEN valor_final_resuelto IS NULL THEN 1 ELSE 0 END)>0
                    THEN NULL ELSE SUM(CONVERT(decimal(28,6),valor_final_resuelto)) END AS tmh
        FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test
        WHERE equipo_codigo='RIPIOS_CV025'
        GROUP BY fecha_operacional
    ) op ON op.Fecha=base.fecha
) cv'''
sql = sql.replace(fuente,op)
sql = sql.replace('WHEN COALESCE(cv.tms_dia, 0) = 0',
                  'WHEN cv.pendiente = 1 THEN NULL\n        WHEN COALESCE(cv.tms_dia, 0) = 0')
sql = sql.replace('WHEN cv.fecha IS NULL\n',
                  "WHEN cv.pendiente = 1 THEN 'PENDIENTE_TUM'\n        WHEN cv.fecha IS NULL\n")
escribir(nuevo,sql,True)

for origen,nuevo,referencias in [
    ('reclamo.v_preliminar_cv25','reclamo.v_preliminar_cv25_contingencia_test',
     [('v_cv25_diario','v_cv25_diario_contingencia_test')]),
    ('reclamo.v_preliminar_cv25_con_acumulado','reclamo.v_preliminar_cv25_con_acumulado_contingencia_test',
     [('v_preliminar_cv25','v_preliminar_cv25_contingencia_test')]),
    ('reclamo.v_reclamo_diario','reclamo.v_reclamo_diario_contingencia_test',
     [('v_preliminar_cv25_con_acumulado','v_preliminar_cv25_con_acumulado_contingencia_test')]),
    ('reclamo.v_diferencia_cv25','reclamo.v_diferencia_cv25_contingencia_test',
     [('v_reclamo_diario','v_reclamo_diario_contingencia_test'),
      ('v_cv25_diario','v_cv25_diario_contingencia_test')]),
]:
    sql = leer(origen)
    old = '[reclamo].[' + origen.split('.')[1] + ']'
    new = '[reclamo].[' + nuevo.split('.')[1] + ']'
    assert old in sql
    sql = sql.replace(old,new,1)
    for a,b in referencias:
        sql = sql.replace('[reclamo].['+a+']','[reclamo].['+b+']')
    escribir(nuevo,sql,True)

# Representatividad TM1/TM2: la variante test conserva RT antes del corte.
nombre = 'inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test'
sql = leer(nombre)
assert sql.count(RT + ' AS r') == 1
fuentes = f'''(
    SELECT fecha_operacional,turno,equipo_codigo,fuente_resuelta,
           valor_final_resuelto,tipo_tum,motivo_decision
    FROM {RT} WHERE fecha_operacional < '2026-09-01'
    UNION ALL
    SELECT fecha_operacional,turno,equipo_codigo,fuente_resuelta,
           valor_final_resuelto,tipo_tum,motivo_decision
    FROM {RO} WHERE fecha_operacional >= '2026-09-01'
) AS r'''
sql = sql.replace(RT + ' AS r', fuentes)
sql = sql.replace('CREATE   VIEW','ALTER VIEW',1).replace('CREATE VIEW','ALTER VIEW',1)
escribir(nombre,sql)

# Datos de tonelaje T1/T2 usados por la variante de representatividad.
nombre = 'inventar_SpcHidr.v_bd_ton_t12_contingencia_test'
sql = leer(nombre)
assert sql.count(RT + ' AS r') == 1
sql = sql.replace(RT + ' AS r', f'''(
    SELECT fecha_operacional,turno,equipo_codigo,fuente_resuelta,
           valor_final_resuelto,tipo_tum,motivo_decision
    FROM {RT} WHERE fecha_operacional < '2026-09-01'
    UNION ALL
    SELECT fecha_operacional,turno,equipo_codigo,fuente_resuelta,
           valor_final_resuelto,tipo_tum,motivo_decision
    FROM {RO} WHERE fecha_operacional >= '2026-09-01'
) AS r''')
sql = sql.replace('CREATE   VIEW','ALTER VIEW',1).replace('CREATE VIEW','ALTER VIEW',1)
escribir(nombre,sql)
