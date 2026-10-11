/*
Controlled DEV-only correction of the materialized operational window.
Before snapshot: ../sequence_backfill_snapshot_before.json
Scope: PAD 2 / campaign 10 / sequence IDs 1199,1200,1259,1260 (modules 76-79).
Module 80 is intentionally excluded because it has no VIGENTE topography.
The script changes only fecha_apertura/fecha_cierre; state and freeze dates stay intact.
*/
SET XACT_ABORT ON;
SET NOCOUNT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    IF DB_NAME() <> N'inventar_SpcHidr'
        THROW 51100, 'Refusing migration outside DEV inventar_SpcHidr.', 1;
    IF @@SERVERNAME <> N'VPS-5347319-X'
        THROW 51101, 'Refusing migration on unexpected SQL Server.', 1;

    DECLARE @Before table
    (
        secuencia_id int PRIMARY KEY,
        modulo_id int NOT NULL,
        estado varchar(20) NOT NULL,
        fecha_apertura date NULL,
        fecha_cierre date NULL
    );
    INSERT INTO @Before VALUES
        (1199,76,'CERRADO','2026-09-23','2026-09-23'),
        (1200,77,'CERRADO','2026-09-23','2026-10-06'),
        (1259,78,'CERRADO','2026-10-06','2026-10-06'),
        (1260,79,'ABIERTO','2026-10-06',NULL);

    IF (SELECT COUNT(*) FROM reclamo.secuencia_rotopala
        WHERE [campaña_id]=10 AND modulo_id BETWEEN 76 AND 79) <> 4
        THROW 51102, 'Target sequence rows changed; compare with snapshot before retrying.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @Before b
        LEFT JOIN reclamo.secuencia_rotopala s
          ON s.secuencia_id=b.secuencia_id AND s.[campaña_id]=10
         AND s.pad_id=2 AND s.rotopala_id=2 AND s.modulo_id=b.modulo_id
        WHERE s.secuencia_id IS NULL OR s.estado<>b.estado
           OR NOT (s.fecha_apertura=b.fecha_apertura OR (s.fecha_apertura IS NULL AND b.fecha_apertura IS NULL))
           OR NOT (s.fecha_cierre=b.fecha_cierre OR (s.fecha_cierre IS NULL AND b.fecha_cierre IS NULL))
    )
        THROW 51103, 'Target row values differ from saved before snapshot.', 1;

    DECLARE @FirstTopo table (modulo_id int PRIMARY KEY, primera_topografia date NOT NULL);
    INSERT INTO @FirstTopo (modulo_id, primera_topografia)
    SELECT modulo_id, MIN(fecha_medicion)
    FROM reclamo.topografia_avance
    WHERE [campaña_id]=10 AND pad_id=2 AND modulo_id BETWEEN 76 AND 79
      AND estado='VIGENTE'
    GROUP BY modulo_id;

    IF (SELECT COUNT(*) FROM @FirstTopo) <> 4
       OR EXISTS (SELECT 1 FROM @FirstTopo WHERE
            (modulo_id=76 AND primera_topografia<>'2026-09-14') OR
            (modulo_id=77 AND primera_topografia<>'2026-09-17') OR
            (modulo_id=78 AND primera_topografia<>'2026-09-26') OR
            (modulo_id=79 AND primera_topografia<>'2026-09-29'))
        THROW 51104, 'VIGENTE topology first dates differ from reviewed simulation.', 1;

    DECLARE @Changes table
    (
        secuencia_id int, modulo_id int, estado varchar(20),
        old_fecha_apertura date NULL, old_fecha_cierre date NULL,
        new_fecha_apertura date NULL, new_fecha_cierre date NULL
    );

    ;WITH proposal AS
    (
        SELECT s.secuencia_id,s.modulo_id,
               f.primera_topografia AS fecha_apertura_propuesta,
               LEAD(f.primera_topografia) OVER (ORDER BY s.orden_secuencia) AS fecha_cierre_propuesta
        FROM reclamo.secuencia_rotopala s
        JOIN @FirstTopo f ON f.modulo_id=s.modulo_id
        WHERE s.[campaña_id]=10 AND s.pad_id=2 AND s.rotopala_id=2
          AND s.modulo_id BETWEEN 76 AND 79
    )
    UPDATE s
       SET fecha_apertura=p.fecha_apertura_propuesta,
           fecha_cierre=p.fecha_cierre_propuesta
    OUTPUT inserted.secuencia_id,inserted.modulo_id,inserted.estado,
           deleted.fecha_apertura,deleted.fecha_cierre,
           inserted.fecha_apertura,inserted.fecha_cierre
      INTO @Changes
    FROM reclamo.secuencia_rotopala s
    JOIN proposal p ON p.secuencia_id=s.secuencia_id
    WHERE s.[campaña_id]=10 AND s.pad_id=2 AND s.rotopala_id=2;

    IF (SELECT COUNT(*) FROM @Changes) <> 4
        THROW 51105, 'Migration did not update exactly four reviewed rows.', 1;

    COMMIT TRANSACTION;
    SELECT * FROM @Changes ORDER BY modulo_id;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
