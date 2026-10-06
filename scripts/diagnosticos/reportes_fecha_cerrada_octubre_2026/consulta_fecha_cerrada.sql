
        ;WITH max_totalizador AS
        (
            SELECT MAX(fecha) AS Max_Fecha_Totalizador
            FROM inventar_SpcHidr.tot_TM
        ),
        rangos_dia AS
        (
            SELECT
                fecha_turno,
                MAX(ts_fin) AS Max_ts_fin_dia
            FROM inventar_SpcHidr.v_bitacora_rangos_norm
            WHERE fecha_turno >= :start
              AND fecha_turno <= :end
              AND Torre IN ('T1', 'T2', 'SRR')
            GROUP BY fecha_turno
        )
        SELECT MAX(r.fecha_turno) AS Fecha_Maxima_Exportable
        FROM rangos_dia r
        CROSS JOIN max_totalizador mt
        WHERE r.Max_ts_fin_dia <= mt.Max_Fecha_Totalizador;
    