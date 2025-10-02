import pandas as pd
from db_connection import get_engine
import datetime
from sqlalchemy import text

def procesar_excel_leyes(file_like, nombre_archivo):
    engine = get_engine()

    try:
        xls = pd.ExcelFile(file_like)
        columnas_leyes = [
                        "Fecha", "TMH_Turno_A", "TMH_Turno_B", "TMH",
                        "Humedades_Turno_A", "Humedades_Turno_B", "Humedades_Dia",
                        "Humedades_SRR_Turno_A", "Humedades_SRR_Turno_B", "Humedades_SRR_Dia",
                        "TMS_Turno_A", "TMS_Turno_B", "TMS_Total",
                        "CuT_Turno_A", "CuT_Turno_B", "CuT_Dia",
                        "CuT_SRR_Turno_A", "CuT_SRR_Turno_B", "CuT_SRR_Dia",
                        "CuS_Turno_A", "CuS_Turno_B", "CuS_Dia",
                        "FeT_Turno_A", "FeT_Turno_B", "FeT_Dia",
                        "FeS_Turno_A", "FeS_Turno_B", "FeS_Dia",
                        "CO3_Turno_A", "CO3_Turno_B", "CO3_Dia",
                        "CuFe_Turno_A", "CuFe_Turno_B", "CuFe_Dia",
                        "ConsH_Turno_A", "ConsH_Turno_B", "ConsH_Dia",
                        "M12_Turno_A", "M12_Turno_B", "M12_Dia",
                        "M100_Turno_A", "M100_Turno_B", "M100_Dia",
                        "Caolinita_Turno_A", "Caolinita_Turno_B", "Caolinita_Dia",
                        "CaolBeta_Turno_A", "CaolBeta_Turno_B", "CaolBeta_Dia",
                        "Cuarzo_Turno_A", "Cuarzo_Turno_B", "Cuarzo_Dia"
                    ]
        

        # ---- LEYES TORRES (Data TM1 y TM2) ----
        hojas_leyes = [('Data TM1', 1), ('Data TM2', 2)]
        for hoja, id_torre in hojas_leyes:
            df = xls.parse(hoja, header=None, skiprows=3, usecols="A:AZ", names=columnas_leyes) # solo columnas A a AZ
            
            # Renombrar explícitamente la primera columna como 'fecha' si es anónima
            if df.columns[0] != 'Fecha' and 'fecha' not in df.columns.str.lower():
                df.rename(columns={df.columns[0]: 'fecha'}, inplace=True)

            df['id_torre'] = id_torre
            df['archivo'] = nombre_archivo
            #df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            #df = df[df['fecha'].notnull()]
            df = df[df['TMH'].notnull()]
            print(df)
            df.info()

            # Eliminar registros existentes por fecha + torre
            with engine.connect() as conn:
                fechas_existentes = df['Fecha'].dropna().unique()
                for f in fechas_existentes:
                    stmt = text("""
                        DELETE FROM inventar_SpcHidr.import_leyes_torres
                        WHERE fecha = :fecha AND id_torre = :torre
                    """)
                    conn.execute(stmt, {"fecha": f, "torre": id_torre})
            
            df.to_sql("import_leyes_torres", engine,schema="inventar_SpcHidr", if_exists="append", index=False)
        # Lista exacta de columnas esperadas
        columnas_granulo = [
            "Torre", "Fecha", "Turno", "CuT", "CuS", "FeT", "FeS", "CO3", "Cl_Ac_kgton", "Cons_Ac_Kgton",
            "Ret_Parcial_2_mall", "Ret_Parcial_1_mall", "Ret_Parcial_34_mall", "Ret_Parcial_12_mall",
            "Ret_Parcial_14_mall", "Ret_Parcial_mall_10", "Ret_Parcial_mall_35", "Ret_Parcial_mall_100",
            "Ret_Parcial_mall_150", "Ret_Parcial_mall_200", "Ret_Parcial_mall_325",
            "Rete_Acumulado_2_mall", "Rete_Acumulado_1_mall", "Rete_Acumulado_34_mall", "Rete_Acumulado_12_mall",
            "Rete_Acumulado_14_mall", "Rete_Acumulado_mall_10", "Rete_Acumulado_mall_35",
            "Rete_Acumulado_mall_100", "Rete_Acumulado_mall_150", "Rete_Acumulado_mall_200", "Rete_Acumulado_mall_325",
            "Pas_Acumulado_2_mall", "Pas_Acumulado_1_mall", "Pas_Acumulado_34_mall", "Pas_Acumulado_12_mall",
            "Pas_Acumulado_14_mall", "Pas_Acumulado_mall_10", "Pas_Acumulado_mall_35",
            "Pas_Acumulado_mall_100", "Pas_Acumulado_mall_150", "Pas_Acumulado_mall_200", "Pas_Acumulado_mall_325",
            "AQ_CuT_2_mall", "AQ_CuT_1_mall", "AQ_CuT_34_mall", "AQ_CuT_12_mall", "AQ_CuT_14_mall",
            "AQ_CuT_mall_10", "AQ_CuT_mall_35", "AQ_CuT_mall_100", "AQ_CuT_mall_150", "AQ_CuT_mall_200",
            "AQ_CuT_mall_325",
            "Ponderado", "Humedad_por", "Rechazo_kg"
        ]

        for hoja, id_torre in [('Informe TORRE N°1', 1), ('Informe TORRE N°2', 2)]:
            df = xls.parse(hoja, header=None, skiprows=2, usecols="A:BI")
            
            if df.shape[1] < len(columnas_granulo):
                raise ValueError(f"La hoja '{hoja}' contiene solo {df.shape[1]} columnas, se esperaban {len(columnas_granulo)}")
            
            df.columns = columnas_granulo + df.columns[len(columnas_granulo):].tolist()  # tolerar columnas extra
            df = df[columnas_granulo]  # limitar a columnas válidas
            df['id_Torre'] = id_torre
            df['archivo'] = nombre_archivo
            #df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')

            # Validar registros válidos: fecha no nula y CuT no nulo (columna D)
            #df = df[df['Fecha'].notnull()]
            df = df[df['CuT'].notnull()]
            #print(df)
            #df.info()
            # Eliminar duplicados antes de insertar
            with engine.connect() as conn:
                for _, row in df.iterrows():
                    stmt = text("""
                        DELETE FROM inventar_SpcHidr.import_granulometria_torres
                        WHERE Fecha = :fecha AND Turno = :turno AND id_Torre = :torre
                    """)
                    conn.execute(stmt, {
                        'fecha': row['Fecha'],
                        'turno': row['Turno'],
                        'torre': row['id_Torre']
                    })

            # Insertar
            df.to_sql("import_granulometria_torres", engine,schema="inventar_SpcHidr", if_exists="append", index=False)

        

        return "Importación realizada correctamente."

    except Exception as e:
        return f"Error en la importación: {str(e)}"