"""Visualizador de AST Fortran 77 usando Graphviz.

Gera um grafo dirigido (PDF/PNG) que representa a arvore sintatica
de um programa Fortran compilado.

Uso:
    from visualizer import visualize
    visualize(ast, output="out/ast")   # gera out/ast.pdf
"""

import os
from graphviz import Digraph

from ast_nodes import (
    ArrayDeclNode,
    ArrayRefNode,
    AssignNode,
    BinOpNode,
    CallNode,
    ContinueNode,
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
    StopNode,
    SubroutineDefNode,
    UnaryOpNode,
    VarDeclNode,
)


class _ASTVisualizer:
    def __init__(self):
        self.dot = Digraph(
            comment="Fortran 77 AST",
            graph_attr={"rankdir": "TB", "fontname": "Helvetica"},
            node_attr={"shape": "box", "style": "rounded,filled", "fontname": "Helvetica", "fontsize": "11"},
            edge_attr={"fontname": "Helvetica", "fontsize": "9"},
        )
        self._counter = 0

    def _new_id(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def _node(self, label: str, color: str = "#dce8f7") -> str:
        nid = self._new_id()
        self.dot.node(nid, label, fillcolor=color)
        return nid

    def _edge(self, parent: str, child: str, label: str = "") -> None:
        self.dot.edge(parent, child, label=label)

    # ── visitors ──────────────────────────────────────────────────────────

    def visit(self, node, parent: str | None = None, edge_label: str = "") -> str:
        meth = getattr(self, f"_visit_{node.__class__.__name__}", self._visit_generic)
        nid = meth(node)
        if parent is not None:
            self._edge(parent, nid, edge_label)
        return nid

    def _visit_generic(self, node) -> str:
        return self._node(node.__class__.__name__, "#f0f0f0")

    def _visit_ProgramNode(self, node: ProgramNode) -> str:
        nid = self._node(f"PROGRAM\n{node.name}", "#b8d4f0")
        for stmt in node.body:
            self.visit(stmt, nid)
        for sub in node.subprograms:
            self.visit(sub, nid, "subprogram")
        return nid

    def _visit_FunctionDefNode(self, node: FunctionDefNode) -> str:
        nid = self._node(f"FUNCTION\n{node.return_type} {node.name}\n({', '.join(node.params)})", "#c8e6c9")
        for stmt in node.body:
            self.visit(stmt, nid)
        return nid

    def _visit_SubroutineDefNode(self, node: SubroutineDefNode) -> str:
        nid = self._node(f"SUBROUTINE\n{node.name}\n({', '.join(node.params)})", "#c8e6c9")
        for stmt in node.body:
            self.visit(stmt, nid)
        return nid

    def _visit_DeclNode(self, node: DeclNode) -> str:
        nid = self._node(f"DECL\n{node.type_name}", "#fff9c4")
        for var in node.vars:
            self.visit(var, nid)
        return nid

    def _visit_VarDeclNode(self, node: VarDeclNode) -> str:
        return self._node(f"VAR\n{node.name}", "#fff9c4")

    def _visit_ArrayDeclNode(self, node: ArrayDeclNode) -> str:
        nid = self._node(f"ARRAY\n{node.name}", "#fff9c4")
        for dim in node.dims:
            self.visit(dim, nid, "dim")
        return nid

    def _visit_AssignNode(self, node: AssignNode) -> str:
        nid = self._node("ASSIGN\n:=", "#ffe0b2")
        self.visit(node.target, nid, "lval")
        self.visit(node.value, nid, "rval")
        return nid

    def _visit_IfNode(self, node: IfNode) -> str:
        nid = self._node("IF", "#f3e5f5")
        self.visit(node.condition, nid, "cond")
        for stmt in node.then_body:
            self.visit(stmt, nid, "then")
        for stmt in node.else_body:
            self.visit(stmt, nid, "else")
        return nid

    def _visit_DoNode(self, node: DoNode) -> str:
        step_str = "" if node.step is None else ", step"
        nid = self._node(f"DO {node.label}\n{node.var} = start, end{step_str}", "#f3e5f5")
        self.visit(node.start, nid, "start")
        self.visit(node.end, nid, "end")
        if node.step is not None:
            self.visit(node.step, nid, "step")
        for stmt in node.body:
            self.visit(stmt, nid)
        return nid

    def _visit_GotoNode(self, node: GotoNode) -> str:
        return self._node(f"GOTO\n{node.label}", "#ffcdd2")

    def _visit_ContinueNode(self, node: ContinueNode) -> str:
        return self._node("CONTINUE", "#e0e0e0")

    def _visit_StopNode(self, node: StopNode) -> str:
        return self._node("STOP", "#ffcdd2")

    def _visit_ReturnNode(self, node: ReturnNode) -> str:
        return self._node("RETURN", "#ffcdd2")

    def _visit_PrintNode(self, node: PrintNode) -> str:
        nid = self._node("PRINT *,", "#e8f5e9")
        for val in node.values:
            self.visit(val, nid)
        return nid

    def _visit_ReadNode(self, node: ReadNode) -> str:
        nid = self._node("READ *,", "#e8f5e9")
        for target in node.targets:
            self.visit(target, nid)
        return nid

    def _visit_CallNode(self, node: CallNode) -> str:
        nid = self._node(f"CALL\n{node.name}", "#e8f5e9")
        for arg in node.args:
            self.visit(arg, nid, "arg")
        return nid

    def _visit_BinOpNode(self, node: BinOpNode) -> str:
        op_map = {
            "PLUS": "+",
            "MINUS": "-",
            "STAR": "*",
            "SLASH": "/",
            "DSTAR": "**",
            "EQ": ".EQ.",
            "NE": ".NE.",
            "LT": ".LT.",
            "LE": ".LE.",
            "GT": ".GT.",
            "GE": ".GE.",
            "AND": ".AND.",
            "OR": ".OR.",
        }
        op = op_map.get(node.op, node.op)
        nid = self._node(op, "#dce8f7")
        self.visit(node.left, nid, "L")
        self.visit(node.right, nid, "R")
        return nid

    def _visit_UnaryOpNode(self, node: UnaryOpNode) -> str:
        op = ".NOT." if node.op == "NOT" else "-"
        nid = self._node(op, "#dce8f7")
        self.visit(node.operand, nid)
        return nid

    def _visit_LiteralNode(self, node: LiteralNode) -> str:
        val = repr(node.value) if node.type_name == "CHARACTER" else str(node.value)
        return self._node(f"{node.type_name}\n{val}", "#f5f5f5")

    def _visit_IdentifierNode(self, node: IdentifierNode) -> str:
        return self._node(f"ID\n{node.name}", "#f5f5f5")

    def _visit_ArrayRefNode(self, node: ArrayRefNode) -> str:
        nid = self._node(f"ARR_REF\n{node.name}", "#f5f5f5")
        for idx in node.indices:
            self.visit(idx, nid, "idx")
        return nid

    def _visit_FuncCallNode(self, node: FuncCallNode) -> str:
        nid = self._node(f"CALL_EXPR\n{node.name}", "#dce8f7")
        for arg in node.args:
            self.visit(arg, nid, "arg")
        return nid


def visualize(ast: ProgramNode, output: str = "ast", view: bool = False) -> str:
    """Gera uma visualizacao grafica da AST em PDF.

    Args:
        ast: Raiz da arvore sintatica (ProgramNode).
        output: Caminho base do ficheiro de saida (sem extensao).
        view: Se True, abre o PDF automaticamente apos gerar.

    Returns:
        Caminho do ficheiro gerado (com extensao .pdf).
    """
    os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)
    viz = _ASTVisualizer()
    viz.visit(ast)
    path = viz.dot.render(output, format="pdf", view=view, cleanup=True)
    return path
