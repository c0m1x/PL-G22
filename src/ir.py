from dataclasses import dataclass
from typing import Any


@dataclass
class TACInstr:
    op: str
    result: str | None = None
    arg1: Any = None
    arg2: Any = None

    def __str__(self):
        parts = [self.op]
        if self.result is not None:
            parts.append(str(self.result))
        if self.arg1 is not None:
            parts.append(str(self.arg1))
        if self.arg2 is not None:
            parts.append(str(self.arg2))
        return " ".join(parts)
