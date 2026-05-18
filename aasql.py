from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class ParseTree:
    source: str


class _Parser:
    def parse(self, data: str) -> ParseTree:
        return ParseTree(source=data)


parser = _Parser()


def remove_ws(tree: ParseTree) -> ParseTree:
    normalized = re.sub(r"\s+", " ", tree.source).strip()
    return ParseTree(source=normalized)


def _split_top_level(text: str) -> list[str]:
    items: list[str] = []
    depth = 0
    start = 0
    in_string = False
    escape = False

    for index, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            items.append(text[start:index].strip())
            start = index + 1

    tail = text[start:].strip()
    if tail:
        items.append(tail)
    return items


def _strip_wrapping(text: str, prefix: str) -> str | None:
    if text.startswith(prefix) and text.endswith(")"):
        return text[len(prefix):-1].strip()
    return None


def _parse_value(text: str) -> str:
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        return text
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return text
    if text in {"true", "false"}:
        return text
    return text


def _comparison_to_filter(expression: str) -> str:
    for operator, sparql_operator in [
        ("$eq", "="),
        ("$ne", "!="),
        ("$gt", ">"),
        ("$ge", ">="),
        ("$lt", "<"),
        ("$le", "<="),
    ]:
        wrapped = _strip_wrapping(expression, f"{operator}(")
        if wrapped is not None:
            parts = _split_top_level(wrapped)
            if len(parts) == 2:
                return f"FILTER ({_parse_value(parts[0])} {sparql_operator} {_parse_value(parts[1])})"

    for operator, function_name in [
        ("$contains", "CONTAINS"),
        ("$starts-with", "STRSTARTS"),
        ("$ends-with", "STRENDS"),
        ("$regex", "REGEX"),
    ]:
        wrapped = _strip_wrapping(expression, f"{operator}(")
        if wrapped is not None:
            parts = _split_top_level(wrapped)
            if len(parts) == 2:
                first = _parse_value(parts[0])
                second = _parse_value(parts[1])
                if function_name == "REGEX":
                    return f"FILTER ({function_name}({first}, {second}))"
                return f"FILTER ({function_name}({first}, {second}))"

    return f"# Unsupported AASQL expression: {expression}"


def _logical_to_sparql(expression: str) -> str:
    expression = expression.strip()

    wrapped = _strip_wrapping(expression, "$and(")
    if wrapped is not None:
        parts = [_logical_to_sparql(part) for part in _split_top_level(wrapped)]
        return "\n".join(parts)

    wrapped = _strip_wrapping(expression, "$or(")
    if wrapped is not None:
        parts = [_logical_to_sparql(part) for part in _split_top_level(wrapped)]
        joined = " UNION ".join(f"{{ {part} }}" for part in parts)
        return joined

    wrapped = _strip_wrapping(expression, "$not(")
    if wrapped is not None:
        inner = _logical_to_sparql(wrapped)
        return f"FILTER NOT EXISTS {{ {inner} }}"

    wrapped = _strip_wrapping(expression, "$match(")
    if wrapped is not None:
        parts = [_logical_to_sparql(part) for part in _split_top_level(wrapped)]
        return "\n".join(parts)

    return _comparison_to_filter(expression)


def parse_tree_to_sparql(tree: ParseTree) -> str:
    """Convert a small AASQL subset to a readable SPARQL query."""
    body = tree.source.strip()
    if body.startswith("$select id"):
        condition = body[len("$select id"):].strip()
        filter_block = _logical_to_sparql(condition)
        return "\n".join([
            "SELECT ?id WHERE {",
            f"  {filter_block}",
            "}",
        ])

    filter_block = _logical_to_sparql(body)
    return "\n".join([
        "SELECT * WHERE {",
        f"  {filter_block}",
        "}",
    ])
