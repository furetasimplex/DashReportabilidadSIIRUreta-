"""Respaldo reproducible de DEV para la migración de nominales de camiones.

El comando capture solo ejecuta SELECT; nunca reemplaza un respaldo existente.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection

MIGRATION = ROOT / 'docs/migrations/factor_camiones_nominales_dev'
BACKUP = MIGRATION / 'backup'
EVIDENCE = ROOT / 'report_export/exports/validacion_factor_nominales_20260930'
OBJECTS = (
    'sp_registrar_limite_factor_camiones_vigencia_test',
    'tr_factor_camiones_vigencia_solapamiento_test',
    'sp_factor_ajuste_camiones_test',
    'sp_mantiene_factor_ajuste_camiones_v2_test',
    'sp_factor_ajuste_camiones_standalone_test',
    'sp_mantiene_factor_ajuste_camiones_v2_standalone_test',
    'v_ajuste_camiones_emision_test',
)
PYTHON_FILES = (
    'monitor_pi_tum/db.py',
    'monitor_pi_tum/limites_camiones_panel.py',
    'monitor_pi_tum/factor_camiones_panel.py',
)


def rows(conn, sql, params=None):
    return [dict(r) for r in conn.execute(text(sql), params or {}).mappings()]


def save_json(path, value):
    path.write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding='utf-8')


def capture():
    if BACKUP.exists():
        raise RuntimeError('Ya existe backup: no se sobrescribe la línea base.')
    with _engine_dev().connect() as conn:
        _assert_dev_connection(conn)
        definitions = {}
        for name in OBJECTS:
            definition = conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:name))'),
                                      {'name': 'inventar_SpcHidr.' + name}).scalar_one()
            if not definition:
                raise RuntimeError('Definición no disponible: ' + name)
            definitions[name] = definition
        data = {
            'identidad': rows(conn, 'SELECT DB_NAME() base, SYSDATETIME() fecha'),
            'parametros': rows(conn, 'SELECT * FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test ORDER BY id'),
            'auditoria': rows(conn, 'SELECT * FROM inventar_SpcHidr.factor_camiones_parametro_auditoria_test ORDER BY id'),
            'control': rows(conn, 'SELECT * FROM inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test ORDER BY Fecha'),
            'vista': rows(conn, 'SELECT * FROM inventar_SpcHidr.v_ajuste_camiones_emision_test ORDER BY Fecha'),
            'checks': rows(conn, "SELECT name,definition,is_disabled,is_not_trusted FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID('inventar_SpcHidr.factor_camiones_parametro_vigencia_test')"),
            'columnas': rows(conn, "SELECT c.name,t.name tipo,c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE c.object_id=OBJECT_ID('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test') ORDER BY c.column_id"),
        }
        # Inspección de cobertura: no presupone que NULL, negativo o duplicado sea válido.
        data['mov_vueltas'] = rows(conn, """SELECT CAST(Fecha AS date) Fecha,
            UPPER(LTRIM(RTRIM(Flota_CEX))) flota,COUNT(*) registros,
            SUM(TRY_CONVERT(float,N_BREAK)) vueltas,
            SUM(CASE WHEN TRY_CONVERT(float,N_BREAK) IS NULL THEN 1 ELSE 0 END) nulos,
            SUM(CASE WHEN TRY_CONVERT(float,N_BREAK)<0 THEN 1 ELSE 0 END) negativos
            FROM inventar_SpcHidr.mov_cam
            WHERE Fecha>='20260701' AND Fecha<'20261001'
              AND UPPER(LTRIM(RTRIM(Destino)))='CH01'
              AND UPPER(LTRIM(RTRIM(Fase)))<>'SRR'
              AND UPPER(LTRIM(RTRIM(Flota_CEX))) IN ('KOM','CAT')
            GROUP BY CAST(Fecha AS date),UPPER(LTRIM(RTRIM(Flota_CEX))) ORDER BY Fecha,flota""")
        data['powerbi_vueltas'] = rows(conn, """SELECT fecha Fecha,
            UPPER(LTRIM(RTRIM(flota_cex_tc))) flota,COUNT(*) registros,
            SUM(TRY_CONVERT(float,n_break)) vueltas,
            SUM(CASE WHEN TRY_CONVERT(float,n_break) IS NULL THEN 1 ELSE 0 END) nulos,
            SUM(CASE WHEN TRY_CONVERT(float,n_break)<0 THEN 1 ELSE 0 END) negativos
            FROM inventar_SpcHidr.mov_cam_powerbi
            WHERE fecha>='20260701' AND fecha<'20261001'
              AND UPPER(LTRIM(RTRIM(destino_descarga)))='CH01'
              AND UPPER(LTRIM(RTRIM(fase)))<>'SRR'
              AND UPPER(LTRIM(RTRIM(flota_cex_tc))) IN ('KOM','CAT')
            GROUP BY fecha,UPPER(LTRIM(RTRIM(flota_cex_tc))) ORDER BY Fecha,flota""")
    BACKUP.mkdir(parents=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, definition in definitions.items():
        target = BACKUP / (name + '.sql')
        target.write_bytes(definition.encode('utf-8'))
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    for name in PYTHON_FILES:
        target = BACKUP / (name.replace('/', '__') + '.before')
        target.write_bytes((ROOT / name).read_bytes())
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    save_json(BACKUP / 'manifest.json', hashes)
    save_json(EVIDENCE / 'antes.json', data)
    (EVIDENCE / 'git_status_antes.txt').write_text(
        subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True), encoding='utf-8')
    print('Respaldo DEV guardado; filas V2:', len(data['control']))
    print('Rango V2:', data['control'][0]['Fecha'], data['control'][-1]['Fecha'])
    for key in ('mov_vueltas', 'powerbi_vueltas'):
        bad = [r for r in data[key] if r['nulos'] or r['negativos']]
        print(key, 'días/flota:', len(data[key]), 'grupos con vueltas inválidas:', len(bad))


def alter_definition(definition):
    result, count = re.subn(r'\bCREATE\s+(?:OR\s+ALTER\s+)?(PROCEDURE|VIEW|TRIGGER)\b',
                            r'CREATE OR ALTER \1', definition, count=1, flags=re.I)
    if count != 1:
        raise ValueError('No se identificó una definición SQL única.')
    return result


def prepare_administration():
    """Genera SQL revisable; NO ejecuta migraciones ni modifica DEV."""
    original = (BACKUP / 'sp_registrar_limite_factor_camiones_vigencia_test.sql').read_text(encoding='utf-8')
    generic = alter_definition(original).replace(
        'sp_registrar_limite_factor_camiones_vigencia_test',
        'sp_registrar_parametro_factor_camiones_vigencia_test')
    generic = generic.replace("'LIMITE_CARGA_AJUSTE'", '@Parametro')
    generic = generic.replace('@Flota varchar(20),', '@Parametro varchar(40),\n    @Flota varchar(20),', 1)
    guard = "IF DB_NAME()<>N'inventar_SpcHidr' THROW 51000, 'Solo DEV.', 1;"
    assert guard in generic
    generic = generic.replace(guard, guard + "\n    IF @Parametro IS NULL OR @Parametro NOT IN ('LIMITE_CARGA_AJUSTE','CARGA_NOMINAL_TMH_VIAJE')\n        THROW 51018, 'Categoria de parametro no permitida.', 1;", 1)
    (MIGRATION / '02_administrador_generico.sql').write_text(generic, encoding='utf-8')
    wrapper = """CREATE OR ALTER PROCEDURE inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test
    @Flota varchar(20), @Valor decimal(18,6), @VigenciaDesde date,
    @Motivo nvarchar(1000), @Usuario nvarchar(128)
AS
BEGIN
    SET NOCOUNT ON;
    EXEC inventar_SpcHidr.sp_registrar_parametro_factor_camiones_vigencia_test
        @Parametro='LIMITE_CARGA_AJUSTE', @Flota=@Flota, @Valor=@Valor,
        @VigenciaDesde=@VigenciaDesde, @Motivo=@Motivo, @Usuario=@Usuario;
END;
"""
    (MIGRATION / '03_wrapper_limites.sql').write_text(wrapper, encoding='utf-8')
    rollback = ["""-- Rollback de esquema/administracion; componente del rollback integral.
-- Usar rollback_dev.sql mediante el runner para restaurar tambien resultados.
SET XACT_ABORT ON;
IF DB_NAME()<>N'inventar_SpcHidr' THROW 51000, 'Solo DEV.', 1;
IF @@TRANCOUNT=0 THROW 51030, 'Rollback requiere una transaccion externa.', 1;
-- No destruir historia nominal registrada despues de los seeds de esta migracion.
IF EXISTS (SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
 WHERE parametro='CARGA_NOMINAL_TMH_VIAJE'
 AND (usuario_registro<>N'MIGRACION_NOMINALES_V2_DEV' OR vigencia_desde<>'20260701'
      OR vigencia_hasta IS NOT NULL OR activo<>1
      OR NOT ((flota='KOM' AND valor=357) OR (flota='CAT' AND valor=236))))
 THROW 51032, 'Existen modificaciones nominales posteriores; revisar rollback.', 1;
IF EXISTS (SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_auditoria_test
 WHERE parametro='CARGA_NOMINAL_TMH_VIAJE')
 THROW 51032, 'Existe auditoria nominal posterior; revisar rollback.', 1;
GO
"""]
    # Restituye exactamente las definiciones observadas, nunca snapshots antiguos.
    for name in OBJECTS:
        rollback.append(alter_definition((BACKUP / (name + '.sql')).read_text(encoding='utf-8')) + '\nGO\n')
    rollback.append("""
DROP PROCEDURE IF EXISTS inventar_SpcHidr.sp_registrar_parametro_factor_camiones_vigencia_test;
DELETE FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
 WHERE parametro='CARGA_NOMINAL_TMH_VIAJE';
ALTER TABLE inventar_SpcHidr.factor_camiones_parametro_vigencia_test
 DROP CONSTRAINT CK__factor_ca__param__41EF6173;
ALTER TABLE inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH CHECK
 ADD CONSTRAINT CK__factor_ca__param__41EF6173 CHECK (parametro='LIMITE_CARGA_AJUSTE');
IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Carga_Nominal_KOM_TMH_Viaje') IS NOT NULL
 ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test DROP COLUMN Carga_Nominal_KOM_TMH_Viaje;
IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Carga_Nominal_CAT_TMH_Viaje') IS NOT NULL
 ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test DROP COLUMN Carga_Nominal_CAT_TMH_Viaje;
""")
    (MIGRATION / 'rollback_preparacion.sql').write_text('\n'.join(rollback), encoding='utf-8')
    print('Administrador genérico y wrapper preparados; no ejecutados.')


EXTRA_COLUMNS = {
    'Carga_Nominal_KOM_TMH_Viaje': 'decimal(18,6)',
    'Carga_Nominal_CAT_TMH_Viaje': 'decimal(18,6)',
    'Estado_Fuente_MOV_CAM': 'varchar(24)',
    'Estado_Fuente_POWERBI': 'varchar(24)',
}
OUTPUT_EXTRA = list(EXTRA_COLUMNS)[:2] + ['Fuente_Camiones'] + list(EXTRA_COLUMNS)[2:]


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Ancla SQL no única: ' + old[:100])
    return source.replace(old, new, 1)


def build_calculation(name):
    sql = (BACKUP / (name + '.sql')).read_text(encoding='utf-8')
    # El encabezado antiguo describe otra fuente; el cuerpo vivo es la base.
    sql = sql[re.search(r'^CREATE\s+PROCEDURE', sql, re.I | re.M).start():]
    sql = alter_definition(sql)
    start = sql.index('    -- FASE 2A:')
    end = sql.index('    ;WITH SRR_Diario', start)
    sql = sql[:start] + """    -- Fotografia temporal unica para ambas categorias; sin valores de respaldo.
    SELECT flota,parametro,valor,vigencia_desde,vigencia_hasta
    INTO #ParametrosFactorV2
    FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (HOLDLOCK)
    WHERE activo=1 AND parametro IN ('LIMITE_CARGA_AJUSTE','CARGA_NOMINAL_TMH_VIAJE');
    ;WITH Dias AS (
        SELECT @FechaInicio Fecha
        UNION ALL SELECT DATEADD(day,1,Fecha) FROM Dias WHERE Fecha<@FechaFin
    )
    SELECT d.Fecha,f.flota,t.parametro,COUNT(p.flota) cantidad,
           MIN(p.valor) valor
    INTO #ConfiguracionFactorV2
    FROM Dias d CROSS JOIN (VALUES ('KOM'),('CAT')) f(flota)
    CROSS JOIN (VALUES ('LIMITE_CARGA_AJUSTE'),('CARGA_NOMINAL_TMH_VIAJE')) t(parametro)
    LEFT JOIN #ParametrosFactorV2 p ON p.flota=f.flota AND p.parametro=t.parametro
      AND p.vigencia_desde<=d.Fecha AND (p.vigencia_hasta IS NULL OR d.Fecha<p.vigencia_hasta)
    GROUP BY d.Fecha,f.flota,t.parametro OPTION (MAXRECURSION 0);
    DECLARE @ErrorLimite nvarchar(2048);
    SELECT TOP(1) @ErrorLimite=CONCAT('Configuracion no unica: ',parametro,' ',flota,' ',Fecha)
    FROM #ConfiguracionFactorV2 WHERE cantidad<>1 ORDER BY Fecha,parametro,flota;
    IF @ErrorLimite IS NOT NULL THROW 51020,@ErrorLimite,1;
    SELECT Fecha,flota,CAST(valor AS float) limite INTO #LimitesFactorV2
    FROM #ConfiguracionFactorV2 WHERE parametro='LIMITE_CARGA_AJUSTE';
    CREATE UNIQUE CLUSTERED INDEX IX_LimitesFactorV2 ON #LimitesFactorV2(Fecha,flota);

""" + sql[end:]
    start = sql.index('    /* ============================================================\n       2.')
    end = sql.index('    /* ============================================================\n       5.', start)
    sql = sql[:start] + """    -- Resolucion comun de vueltas por dia completo. Nunca mezclar flotas de fuentes diferentes.
    SELECT b.Fecha,
           COALESCE(v.Vueltas_KOM,0.0) Vueltas_KOM,
           COALESCE(v.Vueltas_CAT,0.0) Vueltas_CAT,
           nk.valor Carga_Nominal_KOM_TMH_Viaje,
           nc.valor Carga_Nominal_CAT_TMH_Viaje,
           COALESCE(v.Vueltas_KOM,0.0)*nk.valor Produccion_KOM_TMH,
           COALESCE(v.Vueltas_CAT,0.0)*nc.valor Produccion_CAT_TMH,
           COALESCE(v.Vueltas_KOM,0.0)*nk.valor+COALESCE(v.Vueltas_CAT,0.0)*nc.valor Produccion_Total_MovCam,
           COALESCE(v.Fuente_Camiones,'SIN_DATOS_CAMIONES') Fuente_Camiones,
           COALESCE(v.Estado_Fuente_MOV_CAM,'SIN_REGISTROS') Estado_Fuente_MOV_CAM,
           COALESCE(v.Estado_Fuente_POWERBI,'SIN_REGISTROS') Estado_Fuente_POWERBI,
           COALESCE(v.Cantidad_Registros_Originales,0) Cantidad_Registros_Originales,
           COALESCE(v.Cantidad_Registros_Validos,0) Cantidad_Registros_Validos,
           CAST(0 AS int) Cantidad_Duplicados_Eliminados
    INTO #CamionesDiario
    FROM #BaseBalance b
    JOIN #ConfiguracionFactorV2 nk ON nk.Fecha=b.Fecha AND nk.flota='KOM' AND nk.parametro='CARGA_NOMINAL_TMH_VIAJE'
    JOIN #ConfiguracionFactorV2 nc ON nc.Fecha=b.Fecha AND nc.flota='CAT' AND nc.parametro='CARGA_NOMINAL_TMH_VIAJE'
    LEFT JOIN inventar_SpcHidr.v_vueltas_camiones_diarias_test v ON v.Fecha=b.Fecha;
    CREATE UNIQUE CLUSTERED INDEX IX_CamionesDiario_Fecha ON #CamionesDiario(Fecha);
""" + sql[end:]
    anchor = '        b.*,\n        COALESCE(c.Produccion_KOM_TMH, 0.0)'
    sql = replace_once(sql, anchor, '        b.*,\n' + ''.join('        c.' + c + ',\n' for c in OUTPUT_EXTRA) + '        COALESCE(c.Produccion_KOM_TMH, 0.0)')
    sql = replace_once(sql, '        c.Limite_CAT_TMH_Viaje\n    FROM #FactorCorregido',
                       '        c.Limite_CAT_TMH_Viaje,\n' + ',\n'.join('        c.' + c for c in OUTPUT_EXTRA) + '\n    FROM #FactorCorregido')
    return sql


def build_maintainer(name):
    sql = alter_definition((BACKUP / (name + '.sql')).read_text(encoding='utf-8'))
    sql = replace_once(sql, '        Limite_CAT_TMH_Viaje float NOT NULL\n',
        '        Limite_CAT_TMH_Viaje float NOT NULL,\n' + ',\n'.join(
            '        ' + c + ' ' + (EXTRA_COLUMNS.get(c) or 'varchar(100)') + ' NOT NULL' for c in OUTPUT_EXTRA) + '\n')
    sql = replace_once(sql, '        b.Limite_CAT_TMH_Viaje,',
        '        b.Limite_CAT_TMH_Viaje,\n' + ''.join('        b.' + c + ',\n' for c in EXTRA_COLUMNS))
    sql = replace_once(sql, "        CAST('MOV_CAM_DEDUP_OPERACIONAL' AS varchar(100))\n            AS Fuente_Camiones,",
        '        b.Fuente_Camiones,')
    sql = replace_once(sql, '        UPDATE SET', '        UPDATE SET\n' + ''.join(
        '            ' + c + ' = src.' + c + ',\n' for c in EXTRA_COLUMNS))
    sql = replace_once(sql, '            Limite_CAT_TMH_Viaje,',
        '            Limite_CAT_TMH_Viaje,\n' + ''.join('            ' + c + ',\n' for c in EXTRA_COLUMNS))
    start = sql.index('    WHEN NOT MATCHED BY TARGET')
    sql = sql[:start] + replace_once(sql[start:], '            src.Limite_CAT_TMH_Viaje,',
        '            src.Limite_CAT_TMH_Viaje,\n' + ''.join('            src.' + c + ',\n' for c in EXTRA_COLUMNS))
    return sql


def prepare():
    prepare_administration()
    for i, name in enumerate(('sp_factor_ajuste_camiones_test','sp_factor_ajuste_camiones_standalone_test'), 6):
        (MIGRATION / (f'{i:02}_' + name + '.sql')).write_text(build_calculation(name), encoding='utf-8')
    for i, name in enumerate(('sp_mantiene_factor_ajuste_camiones_v2_test','sp_mantiene_factor_ajuste_camiones_v2_standalone_test'), 8):
        (MIGRATION / (f'{i:02}_' + name + '.sql')).write_text(build_maintainer(name), encoding='utf-8')
    view = alter_definition((BACKUP / 'v_ajuste_camiones_emision_test.sql').read_text(encoding='utf-8'))
    view = replace_once(view, '        f.Limite_KOM_TMH_Viaje,',
        ''.join('        f.' + c + ',\n' for c in EXTRA_COLUMNS) + '        f.Limite_KOM_TMH_Viaje,')
    (MIGRATION / '10_v_ajuste_camiones_emision_test.sql').write_text(view, encoding='utf-8')
    schema_extra = '\n'.join(
        f"IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','{c}') IS NULL\n"
        f' ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test ADD {c} {t} NULL;'
        for c,t in EXTRA_COLUMNS.items() if c.startswith('Estado_'))
    (MIGRATION / '01b_trazabilidad_fuentes.sql').write_text(schema_extra + '\n', encoding='utf-8')
    rollback = (MIGRATION / 'rollback_preparacion.sql').read_text(encoding='utf-8')
    rollback += "\nDROP VIEW IF EXISTS inventar_SpcHidr.v_vueltas_camiones_diarias_test;\nDROP FUNCTION IF EXISTS inventar_SpcHidr.fn_resolver_vueltas_camiones_test;\n"
    rollback += '\n'.join(f"IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','{c}') IS NOT NULL\n ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test DROP COLUMN {c};" for c in EXTRA_COLUMNS if c.startswith('Estado_'))
    (MIGRATION / 'rollback_dev.sql').write_text(rollback + '\n', encoding='utf-8')
    print('Paquete SQL generado desde el respaldo vivo; no desplegado.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['capture', 'prepare-administration', 'prepare'])
    args = parser.parse_args()
    if args.command == 'capture':
        capture()
    elif args.command == 'prepare-administration':
        prepare_administration()
    elif args.command == 'prepare':
        prepare()
