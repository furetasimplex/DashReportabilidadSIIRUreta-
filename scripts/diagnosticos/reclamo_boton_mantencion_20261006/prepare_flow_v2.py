"""Build the minimal phased SP alteration from the exact audited DEV definition."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / "sp_definitions_v2_before" / "reclamo.sp_auto_congelar_modulos_nuevos.sql").read_text(encoding="utf-8")
sql = source.replace("CREATE PROCEDURE [reclamo].[sp_auto_congelar_modulos_nuevos]", "ALTER PROCEDURE [reclamo].[sp_auto_congelar_modulos_nuevos]", 1)
old = "    @EjecucionId int = NULL\n)"
assert sql.count(old) == 1
sql = sql.replace(old, "    @EjecucionId int = NULL,\n    @SoloPreparar bit = 0\n)", 1)
old = "        /* -------------------------------------------------------------\n           Abrir los que tienen movimiento real"
assert sql.count(old) == 1
sql = sql.replace(old, "        IF @SoloPreparar = 0\n        BEGIN\n" + old, 1)
old = "        CLOSE grupos;\n        DEALLOCATE grupos;"
assert sql.count(old) == 1
sql = sql.replace(old, old + "\n        END; -- @SoloPreparar: no abrir antes del primer sync", 1)
for old, new in (
    ("ta.[campaña_id] = @Camp AND ta.pad_id = @Pad\n                          AND ta.modulo_id = @Mod", "ta.[campaña_id] = @CampAbrir AND ta.pad_id = @PadAbrir\n                          AND ta.modulo_id = @ModAbrir"),
    ("cr.[campaña_id] = @Camp AND cr.pad_id = @Pad\n                          AND cr.modulo_id = @Mod", "cr.[campaña_id] = @CampAbrir AND cr.pad_id = @PadAbrir\n                          AND cr.modulo_id = @ModAbrir"),
):
    assert sql.count(old) == 1, old
    sql = sql.replace(old, new, 1)
out = HERE / "fixes" / "alter_reclamo.sp_auto_congelar_modulos_nuevos_v2.sql"
out.write_text(sql, encoding="utf-8")
print(out)
