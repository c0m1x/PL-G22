class SymbolTable:
    def __init__(self):
        self.scopes: dict[str, dict[str, dict]] = {}

    def create_scope(self, scope: str):
        if scope not in self.scopes:
            self.scopes[scope] = {}

    def declare(self, scope: str, name: str, info: dict):
        table = self.scopes.setdefault(scope, {})
        if name in table:
            raise ValueError(f"Redeclaracao de simbolo: {name}")
        table[name] = info

    def lookup(self, scope: str, name: str):
        if scope in self.scopes and name in self.scopes[scope]:
            return self.scopes[scope][name]
        if "GLOBAL" in self.scopes and name in self.scopes["GLOBAL"]:
            return self.scopes["GLOBAL"][name]
        return None

    def get_scope(self, scope: str):
        return self.scopes.get(scope, {})
