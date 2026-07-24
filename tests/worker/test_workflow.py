from app.worker.workflow import RunWorkflow


class RecordingRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run_once(self) -> object | None:
        self.calls += 1
        return None if self.calls == 3 else object()


def test_workflow_runs_jobs_sequentially_until_no_work_remains() -> None:
    runner = RecordingRunner()

    result = RunWorkflow(runner=runner).execute("run-1")

    assert result.jobs_processed == 2
