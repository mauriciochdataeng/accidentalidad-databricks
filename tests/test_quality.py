import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from accidentalidad.quality import QualityGate


class QualityTest(unittest.TestCase):
    def setUp(self):
        # Solo se simula la persistencia de Spark; se ejecuta la lógica real del gate.
        self.functions = ModuleType("pyspark.sql.functions")
        self.functions.current_timestamp = lambda: "timestamp_expression"
        self.sql = ModuleType("pyspark.sql")
        self.sql.functions = self.functions
        self.pyspark = ModuleType("pyspark")
        self.pyspark.sql = self.sql
        self.patch = patch.dict(sys.modules, {"pyspark": self.pyspark, "pyspark.sql": self.sql,
                                             "pyspark.sql.functions": self.functions})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.spark = Mock()
        self.report = self.spark.createDataFrame.return_value.withColumn.return_value
        self.writer = self.report.write.format.return_value.mode.return_value
        self.gate = QualityGate(self.spark, "catalog", "run1", "silver")

    def test_critical_failure_is_audited_before_raising(self):
        self.gate.check("accidentes", "duplicate_croquis", 2)
        with self.assertRaisesRegex(ValueError, "duplicate_croquis"):
            self.gate.finish()
        self.writer.saveAsTable.assert_called_once_with("catalog.quality.check_results")
        rows, _ = self.spark.createDataFrame.call_args.args
        self.assertFalse(rows[0][7])
        self.assertEqual(rows[0][0], "run1")

    def test_accepted_anomaly_is_audited_without_blocking(self):
        self.gate.check("vehiculos", "accepted_orphans", 3, severity="WARN", details={"limit": 3})
        self.gate.finish()
        self.writer.saveAsTable.assert_called_once()
        rows, _ = self.spark.createDataFrame.call_args.args
        self.assertEqual(rows[0][6], "WARN")
        self.assertFalse(rows[0][7])
        self.assertIn('"limit": 3', rows[0][8])

    def test_failed_audit_write_blocks_publication(self):
        self.gate.check("accidentes", "count", 10, 10)
        self.writer.saveAsTable.side_effect = OSError("storage unavailable")
        with self.assertRaises(OSError):
            self.gate.finish()

    def test_no_checks_is_not_a_success(self):
        with self.assertRaisesRegex(ValueError, "No se ejecutaron"):
            self.gate.finish()
        self.writer.saveAsTable.assert_not_called()

    def test_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.gate.check("accidentes", "count", 0, severity="INFO")


if __name__ == "__main__":
    unittest.main()
