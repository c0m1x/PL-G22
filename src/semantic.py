from ast_nodes import (
    ArrayDeclNode,
    ArrayRefNode,
    AssignNode,
    BinOpNode,
    CallNode,
    DeclNode,
    DoNode,
    FuncCallNode,
    FunctionDefNode,
    GotoNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    PrintNode,
    ProgramNode,
    ReadNode,
    ReturnNode,
    SubroutineDefNode,
    UnaryOpNode,
)
from symbol_table import SymbolTable


class SemanticAnalyzer:
    def __init__(self):
        self.symtable = SymbolTable()
        self.errors: list[str] = []
        self.current_scope = "GLOBAL"
        self.global_scope = "GLOBAL"
        self.labels: set[str] = set()

    def analyze(self, program: ProgramNode):
        self.current_scope = program.name
        self.global_scope = program.name
        self.symtable.create_scope(program.name)

        # Declare subprogram signatures in global scope before body checks.
        for sub in program.subprograms:
            try:
                param_types, param_kinds = self._infer_subprogram_param_metadata(sub)
                if isinstance(sub, FunctionDefNode):
                    self.symtable.declare(
                        self.global_scope,
                        sub.name,
                        {
                            "kind": "function",
                            "type": sub.return_type,
                            "params": list(sub.params),
                            "param_types": param_types,
                            "param_kinds": param_kinds,
                        },
                    )
                elif isinstance(sub, SubroutineDefNode):
                    self.symtable.declare(
                        self.global_scope,
                        sub.name,
                        {
                            "kind": "subroutine",
                            "type": "VOID",
                            "params": list(sub.params),
                            "param_types": param_types,
                            "param_kinds": param_kinds,
                        },
                    )
            except ValueError as err:
                self.errors.append(str(err))

        self.labels = self._collect_labels(program.body)
        for stmt in program.body:
            self.visit(stmt)

        # Analyze each external subprogram in its own scope.
        for sub in program.subprograms:
            self._analyze_subprogram(sub)

        if self.errors:
            raise ValueError("\n".join(self.errors))
        return self.symtable

    def _analyze_subprogram(self, sub):
        prev_scope = self.current_scope
        prev_labels = self.labels
        sub_scope = f"{self.global_scope}::{sub.name}"
        self.current_scope = sub_scope
        self.symtable.create_scope(sub_scope)

        # FUNCTION return value is assigned via symbol with same name.
        if isinstance(sub, FunctionDefNode):
            try:
                self.symtable.declare(
                    sub_scope,
                    sub.name,
                    {"kind": "var", "type": sub.return_type},
                )
            except ValueError as err:
                self.errors.append(str(err))

        self.labels = self._collect_labels(sub.body)
        for stmt in sub.body:
            self.visit(stmt)

        self.current_scope = prev_scope
        self.labels = prev_labels

    def _collect_labels(self, stmts):
        labels: set[str] = set()
        for stmt in stmts:
            lbl = getattr(stmt, "stmt_label", None)
            if lbl is not None:
                labels.add(str(lbl))
            if isinstance(stmt, IfNode):
                labels.update(self._collect_labels(stmt.then_body))
                labels.update(self._collect_labels(stmt.else_body))
            elif isinstance(stmt, DoNode):
                labels.add(str(stmt.label))
                labels.update(self._collect_labels(stmt.body))
        return labels

    def _infer_subprogram_param_metadata(self, sub):
        declared: dict[str, tuple[str, str]] = {}
        for stmt in sub.body:
            if not isinstance(stmt, DeclNode):
                continue
            for var in stmt.vars:
                if isinstance(var, ArrayDeclNode):
                    declared[var.name] = (stmt.type_name, "array")
                else:
                    declared[var.name] = (stmt.type_name, "var")

        param_types: list[str] = []
        param_kinds: list[str] = []
        for param in sub.params:
            p_type, p_kind = declared.get(param, ("UNKNOWN", "var"))
            param_types.append(p_type)
            param_kinds.append(p_kind)
        return param_types, param_kinds

    def visit(self, node):
        meth = getattr(self, f"visit_{node.__class__.__name__}", None)
        if meth is None:
            return None
        return meth(node)

    def visit_DeclNode(self, node: DeclNode):
        for var in node.vars:
            try:
                # Fortran allows typing external function names in program scope
                # (e.g., INTEGER CONVRT with INTEGER FUNCTION CONVRT).
                if not isinstance(var, ArrayDeclNode):
                    existing = self.symtable.lookup(self.current_scope, var.name)
                    if (
                        existing is not None
                        and existing.get("kind") == "function"
                        and existing.get("type") == node.type_name
                        and self.current_scope == self.global_scope
                    ):
                        continue

                if isinstance(var, ArrayDeclNode):
                    dims = self._extract_array_dims(var)
                    self.symtable.declare(
                        self.current_scope,
                        var.name,
                        {"kind": "array", "type": node.type_name, "dims": dims or []},
                    )
                else:
                    self.symtable.declare(
                        self.current_scope,
                        var.name,
                        {"kind": "var", "type": node.type_name},
                    )
            except ValueError as err:
                self.errors.append(str(err))

    def _lookup(self, name: str):
        sym = self.symtable.lookup(self.current_scope, name)
        if sym is None and self.current_scope != self.global_scope:
            sym = self.symtable.lookup(self.global_scope, name)
        if sym is None:
            self.errors.append(f"Identificador nao declarado: {name}")
            return {"kind": "var", "type": "UNKNOWN"}
        return sym

    def _type_compatible(self, ltype: str, rtype: str):
        if ltype == "UNKNOWN" or rtype == "UNKNOWN":
            return True
        if ltype == rtype:
            return True
        if ltype == "REAL" and rtype == "INTEGER":
            return True
        return False

    def _extract_array_dims(self, node: ArrayDeclNode):
        dims: list[int] = []
        for dim_expr in node.dims:
            if not isinstance(dim_expr, LiteralNode) or dim_expr.type_name != "INTEGER":
                self.errors.append(f"Dimensao de array deve ser literal INTEGER em {node.name}")
                return None
            if dim_expr.value <= 0:
                self.errors.append(f"Dimensao de array deve ser > 0 em {node.name}")
                return None
            dims.append(dim_expr.value)
        return dims

    def visit_AssignNode(self, node: AssignNode):
        ltype = self.visit(node.target)
        rtype = self.visit(node.value)
        if not self._type_compatible(ltype, rtype):
            self.errors.append(f"Atribuicao incompativel: {ltype} <- {rtype}")

    def visit_IdentifierNode(self, node: IdentifierNode):
        sym = self._lookup(node.name)
        return sym["type"]

    def visit_ArrayRefNode(self, node: ArrayRefNode):
        sym = self._lookup(node.name)
        if sym.get("kind") != "array":
            self.errors.append(f"Identificador nao e array: {node.name}")
            return sym["type"]

        dims = sym.get("dims", [])
        if dims and len(node.indices) != len(dims):
            self.errors.append(
                f"Numero de indices incompativel para {node.name}: esperado {len(dims)}, obtido {len(node.indices)}"
            )

        for i, idx in enumerate(node.indices):
            itype = self.visit(idx)
            if itype != "INTEGER":
                self.errors.append(f"Indice de array deve ser INTEGER em {node.name}")
                continue
            if isinstance(idx, LiteralNode) and dims and i < len(dims):
                if idx.value < 1 or idx.value > dims[i]:
                    self.errors.append(f"Indice fora dos limites em {node.name}: {idx.value} nao esta em 1..{dims[i]}")
        return sym["type"]

    def visit_LiteralNode(self, node: LiteralNode):
        return node.type_name

    def visit_UnaryOpNode(self, node: UnaryOpNode):
        t = self.visit(node.operand)
        if node.op == "NOT":
            if t not in ("LOGICAL", "UNKNOWN"):
                self.errors.append("Operador NOT exige operando LOGICAL")
            return "LOGICAL"
        return t

    def visit_BinOpNode(self, node: BinOpNode):
        lt = self.visit(node.left)
        rt = self.visit(node.right)
        if node.op in ("AND", "OR"):
            if lt not in ("LOGICAL", "UNKNOWN") or rt not in ("LOGICAL", "UNKNOWN"):
                self.errors.append(f"Operador {node.op} exige operandos LOGICAL")
            return "LOGICAL"
        if node.op in ("EQ", "NE", "LT", "LE", "GT", "GE"):
            return "LOGICAL"
        if lt == "REAL" or rt == "REAL":
            return "REAL"
        return "INTEGER"

    def visit_PrintNode(self, node: PrintNode):
        for value in node.values:
            self.visit(value)

    def visit_ReadNode(self, node: ReadNode):
        for target in node.targets:
            self.visit(target)

    def visit_IfNode(self, node: IfNode):
        ctype = self.visit(node.condition)
        if ctype != "LOGICAL":
            self.errors.append("Condicao de IF deve ser LOGICAL")
        for stmt in node.then_body:
            self.visit(stmt)
        for stmt in node.else_body:
            self.visit(stmt)

    def visit_DoNode(self, node: DoNode):
        # Loop control variable must be declared and integer-like.
        var_sym = self._lookup(node.var)
        if var_sym.get("type") not in ("INTEGER", "UNKNOWN"):
            self.errors.append("Variavel de controlo do DO deve ser INTEGER")
        start_t = self.visit(node.start)
        end_t = self.visit(node.end)
        if start_t not in ("INTEGER", "UNKNOWN") or end_t not in ("INTEGER", "UNKNOWN"):
            self.errors.append("Limites do DO devem ser INTEGER")
        if node.step is not None:
            step_t = self.visit(node.step)
            if step_t not in ("INTEGER", "UNKNOWN"):
                self.errors.append("STEP do DO deve ser INTEGER")
        for stmt in node.body:
            self.visit(stmt)

    def visit_GotoNode(self, node: GotoNode):
        if str(node.label) not in self.labels:
            self.errors.append(f"GOTO para label inexistente: {node.label}")

    def _validate_call_argument_metadata(self, node_name: str, node_args, expected_types, expected_kinds, callee_kind):
        for idx, arg in enumerate(node_args):
            arg_type = self.visit(arg)

            if idx >= len(expected_types):
                continue

            expected_type = expected_types[idx]
            expected_kind = expected_kinds[idx] if idx < len(expected_kinds) else "var"

            if expected_kind == "array":
                if not isinstance(arg, IdentifierNode):
                    self.errors.append(
                        f"Argumento {idx + 1} de {callee_kind} {node_name} deve ser array"
                    )
                    continue
                arg_sym = self._lookup(arg.name)
                if arg_sym.get("kind") != "array":
                    self.errors.append(
                        f"Argumento {idx + 1} de {callee_kind} {node_name} deve ser array"
                    )
                    continue

            if expected_type != "UNKNOWN" and not self._type_compatible(expected_type, arg_type):
                self.errors.append(
                    f"Tipo de argumento incompativel em {callee_kind} {node_name}: "
                    f"arg {idx + 1} esperado {expected_type}, obtido {arg_type}"
                )

    def visit_FuncCallNode(self, node: FuncCallNode):
        if node.name == "MOD":
            if len(node.args) != 2:
                self.errors.append(
                    f"Numero de argumentos incompativel em FUNCTION MOD: esperado 2, obtido {len(node.args)}"
                )
                for arg in node.args:
                    self.visit(arg)
                return "UNKNOWN"

            arg_types = [self.visit(node.args[0]), self.visit(node.args[1])]
            for at in arg_types:
                if at not in ("INTEGER", "UNKNOWN"):
                    self.errors.append("FUNCTION MOD exige argumentos INTEGER")
                    break
            return "INTEGER"

        sym = self.symtable.lookup(self.global_scope, node.name)
        if sym is None or sym.get("kind") != "function":
            self.errors.append(f"FUNCTION nao declarada: {node.name}")
            for arg in node.args:
                self.visit(arg)
            return "UNKNOWN"

        expected = sym.get("params", [])
        if len(node.args) != len(expected):
            self.errors.append(
                f"Numero de argumentos incompativel em FUNCTION {node.name}: esperado {len(expected)}, obtido {len(node.args)}"
            )

        self._validate_call_argument_metadata(
            node.name,
            node.args,
            sym.get("param_types", []),
            sym.get("param_kinds", []),
            "FUNCTION",
        )
        return sym.get("type", "UNKNOWN")

    def visit_CallNode(self, node: CallNode):
        sym = self.symtable.lookup(self.global_scope, node.name)
        if sym is None or sym.get("kind") != "subroutine":
            self.errors.append(f"SUBROUTINE nao declarada: {node.name}")
            for arg in node.args:
                self.visit(arg)
            return

        expected = sym.get("params", [])
        if len(node.args) != len(expected):
            self.errors.append(
                f"Numero de argumentos incompativel em SUBROUTINE {node.name}: esperado {len(expected)}, obtido {len(node.args)}"
            )

        self._validate_call_argument_metadata(
            node.name,
            node.args,
            sym.get("param_types", []),
            sym.get("param_kinds", []),
            "SUBROUTINE",
        )

    def visit_ReturnNode(self, node: ReturnNode):
        return None

    def visit_ProgramNode(self, node: ProgramNode):
        self.analyze(node)


def analyze(ast):
    analyzer = SemanticAnalyzer()
    symtable = analyzer.analyze(ast)
    return ast, symtable
