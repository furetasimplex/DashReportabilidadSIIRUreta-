-- table_rows
SELECT t.name,SUM(p.row_count) AS approximate_rows
                FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
                JOIN sys.dm_db_partition_stats p ON p.object_id=t.object_id AND p.index_id IN (0,1)
                WHERE s.name='inventar_SpcHidr' AND t.name IN
                ('campana_parcela_control','flujos_reales_oxido','flujos_reales_sulfuro',
                'drena_concentrados_oxido','drena_concentrados_sulfuro','pad','parcela') GROUP BY t.name;

-- query_store_matches
SELECT q.query_id,p.plan_id,rs.count_executions,rs.avg_duration,
                rs.avg_cpu_time,rs.avg_logical_io_reads,rs.last_execution_time,
                i.start_time AS interval_start,i.end_time AS interval_end,qt.query_sql_text
                FROM sys.query_store_query_text qt JOIN sys.query_store_query q ON q.query_text_id=qt.query_text_id
                JOIN sys.query_store_plan p ON p.query_id=q.query_id
                JOIN sys.query_store_runtime_stats rs ON rs.plan_id=p.plan_id
                JOIN sys.query_store_runtime_stats_interval i ON i.runtime_stats_interval_id=rs.runtime_stats_interval_id
                WHERE qt.query_sql_text LIKE '%WITH fechas AS%'
                AND qt.query_sql_text LIKE '%fn_estado_operacional_parcela_diario%'
                AND qt.query_sql_text NOT LIKE '%sys.query_store_query_text%'
                ORDER BY rs.last_execution_time DESC;

-- source_counts
SELECT 'CPC' AS source,COUNT_BIG(*) AS rows FROM inventar_SpcHidr.campana_parcela_control
                UNION ALL SELECT 'flujo_ox',COUNT_BIG(*) FROM inventar_SpcHidr.v_flujos_oxido_unpivot
                UNION ALL SELECT 'flujo_sulf',COUNT_BIG(*) FROM inventar_SpcHidr.v_flujos_sulfuro_unpivot
                UNION ALL SELECT 'drenaje_ox',COUNT_BIG(*) FROM inventar_SpcHidr.v_drena_oxido_operacional
                UNION ALL SELECT 'drenaje_sulf',COUNT_BIG(*) FROM inventar_SpcHidr.v_drena_sulfuro_operacional
                UNION ALL SELECT 'pad',COUNT_BIG(*) FROM inventar_SpcHidr.pad
                UNION ALL SELECT 'parcela',COUNT_BIG(*) FROM inventar_SpcHidr.parcela;