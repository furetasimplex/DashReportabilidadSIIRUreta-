"""Inspección de solo lectura del contrato TUM DEV para el postproceso."""
from sqlalchemy import text
from . import db


def main():
    engine = db._engine_dev()
    with engine.connect() as conn:
        db._assert_dev_connection(conn)
        for schema, name, database in [
            ('hidro','import_batch','DEV_SIIR'),
            ('hidro','import_row_history','DEV_SIIR'),
            ('inventar_SpcHidr','v_contingencia_pi_estado_turno_test','inventar_SpcHidr')]:
            query = text(f'''SELECT c.name FROM [{database}].sys.columns c
                JOIN [{database}].sys.objects o ON o.object_id=c.object_id
                JOIN [{database}].sys.schemas s ON s.schema_id=o.schema_id
                WHERE s.name=:schema AND o.name=:name ORDER BY c.column_id''')
            cols = [r[0] for r in conn.execute(query,{'schema':schema,'name':name})]
            print(f'{database}.{schema}.{name}: {cols}')
        rows = conn.execute(text('''SELECT TOP (10) id, template_code, estado
            FROM [DEV_SIIR].[hidro].[import_batch] ORDER BY id DESC''')).mappings().all()
        print('Recent batches:', [dict(r) for r in rows])
        samples = conn.execute(text('''SELECT TOP (3) dataset_name,
            (SELECT [key] FROM OPENJSON(business_key_json) ORDER BY [key] FOR JSON PATH) AS business_keys,
            (SELECT [key] FROM OPENJSON(after_payload_json) ORDER BY [key] FOR JSON PATH) AS payload_keys
            FROM [DEV_SIIR].[hidro].[import_row_history]
            WHERE dataset_name='informe_tum_totalizadores_turno' ORDER BY batch_id DESC''')).mappings().all()
        print('History JSON keys:', [dict(r) for r in samples])
        recent = conn.execute(text('''SELECT TOP (10) batch_id, dataset_name,
            JSON_VALUE(business_key_json,'$.fecha_operacional') AS fecha,
            JSON_VALUE(business_key_json,'$.turno') AS turno,
            JSON_VALUE(business_key_json,'$.equipo_codigo') AS equipo
            FROM [DEV_SIIR].[hidro].[import_row_history]
            WHERE batch_id=20453 ORDER BY id DESC''')).mappings().all()
        print('Batch 20453 keys:', [dict(r) for r in recent])


if __name__ == '__main__':
    main()
