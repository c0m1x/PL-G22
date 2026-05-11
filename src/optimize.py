"""CLI para otimizar a representacao textual da IR (TAC).

O script lê linhas como as produzidas por `src/main.py --dump-ir`, aplica os
passes existentes em `optimizer.optimize()` e escreve a IR otimizada.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from ir import TACInstr
from optimizer import optimize


def _split_top_level_parts(line: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    escape = False

    for ch in line.strip():
        if quote is not None:
            current.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue

        if ch in {'"', "'"}:
            quote = ch
            current.append(ch)
            continue

        if ch in "([{":
            depth += 1
            current.append(ch)
            continue

        if ch in ")]}":
            depth = max(0, depth - 1)
            current.append(ch)
            continue

        if ch.isspace() and depth == 0:
            if current:
                parts.append("".join(current))
                current = []
            continue

        current.append(ch)

    if current:
        parts.append("".join(current))
    return parts


def _parse_atom(token: str):
    if token == "None":
        return None
    if token == "True":
        return True
    if token == "False":
        return False

    try:
        return ast.literal_eval(token)
    except (ValueError, SyntaxError):
        return token


def parse_ir_line(line: str) -> TACInstr:
    parts = _split_top_level_parts(line)
    if not parts:
        raise ValueError("Linha vazia de IR")

    op = parts[0]
    args = [_parse_atom(part) for part in parts[1:]]
    result = args[0] if len(args) > 0 else None
    arg1 = args[1] if len(args) > 1 else None
    arg2 = args[2] if len(args) > 2 else None
    return TACInstr(op, result, arg1, arg2)


def parse_ir_text(text: str) -> list[TACInstr]:
    instrs: list[TACInstr] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        instrs.append(parse_ir_line(line))
    return instrs


def format_ir_text(instrs: list[TACInstr]) -> str:
    return "\n".join(str(instr) for instr in instrs)


def optimize_ir_text(text: str) -> str:
    instrs = parse_ir_text(text)
    optimized = optimize(instrs)
    return format_ir_text(optimized)


def _read_input(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    return Path(path).read_text()


def _write_output(path: str | None, text: str) -> None:
    if path is None or path == "-":
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    Path(path).write_text(text + ("\n" if text and not text.endswith("\n") else ""))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="optimize_ir",
        description="Optimiza a IR textual gerada pelo compilador Fortran 77.",
    )
    parser.add_argument("input", nargs="?", help="Ficheiro de IR textual (default: stdin)")
    parser.add_argument("-o", "--output", help="Ficheiro de saída (default: stdout)")
    args = parser.parse_args()

    optimized_text = optimize_ir_text(_read_input(args.input))
    _write_output(args.output, optimized_text)


if __name__ == "__main__":
    main()