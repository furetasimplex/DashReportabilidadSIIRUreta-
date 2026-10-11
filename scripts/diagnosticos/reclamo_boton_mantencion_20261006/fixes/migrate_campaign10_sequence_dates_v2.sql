/* Run in a single SQLAlchemy engine.begin() transaction on guarded DEV only.
   Expected current rows come from timeline_76_80_before.json.
   Operational dates are computed from LIVE VIGENTE topography. */
SET XACT_ABORT ON;
SET NOCOUNT ON;
IF DB_NAME() <> N'inventar_SpcHidr' OR @@SERVERNAME <> N'VPS-5347319-X'
    THROW 51200, 'Unexpected DEV target.', 1;

DECLARE @Before table
(
    secuencia_id int PRIMARY KEY, modulo_id int, estado varchar(20),
    apertura date NULL, cierre date NULL
);
INSERT INTO @Before VALUES
    (1199,76,'CERRADO','2026-09-23','2026-09-23'),
    (1200,77,'CERRADO','2026-09-23','2026-10-06'),
    (1259,78,'CERRADO','2026-10-06','2026-10-06'),
    (1260,79,'ABIERTO','2026-10-06',NULL);

IF (SELECT COUNT(*) FROM reclamo.secuencia_rotopala
    WHERE [campaña_id]=10 AND pad_id=2 AND modulo_id BETWEEN 76 AND 79) <> 4
    THROW 51201, 'Sequence row count changed.', 1;
IF EXISTS
(
    SELECT 1 FROM @Before b
    LEFT JOIN reclamo.secuencia_rotopala s
      ON s.secuencia_id=b.secuencia_id AND s.[campaña_id]=10 AND s.pad_id=2
     AND s.rotopala_id=2 AND s.modulo_id=b.modulo_id
    WHERE s.secuencia_id IS NULL OR s.estado<>b.estado
       OR NOT (s.fecha_apertura=b.apertura OR (s.fecha_apertura IS NULL AND b.apertura IS NULL))
       OR NOT (s.fecha_cierre=b.cierre OR (s.fecha_cierre IS NULL AND b.cierre IS NULL))
)
    THROW 51202, 'Current dates or states differ from v2 before snapshot.', 1;

DECLARE @Topo table (modulo_id int PRIMARY KEY, primera date NOT NULL);
INSERT INTO @Topo
SELECT modulo_id, MIN(CAST(fecha_medicion AS date))
FROM reclamo.topografia_avance
WHERE [campaña_id]=10 AND pad_id=2 AND modulo_id BETWEEN 76 AND 79
  AND estado='VIGENTE'
GROUP BY modulo_id;
IF (SELECT COUNT(*) FROM @Topo) <> 4
    THROW 51203, 'Four modules must have VIGENTE topography.', 1;
IF EXISTS
(
    SELECT 1 FROM @Topo t
    WHERE (t.modulo_id=76 AND t.primera<>'2026-09-14')
       OR (t.modulo_id=77 AND t.primera<>'2026-09-17')
       OR (t.modulo_id=78 AND t.primera<>'2026-09-26')
       OR (t.modulo_id=79 AND t.primera<>'2026-09-29')
)
    THROW 51204, 'VIGENTE evidence changed since the read-only simulation.', 1;

DECLARE @Changes table
(
    secuencia_id int, modulo_id int, estado varchar(20),
    old_apertura date NULL, old_cierre date NULL,
    new_apertura date NULL, new_cierre date NULL
);
;WITH proposal AS
(
    SELECT s.secuencia_id, t.primera AS apertura,
           CASE WHEN s.estado='CERRADO'
                THEN LEAD(t.primera) OVER (ORDER BY s.orden_secuencia)
                ELSE s.fecha_cierre END AS cierre
    FROM reclamo.secuencia_rotopala s
    JOIN @Topo t ON t.modulo_id=s.modulo_id
    WHERE s.[campaña_id]=10 AND s.pad_id=2 AND s.rotopala_id=2
      AND s.modulo_id BETWEEN 76 AND 79
)
UPDATE s
   SET fecha_apertura=p.apertura, fecha_cierre=p.cierre
OUTPUT inserted.secuencia_id,inserted.modulo_id,inserted.estado,
       deleted.fecha_apertura,deleted.fecha_cierre,
       inserted.fecha_apertura,inserted.fecha_cierre
  INTO @Changes
FROM reclamo.secuencia_rotopala s
JOIN proposal p ON p.secuencia_id=s.secuencia_id
WHERE s.fecha_apertura<>p.apertura
   OR s.fecha_cierre<>p.cierre
   OR (s.fecha_cierre IS NULL AND p.cierre IS NOT NULL)
   OR (s.fecha_cierre IS NOT NULL AND p.cierre IS NULL);

IF (SELECT COUNT(*) FROM @Changes) <> 4
    THROW 51205, 'V2 migration did not change exactly the four reviewed rows.', 1;
SELECT * FROM @Changes ORDER BY modulo_id;
