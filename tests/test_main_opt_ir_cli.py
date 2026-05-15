import subprocess
import sys
from pathlib import Path


def test_main_opt_ir_subcommand(tmp_path):
    ir_path = tmp_path / "input.ir"
    out_path = tmp_path / "output.ir"
    ir_path.write_text("COPY _t0 5\nCOPY X _t0\n")

    result = subprocess.run(
        [sys.executable, "src/main.py", "opt-ir", str(ir_path), "-o", str(out_path)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == ""
    assert result.stderr == ""
    assert "COPY X 5" in out_path.read_text()


def test_main_compile_cli_does_not_emit_ply_warnings(tmp_path):
    src_path = tmp_path / "hello.f"
    out_path = tmp_path / "hello.vm"
    src_path.write_text("PROGRAM HELLO\nPRINT *, 'Ola'\nEND\n")

    result = subprocess.run(
        [sys.executable, "src/main.py", str(src_path), "-o", str(out_path)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == ""
    assert result.stderr == ""
    assert 'PUSHS "Ola"' in out_path.read_text()
