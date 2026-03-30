from ast_nodes import (
    ArrayRefNode,
    AssignNode,
    BinOpNode,
    DeclNode,
    DoNode,
    GotoNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    PrintNode,
    ReadNode,
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
    def __init__(self):
        self.instrs: list[TACInstr] = []
        self.temp_count = 0
        self.label_count = 0

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

    def visit(self, node):
        meth = getattr(self, f"visit_{node.__class__.__name__}", None)
        if meth is None:
            return None
        return meth(node)

    def visit_DeclNode(self, node: DeclNode):
        return None

    def visit_LiteralNode(self, node: LiteralNode):
        return node.value

    def visit_IdentifierNode(self, node: IdentifierNode):
        return node.name

    def visit_ArrayRefNode(self, node: ArrayRefNode):
        idx_val = self.visit(node.indices[0])
        t = self.new_temp()
        self.emit("LOAD_ARR", t, node.name, idx_val)
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
            self.emit("COPY", node.target.name, src)
        else:
            idx = self.visit(node.target.indices[0])
            self.emit("STORE_ARR", node.target.name, idx, src)

    def visit_PrintNode(self, node: PrintNode):
        for value in node.values:
            val = self.visit(value)
            self.emit("PRINT", None, val)

    def visit_ReadNode(self, node: ReadNode):
        for target in node.targets:
            if isinstance(target, IdentifierNode):
                self.emit("READ", target.name)
            elif isinstance(target, ArrayRefNode):
                idx = self.visit(target.indices[0])
                self.emit("READ_ARR", target.name, idx)

    def visit_GotoNode(self, node: GotoNode):
        self.emit("JMP", node.label)

    def visit_DoNode(self, node: DoNode):
        self.emit("COPY", node.var, self.visit(node.start))
        start_lbl = f"DO_{node.label}"
        end_lbl = f"ENDDO_{node.label}"
        self.emit("LABEL", start_lbl)
        cond = self.new_temp()
        self.emit("LE", cond, node.var, self.visit(node.end))
        self.emit("JMPF", end_lbl, cond)
        for stmt in node.body:
            self.visit(stmt)
        step_val = 1 if node.step is None else self.visit(node.step)
        inc = self.new_temp()
        self.emit("ADD", inc, node.var, step_val)
        self.emit("COPY", node.var, inc)
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


def generate_ir(ast):
    gen = IRGen()
    for stmt in ast.body:
        gen.visit(stmt)
    return gen.instrs
