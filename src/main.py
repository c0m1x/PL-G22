import argparse
from codegen import generate_vm
from ir_gen import generate_ir
from lexer import tokenize
from optimizer import optimize
from parser import parse
from preprocessor import preprocess
from semantic import analyze


def _dump_ir(ir):
    return "\n".join(str(instr) for instr in ir)


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument("input")
    argp.add_argument("-o", "--output", default="out.vm")
    argp.add_argument("--dump-ast", action="store_true")
    argp.add_argument("--dump-ir", action="store_true")
    argp.add_argument("--no-opt", action="store_true")
    args = argp.parse_args()

    with open(args.input) as f:
        source = f.read()

    lines = preprocess(source)

    token_lines = tokenize(lines)
    ast = parse(token_lines)
    ast, _symtable = analyze(ast)

    ir = generate_ir(ast)
    if not args.no_opt:
        ir = optimize(ir)

    vm = generate_vm(ir, ast)

    if args.dump_ast:
        print(ast)
    if args.dump_ir:
        print(_dump_ir(ir))

    with open(args.output, "w") as f:
        f.write("\n".join(vm) + "\n")

if __name__ == "__main__":
    main()
