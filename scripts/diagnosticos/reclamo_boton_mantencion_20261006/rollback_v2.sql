/* Restore the exact v2 before snapshot, only while v2 proposed dates remain. */
SET XACT_ABORT ON;
SET NOCOUNT ON;
IF DB_NAME() <> N'inventar_SpcHidr' OR @@SERVERNAME <> N'VPS-5347319-X'
    THROW 51210, 'Unexpected DEV target.', 1;
DECLARE @Expected table
(
    secuencia_id int PRIMARY KEY, modulo_id int, estado varchar(20),
    apertura date NULL, cierre date NULL,
    old_apertura date NULL, old_cierre date NULL
);
INSERT INTO @Expected VALUES
    (1199,76,'CERRADO','2026-09-14','2026-09-17','2026-09-23','2026-09-23'),
    (1200,77,'CERRADO','2026-09-17','2026-09-26','2026-09-23','2026-10-06'),
    (1259,78,'CERRADO','2026-09-26','2026-09-29','2026-10-06','2026-10-06'),
    (1260,79,'ABIERTO','2026-09-29',NULL,'2026-10-06',NULL);
IF EXISTS
(
    SELECT 1 FROM @Expected e
    LEFT JOIN reclamo.secuencia_rotopala s
      ON s.secuencia_id=e.secuencia_id AND s.[campaña_id]=10 AND s.pad_id=2
     AND s.rotopala_id=2 AND s.modulo_id=e.modulo_id
    WHERE s.secuencia_id IS NULL OR s.estado<>e.estado
       OR NOT (s.fecha_apertura=e.apertura OR (s.fecha_apertura IS NULL AND e.apertura IS NULL))
       OR NOT (s.fecha_cierre=e.cierre OR (s.fecha_cierre IS NULL AND e.cierre IS NULL))
)
    THROW 51211, 'Post-v2 rows changed; refusing rollback.', 1;
UPDATE s
   SET fecha_apertura=e.old_apertura, fecha_cierre=e.old_cierre
FROM reclamo.secuencia_rotopala s
JOIN @Expected e ON e.secuencia_id=s.secuencia_id
WHERE s.[campaña_id]=10 AND s.pad_id=2 AND s.rotopala_id=2;
IF @@ROWCOUNT<>4 THROW 51212, 'Rollback did not update exactly four rows.', 1;
