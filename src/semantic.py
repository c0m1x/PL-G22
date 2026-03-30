from ast_nodes import (
    ArrayDeclNode,
    ArrayRefNode,
    AssignNode,
    BinOpNode,
    DeclNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    PrintNode,
    ProgramNode,
    ReadNode,
    UnaryOpNode,
)
from symbol_table import SymbolTable


class SemanticAnalyzer:
    def __init__(self):
        self.symtable = SymbolTable()
        self.errors: list[str] = []
        self.current_scope = "GLOBAL"

    def analyze(self, program: ProgramNode):
        self.current_scope = program.name
        self.symtable.create_scope(program.name)
        for stmt in program.body:
            self.visit(stmt)
        if self.errors:
            raise ValueError("\n".join(self.errors))
        return self.symtable

    def visit(self, node):
        meth = getattr(self, f"visit_{node.__class__.__name__}", None)
        if meth is None:
            return None
        return meth(node)

    def visit_DeclNode(self, node: DeclNode):
        for var in node.vars:
            try:
                if isinstance(var, ArrayDeclNode):
                    self.symtable.declare(
                        self.current_scope,
                        var.name,
                        {"kind": "array", "type": node.type_name, "dims": var.dims},
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
        if sym is None:
            self.errors.append(f"Identificador nao declarado: {name}")
            return {"kind": "var", "type": "UNKNOWN"}
        return sym

    def _type_compatible(self, ltype: str, rtype: str):
        if ltype == rtype:
            return True
        if ltype == "REAL" and rtype == "INTEGER":
            return True
        return False

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
        for idx in node.indices:
            itype = self.visit(idx)
            if itype != "INTEGER":
                self.errors.append(f"Indice de array deve ser INTEGER em {node.name}")
        return sym["type"]

    def visit_LiteralNode(self, node: LiteralNode):
        return node.type_name

    def visit_UnaryOpNode(self, node: UnaryOpNode):
        t = self.visit(node.operand)
        if node.op == "NOT":
            return "LOGICAL"
        return t

    def visit_BinOpNode(self, node: BinOpNode):
        lt = self.visit(node.left)
        rt = self.visit(node.right)
        if node.op in ("EQ", "NE", "LT", "LE", "GT", "GE", "AND", "OR"):
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

    def visit_ProgramNode(self, node: ProgramNode):
        self.analyze(node)


def analyze(ast):
    analyzer = SemanticAnalyzer()
    symtable = analyzer.analyze(ast)
    return ast, symtable
