-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json


CREATE   VIEW siir_curated.vw_siir_drena_concentrado_parcela_long

AS

WITH base AS (

SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src

UNION ALL

SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('fe2' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_fe2]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('fet' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_fet]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('h_p' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_h_p]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
UNION ALL
SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('ph' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_ph]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src

)

SELECT

    b.id_origen_registro,

    b.fecha_registro,

    b.fecha_dia,

    DATEFROMPARTS(YEAR(b.fecha_dia), MONTH(b.fecha_dia), 1) AS mes_inicio,

    YEAR(b.fecha_dia)  AS anio,

    MONTH(b.fecha_dia) AS mes,

    b.pad_id_legacy,

    b.pad_nombre,

    p.parcela_id_global,

    p.nro_parcela_pad,

    p.codigo_parcela_pad,

    p.codigo_parcela_negocio,

    b.analito_codigo,

    a.analito_nombre,

    a.orden_analito,



    b.valor_raw,



    CASE

        WHEN b.valor_raw IS NULL THEN NULL

        WHEN ABS(b.valor_raw) < CONVERT(decimal(18,6), 0.000001)

            THEN CONVERT(decimal(18,6), 0)

        ELSE b.valor_raw

    END AS valor,



    CAST(

        CASE WHEN b.valor_raw IS NULL THEN 1 ELSE 0 END

        AS bit

    ) AS flag_no_convertible,



    CAST(

        CASE

            WHEN b.valor_raw IS NOT NULL

             AND ABS(b.valor_raw) < CONVERT(decimal(18,6), 0.000001)

                THEN 1

            ELSE 0

        END

        AS bit

    ) AS flag_ruido_cercano_cero,



    CAST(

        CASE

            WHEN b.valor_raw IS NOT NULL

             AND b.valor_raw < 0

                THEN 1

            ELSE 0

        END

        AS bit

    ) AS flag_valor_negativo,



    CAST(

        CASE

            WHEN b.pad_id_legacy = 1 THEN 'inventar_SpcHidr.drena_concentrados_oxido'

            WHEN b.pad_id_legacy = 2 THEN 'inventar_SpcHidr.drena_concentrados_sulfuro'

            ELSE 'desconocido'

        END

        AS varchar(128)

    ) AS tabla_origen

FROM base AS b

INNER JOIN siir_curated.vw_siir_dim_parcela_riego AS p

    ON p.pad_id_legacy = b.pad_id_legacy

   AND p.nro_parcela_pad = b.nro_parcela_pad

INNER JOIN siir_curated.vw_siir_dim_analito_riego AS a

    ON a.analito_codigo = b.analito_codigo;
