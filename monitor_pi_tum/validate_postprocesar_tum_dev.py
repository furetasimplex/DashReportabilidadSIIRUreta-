"""Repite un batch DEV y verifica que el tonelaje y la bitácora sean estables."""
import argparse
from sqlalchemy import text
from . import db
from . import postprocesar_tum_contingencia as post


def snapshot(conn, fechas):
    cols = ('TMH_CV008_A','TMH_CV108_A','TMH_Apilado_Total_A',
            'TMH_CV008_B','TMH_CV108_B','TMH_Apilado_Total_B','TMH_Apilado_Total_Dia')
    data = {}
    for dia in fechas:
        row = conn.execute(text(f'SELECT {", ".join(cols)} FROM {post.APILADO} WHERE Fecha=:fecha'),
                           {'fecha':dia}).one_or_none()
        data[dia] = tuple(row) if row else None
    acciones = conn.execute(text(f'SELECT COUNT(*) FROM {db.BITACORA}')).scalar_one()
    return data, acciones


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-id',type=int,required=True)
    args = parser.parse_args()
    engine = db._engine_dev()
    with engine.connect() as conn:
        db._assert_dev_connection(conn)
        plan = post.planificar(conn,args.batch_id)
        antes = snapshot(conn,plan.fechas)
    post.ejecutar(args.batch_id,True,engine)
    with engine.connect() as conn:
        db._assert_dev_connection(conn)
        despues = snapshot(conn,plan.fechas)
    if antes != despues:
        raise AssertionError('El tonelaje o la cantidad de acciones cambió al repetir el batch.')
    print(f'Batch {args.batch_id}: repetición idempotente; fechas={len(plan.fechas)}; '
          f'acciones antes/después={antes[1]}/{despues[1]}; tonelaje estable.')


if __name__ == '__main__':
    main()
