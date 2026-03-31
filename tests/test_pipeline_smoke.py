from codegen import generate_vm
from ir_gen import generate_ir
from lexer import tokenize
from parser import parse
from preprocessor import preprocess
from semantic import analyze


def test_pipeline_generates_vm_for_simple_program():
    source = (
        "      PROGRAM T\n"
        "      INTEGER N\n"
        "      N = 5\n"
        "      PRINT *, N\n"
        "      END\n"
    )

    lines = preprocess(source)
    tokens = tokenize(lines)
    ast = parse(tokens)
    ast, _sym = analyze(ast)
    ir = generate_ir(ast)
    vm = generate_vm(ir, ast)

    assert any(ins.op == "PRINT" for ins in ir)
    assert vm[0].startswith("PUSHN")
    assert vm[-1] == "STOP"
