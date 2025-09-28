# parser demo: read expressions from a file, tokenize, parse into AST, and print ASTs.
# This code will create a sample input file, implement a lexer + recursive-descent parser,
# parse each line, and print a readable AST representation.

import re, json, pathlib
from dataclasses import dataclass
from typing import List, Optional, Union

# ----------------------------- AST node classes -----------------------------
@dataclass
class ASTNode:
    def to_dict(self):
        raise NotImplementedError()

    def sexpr(self) -> str:
        raise NotImplementedError()

@dataclass
class Number(ASTNode):
    value: Union[int, float]
    def to_dict(self):
        return {"type": "Number", "value": self.value}
    def sexpr(self):
        return str(self.value)

@dataclass
class Var(ASTNode):
    name: str
    def to_dict(self):
        return {"type": "Var", "name": self.name}
    def sexpr(self):
        return self.name

@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode
    def to_dict(self):
        return {"type": "UnaryOp", "op": self.op, "operand": self.operand.to_dict()}
    def sexpr(self):
        return f"({self.op} {self.operand.sexpr()})"

@dataclass
class BinOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
    def to_dict(self):
        return {"type": "BinOp", "op": self.op, "left": self.left.to_dict(), "right": self.right.to_dict()}
    def sexpr(self):
        return f"({self.op} {self.left.sexpr()} {self.right.sexpr()})"

@dataclass
class FuncCall(ASTNode):
    name: str
    args: List[ASTNode]
    def to_dict(self):
        return {"type": "FuncCall", "name": self.name, "args": [a.to_dict() for a in self.args]}
    def sexpr(self):
        args_s = ' '.join(a.sexpr() for a in self.args)
        return f"({self.name} {args_s})" if args_s else f"({self.name})"


# -------------------------------- Lexer ------------------------------------
TOKEN_SPEC = [
    ("NUMBER",  r"\d+(\.\d+)?"),    # integer or decimal number
    ("IDENT",   r"[A-Za-z_][A-Za-z0-9_]*"),
    ("PLUS",    r"\+"),
    ("MINUS",   r"-"),
    ("MUL",     r"\*"),
    ("DIV",     r"/"),
    ("POW",     r"\^"),
    ("LPAREN",  r"\("),
    ("RPAREN",  r"\)"),
    ("COMMA",   r","),
    ("SKIP",    r"[ \t]+"),
    ("MISMATCH",r"."),
]

TOK_REGEX = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
TOKEN_RE = re.compile(TOK_REGEX)

@dataclass
class Token:
    type: str
    value: str

def lex(text: str) -> List[Token]:
    tokens = []
    for mo in TOKEN_RE.finditer(text):
        kind = mo.lastgroup
        val = mo.group()
        if kind == "NUMBER":
            tokens.append(Token(kind, val))
        elif kind == "IDENT":
            tokens.append(Token(kind, val))
        elif kind in ("PLUS","MINUS","MUL","DIV","POW","LPAREN","RPAREN","COMMA"):
            tokens.append(Token(kind, val))
        elif kind == "SKIP":
            continue
        elif kind == "MISMATCH":
            raise SyntaxError(f"Unexpected character: {val!r}")
    tokens.append(Token("EOF",""))
    return tokens

# ------------------------------ Parser -------------------------------------
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def eat(self, typ: str) -> Token:
        tok = self.current()
        if tok.type == typ:
            self.pos += 1
            return tok
        raise SyntaxError(f"Expected token {typ}, got {tok.type} ({tok.value}) at position {self.pos}")

    def parse(self) -> ASTNode:
        node = self.parse_expression()
        if self.current().type != "EOF":
            raise SyntaxError("Extra input after valid expression")
        return node

    # Expression -> Term ((PLUS|MINUS) Term)*
    def parse_expression(self) -> ASTNode:
        node = self.parse_term()
        while self.current().type in ("PLUS","MINUS"):
            op = self.eat(self.current().type).value
            rhs = self.parse_term()
            node = BinOp(op, node, rhs)
        return node

    # Term -> Power ((MUL|DIV) Power)*
    def parse_term(self) -> ASTNode:
        node = self.parse_power()
        while self.current().type in ("MUL","DIV"):
            op = self.eat(self.current().type).value
            rhs = self.parse_power()
            node = BinOp(op, node, rhs)
        return node

    # Power -> Factor (POW Power)?   (right-associative)
    def parse_power(self) -> ASTNode:
        node = self.parse_factor()
        if self.current().type == "POW":
            self.eat("POW")
            rhs = self.parse_power()  # right-assoc
            node = BinOp("^", node, rhs)
        return node

    # Factor -> (PLUS|MINUS) Factor | Atom
    def parse_factor(self) -> ASTNode:
        if self.current().type == "PLUS":
            self.eat("PLUS")
            return UnaryOp("+", self.parse_factor())
        if self.current().type == "MINUS":
            self.eat("MINUS")
            return UnaryOp("-", self.parse_factor())
        return self.parse_atom()

    # Atom -> NUMBER | IDENT (LPAREN arglist? RPAREN)? | LPAREN Expression RPAREN
    def parse_atom(self) -> ASTNode:
        tok = self.current()
        if tok.type == "NUMBER":
            self.eat("NUMBER")
            if "." in tok.value:
                return Number(float(tok.value))
            else:
                return Number(int(tok.value))
        if tok.type == "IDENT":
            name = self.eat("IDENT").value
            # function call?
            if self.current().type == "LPAREN":
                self.eat("LPAREN")
                args = []
                if self.current().type != "RPAREN":
                    args.append(self.parse_expression())
                    while self.current().type == "COMMA":
                        self.eat("COMMA")
                        args.append(self.parse_expression())
                self.eat("RPAREN")
                return FuncCall(name, args)
            else:
                return Var(name)
        if tok.type == "LPAREN":
            self.eat("LPAREN")
            node = self.parse_expression()
            self.eat("RPAREN")
            return node
        raise SyntaxError(f"Unexpected token {tok.type} ({tok.value}) at atom")

# -------------------------- Utilities & CLI --------------------------------
def parse_line(line: str) -> ASTNode:
    tokens = lex(line)
    p = Parser(tokens)
    return p.parse()

def ast_to_json(node: ASTNode) -> str:
    return json.dumps(node.to_dict(), ensure_ascii=False, indent=2)

def ast_pretty(node: ASTNode) -> str:
    return node.sexpr()

# Create a sample input file
sample_path = pathlib.Path("./expressions.txt")
sample_text = """\
3 * 4 + 10 / 2
(12 + 217) * 3 - 621
"""
sample_path.write_text(sample_text, encoding="utf-8")

print("Sample input written to:", sample_path)
print("Contents:\n", sample_text)

# Parse file
results = []
with sample_path.open("r", encoding="utf-8") as f:
    for i, raw in enumerate(f, start=1):
        line = raw.strip()
        if not line: 
            continue
        try:
            node = parse_line(line)
            results.append({"line_no": i, "expr": line, "ast_json": node.to_dict(), "sexpr": node.sexpr()})
            print(f"Line {i}: {line}")
            print("  S-expression:", node.sexpr())
            print("  JSON AST:\n", ast_to_json(node))
        except Exception as e:
            print(f"Line {i}: parse error: {e}")

# Save results to a json file for inspection
out_path = pathlib.Path("./expressions_ast.json")
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nASTs saved to:", out_path)