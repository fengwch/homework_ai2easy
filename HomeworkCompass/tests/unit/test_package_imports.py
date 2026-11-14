import pytest

from homework_compass import errors


@pytest.mark.parametrize("name", [
    "HomeworkError", "ExtractionError", "NeedsConfirmation",
    "LayoutError", "FontError", "ApiError",
])
def test_exception_hierarchy(name):
    exc = getattr(errors, name)
    assert issubclass(exc, errors.HomeworkError)


def test_no_sys_path_hacks_in_source():
    """src/ 布局的意义就是消灭 sys.path.insert，这里把它变成硬约束。"""
    from pathlib import Path
    root = Path(errors.__file__).parent
    offenders = [p for p in root.rglob("*.py") if "sys.path.insert" in p.read_text()]
    assert offenders == []
