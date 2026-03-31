import argparse
import sys

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
    argp = argparse.ArgumentParser(
        prog="fortran77c",
        description="Compilador Fortran 77 -> EWVM",
    )
    argp.add_argument("input", nargs="?", help="Ficheiro Fortran de entrada")
    argp.add_argument("-o", "--output", default="out.vm", help="Ficheiro VM de saida (default: out.vm)")
    argp.add_argument("--dump-ast", action="store_true", help="Mostra a AST")
    argp.add_argument("--dump-ir", action="store_true", help="Mostra a representacao intermédia (TAC)")
    argp.add_argument("--no-opt", action="store_true", help="Desativa otimizacoes")
    argp.add_argument("--visualize", metavar="PATH", help="Gera PDF da AST para PATH (requer graphviz)")
    argp.add_argument("--run", action="store_true", help="Executa na EWVM apos compilar")
    argp.add_argument("--input", dest="run_input", default="", help="Input para o programa ao usar --run")
    argp.add_argument("--repl", action="store_true", help="Inicia o REPL interativo")
    args = argp.parse_args()

    if args.repl:
        from repl import run_repl

        run_repl()
        return

    if args.input is None:
        argp.error("Argumento 'input' obrigatorio (ou usa --repl)")

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

    if args.visualize:
        try:
            from visualizer import visualize

            path = visualize(ast, output=args.visualize)
            print(f"AST gerada: {path}", file=sys.stderr)
        except ImportError:
            print("graphviz nao instalado: pip install graphviz", file=sys.stderr)

    with open(args.output, "w") as f:
        f.write("\n".join(vm) + "\n")

    if args.run:
        try:
            from ewvm import run_code

            output = run_code("\n".join(vm), args.run_input)
            print(output)
        except ImportError:
            print("requests/beautifulsoup4 nao instalados", file=sys.stderr)
        except RuntimeError as exc:
            print(f"Erro EWVM: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
