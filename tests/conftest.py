import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from codegen import generate_vm
from ir_gen import generate_ir
from lexer import tokenize
from optimizer import optimize
from parser import parse
from preprocessor import preprocess
from semantic import analyze


def compile_fortran(source: str):
    """Compile Fortran source through the full pipeline without optimizer.

    Returns (ast, ir, vm) where vm is a list of instruction strings.
    """
    lines = preprocess(source)
    tokens = tokenize(lines)
    ast = parse(tokens)
    ast, _sym = analyze(ast)
    ir = generate_ir(ast)
    vm = generate_vm(ir, ast)
    return ast, ir, vm


def compile_fortran_optimized(source: str):
    """Compile Fortran source through the full pipeline with optimizer.

    Returns (ast, ir, vm) where ir is post-optimization and vm is a list.
    """
    lines = preprocess(source)
    tokens = tokenize(lines)
    ast = parse(tokens)
    ast, _sym = analyze(ast)
    ir = generate_ir(ast)
    ir = optimize(ir)
    vm = generate_vm(ir, ast)
    return ast, ir, vm
