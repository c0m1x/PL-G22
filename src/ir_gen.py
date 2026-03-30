from ast_nodes import (
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
    ReadNode,
    ReturnNode,
    StopNode,
    SubroutineDefNode,
    UnaryOpNode,
)
from ir import TACInstr


_BIN_OP_MAP = {
    "PLUS": "ADD",
    "MINUS": "SUB",
    "STAR": "MUL",
    "SLASH": "DIV",
    "DSTAR": "POW",
    "EQ": "EQ",
    "NE": "NE",
    "LT": "LT",
    "LE": "LE",
    "GT": "GT",
    "GE": "GE",
    "AND": "AND",
    "OR": "OR",
}


class IRGen:
    def __init__(self, ast=None):
        self.instrs: list[TACInstr] = []
        self.temp_count = 0
        self.label_count = 0
        self.inline_count = 0
        self.scope_stack: list[dict[str, str]] = []
        self.return_label_stack: list[str] = []
        self.functions: dict[str, FunctionDefNode] = {}
        self.subroutines: dict[str, SubroutineDefNode] = {}
        if ast is not None and getattr(ast, "subprograms", None):
            for sub in ast.subprograms:
                if isinstance(sub, FunctionDefNode):
                    self.functions[sub.name] = sub
                elif isinstance(sub, SubroutineDefNode):
                    self.subroutines[sub.name] = sub

    def new_temp(self):
        t = f"_t{self.temp_count}"
        self.temp_count += 1
        return t

    def new_label(self, hint="L"):
        l = f"{hint}_{self.label_count}"
        self.label_count += 1
        return l

    def emit(self, op, result=None, arg1=None, arg2=None):
        self.instrs.append(TACInstr(op, result, arg1, arg2))

    def _map_name(self, name: str):
        mapped = name
        for scope in self.scope_stack:
            mapped = scope.get(mapped, mapped)
        return mapped

    def _map_label(self, label: str):
        key = f"@L:{label}"
        mapped = key
        for scope in self.scope_stack:
            mapped = scope.get(mapped, mapped)
        return mapped[3:] if isinstance(mapped, str) and mapped.startswith("@L:") else mapped

    def visit(self, node):
        stmt_label = getattr(node, "stmt_label", None)
        if stmt_label is not None:
            self.emit("LABEL", self._map_label(str(stmt_label)))
        meth = getattr(self, f"visit_{node.__class__.__name__}", None)
        if meth is None:
            return None
        return meth(node)

    def visit_DeclNode(self, node: DeclNode):
        return None

    def visit_LiteralNode(self, node: LiteralNode):
        if node.type_name == "CHARACTER":
            return ("STR", node.value)
        return node.value

    def visit_IdentifierNode(self, node: IdentifierNode):
        return self._map_name(node.name)

    def visit_ArrayRefNode(self, node: ArrayRefNode):
        idx_vals = [self.visit(idx) for idx in node.indices]
        t = self.new_temp()
        self.emit("LOAD_ARR", t, self._map_name(node.name), idx_vals)
        return t

    def visit_UnaryOpNode(self, node: UnaryOpNode):
        value = self.visit(node.operand)
        if node.op == "MINUS":
            t = self.new_temp()
            self.emit("NEG", t, value)
            return t
        if node.op == "NOT":
            t = self.new_temp()
            self.emit("NOT", t, value)
            return t
        return value

    def visit_BinOpNode(self, node: BinOpNode):
        left = self.visit(node.left)
        right = self.visit(node.right)
        t = self.new_temp()
        self.emit(_BIN_OP_MAP[node.op], t, left, right)
        return t

    def visit_AssignNode(self, node: AssignNode):
        src = self.visit(node.value)
        if isinstance(node.target, IdentifierNode):
            self.emit("COPY", self._map_name(node.target.name), src)
        else:
            idx_vals = [self.visit(idx) for idx in node.target.indices]
            self.emit("STORE_ARR", self._map_name(node.target.name), idx_vals, src)

    def visit_PrintNode(self, node: PrintNode):
        for value in node.values:
            val = self.visit(value)
            self.emit("PRINT", None, val)

    def visit_ReadNode(self, node: ReadNode):
        for target in node.targets:
            if isinstance(target, IdentifierNode):
                self.emit("READ", self._map_name(target.name))
            elif isinstance(target, ArrayRefNode):
                idx_vals = [self.visit(idx) for idx in target.indices]
                self.emit("READ_ARR", self._map_name(target.name), idx_vals)

    def visit_GotoNode(self, node: GotoNode):
        self.emit("JMP", self._map_label(node.label))

    def visit_DoNode(self, node: DoNode):
        loop_var = self._map_name(node.var)
        loop_label = self._map_label(node.label)
        self.emit("COPY", loop_var, self.visit(node.start))
        start_lbl = f"DO_{loop_label}"
        end_lbl = f"ENDDO_{loop_label}"
        self.emit("LABEL", start_lbl)
        cond = self.new_temp()
        self.emit("LE", cond, loop_var, self.visit(node.end))
        self.emit("JMPF", end_lbl, cond)
        for stmt in node.body:
            self.visit(stmt)
        step_val = 1 if node.step is None else self.visit(node.step)
        inc = self.new_temp()
        self.emit("ADD", inc, loop_var, step_val)
        self.emit("COPY", loop_var, inc)
        self.emit("JMP", start_lbl)
        self.emit("LABEL", end_lbl)

    def visit_IfNode(self, node: IfNode):
        else_lbl = self.new_label("ELSE")
        end_lbl = self.new_label("ENDIF")
        cond = self.visit(node.condition)
        self.emit("JMPF", else_lbl, cond)
        for stmt in node.then_body:
            self.visit(stmt)
        self.emit("JMP", end_lbl)
        self.emit("LABEL", else_lbl)
        for stmt in node.else_body:
            self.visit(stmt)
        self.emit("LABEL", end_lbl)

    def visit_StopNode(self, node: StopNode):
        self.emit("HALT")

    def _push_inline_scope(self, name: str, params: list[str], args: list, by_ref=False):
        call_id = self.inline_count
        self.inline_count += 1
        prefix = f"{name}_{call_id}"
        mapping: dict[str, str] = {}
        for idx, param in enumerate(params):
            mapping[param] = f"{prefix}__arg_{idx}_{param}"
        mapping[name] = f"{prefix}__ret"
        return_label = f"{prefix}__return"
        mapping["@RETURN"] = return_label
        self.scope_stack.append(mapping)

        for idx, arg in enumerate(args[: len(params)]):
            param = params[idx]
            if by_ref and isinstance(arg, IdentifierNode):
                mapping[param] = self._map_name(arg.name)
                continue
            arg_val = self.visit(arg)
            self.emit("COPY", mapping[param], arg_val)

        return mapping, return_label

    def _inline_body_with_labels(self, body, prefix: str):
        if not self.scope_stack:
            for stmt in body:
                self.visit(stmt)
            return

        # Build stable mapping for numeric labels used by GOTO/DO and statement labels.
        label_map: dict[str, str] = {}

        def collect(stmts):
            for st in stmts:
                stmt_lbl = getattr(st, "stmt_label", None)
                if stmt_lbl is not None:
                    label_map[str(stmt_lbl)] = f"{prefix}__L{stmt_lbl}"
                if isinstance(st, DoNode):
                    label_map[str(st.label)] = f"{prefix}__L{st.label}"
                    collect(st.body)
                elif isinstance(st, IfNode):
                    collect(st.then_body)
                    collect(st.else_body)

        collect(body)
        top = self.scope_stack[-1]
        for orig, mapped in label_map.items():
            top[f"@L:{orig}"] = mapped

        for stmt in body:
            self.visit(stmt)

    def visit_FuncCallNode(self, node: FuncCallNode):
        if node.name not in self.functions:
            # Semantic should reject this earlier; preserve pipeline with a neutral value.
            t = self.new_temp()
            self.emit("COPY", t, 0)
            return t

        fn = self.functions[node.name]
        mapping, return_label = self._push_inline_scope(fn.name, fn.params, node.args, by_ref=False)
        self.return_label_stack.append(return_label)
        prefix = mapping[fn.name].rsplit("__", 1)[0]
        self._inline_body_with_labels(fn.body, prefix)
        self.emit("LABEL", return_label)
        self.return_label_stack.pop()
        self.scope_stack.pop()

        result_temp = self.new_temp()
        self.emit("COPY", result_temp, mapping[fn.name])
        return result_temp

    def visit_CallNode(self, node: CallNode):
        if node.name not in self.subroutines:
            return
        sub = self.subroutines[node.name]
        mapping, return_label = self._push_inline_scope(sub.name, sub.params, node.args, by_ref=True)
        self.return_label_stack.append(return_label)
        prefix = f"{sub.name}_{self.inline_count - 1}"
        self._inline_body_with_labels(sub.body, prefix)
        self.emit("LABEL", return_label)
        self.return_label_stack.pop()
        self.scope_stack.pop()

    def visit_ReturnNode(self, node: ReturnNode):
        if self.return_label_stack:
            self.emit("JMP", self.return_label_stack[-1])


def generate_ir(ast):
    gen = IRGen(ast)
    for stmt in ast.body:
        gen.visit(stmt)
    return gen.instrs
