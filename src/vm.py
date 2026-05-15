"""Interpretador local das instrucoes EWVM."""

from __future__ import annotations

import ast
import sys
from typing import Any


class VMError(Exception):
    pass


def _parse(code: str):
    instrs = []
    labels: dict[str, int] = {}
    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":"):
            labels[line[:-1]] = len(instrs)
            continue
        parts = line.split(None, 1)
        op = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ""
        instrs.append((op, arg))
    return instrs, labels


def run(code: str, input_data: str = "", max_steps: int = 100_000) -> str:
    instrs, labels = _parse(code)
    stack: list[Any] = []
    heap: list[Any] = []
    output_parts: list[str] = []
    stdin_lines = iter(input_data.splitlines())
    pc = 0
    steps = 0

    def pop():
        if not stack:
            raise VMError("Stack underflow")
        return stack.pop()

    def push(v):
        stack.append(v)

    def heap_get(addr):
        if addr >= len(heap):
            return 0
        return heap[addr]

    def heap_set(addr, val):
        if addr >= len(heap):
            heap.extend([0] * (addr + 1 - len(heap)))
        heap[addr] = val

    while pc < len(instrs):
        if steps > max_steps:
            raise VMError("Limite de passos excedido (loop infinito?)")
        steps += 1

        op, arg = instrs[pc]
        pc += 1

        if op == "PUSHN":
            n = int(arg)
            for _ in range(n):
                heap.append(0)

        elif op == "START":
            pass

        elif op == "PUSHI":
            push(int(arg))

        elif op == "PUSHF":
            push(float(arg))

        elif op == "PUSHS":
            s = arg.strip()
            if s.startswith('"') and s.endswith('"'):
                try:
                    s = ast.literal_eval(s)
                except (SyntaxError, ValueError):
                    s = s[1:-1]
            push(s)

        elif op == "PUSHG":
            push(heap_get(int(arg)))

        elif op == "STOREG":
            heap_set(int(arg), pop())

        elif op == "PUSHGP":
            push(0)

        elif op == "PADD":
            offset = pop()
            base = pop()
            push(base + offset)

        elif op == "LOADN":
            offset = pop()
            base = pop()
            push(heap_get(base + offset))

        elif op == "STOREN":
            val = pop()
            offset = pop()
            base = pop()
            heap_set(base + offset, val)

        elif op == "ADD":
            b, a = pop(), pop()
            push(a + b)

        elif op == "SUB":
            b, a = pop(), pop()
            push(a - b)

        elif op == "MUL":
            b, a = pop(), pop()
            push(a * b)

        elif op == "DIV":
            b, a = pop(), pop()
            if b == 0:
                raise VMError("Divisao por zero")
            if isinstance(a, float) or isinstance(b, float):
                push(a / b)
            else:
                push(int(a) // int(b))

        elif op == "MOD":
            b, a = pop(), pop()
            if b == 0:
                raise VMError("Modulo por zero")
            push(int(a) % int(b))

        elif op == "EQUAL":
            b, a = pop(), pop()
            push(1 if a == b else 0)

        elif op == "NOT":
            push(1 if pop() == 0 else 0)

        elif op == "INF":
            b, a = pop(), pop()
            push(1 if a < b else 0)

        elif op == "INFEQ":
            b, a = pop(), pop()
            push(1 if a <= b else 0)

        elif op == "SUP":
            b, a = pop(), pop()
            push(1 if a > b else 0)

        elif op == "SUPEQ":
            b, a = pop(), pop()
            push(1 if a >= b else 0)

        elif op == "AND":
            b, a = pop(), pop()
            push(1 if (a != 0 and b != 0) else 0)

        elif op == "OR":
            b, a = pop(), pop()
            push(1 if (a != 0 or b != 0) else 0)

        elif op == "JUMP":
            lbl = arg.strip()
            if lbl not in labels:
                raise VMError(f"Label desconhecido: {lbl!r}")
            pc = labels[lbl]

        elif op == "JZ":
            lbl = arg.strip()
            if lbl not in labels:
                raise VMError(f"Label desconhecido: {lbl!r}")
            if pop() == 0:
                pc = labels[lbl]

        elif op == "READ":
            try:
                line = next(stdin_lines)
            except StopIteration:
                line = sys.stdin.readline().rstrip("\n")
            push(line)

        elif op == "ATOI":
            push(int(pop()))

        elif op == "ATOF":
            push(float(pop()))

        elif op == "WRITEI":
            output_parts.append(str(int(pop())))

        elif op == "WRITEF":
            output_parts.append(str(float(pop())))

        elif op == "WRITES":
            output_parts.append(str(pop()))

        elif op == "WRITELN":
            output_parts.append("\n")

        elif op == "STOP":
            break

        else:
            raise VMError(f"Instrucao desconhecida: {op!r}")

    return "".join(output_parts)
