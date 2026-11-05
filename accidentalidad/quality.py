"""Resultados de calidad persistidos antes de bloquear la publicación."""

import json


class QualityGate:
    def __init__(self, spark, catalog, run_id, layer):
        self.spark = spark
        self.catalog = catalog
        self.run_id = run_id
        self.layer = layer
        self.rows = []

    def check(self, dataset, rule, observed, expected=0, severity="ERROR", details=None):
        if severity not in ("ERROR", "WARN"):
            raise ValueError("Severidad inválida")
        self.rows.append((
            self.run_id, self.layer, dataset, rule, str(observed), str(expected),
            severity, observed == expected, json.dumps(details or {}, ensure_ascii=False),
        ))

    def finish(self):
        from pyspark.sql import functions as F

        if not self.rows:
            raise ValueError("No se ejecutaron controles de calidad")
        self.spark.sql(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.quality")
        schema = (
            "run_id string, layer string, dataset string, rule string, observed string, "
            "expected string, severity string, passed boolean, details string"
        )
        report = self.spark.createDataFrame(self.rows, schema).withColumn("checked_at", F.current_timestamp())
        report.write.format("delta").mode("append").saveAsTable(f"{self.catalog}.quality.check_results")
        failures = [f"{r[2]}.{r[3]}: {r[4]} (esperado {r[5]})" for r in self.rows if r[6] == "ERROR" and not r[7]]
        if failures:
            raise ValueError(f"Calidad {self.layer}, run_id={self.run_id}: " + "; ".join(failures))
        print(f"[OK] Calidad {self.layer}, run_id={self.run_id}; {len(self.rows)} controles")
