"""Build reviewed ALTER batches from read-only LIVE definitions."""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEF = HERE / "sp_definitions"
FIX = HERE / "fixes"
FIX.mkdir(exist_ok=True)


def read(name: str) -> str:
    return (DEF / f"reclamo.{name}.sql").read_text(encoding="utf-8")


def replace_once(source: str, pattern: str, replacement: str, label: str, *, regex=False) -> str:
    if regex:
        updated, count = re.subn(pattern, replacement, source, count=1, flags=re.I | re.S)
    else:
        count = source.count(pattern)
        updated = source.replace(pattern, replacement, 1)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return updated


def deploy(name: str, source: str) -> None:
    source, count = re.subn(r"(?im)^\s*CREATE\s+PROCEDURE\b", "ALTER PROCEDURE", source, count=1)
    if count != 1:
        raise RuntimeError(f"{name}: could not convert first CREATE PROCEDURE to ALTER")
    (FIX / f"alter_reclamo.{name}.sql").write_text(source, encoding="utf-8")


# Open any newly frozen topology module on its first valid operational
# topography date; when synchronization has not run yet, use the same positive
# source movements already used to discover the candidate.
freeze = read("sp_auto_congelar_modulos_nuevos")
camp_col = re.search(r"cr\.\[([^\]]+)\]", freeze)
if not camp_col:
    raise RuntimeError("Could not discover campaign column in live source query")
camp = camp_col.group(1)
open_expr = f"""(SELECT MIN(x.fecha_operacional)
                    FROM (
                        SELECT CAST(ta.fecha_medicion AS date) AS fecha_operacional
                        FROM [reclamo].[topografia_avance] ta
                        WHERE ta.[{camp}] = @Camp AND ta.pad_id = @Pad
                          AND ta.modulo_id = @Mod AND ta.estado = 'VIGENTE'
                        UNION ALL
                        SELECT CAST(cr.fecha AS date)
                        FROM [inventar_SpcHidr].[control_reclamo_diario] cr
                        WHERE cr.[{camp}] = @Camp AND cr.pad_id = @Pad
                          AND cr.modulo_id = @Mod AND COALESCE(cr.volumen_diario_m3,0) > 0
                    ) x)"""
freeze = replace_once(
    freeze,
    "SET estado = 'ABIERTO', fecha_apertura = CAST(SYSDATETIME() AS date)",
    f"SET estado = 'ABIERTO', fecha_apertura = {open_expr}",
    "freeze/open timestamp",
)
deploy("sp_auto_congelar_modulos_nuevos", freeze)


# The orphan-cup refill already chooses a pending row only when it has valid
# topography later than the latest closed row. Reuse precisely that qualifying
# evidence for fecha_apertura instead of the day the helper happened to run.
maintain = read("sp_auto_mantener_secuencia")
camp_col = re.search(r"s\.[\[]([^\]]+)\]", maintain)
if not camp_col:
    raise RuntimeError("Could not discover campaign column in sequence source")
camp = camp_col.group(1)
maintain = replace_once(
    maintain,
    "SET estado = 'ABIERTO', fecha_apertura = CAST(SYSDATETIME() AS date)",
    f"""SET estado = 'ABIERTO', fecha_apertura =
                (SELECT MIN(CAST(t.fecha_medicion AS date))
                 FROM [reclamo].[topografia_avance] t
                 WHERE t.[{camp}] = @CampRell AND t.pad_id = @PadRell
                   AND t.modulo_id = @ModRell AND t.estado = 'VIGENTE'
                   AND (@UltimaMedicionCerrado IS NULL OR t.fecha_medicion > @UltimaMedicionCerrado))""",
    "orphan refill/open timestamp",
)
deploy("sp_auto_mantener_secuencia", maintain)


# Compute the same operational transition for every close reason. Prefer the
# earliest valid topography of the next sequence row; before the freeze step
# has created that row, resolve the nearest later numbered available module
# with positive topographic movement in the same campaign/PAD. If that has not
# synchronized yet, consult its source. If no next-module evidence exists,
# use the last valid topography of the closing module. With no topography on
# either side, leave the date NULL instead of inventing a historical date.
close = read("sp_auto_cerrar_y_avanzar_secuencia")
camp_match = re.search(r"s2\.\[([^\]]+)\]\s*=\s*@Camp", close)
if not camp_match:
    raise RuntimeError("Could not discover campaign column in successor query")
camp = camp_match.group(1)
start = close.index("SET @FechaUltimaActual = NULL;")
update_match = re.search(
    r"\s+UPDATE\s+\[reclamo\]\.\[secuencia_rotopala\]\s+SET estado = 'CERRADO'",
    close[start:], re.I,
)
if not update_match:
    raise RuntimeError("Could not locate closing UPDATE boundary")
end = start + update_match.start()
transition_block = f"""SET @FechaUltimaActual = NULL;
SET @FechaPrimeraSiguiente = NULL;
SET @FechaTransicion = NULL;
SET @SigModId = NULL;

SELECT @FechaUltimaActual = MAX(x.fecha_operacional)
FROM
(
    SELECT CAST(t.fecha_medicion AS date) AS fecha_operacional
    FROM [reclamo].[topografia_avance] t
    WHERE t.[{camp}] = @Camp AND t.pad_id = @Pad AND t.modulo_id = @Mod AND t.estado = 'VIGENTE'
    UNION ALL
    SELECT CAST(cr.fecha AS date)
    FROM [inventar_SpcHidr].[control_reclamo_diario] cr
    WHERE cr.[{camp}] = @Camp AND cr.pad_id = @Pad AND cr.modulo_id = @Mod
      AND COALESCE(cr.volumen_diario_m3,0) > 0
) x;

SELECT TOP (1) @SigModId = s2.modulo_id
FROM [reclamo].[secuencia_rotopala] s2
WHERE s2.rotopala_id = @RotId AND s2.[{camp}] = @Camp
  AND s2.orden_secuencia > @OrdenActual
ORDER BY s2.orden_secuencia;

IF @SigModId IS NULL
BEGIN
    SELECT TOP (1) @SigModId = md.id_modulo
    FROM [inventar_SpcHidr].[disponible_rotopalas] dr
    INNER JOIN [inventar_SpcHidr].[modulo] md ON md.id_modulo = dr.modulo_id
    WHERE dr.[{camp}] = @Camp AND md.numero > @ModNum
    ORDER BY md.numero;
END;

IF @SigModId IS NOT NULL
BEGIN
    SELECT @FechaPrimeraSiguiente = MIN(x.fecha_operacional)
    FROM
    (
        SELECT CAST(t.fecha_medicion AS date) AS fecha_operacional
        FROM [reclamo].[topografia_avance] t
        WHERE t.[{camp}] = @Camp AND t.pad_id = @Pad
          AND t.modulo_id = @SigModId AND t.estado = 'VIGENTE'
        UNION ALL
        SELECT CAST(cr.fecha AS date)
        FROM [inventar_SpcHidr].[control_reclamo_diario] cr
        WHERE cr.[{camp}] = @Camp AND cr.pad_id = @Pad
          AND cr.modulo_id = @SigModId AND COALESCE(cr.volumen_diario_m3,0) > 0
    ) x;
END;

SET @FechaTransicion = COALESCE(@FechaPrimeraSiguiente, @FechaUltimaActual);

"""
close = close[:start] + transition_block + close[end:]
close = replace_once(
    close,
    "IF @SigSecuenciaId IS NOT NULL AND @SigEstado = 'PENDIENTE'",
    "IF @SigSecuenciaId IS NOT NULL AND @SigEstado = 'PENDIENTE' AND @FechaTransicion IS NOT NULL",
    "do not open undated successor",
)
deploy("sp_auto_cerrar_y_avanzar_secuencia", close)

print("Wrote 3 ALTER batches to", FIX)
