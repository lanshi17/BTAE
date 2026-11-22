from concurrent.futures import ThreadPoolExecutor

from epe.core.models import Task
from epe.governance.tasks import create_task


def test_task_creation_is_exclusive_under_concurrent_writers(tmp_path):
    task = Task("TASK-001", "feature", "objective", ["acceptance"], "low", ["CLASS-001"], None, "planned", 1, {
        "schema_version": 1, "id": "TASK-001", "type": "feature", "objective": "objective",
        "acceptance": ["acceptance"], "risk": "low", "target_entities": ["CLASS-001"],
    })

    def create():
        create_task(tmp_path, {"storage": {"tasks": "tasks"}}, task)
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
    results = []
    for future in futures:
        try:
            results.append(future.result())
        except FileExistsError:
            results.append(False)
    assert results.count(True) == 1
    assert (tmp_path / "tasks/TASK-001.json").read_text(encoding="utf-8").count('"id": "TASK-001"') == 1
