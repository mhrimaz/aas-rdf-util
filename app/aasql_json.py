from __future__ import annotations

import json
from typing import Any

CAST_OPERATORS = {
    "$strCast": "str",
    "$numCast": "num",
    "$hexCast": "hex",
    "$boolCast": "bool",
    "$dateTimeCast": "dateTime",
    "$timeCast": "time",
}

DATE_PART_OPERATORS = {
    "$dayOfWeek": "$dayOfWeek",
    "$dayOfMonth": "$dayOfMonth",
    "$month": "$month",
    "$year": "$year",
}

COMPARISON_OPERATORS = {"$eq", "$ne", "$gt", "$ge", "$lt", "$le"}
STRING_OPERATORS = {"$contains", "$starts-with", "$ends-with", "$regex"}


class AASQLJsonError(ValueError):
    """Raised when JSON query structure cannot be converted to textual AASQL."""


def _literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    raise AASQLJsonError(f"Unsupported literal type: {type(value).__name__}")


def _value_to_expr(value: dict[str, Any]) -> str:
    if "$field" in value:
        return value["$field"]
    if "$strVal" in value:
        return _literal(value["$strVal"])
    if "$numVal" in value:
        return _literal(value["$numVal"])
    if "$hexVal" in value:
        return _literal(value["$hexVal"])
    if "$dateTimeVal" in value:
        return _literal(value["$dateTimeVal"])
    if "$timeVal" in value:
        return _literal(value["$timeVal"])
    if "$boolean" in value:
        return _literal(value["$boolean"])
    if "$attribute" in value:
        raise AASQLJsonError("$attribute is not supported for query to SPARQL conversion")

    for key, fn_name in CAST_OPERATORS.items():
        if key in value:
            return f"{fn_name}({_value_to_expr(value[key])})"

    for key, fn_name in DATE_PART_OPERATORS.items():
        if key in value:
            nested = value[key]
            if isinstance(nested, dict):
                return f"{fn_name}({_value_to_expr(nested)})"
            return f"{fn_name}({_literal(nested)})"

    raise AASQLJsonError(f"Unsupported value object: {value}")


def _comparison_to_expr(expr: dict[str, Any]) -> str:
    for operator in COMPARISON_OPERATORS:
        if operator in expr:
            left, right = expr[operator]
            return f"{_value_to_expr(left)} {operator} {_value_to_expr(right)}"

    for operator in STRING_OPERATORS:
        if operator in expr:
            left, right = expr[operator]
            return f"{operator}({_value_to_expr(left)}, {_value_to_expr(right)})"

    if "$boolean" in expr:
        return _literal(expr["$boolean"])

    if "$match" in expr:
        items = ", ".join(_comparison_to_expr(item) for item in expr["$match"])
        return f"$match({items})"

    raise AASQLJsonError(f"Unsupported comparison expression: {expr}")


def _logical_to_expr(expr: dict[str, Any]) -> str:
    if "$and" in expr:
        return "$and(" + ", ".join(_logical_to_expr(item) for item in expr["$and"]) + ")"
    if "$or" in expr:
        return "$or(" + ", ".join(_logical_to_expr(item) for item in expr["$or"]) + ")"
    if "$not" in expr:
        return f"$not({_logical_to_expr(expr['$not'])})"

    return _comparison_to_expr(expr)


def aasql_json_to_text(payload: dict[str, Any]) -> str:
    """Convert AASQL JSON-schema representation into textual AASQL syntax."""
    root = payload
    if "Query" in payload:
        root = payload["Query"]

    if "$condition" in root:
        condition = root["$condition"]
    elif isinstance(root, dict):
        condition = root
    else:
        raise AASQLJsonError("Query payload must be an object")

    select = root.get("$select") if isinstance(root, dict) else None
    condition_expr = _logical_to_expr(condition)
    if select == "id":
        return f"$select id {condition_expr}"
    return condition_expr
