import unittest

from accidentalidad.policies import (
    choose_candidate, nonnegative_int, parse_bool, promotion_allowed,
    sql_identifier, temporal_partition,
)


class PoliciesTest(unittest.TestCase):
    def test_sql_identifiers_reject_injection_and_qualified_names(self):
        self.assertEqual(sql_identifier("accidentalidad_dev"), "accidentalidad_dev")
        for name in ["x; DROP SCHEMA silver", "a.b", "a`b", "", "123", "a-b"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                sql_identifier(name)

    def test_strict_configuration(self):
        self.assertTrue(parse_bool("true"))
        self.assertFalse(parse_bool("false"))
        for value in ["yes", "True", "", None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_bool(value)
        self.assertEqual(nonnegative_int("3"), 3)
        for value in ["-1", "1.2"]:
            with self.assertRaises(ValueError):
                nonnegative_int(value)

    def test_temporal_boundaries_are_disjoint_and_exclude_outside_years(self):
        expected = {2017: "excluded", 2018: "train", 2019: "train", 2020: "train",
                    2021: "validation", 2022: "test", 2023: "excluded", None: "excluded"}
        self.assertEqual({year: temporal_partition(year) for year in expected}, expected)
        with self.assertRaises(ValueError):
            temporal_partition(2021, start=2022)

    def test_candidate_selection_never_uses_test_score(self):
        results = [
            {"model": "a", "validation_f1": 0.6, "test_f1": 0.99},
            {"model": "b", "validation_f1": 0.8, "test_f1": 0.2},
        ]
        self.assertEqual(choose_candidate(results)["model"], "b")

    def test_ties_are_deterministic(self):
        results = [{"model": "b", "validation_f1": 0.6}, {"model": "a", "validation_f1": 0.6}]
        self.assertEqual(choose_candidate(results)["model"], "a")

    def test_invalid_selection_scores_fail(self):
        for results in [[], [{"model": "a", "validation_f1": float("nan")}],
                        [{"model": "a", "validation_f1": 1.1}]]:
            with self.assertRaises(ValueError):
                choose_candidate(results)

    def test_first_champion_requires_minimum_and_beating_baseline(self):
        self.assertTrue(promotion_allowed(0.7, 0.4))
        self.assertFalse(promotion_allowed(0.4, 0.2))
        self.assertFalse(promotion_allowed(0.7, 0.7))
        self.assertFalse(promotion_allowed(0.6, 0.7))

    def test_incumbent_requires_strict_improvement(self):
        self.assertTrue(promotion_allowed(0.8, 0.4, 0.7, improvement=0.01))
        self.assertFalse(promotion_allowed(0.7, 0.4, 0.7))
        self.assertFalse(promotion_allowed(0.71, 0.4, 0.7, improvement=0.02))

    def test_nonfinite_promotion_metrics_or_thresholds_are_rejected(self):
        for args in [(float("nan"), 0.3), (0.7, float("inf")), (0.7, 0.3, -0.1)]:
            with self.assertRaises(ValueError):
                promotion_allowed(*args)
        for kwargs in [{"minimum": -0.1}, {"minimum": 1.1}, {"improvement": -0.1}, {"improvement": float("nan")}]:
            with self.assertRaises(ValueError):
                promotion_allowed(0.7, 0.3, **kwargs)


if __name__ == "__main__":
    unittest.main()
