CREATE   VIEW inventar_SpcHidr.v_contingencia_totalizador_turno
AS

SELECT
    t.id,

    t.fecha_operacional,
    t.turno,

    t.informe_tipo,
    t.circuito,
    t.equipo_codigo,
    t.equipo_nombre,
    t.tipo_medicion,

    t.lectura_inicial,
    t.lectura_final,
    t.valor_turno,
    t.total_excel,
    t.unidad_medida,

    /* ============================================================
       COMPATIBILIDAD CON LA CAPA DE CONTINGENCIA EXISTENTE

       Nueva nomenclatura TUM:
         lectura_inicial_es_formula
         lectura_final_es_formula

       Nomenclatura que ya usa nuestro resolver:
         lectura_inicial_calculada
         lectura_final_calculada
       ============================================================ */
    CAST(t.lectura_inicial_es_formula AS bit)
        AS lectura_inicial_calculada,

    CAST(t.lectura_final_es_formula AS bit)
        AS lectura_final_calculada,

    t.batch_id,
    t.template_code,

    t.business_key_hash,
    t.row_signature,

    /* Nombre histórico utilizado por la contingencia */
    t.archivo_origen AS archivo_batch,

    t.source_sheet,
    t.source_row_number,
    t.source_cells_json,
    t.raw_values_json,
    t.quality_json,

    t.source_revision_at,
    t.created_at,
    t.updated_at

FROM
    inventar_SpcHidr.inventar_SpcHidr.informe_tum_totalizadores_turno AS t;
