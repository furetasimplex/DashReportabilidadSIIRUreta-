/* ============================================================================
   Migraciones incrementales de inventar_SpcHidr.reporte_torre_oficial_detalle

   El CREATE TABLE de reporte_torre_oficial.sql quedo desfasado respecto de la
   BD: las columnas de TM3/SRR y los largos de comentario se aplicaron a mano
   sin registrarlos. Este archivo deja constancia de ese estado y agrega la
   columna Pad_Original.

   Todo es idempotente: se puede ejecutar tantas veces como haga falta.
   ============================================================================ */

/* ---------------------------------------------------------------------------
   1. Columnas TM3 / SRR  (ya presentes en produccion al 2026-07-30, se dejan
      registradas para que el esquema sea reproducible desde cero)
   --------------------------------------------------------------------------- */
IF COL_LENGTH('inventar_SpcHidr.reporte_torre_oficial_detalle', 'TMH_CV01') IS NULL
    ALTER TABLE inventar_SpcHidr.reporte_torre_oficial_detalle
        ADD TMH_CV01 DECIMAL(18, 4) NULL;
GO
IF COL_LENGTH('inventar_SpcHidr.reporte_torre_oficial_detalle', 'Rep_TM3_Quimico') IS NULL
    ALTER TABLE inventar_SpcHidr.reporte_torre_oficial_detalle
        ADD Rep_TM3_Quimico INT NULL;
GO
IF COL_LENGTH('inventar_SpcHidr.reporte_torre_oficial_detalle', 'Rep_TM3_Fisico') IS NULL
    ALTER TABLE inventar_SpcHidr.reporte_torre_oficial_detalle
        ADD Rep_TM3_Fisico INT NULL;
GO
IF COL_LENGTH('inventar_SpcHidr.reporte_torre_oficial_detalle', 'TM3_Activo') IS NULL
    ALTER TABLE inventar_SpcHidr.reporte_torre_oficial_detalle
        ADD TM3_Activo INT NULL;
GO
IF COL_LENGTH('inventar_SpcHidr.reporte_torre_oficial_detalle', 'Comentario_TM3_Quimico') IS NULL
    ALTER TABLE inventar_SpcHidr.reporte_torre_oficial_detalle
        ADD Comentario_TM3_Quimico NVARCHAR(2000) NULL;
GO
IF COL_LENGTH('inventar_SpcHidr.reporte_torre_oficial_detalle', 'Comentario_TM3_Fisico') IS NULL
    ALTER TABLE inventar_SpcHidr.reporte_torre_oficial_detalle
        ADD Comentario_TM3_Fisico NVARCHAR(2000) NULL;
GO

/* ---------------------------------------------------------------------------
   2. Pad editable  (2026-07-30)

   Pad          = valor EFECTIVO. Es el que alimenta todos los calculos del
                  reporte (tabla "Mineral apilado por Pad", detalle mensual).
   Pad_Original = valor DERIVADO por _normalizar_material_torres + material
                  predominante por tonelaje. Nunca se edita.

   Invariante: una fila fue ajustada a mano si y solo si Pad <> Pad_Original.
   El backfill hace Pad_Original = Pad en el historico, donde no hubo ediciones,
   de modo que el invariante se cumple tambien hacia atras.
   --------------------------------------------------------------------------- */
IF COL_LENGTH('inventar_SpcHidr.reporte_torre_oficial_detalle', 'Pad_Original') IS NULL
    ALTER TABLE inventar_SpcHidr.reporte_torre_oficial_detalle
        ADD Pad_Original NVARCHAR(100) NULL;
GO

UPDATE inventar_SpcHidr.reporte_torre_oficial_detalle
SET Pad_Original = Pad
WHERE Pad_Original IS NULL
  AND Pad IS NOT NULL;
GO

/* ---------------------------------------------------------------------------
   3. Autoria del ajuste  (2026-07-30)

   Pad_Ajustado_Por = usuario que publico el reporte donde aparecio el ajuste.
   NULL cuando Pad == Pad_Original (no hubo ajuste). Al republicar un mes, un
   override arrastrado conserva su autor original; no se resella.
   --------------------------------------------------------------------------- */
IF COL_LENGTH('inventar_SpcHidr.reporte_torre_oficial_detalle', 'Pad_Ajustado_Por') IS NULL
    ALTER TABLE inventar_SpcHidr.reporte_torre_oficial_detalle
        ADD Pad_Ajustado_Por NVARCHAR(100) NULL;
GO

/* Verificacion: filas con Pad ajustado a mano y quien lo hizo. */
-- SELECT id_reporte, Fecha, Turno, Pad_Original, Pad, Pad_Ajustado_Por
-- FROM inventar_SpcHidr.reporte_torre_oficial_detalle
-- WHERE ISNULL(Pad, '') <> ISNULL(Pad_Original, '')
-- ORDER BY Fecha, Turno;
