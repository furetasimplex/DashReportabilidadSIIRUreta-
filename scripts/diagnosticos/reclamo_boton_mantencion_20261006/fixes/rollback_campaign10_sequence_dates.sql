/* Roll back the four-row migration, guarded by the expected post-migration dates. */
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF DB_NAME() <> N'inventar_SpcHidr' OR @@SERVERNAME <> N'VPS-5347319-X'
        THROW 51110, 'Refusing rollback outside the reviewed DEV target.', 1;

    IF (SELECT COUNT(*) FROM reclamo.secuencia_rotopala
        WHERE [campaña_id]=10 AND modulo_id BETWEEN 76 AND 79) <> 4
        THROW 51111, 'Target sequence row count changed; inspect before rollback.', 1;
    IF EXISTS
    (
        SELECT 1 FROM reclamo.secuencia_rotopala
        WHERE [campaña_id]=10 AND pad_id=2 AND rotopala_id=2 AND
        (
            (modulo_id=76 AND (fecha_apertura<>'2026-09-14' OR fecha_cierre<>'2026-09-17')) OR
            (modulo_id=77 AND (fecha_apertura<>'2026-09-17' OR fecha_cierre<>'2026-09-26')) OR
            (modulo_id=78 AND (fecha_apertura<>'2026-09-26' OR fecha_cierre<>'2026-09-29')) OR
            (modulo_id=79 AND (fecha_apertura<>'2026-09-29' OR fecha_cierre IS NOT NULL))
        )
    )
        THROW 51112, 'Post-migration dates differ; rollback would overwrite newer work.', 1;

    UPDATE reclamo.secuencia_rotopala
       SET fecha_apertura=CASE modulo_id
               WHEN 76 THEN '2026-09-23' WHEN 77 THEN '2026-09-23'
               WHEN 78 THEN '2026-10-06' WHEN 79 THEN '2026-10-06' END,
           fecha_cierre=CASE modulo_id
               WHEN 76 THEN '2026-09-23' WHEN 77 THEN '2026-10-06'
               WHEN 78 THEN '2026-10-06' WHEN 79 THEN NULL END
    WHERE [campaña_id]=10 AND pad_id=2 AND rotopala_id=2
      AND secuencia_id IN (1199,1200,1259,1260)
      AND modulo_id BETWEEN 76 AND 79;

    COMMIT TRANSACTION;
    SELECT secuencia_id,modulo_id,estado,fecha_apertura,fecha_cierre
    FROM reclamo.secuencia_rotopala
    WHERE [campaña_id]=10 AND secuencia_id IN (1199,1200,1259,1260)
    ORDER BY orden_secuencia;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
