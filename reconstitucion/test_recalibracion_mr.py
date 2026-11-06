import unittest
from datetime import date

from recalibracion_mr import ModuleObservation, RecalibrationError, calibrate_density


class RecalibrationTests(unittest.TestCase):
    def test_density_preserves_db_frozen_wet_and_uses_real_open_volume(self):
        rows = [
            ModuleObservation(2, 12, 10, 100, 120, True,
                date(2026, 9, 1), date(2026, 9, 4), 150),
            ModuleObservation(2, 12, 11, 50, 80, False,
                abierto_al_corte=True),
        ]
        result = calibrate_density(250, rows, pad_id=2, campana_id=12,
                                   cutoff=date(2026, 9, 10))
        self.assertEqual(result.fixed_tmh, 150)
        self.assertEqual(result.adjustable_volume_real_m3, 50)
        self.assertEqual(result.density_tmh_per_m3, 2)
        self.assertEqual(result.targets_tmh, {11: None, 10: 150})

    def test_zero_fixed_modules_is_valid(self):
        result = calibrate_density(60, [ModuleObservation(1, 3, 7, 30, 40)],
                                   pad_id=1, campana_id=3, cutoff=date(2026, 1, 2))
        self.assertEqual(result.fixed_tmh, 0)
        self.assertEqual(result.density_tmh_per_m3, 2)
        self.assertEqual(result.targets_tmh[7], 80)

    def test_zero_global_mass_with_positive_real_volume_gives_zero_targets(self):
        result = calibrate_density("0", [ModuleObservation(1, 3, 7, 30, 40)],
                                   pad_id=1, campana_id=3, cutoff=date(2026, 1, 2))
        self.assertEqual(result.density_tmh_per_m3, 0)
        self.assertEqual(result.targets_tmh[7], 0)

    def test_all_modules_frozen_and_mass_closed_needs_no_new_density(self):
        row = ModuleObservation(2, 12, 10, 100, 120, True,
            date(2026, 9, 1), date(2026, 9, 4), 150)
        result = calibrate_density(150, [row], pad_id=2, campana_id=12,
                                   cutoff=date(2026, 9, 10))
        self.assertIsNone(result.density_tmh_per_m3)
        self.assertEqual(result.targets_tmh, {10: 150})

    def test_frozen_dry_only_is_actionable_error(self):
        row = ModuleObservation(2, 12, 10, 100, 120, True,
            date(2026, 9, 1), date(2026, 9, 4), None)
        with self.assertRaisesRegex(RecalibrationError, "TMH fijada directa"):
            calibrate_density(250, [row], pad_id=2, campana_id=12,
                              cutoff=date(2026, 9, 10))

    def test_frozen_after_cutoff_is_not_used_retroactively(self):
        rows = [
            ModuleObservation(2, 12, 10, 100, 120, True,
                date(2026, 9, 11), date(2026, 9, 12), 150),
            ModuleObservation(2, 12, 11, 50, 80, False,
                abierto_al_corte=True),
        ]
        result = calibrate_density(250, rows, pad_id=2, campana_id=12,
                                   cutoff=date(2026, 9, 10))
        self.assertEqual(result.fixed_tmh, 0)
        self.assertEqual(result.density_tmh_per_m3, 250 / 150)

    def test_frozen_without_asof_dates_and_multiple_open_modules_fail(self):
        frozen_without_dates = ModuleObservation(2, 12, 10, 100, 120, True,
            tmh_fijada=150)
        with self.assertRaisesRegex(RecalibrationError, "faltan fechas"):
            calibrate_density(250, [frozen_without_dates], pad_id=2, campana_id=12,
                              cutoff=date(2026, 9, 10))
        opened = [ModuleObservation(2, 12, 10, 50, 80, abierto_al_corte=True),
                  ModuleObservation(2, 12, 11, 50, 80, abierto_al_corte=True)]
        with self.assertRaisesRegex(RecalibrationError, "más de un módulo abierto"):
            calibrate_density(250, opened, pad_id=2, campana_id=12,
                              cutoff=date(2026, 9, 10))

    def test_identity_scope_and_duplicates_fail(self):
        with self.assertRaisesRegex(RecalibrationError, "mezcla PAD o campaña"):
            calibrate_density(10, [ModuleObservation(1, 1, 1, 2),
                                    ModuleObservation(2, 1, 2, 2)],
                              pad_id=1, campana_id=1, cutoff=date(2026, 1, 1))
        with self.assertRaisesRegex(RecalibrationError, "duplicada"):
            calibrate_density(10, [ModuleObservation(1, 1, 1, 2),
                                    ModuleObservation(1, 1, 1, 2)],
                              pad_id=1, campana_id=1, cutoff=date(2026, 1, 1))


if __name__ == "__main__":
    unittest.main()
