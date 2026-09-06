"""Self-check for sweep.py. Run: python test_sweep.py (or pytest)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sweep


def _write(body: str) -> tuple[Path, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / "note.md"
    path.write_text(body, encoding="utf-8")
    return path, tmp


def test_open_marker_is_a_candidate() -> None:
    path, tmp = _write("- eaves: blocked on OPENROUTER_API_KEY\n")
    with tmp:
        hits = sweep.scan(path)
        assert len(hits) == 1, hits
        assert hits[0].line_no == 1
        assert "blocked on" in hits[0].text


def test_closed_marker_beats_open_marker() -> None:
    path, tmp = _write("- hippo: was blocked on the 522, now SHIPPED\n")
    with tmp:
        assert sweep.scan(path) == []


def test_possessive_keith_is_not_a_gate() -> None:
    path, tmp = _write("Keith's friend has a chemical engineering background.\n")
    with tmp:
        assert sweep.scan(path) == []


def test_action_shaped_keith_is_a_gate() -> None:
    path, tmp = _write("This needs Keith to press submit.\n")
    with tmp:
        assert len(sweep.scan(path)) == 1


def test_blank_lines_skipped_and_numbering_is_one_based() -> None:
    path, tmp = _write("\n\n- prc26: pending the S3 gate\n")
    with tmp:
        hits = sweep.scan(path)
        assert [h.line_no for h in hits] == [3]


def test_missing_file_skips_instead_of_raising() -> None:
    assert sweep.scan(Path("no-such-dir") / "gone.md") == []


def test_render_is_root_relative_and_truncated() -> None:
    long_line = "blocked on " + "x" * (sweep.MAX_LINE + 50)
    path, tmp = _write(long_line + "\n")
    with tmp:
        root = path.parent
        rendered = sweep.scan(path)[0].render(root)
        assert rendered.startswith("note.md:1: ")
        assert len(rendered.split(": ", 1)[1]) == sweep.MAX_LINE


def test_render_falls_back_to_absolute_path_outside_root() -> None:
    path, tmp = _write("blocked on something\n")
    with tmp:
        rendered = sweep.scan(path)[0].render(Path("/somewhere/else"))
        assert str(path) in rendered


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"ok: {len(tests)} tests passed")
