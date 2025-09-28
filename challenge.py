from lark import Lark, Transformer
from dataclasses import dataclass

# ===== AST Classes =====
@dataclass
class Expr:
    pass

@dataclass
class Num(Expr):
    value: int
    def __repr__(self): return f"Num({int(self.value)})"

@dataclass
class Add(Expr):
    left: Expr
    right: Expr
    def __repr__(self): return f"Add({self.left}, {self.right})"

@dataclass
class Minus(Expr):
    left: Expr
    right: Expr
    def __repr__(self): return f"Minus({self.left}, {self.right})"

@dataclass
class Multi(Expr):
    left: Expr
    right: Expr
    def __repr__(self): return f"Multi({self.left}, {self.right})"

@dataclass
class Div(Expr):
    left: Expr
    right: Expr
    def __repr__(self): return f"Div({self.left}, {self.right})"

@dataclass
class Par(Expr):
    expr: Expr
    def __repr__(self): return f"Par({self.expr})"


# ===== Grammar Rules =====
grammar = """
    ?start: exp
    ?exp: NUMBER         -> number
         | exp "+" exp   -> add
         | exp "-" exp   -> sub
         | exp "*" exp   -> mul
         | exp "/" exp   -> div
         | "(" exp ")"   -> par
    %import common.NUMBER
    %import common.WS_INLINE
    %ignore WS_INLINE
"""


# ===== Transformer: Parse Tree -> AST =====
class ASTBuilder(Transformer):
    def number(self, items):
        return Num(int(items[0]))
    def add(self, items):
        return Add(items[0], items[1])
    def sub(self, items):
        return Minus(items[0], items[1])
    def mul(self, items):
        return Multi(items[0], items[1])
    def div(self, items):
        return Div(items[0], items[1])
    def par(self, items):
        return Par(items[0])


# ===== Build the Parser =====
parser = Lark(grammar, parser="earley")
transformer = ASTBuilder()

# ===== Read expressions from file =====
with open("expr.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# ===== Parse and transform each expression =====
for line in lines:
    tree = parser.parse(line)           # parse with Earley
    expr = transformer.transform(tree)  # transform manually to AST
    print(expr)

# Add(Multi(Num(3), Num(4)), Div(Num(10), Num(2)))
# Minus(Multi(Par(Add(Num(12), Num(217))), Num(3)), Num(621))
