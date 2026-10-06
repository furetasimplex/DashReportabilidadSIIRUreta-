WITH pi_raw AS (
    SELECT CAST(v.fecha_turno AS date) AS fecha,
           MAX(CAST(v.cv025tot AS decimal(30,12))) AS pi_diario_original,
           MAX(CAST(v.cv025_tot AS decimal(30,12))) AS pi_alternativo,
           COUNT_BIG(*) AS pi_filas_dia
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados AS v
    GROUP BY CAST(v.fecha_turno AS date)
), turnos AS (
    SELECT r.fecha_operacional AS fecha,
           UPPER(LTRIM(RTRIM(r.turno))) AS turno,
           r.estado_tecnico_pi,
           r.tum_disponible,
           r.tipo_tum,
           CAST(r.valor_turno_tum AS decimal(30,12)) AS tum_turno,
           CAST(r.valor_pi_final AS decimal(30,12)) AS pi_turno,
           r.tum_batch_id,
           r.archivo_batch
    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno AS r
    WHERE r.equipo_codigo = 'RIPIOS_CV025'
), tum_dia AS (
    SELECT fecha,
           COUNT_BIG(*) AS turnos_observados,
           SUM(CASE WHEN turno IN ('A','B') AND tum_disponible=1
                         AND tipo_tum='TUM_DIRECTO' AND tum_turno>=0
                    THEN 1 ELSE 0 END) AS turnos_tum_directo,
           SUM(CASE WHEN turno IN ('A','B') AND tum_disponible=1
                         AND tipo_tum='TUM_DIRECTO' AND tum_turno>=0
                    THEN tum_turno ELSE CAST(0 AS decimal(30,12)) END) AS tum_diario,
           MAX(CASE WHEN (estado_tecnico_pi LIKE 'SIN_CAMBIO%' OR estado_tecnico_pi='SIN_PI')
                         AND tipo_tum='TUM_DIRECTO' AND tum_turno>0 THEN 1 ELSE 0 END) AS inicia_contingencia,
           MAX(CASE WHEN estado_tecnico_pi LIKE 'CON_VARIACION%' AND pi_turno>0
                    THEN 1 ELSE 0 END) AS recupera_pi,
           MAX(CASE WHEN estado_tecnico_pi LIKE 'SIN_CAMBIO%' THEN 1 ELSE 0 END) AS pi_plano,
           MAX(CASE WHEN turno='A' THEN tum_batch_id END) AS tum_batch_id_a,
           MAX(CASE WHEN turno='B' THEN tum_batch_id END) AS tum_batch_id_b,
           MAX(CASE WHEN turno='A' THEN archivo_batch END) AS archivo_batch_a,
           MAX(CASE WHEN turno='B' THEN archivo_batch END) AS archivo_batch_b
    FROM turnos
    GROUP BY fecha
), dias AS (
    SELECT COALESCE(p.fecha,t.fecha) AS fecha,
           p.pi_diario_original,p.pi_alternativo,p.pi_filas_dia,
           CASE WHEN t.turnos_observados=2 AND t.turnos_tum_directo=2
                THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS tum_completo,
           CASE WHEN t.turnos_observados=2 AND t.turnos_tum_directo=2
                THEN t.tum_diario ELSE NULL END AS tum_diario,
           ISNULL(t.inicia_contingencia,0) AS inicia_contingencia,
           ISNULL(t.recupera_pi,0) AS recupera_pi,
           ISNULL(t.pi_plano,0) AS pi_plano,
           t.tum_batch_id_a,t.tum_batch_id_b,t.archivo_batch_a,t.archivo_batch_b
    FROM pi_raw AS p FULL OUTER JOIN tum_dia AS t ON t.fecha=p.fecha
), grupos AS (
    SELECT d.*,
           ISNULL(SUM(d.recupera_pi) OVER (ORDER BY d.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),0) AS grupo_recuperacion
    FROM dias AS d
), semillas AS (
    SELECT g.*,
           MIN(CASE WHEN g.inicia_contingencia=1 THEN g.fecha END)
               OVER (PARTITION BY g.grupo_recuperacion) AS fecha_inicio_episodio
    FROM grupos AS g
), dias_episodio AS (
    SELECT s.*
    FROM semillas AS s
    WHERE s.fecha_inicio_episodio IS NOT NULL AND s.fecha>=s.fecha_inicio_episodio
), balances AS (
    SELECT grupo_recuperacion,fecha_inicio_episodio,
           MAX(CASE WHEN recupera_pi=1 THEN fecha END) AS fecha_recuperacion,
           SUM(CASE WHEN pi_diario_original IS NULL OR pi_filas_dia<>1 THEN 1 ELSE 0 END) AS dias_sin_pi_unico,
           SUM(CASE WHEN tum_completo=0 THEN 1 ELSE 0 END) AS dias_sin_tum_completo,
           SUM(pi_diario_original) AS masa_pi_episodio,
           SUM(tum_diario) AS masa_tum_episodio
    FROM dias_episodio
    GROUP BY grupo_recuperacion,fecha_inicio_episodio
)
SELECT s.fecha,
       s.pi_diario_original,s.pi_alternativo,s.tum_diario,s.tum_completo,
       CAST(CASE WHEN s.recupera_pi=1 AND b.fecha_inicio_episodio IS NOT NULL THEN 'RECUPERACION'
                 WHEN s.pi_plano=1 THEN 'PI_PLANO'
                 WHEN s.pi_diario_original IS NULL THEN 'SIN_PI'
                 ELSE 'NORMAL_PI' END AS varchar(30)) AS estado_pi_dia,
       CASE WHEN b.fecha_inicio_episodio IS NOT NULL
            THEN CONCAT('CV025_',CONVERT(char(8),b.fecha_inicio_episodio,112)) END AS episodio_id,
       b.fecha_inicio_episodio,b.fecha_recuperacion,
       b.masa_pi_episodio,b.masa_tum_episodio,
       CASE WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
            THEN b.masa_pi_episodio-b.masa_tum_episodio END AS residual_masa,
       CAST(CASE
           WHEN b.fecha_inicio_episodio IS NULL AND s.pi_filas_dia>1 THEN 'PI_DIARIO_DUPLICADO'
           WHEN b.fecha_inicio_episodio IS NULL AND s.pi_plano=1 AND s.tum_completo=0 THEN 'SIN_TUM_NO_RESOLUBLE'
           WHEN b.fecha_inicio_episodio IS NULL THEN 'NORMAL_PI'
           WHEN b.fecha_recuperacion IS NULL AND s.tum_completo=1 THEN 'CONTINGENCIA_TUM_ABIERTA'
           WHEN b.fecha_recuperacion IS NULL THEN 'SIN_TUM_NO_RESOLUBLE'
           WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
                AND b.masa_pi_episodio=b.masa_tum_episodio THEN 'CONTINGENCIA_TUM_RECONCILIADA'
           ELSE 'RECUPERACION_REQUIERE_REVISION' END AS varchar(45)) AS estado_episodio,
       CAST(CASE
           WHEN b.fecha_inicio_episodio IS NULL AND
                (s.pi_filas_dia>1 OR (s.pi_plano=1 AND s.tum_completo=0)) THEN 'SIN_RESOLVER'
           WHEN b.fecha_inicio_episodio IS NULL THEN 'PI'
           WHEN b.fecha_recuperacion IS NULL AND s.tum_completo=1 THEN 'TUM_PROVISIONAL'
           WHEN b.fecha_recuperacion IS NULL THEN 'SIN_RESOLVER'
           WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
                AND b.masa_pi_episodio=b.masa_tum_episodio THEN 'TUM'
           ELSE 'SIN_RESOLVER' END AS varchar(25)) AS fuente_resuelta_dia,
       CAST(CASE
           WHEN b.fecha_inicio_episodio IS NULL AND
                (s.pi_filas_dia>1 OR (s.pi_plano=1 AND s.tum_completo=0)) THEN NULL
           WHEN b.fecha_inicio_episodio IS NULL THEN s.pi_diario_original
           WHEN b.fecha_recuperacion IS NULL AND s.tum_completo=1 THEN s.tum_diario
           WHEN b.fecha_recuperacion IS NULL THEN NULL
           WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
                AND b.masa_pi_episodio=b.masa_tum_episodio THEN s.tum_diario
           ELSE NULL END AS decimal(30,12)) AS tmh_resuelto,
       CAST(CASE
           WHEN b.fecha_inicio_episodio IS NULL AND s.pi_filas_dia>1 THEN 'PI_DIARIO_DUPLICADO'
           WHEN b.fecha_inicio_episodio IS NULL AND s.pi_plano=1 AND s.tum_completo=0 THEN 'FALTA_TUM_DIRECTO'
           WHEN b.fecha_inicio_episodio IS NULL THEN 'PI_SIN_EPISODIO'
           WHEN b.fecha_recuperacion IS NULL AND s.tum_completo=1 THEN 'ESPERANDO_RECUPERACION_PI'
           WHEN b.fecha_recuperacion IS NULL THEN 'FALTA_TUM_DIRECTO'
           WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
                AND b.masa_pi_episodio=b.masa_tum_episodio THEN 'MASA_PI_TUM_EXACTA'
           ELSE 'MASA_O_COBERTURA_NO_RECONCILIADA' END AS varchar(50)) AS motivo_resolucion,
       s.tum_batch_id_a,s.tum_batch_id_b,s.archivo_batch_a,s.archivo_batch_b
FROM semillas AS s
LEFT JOIN balances AS b ON b.grupo_recuperacion=s.grupo_recuperacion
                       AND s.fecha>=b.fecha_inicio_episodio
