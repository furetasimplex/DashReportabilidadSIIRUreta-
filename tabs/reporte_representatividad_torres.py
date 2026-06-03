import pandas as pd
from sqlalchemy import text
from db_connection import get_engine


def cargar_representatividad_torres(fecha_inicio, fecha_fin):
    engine = get_engine()

    query = text("""
        EXEC inventar_SpcHidr.sp_reporte_representatividad_torres
            @fecha_inicio = :fecha_inicio,
            @fecha_fin = :fecha_fin
    """)

    with engine.connect() as conn:
        df = pd.read_sql(
            query,
            conn,
            params={
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            }
        )

    return df