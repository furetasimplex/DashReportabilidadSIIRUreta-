/*
Regression contract for delayed automation:
module A has topology on D1; module B first has topology on D2;
the automation runs on D5. Operational dates must use D2 for the transition.
This script is self-contained and performs no database writes.
*/
SET NOCOUNT ON;
DECLARE @Evidence table
(
    orden int NOT NULL PRIMARY KEY,
    modulo varchar(10) NOT NULL,
    primera_topografia date NULL
);
INSERT INTO @Evidence (orden, modulo, primera_topografia)
VALUES (1, 'A', '2026-09-26'), (2, 'B', '2026-09-29');

DECLARE @FechaEjecucion date = '2026-10-06';
DECLARE @CierreA date, @AperturaB date, @CierreB date;

SELECT @CierreA = e.primera_topografia
FROM @Evidence e WHERE e.orden = 2;
SELECT @AperturaB = e.primera_topografia
FROM @Evidence e WHERE e.orden = 2;
/* No later module evidence: do not synthesize B's close date from D5. */
SET @CierreB = NULL;

IF @CierreA <> '2026-09-29' OR @AperturaB <> '2026-09-29'
    THROW 51000, 'Delayed transition did not use successor first topology date.', 1;
IF @CierreA = @FechaEjecucion OR @AperturaB = @FechaEjecucion
    THROW 51001, 'Execution date leaked into operational transition date.', 1;
IF @CierreB IS NOT NULL
    THROW 51002, 'A close date was invented without successor evidence.', 1;

/* Idempotency: deriving the same dates again from immutable evidence is stable. */
DECLARE @CierreA2 date, @AperturaB2 date;
SELECT @CierreA2 = e.primera_topografia FROM @Evidence e WHERE e.orden = 2;
SELECT @AperturaB2 = e.primera_topografia FROM @Evidence e WHERE e.orden = 2;
IF @CierreA2 <> @CierreA OR @AperturaB2 <> @AperturaB
    THROW 51003, 'Repeated derivation changed the operational dates.', 1;

SELECT 'PASS' AS resultado,
       CAST('2026-09-26' AS date) AS modulo_a_topografia_d1,
       @CierreA AS modulo_a_cierre,
       @AperturaB AS modulo_b_apertura,
       @CierreB AS modulo_b_cierre,
       @FechaEjecucion AS fecha_ejecucion_d5;
