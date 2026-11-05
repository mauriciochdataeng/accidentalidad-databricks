import ast
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock

try:
    import tomllib
except ImportError:
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]


class NotebookValidationTest(unittest.TestCase):
    @unittest.skipIf(tomllib is None, "Validación TOML requiere Python 3.11 o posterior")
    def test_shared_environment_dependencies_match_requirements(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        requirements = {
            line.strip() for line in (ROOT / "requirements-databricks.txt").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertEqual(set(project["project"]["dependencies"]), requirements)
        self.assertGreaterEqual(int(project["tool"]["databricks"]["environment"]["environment_version"]), 5)

    def test_notebooks_are_parseable_and_do_not_embed_runtime_outputs(self):
        notebooks = sorted(ROOT.glob("*/*.ipynb"))
        self.assertEqual(len(notebooks), 7)
        for path in notebooks:
            notebook = json.loads(path.read_text())
            self.assertEqual(notebook["nbformat"], 4)
            for index, cell in enumerate(notebook["cells"]):
                if cell["cell_type"] == "code":
                    with self.subTest(notebook=path.name, cell=index):
                        source = "".join(cell["source"])
                        # Las celdas magic de Databricks no son sintaxis Python estándar.
                        if source.startswith(("%pip ", "%uv ")):
                            command, _, arguments = source.strip().partition(" ")
                            source = f"get_ipython().run_line_magic({command[1:]!r}, {arguments!r})"
                        ast.parse(source)
                        self.assertEqual(cell["outputs"], [])
                        self.assertIsNone(cell["execution_count"])

    def test_bronze_gate_failure_prevents_all_table_writes(self):
        path = ROOT / "01_Exploracion_y_Transformacion/01_Ingesta_Bronze.ipynb"
        code = "".join(json.loads(path.read_text())["cells"][12]["source"])
        names = ["accidentes", "causas", "vehiculos", "victimas"]
        frames = {name: MagicMock() for name in names}
        gate_type = MagicMock()
        gate_type.return_value.finish.side_effect = ValueError("invalid source")
        namespace = {f"df_{name}_bronze": frame for name, frame in frames.items()}
        namespace.update({"QualityGate": gate_type, "spark": MagicMock(), "F": MagicMock(),
                          "PROY_CATALOG": "catalog", "RUN_ID": "run", "ENFORCE_COUNTS": True,
                          "EXPECTED_COUNTS": {name: 10 for name in names}})
        with self.assertRaisesRegex(ValueError, "invalid source"):
            exec(compile(code, str(path), "exec"), namespace)
        for frame in frames.values():
            frame.write.format.assert_not_called()

    def test_silver_gate_failure_prevents_all_table_writes(self):
        path = ROOT / "01_Exploracion_y_Transformacion/02_Transformacion_Silver.ipynb"
        code = "".join(json.loads(path.read_text())["cells"][24]["source"])
        frames = {name: MagicMock() for name in ["accidentes", "causas", "vehiculos", "victimas"]}
        gate = MagicMock()
        gate.finish.side_effect = ValueError("invalid silver")
        namespace = {"df_accidentes_silver": frames["accidentes"], "df_victimas_silver": frames["victimas"],
                     "tablas_silver": frames, "gate": gate, "F": MagicMock(), "PROY_CATALOG": "catalog"}
        with self.assertRaisesRegex(ValueError, "invalid silver"):
            exec(compile(code, str(path), "exec"), namespace)
        for frame in frames.values():
            frame.write.format.assert_not_called()


if __name__ == "__main__":
    unittest.main()
