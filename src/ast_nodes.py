from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProgramNode:
    name: str
    body: list[Any]
    subprograms: list[Any] = field(default_factory=list)


@dataclass
class VarDeclNode:
    name: str


@dataclass
class ArrayDeclNode:
    name: str
    dims: list[Any]


@dataclass
class DeclNode:
    type_name: str
    vars: list[Any]


@dataclass
class IdentifierNode:
    name: str


@dataclass
class ArrayRefNode:
    name: str
    indices: list[Any]


@dataclass
class FuncCallNode:
    name: str
    args: list[Any]


@dataclass
class LiteralNode:
    value: Any
    type_name: str


@dataclass
class UnaryOpNode:
    op: str
    operand: Any


@dataclass
class BinOpNode:
    op: str
    left: Any
    right: Any


@dataclass
class AssignNode:
    target: Any
    value: Any


@dataclass
class PrintNode:
    values: list[Any]


@dataclass
class ReadNode:
    targets: list[Any]


@dataclass
class CallNode:
    name: str
    args: list[Any]


@dataclass
class IfNode:
    condition: Any
    then_body: list[Any]
    else_body: list[Any] = field(default_factory=list)


@dataclass
class DoNode:
    label: str
    var: str
    start: Any
    end: Any
    step: Any | None
    body: list[Any]


@dataclass
class GotoNode:
    label: str


@dataclass
class ContinueNode:
    label: str | None = None


@dataclass
class StopNode:
    pass


@dataclass
class ReturnNode:
    pass


@dataclass
class FunctionDefNode:
    return_type: str
    name: str
    params: list[str]
    body: list[Any]


@dataclass
class SubroutineDefNode:
    name: str
    params: list[str]
    body: list[Any]
