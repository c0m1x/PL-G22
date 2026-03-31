"""REPL interativo para o compilador Fortran 77.

Modos disponiveis (mudar com /comando):
  /translate  -- mostra o codigo VM gerado (default)
  /parse      -- mostra a AST (representacao textual)
  /ir         -- mostra a representacao intermédia (TAC)
  /run        -- executa o codigo na EWVM e mostra o output
  /visualize  -- gera PDF da AST (requer graphviz instalado)

O programa Fortran e introduzido linha a linha. Quando o REPL detecta
a linha END (final do programa principal), compila e executa.
"""

from __future__ import annotations

import sys
from enum import Enum

try:
    from prompt_toolkit import PromptSession, print_formatted_text, ANSI
    from prompt_toolkit.patch_stdout import patch_stdout
    _HAS_PROMPT_TOOLKIT = True
except ImportError:
    _HAS_PROMPT_TOOLKIT = False

from codegen import generate_vm
from ir_gen import generate_ir
from lexer import tokenize
from optimizer import optimize
from parser import parse
from preprocessor import preprocess
from semantic import analyze


class Mode(Enum):
    TRANSLATE = "translate"
    PARSE = "parse"
    IR = "ir"
    RUN = "run"
    VISUALIZE = "visualize"

    def prompt(self) -> str:
        return f"{self.value} >> "


_COMMANDS = {f"/{m.value}" for m in Mode}


def _compile(source: str):
    lines = preprocess(source)
    toks = tokenize(lines)
    ast = parse(toks)
    ast, _sym = analyze(ast)
    ir = generate_ir(ast)
    ir_opt = optimize(ir)
    vm = generate_vm(ir_opt, ast)
    return ast, ir_opt, vm


def _print_err(msg: str) -> None:
    if _HAS_PROMPT_TOOLKIT:
        print_formatted_text(ANSI(f"\x1b[31m{msg}\x1b[0m"))
    else:
        print(f"[erro] {msg}", file=sys.stderr)


def _run_action(mode: Mode, source: str) -> None:
    try:
        ast, ir, vm = _compile(source)
    except (SyntaxError, ValueError) as exc:
        _print_err(str(exc))
        return

    if mode == Mode.PARSE:
        print(repr(ast))

    elif mode == Mode.IR:
        for instr in ir:
            print(instr)

    elif mode == Mode.TRANSLATE:
        print("\n".join(vm))

    elif mode == Mode.RUN:
        try:
            from ewvm import run_code
        except ImportError:
            _print_err("Modulo ewvm nao disponivel. Instala: pip install requests beautifulsoup4")
            return
        try:
            output = run_code("\n".join(vm))
            print(output)
        except RuntimeError as exc:
            _print_err(str(exc))

    elif mode == Mode.VISUALIZE:
        try:
            from visualizer import visualize
        except ImportError:
            _print_err("Modulo graphviz nao disponivel. Instala: pip install graphviz")
            return
        path = visualize(ast, output="ast_output")
        print(f"AST gerada: {path}")


def _is_program_end(line: str) -> bool:
    """Devolve True se a linha (apos preprocessamento) e o END do programa."""
    stripped = line.strip().upper()
    if stripped == "END" or stripped.startswith("END "):
        return True
    # fixed-form: statement starts at column 7 (index 6)
    padded = line.ljust(72)
    code_part = padded[6:72].strip().upper()
    return code_part == "END" or code_part.startswith("END ")


def _read_program_simple(prompt_prefix: str) -> str | None:
    """Lê um programa Fortran linha a linha (modo sem prompt_toolkit)."""
    print(f"{prompt_prefix}(escreve o programa Fortran; termina com END)")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            return None
        lines.append(line)
        # Check if fixed-form col 7+ starts with END
        padded = line.ljust(72)
        code_part = padded[6:72].strip().upper()
        if code_part == "END" or code_part.startswith("END "):
            break
    return "\n".join(lines)


def run_repl() -> None:
    """Inicia o REPL interativo."""
    mode = Mode.TRANSLATE
    print("Compilador Fortran 77 -- REPL")
    print(f"Modo inicial: {mode.value.upper()}")
    print(f"Modos: {', '.join(_COMMANDS)}")
    print("Ctrl-D ou Ctrl-C para sair.\n")

    if _HAS_PROMPT_TOOLKIT:
        session: PromptSession = PromptSession()
        with patch_stdout():
            while True:
                try:
                    line = session.prompt(mode.prompt())
                except (EOFError, KeyboardInterrupt):
                    print("\nSaindo.")
                    break

                if not line.strip():
                    continue

                if line.strip() in _COMMANDS:
                    mode = Mode(line.strip()[1:])
                    print(f"Modo: {mode.value.upper()}")
                    continue

                # Accumulate multi-line program
                lines = [line]
                if not _is_program_end(line):
                    # Need more lines
                    while True:
                        try:
                            nxt = session.prompt("... ")
                        except (EOFError, KeyboardInterrupt):
                            break
                        lines.append(nxt)
                        if _is_program_end(nxt):
                            break

                source = "\n".join(lines)
                _run_action(mode, source)
    else:
        while True:
            try:
                line = input(mode.prompt())
            except EOFError:
                print("\nSaindo.")
                break
            except KeyboardInterrupt:
                print("\nSaindo.")
                break

            if not line.strip():
                continue

            if line.strip() in _COMMANDS:
                mode = Mode(line.strip()[1:])
                print(f"Modo: {mode.value.upper()}")
                continue

            lines = [line]
            if not _is_program_end(line):
                print("... (continua; termina com END)")
                while True:
                    try:
                        nxt = input("... ")
                    except EOFError:
                        break
                    lines.append(nxt)
                    if _is_program_end(nxt):
                        break

            source = "\n".join(lines)
            _run_action(mode, source)
