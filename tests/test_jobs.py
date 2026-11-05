from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from accidentalidad.jobs import deploy_job


class DeploymentTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.settings = Mock()
        self.settings.as_shallow_dict.return_value = {"name": "pipeline", "tasks": ["new_task"]}

    def test_new_job_is_created_without_running(self):
        self.client.jobs.list.return_value = []
        self.client.jobs.create.return_value.job_id = 42
        self.assertEqual(deploy_job(self.client, "pipeline", self.settings), 42)
        self.client.jobs.create.assert_called_once_with(name="pipeline", tasks=["new_task"])
        self.client.jobs.run_now.assert_not_called()

    def test_existing_job_gets_the_complete_new_definition(self):
        self.client.jobs.list.return_value = [SimpleNamespace(job_id=7, settings=SimpleNamespace(name="pipeline"))]
        self.client.jobs.list_runs.return_value = iter([])
        self.assertEqual(deploy_job(self.client, "pipeline", self.settings), 7)
        self.client.jobs.reset.assert_called_once_with(job_id=7, new_settings=self.settings)
        self.client.jobs.create.assert_not_called()

    def test_active_run_blocks_reset(self):
        self.client.jobs.list.return_value = [SimpleNamespace(job_id=7, settings=SimpleNamespace(name="pipeline"))]
        self.client.jobs.list_runs.return_value = iter([SimpleNamespace(run_id=99)])
        with self.assertRaises(RuntimeError):
            deploy_job(self.client, "pipeline", self.settings)
        self.client.jobs.reset.assert_not_called()
        self.client.jobs.create.assert_not_called()

    def test_ambiguous_job_name_blocks_all_mutations(self):
        job = SimpleNamespace(job_id=7, settings=SimpleNamespace(name="pipeline"))
        self.client.jobs.list.return_value = [job, job]
        with self.assertRaises(ValueError):
            deploy_job(self.client, "pipeline", self.settings)
        self.client.jobs.reset.assert_not_called()
        self.client.jobs.create.assert_not_called()

    def test_api_error_propagates_without_creating_a_duplicate(self):
        self.client.jobs.list.side_effect = PermissionError("denied")
        with self.assertRaises(PermissionError):
            deploy_job(self.client, "pipeline", self.settings)
        self.client.jobs.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
