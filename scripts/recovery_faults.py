"""Worker-only fault injection selected by fixture IDs outside action configuration."""
import json


def failure_boundary(original, directory, wait_until):
    def execute(action, **kwargs):
        manifest = directory / "fault-actions.json"
        targets = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
        if action.pk == targets.get("transient") and not (directory / "retry-release").exists():
            (directory / "transient-raised").touch()
            raise RuntimeError("Synthetic S04 transient worker failure")
        result = original(action, **kwargs)
        if action.pk == targets.get("crash") and not (directory / "release").exists():
            (directory / "held").touch()
            wait_until(lambda: (directory / "release").exists(), "parent stops the owned worker", timeout=60)
        return result
    return execute
