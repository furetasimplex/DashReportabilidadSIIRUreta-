-- object inventar_SpcHidr.vw_tablero_lixiviacion_final_v2
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_tablero_lixiviacion_final_v2"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_tablero_lixiviacion_final_v2
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_tablero_lixiviacion_final_v2"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_tablero_lixiviacion_final_v2
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_tablero_lixiviacion_final_v2"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.fn_estado_operacional_parcela_diario
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.fn_estado_operacional_parcela_diario"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.fn_estado_operacional_parcela_diario
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.fn_estado_operacional_parcela_diario"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.fn_estado_operacional_parcela_diario
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.fn_estado_operacional_parcela_diario"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.campana_parcela_control
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.campana_parcela_control"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.campana_parcela_control
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.campana_parcela_control"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.campana_parcela_control
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.campana_parcela_control"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.vw_drena_concentrados_oxido_long_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_drena_concentrados_oxido_long_operacional"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_drena_concentrados_oxido_long_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_drena_concentrados_oxido_long_operacional"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_drena_concentrados_oxido_long_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_drena_concentrados_oxido_long_operacional"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.vw_drena_concentrados_sulfuro_long_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_drena_concentrados_sulfuro_long_operacional"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_drena_concentrados_sulfuro_long_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_drena_concentrados_sulfuro_long_operacional"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_drena_concentrados_sulfuro_long_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_drena_concentrados_sulfuro_long_operacional"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.vw_flujos_reales_oxido_long
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_flujos_reales_oxido_long"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_flujos_reales_oxido_long
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_flujos_reales_oxido_long"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_flujos_reales_oxido_long
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_flujos_reales_oxido_long"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.vw_flujos_reales_sulfuro_long
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_flujos_reales_sulfuro_long"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_flujos_reales_sulfuro_long
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_flujos_reales_sulfuro_long"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_flujos_reales_sulfuro_long
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_flujos_reales_sulfuro_long"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.vw_riego_oxido_refino_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_oxido_refino_operacional"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_riego_oxido_refino_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_oxido_refino_operacional"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_riego_oxido_refino_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_oxido_refino_operacional"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.vw_riego_sulfuro_refino_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_sulfuro_refino_operacional"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_riego_sulfuro_refino_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_sulfuro_refino_operacional"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_riego_sulfuro_refino_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_sulfuro_refino_operacional"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.pad
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.pad"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.pad
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.pad"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.pad
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.pad"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.parcela
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.parcela"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.parcela
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.parcela"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.parcela
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.parcela"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.v_drena_oxido_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_oxido_operacional"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.v_drena_oxido_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_oxido_operacional"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.v_drena_oxido_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_oxido_operacional"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.v_drena_sulfuro_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_sulfuro_operacional"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.v_drena_sulfuro_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_sulfuro_operacional"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.v_drena_sulfuro_operacional
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_sulfuro_operacional"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.v_flujos_oxido_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_flujos_oxido_unpivot"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.v_flujos_oxido_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_flujos_oxido_unpivot"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.v_flujos_oxido_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_flujos_oxido_unpivot"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.v_flujos_sulfuro_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_flujos_sulfuro_unpivot"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.v_flujos_sulfuro_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_flujos_sulfuro_unpivot"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.v_flujos_sulfuro_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_flujos_sulfuro_unpivot"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.drena_concentrados_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.drena_concentrados_oxido"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.drena_concentrados_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.drena_concentrados_oxido"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.drena_concentrados_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.drena_concentrados_oxido"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.drena_concentrados_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.drena_concentrados_sulfuro"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.drena_concentrados_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.drena_concentrados_sulfuro"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.drena_concentrados_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.drena_concentrados_sulfuro"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.flujos_reales_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.flujos_reales_oxido"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.flujos_reales_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.flujos_reales_oxido"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.flujos_reales_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.flujos_reales_oxido"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.flujos_reales_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.flujos_reales_sulfuro"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.flujos_reales_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.flujos_reales_sulfuro"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.flujos_reales_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.flujos_reales_sulfuro"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.vw_riego_oxido_refino_base
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_oxido_refino_base"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_riego_oxido_refino_base
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_oxido_refino_base"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_riego_oxido_refino_base
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_oxido_refino_base"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.vw_riego_sulfuro_refino_base
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_sulfuro_refino_base"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.vw_riego_sulfuro_refino_base
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_sulfuro_refino_base"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.vw_riego_sulfuro_refino_base
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.vw_riego_sulfuro_refino_base"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.v_drena_oxido_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_oxido_unpivot"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.v_drena_oxido_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_oxido_unpivot"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.v_drena_oxido_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_oxido_unpivot"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.v_drena_sulfuro_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_sulfuro_unpivot"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.v_drena_sulfuro_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_sulfuro_unpivot"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.v_drena_sulfuro_unpivot
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.v_drena_sulfuro_unpivot"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.riego_concentrados_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.riego_concentrados_oxido"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.riego_concentrados_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.riego_concentrados_oxido"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.riego_concentrados_oxido
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.riego_concentrados_oxido"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- object inventar_SpcHidr.riego_concentrados_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.riego_concentrados_sulfuro"}
SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name);

-- columns inventar_SpcHidr.riego_concentrados_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.riego_concentrados_sulfuro"}
SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id;

-- dependencies inventar_SpcHidr.riego_concentrados_sulfuro
-- Parametros SQLAlchemy: {"name": "inventar_SpcHidr.riego_concentrados_sulfuro"}
SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name);

-- v2_metrics
-- Parametros SQLAlchemy: {"desde": "2026-09-10", "hasta": "2026-09-10"}
WITH b AS (SELECT * FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta),
                k AS (SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) AS n FROM b GROUP BY pad_id,parcela_id,fecha)
                SELECT (SELECT COUNT_BIG(*) FROM b) AS rows,(SELECT COUNT_BIG(*) FROM k) AS unique_keys,
                (SELECT COUNT_BIG(*) FROM k WHERE n>1) AS duplicate_keys,(SELECT MAX(n) FROM k) AS max_per_key,
                (SELECT COUNT_BIG(*) FROM b WHERE pad_id IS NULL OR parcela_id IS NULL OR fecha IS NULL) AS null_keys;

-- v2_aggregates
-- Parametros SQLAlchemy: {"desde": "2026-09-10", "hasta": "2026-09-10"}
SELECT pad_id,estado_asignacion,COUNT_BIG(*) AS rows,
                SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,
                COUNT(delta_cu_gl) AS delta_count,COUNT(cu_drenaje_gl) AS drenaje_count,COUNT(cu_refino_gl) AS refino_count,
                SUM(CASE WHEN delta_cu_gl<0 THEN 1 ELSE 0 END) AS negative_delta,
                SUM(CASE WHEN campana_id IS NULL THEN 1 ELSE 0 END) AS null_campaign
                FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY pad_id,estado_asignacion;

-- v2_metrics
-- Parametros SQLAlchemy: {"desde": "2026-09-01", "hasta": "2026-09-10"}
WITH b AS (SELECT * FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta),
                k AS (SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) AS n FROM b GROUP BY pad_id,parcela_id,fecha)
                SELECT (SELECT COUNT_BIG(*) FROM b) AS rows,(SELECT COUNT_BIG(*) FROM k) AS unique_keys,
                (SELECT COUNT_BIG(*) FROM k WHERE n>1) AS duplicate_keys,(SELECT MAX(n) FROM k) AS max_per_key,
                (SELECT COUNT_BIG(*) FROM b WHERE pad_id IS NULL OR parcela_id IS NULL OR fecha IS NULL) AS null_keys;

-- v2_aggregates
-- Parametros SQLAlchemy: {"desde": "2026-09-01", "hasta": "2026-09-10"}
SELECT pad_id,estado_asignacion,COUNT_BIG(*) AS rows,
                SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,
                COUNT(delta_cu_gl) AS delta_count,COUNT(cu_drenaje_gl) AS drenaje_count,COUNT(cu_refino_gl) AS refino_count,
                SUM(CASE WHEN delta_cu_gl<0 THEN 1 ELSE 0 END) AS negative_delta,
                SUM(CASE WHEN campana_id IS NULL THEN 1 ELSE 0 END) AS null_campaign
                FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY pad_id,estado_asignacion;

-- v2_metrics
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
WITH b AS (SELECT * FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta),
                k AS (SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) AS n FROM b GROUP BY pad_id,parcela_id,fecha)
                SELECT (SELECT COUNT_BIG(*) FROM b) AS rows,(SELECT COUNT_BIG(*) FROM k) AS unique_keys,
                (SELECT COUNT_BIG(*) FROM k WHERE n>1) AS duplicate_keys,(SELECT MAX(n) FROM k) AS max_per_key,
                (SELECT COUNT_BIG(*) FROM b WHERE pad_id IS NULL OR parcela_id IS NULL OR fecha IS NULL) AS null_keys;

-- v2_aggregates
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
SELECT pad_id,estado_asignacion,COUNT_BIG(*) AS rows,
                SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,
                COUNT(delta_cu_gl) AS delta_count,COUNT(cu_drenaje_gl) AS drenaje_count,COUNT(cu_refino_gl) AS refino_count,
                SUM(CASE WHEN delta_cu_gl<0 THEN 1 ELSE 0 END) AS negative_delta,
                SUM(CASE WHEN campana_id IS NULL THEN 1 ELSE 0 END) AS null_campaign
                FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY pad_id,estado_asignacion;

-- join_compatibility
-- Parametros SQLAlchemy: {"desde": "2026-09-10", "hasta": "2026-09-10"}
WITH dates AS (SELECT CAST(:desde AS date) AS fecha UNION ALL
                SELECT DATEADD(day,1,fecha) FROM dates WHERE fecha<CAST(:hasta AS date)),
                e AS (SELECT f.* FROM dates d CROSS APPLY inventar_SpcHidr.fn_estado_operacional_parcela_diario(d.fecha) f),
                b AS (SELECT * FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta),
                ek AS (SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) n FROM e GROUP BY pad_id,parcela_id,fecha)
                SELECT (SELECT COUNT_BIG(*) FROM b) AS v2_rows,(SELECT COUNT_BIG(*) FROM e) AS estado_rows,
                (SELECT COUNT_BIG(*) FROM ek WHERE n>1) AS estado_duplicate_keys,
                (SELECT COUNT_BIG(*) FROM b LEFT JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id) AS left_join_rows,
                (SELECT COUNT_BIG(*) FROM b INNER JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id) AS inner_join_rows,
                (SELECT COUNT_BIG(*) FROM b WHERE NOT EXISTS (SELECT 1 FROM e WHERE e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id)) AS v2_unmatched,
                (SELECT COUNT_BIG(*) FROM e WHERE NOT EXISTS (SELECT 1 FROM b WHERE e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id)) AS estado_unmatched,
                (SELECT COUNT_BIG(*) FROM b JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id
                 WHERE b.campana_id<>e.campana_id OR (b.campana_id IS NULL AND e.campana_id IS NOT NULL)
                    OR (b.campana_id IS NOT NULL AND e.campana_id IS NULL)) AS campaign_mismatch
                OPTION (MAXRECURSION 100);

-- join_compatibility
-- Parametros SQLAlchemy: {"desde": "2026-09-01", "hasta": "2026-09-10"}
WITH dates AS (SELECT CAST(:desde AS date) AS fecha UNION ALL
                SELECT DATEADD(day,1,fecha) FROM dates WHERE fecha<CAST(:hasta AS date)),
                e AS (SELECT f.* FROM dates d CROSS APPLY inventar_SpcHidr.fn_estado_operacional_parcela_diario(d.fecha) f),
                b AS (SELECT * FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta),
                ek AS (SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) n FROM e GROUP BY pad_id,parcela_id,fecha)
                SELECT (SELECT COUNT_BIG(*) FROM b) AS v2_rows,(SELECT COUNT_BIG(*) FROM e) AS estado_rows,
                (SELECT COUNT_BIG(*) FROM ek WHERE n>1) AS estado_duplicate_keys,
                (SELECT COUNT_BIG(*) FROM b LEFT JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id) AS left_join_rows,
                (SELECT COUNT_BIG(*) FROM b INNER JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id) AS inner_join_rows,
                (SELECT COUNT_BIG(*) FROM b WHERE NOT EXISTS (SELECT 1 FROM e WHERE e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id)) AS v2_unmatched,
                (SELECT COUNT_BIG(*) FROM e WHERE NOT EXISTS (SELECT 1 FROM b WHERE e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id)) AS estado_unmatched,
                (SELECT COUNT_BIG(*) FROM b JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id
                 WHERE b.campana_id<>e.campana_id OR (b.campana_id IS NULL AND e.campana_id IS NOT NULL)
                    OR (b.campana_id IS NOT NULL AND e.campana_id IS NULL)) AS campaign_mismatch
                OPTION (MAXRECURSION 100);

-- reference_cases
-- Parametros SQLAlchemy: {"fecha": "2026-09-10"}
SELECT e.fecha,e.pad_id,e.numero_parcela,e.parcela_id,
            e.campana_id AS operational_campana_id,e.estado_operacional,e.composicion_modulos,e.riego_activo,e.drenaje_activo,
            b.campana_id AS diagnostic_campana_id,b.numero_campana,b.estado_asignacion,b.flujo_m3_h,b.flujo_m3_d,
            b.cu_drenaje_gl,b.cu_refino_gl,b.delta_cu_gl,b.transferencia_cu_kg_d,b.transferencia_cu_t_d
            FROM inventar_SpcHidr.fn_estado_operacional_parcela_diario(:fecha) e LEFT JOIN inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 b ON b.fecha=e.fecha AND b.pad_id=e.pad_id AND b.parcela_id=e.parcela_id
            WHERE (e.pad_id=1 AND e.numero_parcela IN (1,17,29)) OR (e.pad_id=2 AND e.numero_parcela IN (1,7,9,28))
            ORDER BY e.pad_id,e.numero_parcela;

-- source_uniqueness vw_flujos_reales_oxido_long
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
WITH k AS (
                    SELECT parcela_id,fecha,COUNT_BIG(*) n FROM inventar_SpcHidr.vw_flujos_reales_oxido_long
                    WHERE fecha BETWEEN :desde AND :hasta GROUP BY parcela_id,fecha)
                    SELECT SUM(n) AS rows,COUNT_BIG(*) AS unique_keys,MAX(n) AS max_per_key,
                    SUM(CASE WHEN n>1 THEN 1 ELSE 0 END) AS duplicate_keys FROM k;

-- source_uniqueness vw_drena_concentrados_oxido_long_operacional
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
WITH k AS (
                    SELECT nro_parcela_pad,fecha,COUNT_BIG(*) n FROM inventar_SpcHidr.vw_drena_concentrados_oxido_long_operacional
                    WHERE fecha BETWEEN :desde AND :hasta GROUP BY nro_parcela_pad,fecha)
                    SELECT SUM(n) AS rows,COUNT_BIG(*) AS unique_keys,MAX(n) AS max_per_key,
                    SUM(CASE WHEN n>1 THEN 1 ELSE 0 END) AS duplicate_keys FROM k;

-- source_uniqueness vw_riego_oxido_refino_operacional
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
WITH k AS (
                    SELECT fecha,COUNT_BIG(*) n FROM inventar_SpcHidr.vw_riego_oxido_refino_operacional
                    WHERE fecha BETWEEN :desde AND :hasta GROUP BY fecha)
                    SELECT SUM(n) AS rows,COUNT_BIG(*) AS unique_keys,MAX(n) AS max_per_key,
                    SUM(CASE WHEN n>1 THEN 1 ELSE 0 END) AS duplicate_keys FROM k;

-- source_uniqueness vw_flujos_reales_sulfuro_long
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
WITH k AS (
                    SELECT parcela_id,fecha,COUNT_BIG(*) n FROM inventar_SpcHidr.vw_flujos_reales_sulfuro_long
                    WHERE fecha BETWEEN :desde AND :hasta GROUP BY parcela_id,fecha)
                    SELECT SUM(n) AS rows,COUNT_BIG(*) AS unique_keys,MAX(n) AS max_per_key,
                    SUM(CASE WHEN n>1 THEN 1 ELSE 0 END) AS duplicate_keys FROM k;

-- source_uniqueness vw_drena_concentrados_sulfuro_long_operacional
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
WITH k AS (
                    SELECT nro_parcela_pad,fecha,COUNT_BIG(*) n FROM inventar_SpcHidr.vw_drena_concentrados_sulfuro_long_operacional
                    WHERE fecha BETWEEN :desde AND :hasta GROUP BY nro_parcela_pad,fecha)
                    SELECT SUM(n) AS rows,COUNT_BIG(*) AS unique_keys,MAX(n) AS max_per_key,
                    SUM(CASE WHEN n>1 THEN 1 ELSE 0 END) AS duplicate_keys FROM k;

-- source_uniqueness vw_riego_sulfuro_refino_operacional
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
WITH k AS (
                    SELECT fecha,COUNT_BIG(*) n FROM inventar_SpcHidr.vw_riego_sulfuro_refino_operacional
                    WHERE fecha BETWEEN :desde AND :hasta GROUP BY fecha)
                    SELECT SUM(n) AS rows,COUNT_BIG(*) AS unique_keys,MAX(n) AS max_per_key,
                    SUM(CASE WHEN n>1 THEN 1 ELSE 0 END) AS duplicate_keys FROM k;

-- outside_positive
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
SELECT fecha,pad_id,parcela_id,nro_parcela_pad,
            campana_id,estado_asignacion,flujo_m3_d,delta_cu_gl,transferencia_cu_t_d
            FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta
            AND estado_asignacion='FUERA_VENTANA_RIEGO' AND flujo_m3_d>0
            ORDER BY fecha,pad_id,parcela_id;

-- runtime_helper
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
SELECT DISTINCT pad_id,campana_id,numero_campana FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta AND campana_id IS NOT NULL ORDER BY pad_id,campana_id,numero_campana;

-- runtime_helper
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
SELECT DISTINCT pad_id,parcela_id,nro_parcela_pad FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta ORDER BY pad_id,parcela_id,nro_parcela_pad;

-- runtime_helper
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
SELECT COUNT_BIG(*) AS registros,SUM(flujo_m3_d) AS flujo,
        SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,
        COUNT_BIG(CASE WHEN estado_asignacion='FUERA_VENTANA_RIEGO' THEN 1 END) AS fuera
        FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta;

-- runtime_helper
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
SELECT fecha,pad_id,SUM(flujo_m3_d) AS flujo,
        AVG(cu_drenaje_gl) AS drenaje,AVG(cu_refino_gl) AS refino,
        SUM(transferencia_cu_t_d) AS transferencia
        FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY fecha,pad_id ORDER BY fecha,pad_id;

-- runtime_helper
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10"}
SELECT COUNT_BIG(*) FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta;

-- runtime_helper
-- Parametros SQLAlchemy: {"desde": "2026-06-01", "hasta": "2026-09-10", "offset": 0, "size": 25}
SELECT fecha AS fecha,CASE pad_id WHEN 1 THEN N'Óxidos' WHEN 2 THEN N'Sulfuros' ELSE N'PAD desconocido' END AS pad,nro_parcela_pad AS parcela,numero_campana AS campana,estado_asignacion AS estado,flujo_m3_d AS flujo_m3_d,cu_drenaje_gl AS cu_drenaje_gl,cu_refino_gl AS cu_refino_gl,delta_cu_gl AS delta_cu_gl,transferencia_cu_t_d AS transferencia_cu_t_d
            FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta ORDER BY fecha,pad_id,parcela_id
            OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY;