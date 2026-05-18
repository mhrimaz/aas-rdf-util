from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker
from lark import Lark, Token, Transformer, Tree


class AASQLPipelineError(ValueError):
    """Raised when AASQL parsing, validation, or conversion fails."""


GRAMMAR = r"""
// High-Level Productions (query branch + placeholder access-rule branch)
start: query | all_access_permission_rules

query: select_statement? logical_expression
select_statement: "$select" ws "id" ws

?logical_expression: logical_nested_expression
                                     | logical_or_expression
                                     | logical_and_expression
                                     | logical_not_expression
                                     | match_expression
                                     | BOOL_LITERAL      -> bool_literal
                                     | cast_to_bool
                                     | single_comparison

logical_nested_expression: "(" ws logical_expression ")" ws

logical_or_expression: "$or" ws "(" ws logical_expression ("," ws logical_expression)+ ")" ws
logical_and_expression: "$and" ws "(" ws logical_expression ("," ws logical_expression)+ ")" ws
logical_not_expression: "$not" ws "(" ws logical_expression ")" ws

match_expression: "$match" ws "(" ws (single_comparison | match_expression) ("," ws (single_comparison | match_expression))* ")" ws

single_comparison: string_comparison
                                 | numerical_comparison
                                 | hex_comparison
                                 | bool_comparison
                                 | date_time_comparison
                                 | time_comparison

all_comparisons: OP

string_comparison: STR_FN ws "(" ws string_operand ws "," ws string_operand ws ")" ws   -> function_comparison
                                 | operand ws all_comparisons ws operand ws                                  -> comparison

numerical_comparison: operand ws all_comparisons ws operand ws  -> comparison
hex_comparison: operand ws all_comparisons ws operand ws        -> comparison
bool_comparison: operand ws EQ_NE ws operand ws      -> comparison
date_time_comparison: operand ws all_comparisons ws operand ws  -> comparison
time_comparison: operand ws all_comparisons ws operand ws       -> comparison

operand: string_operand
             | numerical_operand
             | hex_operand
             | bool_operand
             | date_time_operand
             | time_operand

string_operand: field_identifier
                            | STRING_LITERAL          -> string_literal
                            | cast_to_string
                            | single_attribute
numerical_operand: NUMERICAL_LITERAL    -> num_literal
                                 | cast_to_numerical
                                 | date_time_to_num
hex_operand: HEX_LITERAL                -> hex_literal
                    | cast_to_hex
bool_operand: BOOL_LITERAL              -> bool_literal
                     | cast_to_bool
date_time_operand: DATETIME_LITERAL     -> date_time_literal
                                | cast_to_date_time
                                | global_attribute
time_operand: TIME_LITERAL              -> time_literal
                        | cast_to_time

cast_to_string: "str" ws "(" ws operand ws ")" ws            -> cast_to_string_expr
cast_to_numerical: "num" ws "(" ws operand ws ")" ws         -> cast_to_numerical_expr
cast_to_hex: "hex" ws "(" ws operand ws ")" ws               -> cast_to_hex_expr
cast_to_bool: "bool" ws "(" ws operand ws ")" ws             -> cast_to_bool_expr
cast_to_date_time: "dateTime" ws "(" ws string_operand ws ")" ws -> cast_to_date_time_expr
cast_to_time: "time" ws "(" ws (string_operand | date_time_operand) ws ")" ws -> cast_to_time_expr

date_time_to_num: DATE_FN ws "(" ws date_time_operand ws ")" ws -> date_part_expr

single_attribute: claim_attribute | global_attribute | reference_attribute
claim_attribute: "CLAIM" ws "(" ws CLAIM_LITERAL ws ")"
global_attribute: "GLOBAL" ws "(" ws ("LOCALNOW" | "UTCNOW" | "CLIENTNOW" | "ANONYMOUS") ws ")"
reference_attribute: "REFERENCE" ws "(" ws REFERENCE_LITERAL ws ")"

field_identifier: FIELD

// Placeholder branch so grammar stays close to provided one; conversion remains query-only.
all_access_permission_rules: /(DEFATTRIBUTES|DEFACLS|DEFOBJECTS|DEFFORMULAS|ACCESSRULE:)[\s\S]*/

STR_FN: "$contains"|"$starts-with"|"$ends-with"|"$regex"
OP: "$eq"|"$ne"|"$gt"|"$lt"|"$ge"|"$le"
EQ_NE: "$eq"|"$ne"
DATE_FN: "$dayOfWeek"|"$dayOfMonth"|"$month"|"$year"
FIELD: /\$[A-Za-z][A-Za-z0-9#\.\[\]_]*/

DIGIT: "0".."9"
BOOL_LITERAL: "true" | "false"
HEX_LITERAL: "16#" /[0-9A-F]+/
NUMERICAL_LITERAL: /[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?/
STRING_LITERAL: /"([A-Za-z0-9\/*\[\]() _@#\\+\-.,:$^]+)"/
DATETIME_LITERAL: /[0-9]{4}-[0-9]{2}-[0-9]{2}(T[0-9]{2}:[0-9]{2}(:[0-9]{2})?(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})?)?/
TIME_LITERAL: /[0-9]{2}:[0-9]{2}(:[0-9]{2})?(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})?/
ID_SHORT: /[a-zA-Z]([a-zA-Z0-9_-]*[a-zA-Z0-9])?/

CLAIM_LITERAL: STRING_LITERAL
REFERENCE_LITERAL: STRING_LITERAL

ws: REQUIRED_WS?
REQUIRED_WS: /[ \t\r\n]+/

%ignore /[ \t\r\n]+/
"""


AASQL_JSON_SCHEMA_PATH = Path(__file__).with_name("aasql_schema.json")
with AASQL_JSON_SCHEMA_PATH.open("r", encoding="utf-8") as schema_file:
    AASQL_JSON_SCHEMA: dict[str, Any] = json.load(schema_file)


_parser = Lark(GRAMMAR, parser="earley")
_validator = Draft7Validator(AASQL_JSON_SCHEMA, format_checker=FormatChecker())

_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)
_TIME_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)


class _TreeToJson(Transformer):
    @staticmethod
    def _compact(items: list[Any]) -> list[Any]:
        return [item for item in items if item is not None]

    def start(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def query(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        if len(compact) == 2:
            return {"Query": {"$select": "id", "$condition": compact[1]}}
        return {"Query": {"$condition": compact[0]}}

    def select_statement(self, _items: list[Any]) -> str:
        return "id"

    def logical_and_expression(self, items: list[Any]) -> dict[str, Any]:
        return {"$and": self._compact(items)}

    def logical_or_expression(self, items: list[Any]) -> dict[str, Any]:
        return {"$or": self._compact(items)}

    def logical_not_expression(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$not": compact[0]}

    def match_expression(self, items: list[Any]) -> dict[str, Any]:
        return {"$match": self._compact(items)}

    def logical_nested_expression(self, items: list[Any]) -> dict[str, Any]:
        return items[0]

    def single_comparison(self, items: list[Any]) -> dict[str, Any]:
        return items[0]

    def string_comparison(self, items: list[Any]) -> dict[str, Any]:
        return items[0]

    def numerical_comparison(self, items: list[Any]) -> dict[str, Any]:
        return items[0]

    def hex_comparison(self, items: list[Any]) -> dict[str, Any]:
        return items[0]

    def bool_comparison(self, items: list[Any]) -> dict[str, Any]:
        return items[0]

    def date_time_comparison(self, items: list[Any]) -> dict[str, Any]:
        return items[0]

    def time_comparison(self, items: list[Any]) -> dict[str, Any]:
        return items[0]

    def function_comparison(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        operator, left, right = compact
        return {operator: [left, right]}

    def comparison(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        if len(compact) == 3:
            left, operator, right = compact
            if isinstance(operator, str) and operator.startswith("$"):
                return {operator: [left, right]}

        raise AASQLPipelineError("Unsupported comparison shape")

    def all_comparisons(self, items: list[Any]) -> str:
        compact = self._compact(items)
        return str(compact[0])

    def operand(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def string_operand(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def numerical_operand(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def hex_operand(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def bool_operand(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def date_time_operand(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def time_operand(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def field_identifier(self, items: list[Any]) -> dict[str, Any]:
        return {"$field": str(items[0])}

    def string_literal(self, items: list[Any]) -> dict[str, Any]:
        raw = str(items[0])
        s = json.loads(raw)
        if _DATETIME_RE.match(s):
            return {"$dateTimeVal": s}
        if _TIME_RE.match(s):
            return {"$timeVal": s}
        return {"$strVal": s}

    def num_literal(self, items: list[Any]) -> dict[str, Any]:
        raw = str(items[0])
        if "." in raw or "e" in raw.lower():
            return {"$numVal": float(raw)}
        return {"$numVal": int(raw)}

    def hex_literal(self, items: list[Any]) -> dict[str, Any]:
        return {"$hexVal": str(items[0])}

    def bool_literal(self, items: list[Any]) -> dict[str, Any]:
        return {"$boolean": str(items[0]).lower() == "true"}

    def date_time_literal(self, items: list[Any]) -> dict[str, Any]:
        return {"$dateTimeVal": str(items[0])}

    def time_literal(self, items: list[Any]) -> dict[str, Any]:
        return {"$timeVal": str(items[0])}

    def cast_to_string_expr(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$strCast": compact[0]}

    def cast_to_numerical_expr(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$numCast": compact[0]}

    def cast_to_hex_expr(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$hexCast": compact[0]}

    def cast_to_bool_expr(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$boolCast": compact[0]}

    def cast_to_date_time_expr(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$dateTimeCast": compact[0]}

    def cast_to_time_expr(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$timeCast": compact[0]}

    def date_part_expr(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {str(compact[0]): compact[1]}

    def single_attribute(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return compact[0]

    def claim_attribute(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$attribute": {"CLAIM": json.loads(str(compact[0]))}}

    def global_attribute(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$attribute": {"GLOBAL": str(compact[0])}}

    def reference_attribute(self, items: list[Any]) -> dict[str, Any]:
        compact = self._compact(items)
        return {"$attribute": {"REFERENCE": json.loads(str(compact[0]))}}

    def ws(self, _items: list[Any]) -> None:
        return None

    def REQUIRED_WS(self, _token: Any) -> None:
        return None

    def all_access_permission_rules(self, _items: list[Any]) -> dict[str, Any]:
        raise AASQLPipelineError("AllAccessPermissionRules parsing is not implemented in this converter yet")

    def OP(self, token: Any) -> str:
        return str(token)

    def EQ_NE(self, token: Any) -> str:
        return str(token)

    def STR_FN(self, token: Any) -> str:
        return str(token)

    def DATE_FN(self, token: Any) -> str:
        return str(token)

    def FIELD(self, token: Any) -> str:
        return str(token)


@dataclass
class _FieldBinding:
    var: str
    patterns: list[str]


@dataclass
class _SparqlContext:
    where_patterns: set[str] = field(default_factory=set)
    used_vars: set[str] = field(default_factory=set)
    match_scope_stack: list[dict[str, str]] = field(default_factory=list)

    def bind_field(self, field_name: str) -> str:
        binding = _field_binding(field_name, self)
        self.where_patterns.update(binding.patterns)
        self.used_vars.add(binding.var)
        return binding.var

    def push_match_scope(self) -> None:
        self.match_scope_stack.append({})

    def pop_match_scope(self) -> None:
        if self.match_scope_stack:
            self.match_scope_stack.pop()

    def get_scoped_var(self, scope: str) -> str | None:
        for scope_map in reversed(self.match_scope_stack):
            if scope in scope_map:
                return scope_map[scope]
        return None

    def set_scoped_var(self, scope: str, var_name: str) -> None:
        if not self.match_scope_stack:
            self.push_match_scope()
        self.match_scope_stack[-1][scope] = var_name


def _sanitize_var_name(field_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", field_name.lstrip("$"))
    return f"?{cleaned}"


def _split_field_identifier(field_name: str) -> tuple[str, str]:
    if "#" not in field_name:
        raise AASQLPipelineError(f"Invalid field identifier: {field_name}")
    return field_name.split("#", 1)


def _split_segment(segment: str) -> tuple[str, str | int | None]:
    if segment.endswith("[]"):
        return segment[:-2], "any"

    indexed_match = re.match(r"^(.+)\[(\d+)\]$", segment)
    if indexed_match:
        return indexed_match.group(1), int(indexed_match.group(2))

    return segment, None


def _field_list_prefix(field_name: str) -> str | None:
    match = re.search(r"\[\]", field_name)
    if not match:
        return None
    return field_name[: match.end()]


def _collect_field_refs(expr: dict[str, Any]) -> list[str]:
    refs: list[str] = []

    if "$field" in expr:
        return [expr["$field"]]

    for key in ("$and", "$or", "$match"):
        if key in expr:
            for item in expr[key]:
                refs.extend(_collect_field_refs(item))
            return refs

    if "$not" in expr:
        refs.extend(_collect_field_refs(expr["$not"]))
        return refs

    binary_keys = (
        "$eq",
        "$ne",
        "$gt",
        "$ge",
        "$lt",
        "$le",
        "$contains",
        "$starts-with",
        "$ends-with",
        "$regex",
    )
    for key in binary_keys:
        if key in expr:
            for item in expr[key]:
                if isinstance(item, dict):
                    refs.extend(_collect_field_refs(item))
            return refs

    unary_keys = (
        "$strCast",
        "$numCast",
        "$hexCast",
        "$boolCast",
        "$dateTimeCast",
        "$timeCast",
        "$dayOfWeek",
        "$dayOfMonth",
        "$month",
        "$year",
    )
    for key in unary_keys:
        if key in expr and isinstance(expr[key], dict):
            refs.extend(_collect_field_refs(expr[key]))
            return refs

    return refs


def _validate_match_semantics(expr: dict[str, Any], inherited_scope: str | None = None) -> None:
    if "$match" in expr:
        items = expr["$match"]
        local_scope = inherited_scope
        direct_scopes: set[str] = set()

        for item in items:
            if any(op in item for op in ("$and", "$or", "$not")):
                raise AASQLPipelineError("$match can include only comparisons and nested $match expressions")

            if "$match" in item:
                continue

            for field_ref in _collect_field_refs(item):
                list_prefix = _field_list_prefix(field_ref)
                if list_prefix:
                    direct_scopes.add(list_prefix)

        if local_scope is None and direct_scopes:
            if len(direct_scopes) > 1:
                raise AASQLPipelineError(
                    "All [] path expressions inside one $match must share the same first list prefix"
                )
            local_scope = next(iter(direct_scopes))

        if local_scope:
            for item in items:
                if "$match" in item:
                    _validate_match_semantics(item, local_scope)
                    continue

                for field_ref in _collect_field_refs(item):
                    list_prefix = _field_list_prefix(field_ref)
                    if list_prefix and not list_prefix.startswith(local_scope):
                        raise AASQLPipelineError(
                            "A [] path expression inside $match must point to the list under consideration"
                        )
            return

    if "$and" in expr:
        for item in expr["$and"]:
            _validate_match_semantics(item, inherited_scope)
    elif "$or" in expr:
        for item in expr["$or"]:
            _validate_match_semantics(item, inherited_scope)
    elif "$not" in expr:
        _validate_match_semantics(expr["$not"], inherited_scope)


def _field_binding(field_name: str, ctx: _SparqlContext) -> _FieldBinding:
    var_name = _sanitize_var_name(field_name)

    field_map: dict[str, list[str]] = {
        "$aas#id": ["?aas a aas:AssetAdministrationShell", f"?aas aas:id {var_name}"],
        "$aas#idShort": ["?aas a aas:AssetAdministrationShell", f"?aas aas:idShort {var_name}"],
        "$aas#assetInformation.assetKind": [
            "?aas a aas:AssetAdministrationShell",
            f"?aas aas:assetInformation/aas:assetKind {var_name}",
        ],
        "$aas#assetInformation.assetType": [
            "?aas a aas:AssetAdministrationShell",
            f"?aas aas:assetInformation/aas:assetType {var_name}",
        ],
        "$aas#assetInformation.globalAssetId": [
            "?aas a aas:AssetAdministrationShell",
            f"?aas aas:assetInformation/aas:globalAssetId {var_name}",
        ],
        "$sm#id": ["?sm a aas:Submodel", f"?sm aas:id {var_name}"],
        "$sm#idShort": ["?sm a aas:Submodel", f"?sm aas:idShort {var_name}"],
        "$sm#semanticId": ["?sm a aas:Submodel", f"?sm aas:semanticId/aas:key/aas:value {var_name}"],
        "$cd#id": ["?cd a aas:ConceptDescription", f"?cd aas:id {var_name}"],
        "$cd#idShort": ["?cd a aas:ConceptDescription", f"?cd aas:idShort {var_name}"],
        "$aasdesc#id": ["?aas a aas:AssetAdministrationShell", f"?aas aas:id {var_name}"],
        "$aasdesc#idShort": ["?aas a aas:AssetAdministrationShell", f"?aas aas:idShort {var_name}"],
        "$aasdesc#assetKind": [
            "?aas a aas:AssetAdministrationShell",
            f"?aas aas:assetInformation/aas:assetKind {var_name}",
        ],
        "$aasdesc#globalAssetId": [
            "?aas a aas:AssetAdministrationShell",
            f"?aas aas:assetInformation/aas:globalAssetId {var_name}",
        ],
        "$smdesc#id": ["?sm a aas:Submodel", f"?sm aas:id {var_name}"],
        "$smdesc#idShort": ["?sm a aas:Submodel", f"?sm aas:idShort {var_name}"],
        "$smdesc#semanticId": ["?sm a aas:Submodel", f"?sm aas:semanticId/aas:key/aas:value {var_name}"],
        "$sme#idShort": [
            "?sm a aas:Submodel",
            "?sm (aas:submodelElement|aas:submodelElement/aas:value*) ?sme",
            f"?sme aas:idShort {var_name}",
        ],
        "$sme#semanticId": [
            "?sm a aas:Submodel",
            "?sm (aas:submodelElement|aas:submodelElement/aas:value*) ?sme",
            f"?sme aas:semanticId/aas:key/aas:value {var_name}",
        ],
        "$sme#value": [
            "?sm a aas:Submodel",
            "?sm (aas:submodelElement|aas:submodelElement/aas:value*) ?sme",
            f"?sme aas:value {var_name}",
        ],
    }

    if field_name in field_map:
        return _FieldBinding(var=var_name, patterns=field_map[field_name])

    if field_name.startswith("$sme"):
        root, leaf = _split_field_identifier(field_name)
        path_part = root[len("$sme"):].lstrip(".")
        segments = [seg for seg in path_part.split(".") if seg] if path_part else []

        patterns: list[str] = [
            "?sm a aas:Submodel",
            "?sm (aas:submodelElement|aas:submodelElement/aas:value*) ?sme_root",
        ]

        current_var = "?sme_root"
        consumed_segments: list[str] = []

        for idx, segment in enumerate(segments):
            segment_name, segment_index = _split_segment(segment)
            next_var = f"?sme_path_{idx + 1}"

            patterns.append(f"{current_var} aas:value {next_var}")
            patterns.append(f'{next_var} aas:idShort "{segment_name}"')

            if isinstance(segment_index, int):
                patterns.append(f"{next_var} aas:index {segment_index}")

            consumed_segments.append(segment)
            if segment_index == "any":
                scope_expr = f"$sme.{'.'.join(consumed_segments)}"
                existing_var = ctx.get_scoped_var(scope_expr)
                if existing_var:
                    patterns.append(f"FILTER({next_var} = {existing_var})")
                    next_var = existing_var
                else:
                    ctx.set_scoped_var(scope_expr, next_var)

            current_var = next_var

        leaf_map = {
            "value": "aas:value",
            "idShort": "aas:idShort",
            "semanticId": "aas:semanticId/aas:key/aas:value",
            "valueType": "aas:valueType",
            "language": "aas:language",
            "id": "aas:id",
        }
        if leaf not in leaf_map:
            raise AASQLPipelineError(f"Unsupported SME leaf field: {leaf}")

        patterns.append(f"{current_var} {leaf_map[leaf]} {var_name}")
        return _FieldBinding(var=var_name, patterns=patterns)

    if field_name.startswith("$aas#") and "specificAssetIds" in field_name:
        _root, leaf = _split_field_identifier(field_name)

        patterns = [
            "?aas a aas:AssetAdministrationShell",
            "?aas aas:assetInformation ?aas_asset_info",
            "?aas_asset_info (aas:specificAssetId|aas:specificAssetIds) ?aas_specific_asset_id",
        ]

        list_scope = "$aas#assetInformation.specificAssetIds[]"
        existing_scope_var = ctx.get_scoped_var(list_scope)
        if existing_scope_var:
            patterns.append(f"FILTER(?aas_specific_asset_id = {existing_scope_var})")
        else:
            ctx.set_scoped_var(list_scope, "?aas_specific_asset_id")

        leaf_map = {
            "assetInformation.specificAssetIds[].name": "aas:name",
            "assetInformation.specificAssetIds[].value": "aas:value",
            "assetInformation.specificAssetIds[].externalSubjectId": "aas:externalSubjectId",
        }
        if leaf not in leaf_map:
            raise AASQLPipelineError(f"Unsupported AAS specificAssetIds leaf field: {leaf}")

        patterns.append(f"?aas_specific_asset_id {leaf_map[leaf]} {var_name}")
        return _FieldBinding(var=var_name, patterns=patterns)

    if field_name.startswith("$aas#submodels"):
        _root, path = _split_field_identifier(field_name)
        patterns = ["?aas a aas:AssetAdministrationShell"]

        sub_ref_scope = "$aas#submodels[]"
        existing_sub_ref = ctx.get_scoped_var(sub_ref_scope)
        if existing_sub_ref:
            sub_ref_var = existing_sub_ref
        else:
            sub_ref_var = "?aas_sub_ref"
            ctx.set_scoped_var(sub_ref_scope, sub_ref_var)
        patterns.append(f"?aas aas:submodel {sub_ref_var}")

        if path == "submodels[].type":
            patterns.append(f"{sub_ref_var} aas:type {var_name}")
            return _FieldBinding(var=var_name, patterns=patterns)

        if path.startswith("submodels[].keys[]."):
            key_scope = "$aas#submodels[].keys[]"
            existing_key = ctx.get_scoped_var(key_scope)
            if existing_key:
                key_var = existing_key
            else:
                key_var = "?aas_sub_key"
                ctx.set_scoped_var(key_scope, key_var)
            patterns.append(f"{sub_ref_var} aas:key {key_var}")
            leaf = path[len("submodels[].keys[]."):]
            key_leaf_map = {"type": "aas:type", "value": "aas:value"}
            if leaf not in key_leaf_map:
                raise AASQLPipelineError(f"Unsupported AAS submodels keys leaf field: {leaf}")
            patterns.append(f"{key_var} {key_leaf_map[leaf]} {var_name}")
            return _FieldBinding(var=var_name, patterns=patterns)

        raise AASQLPipelineError(f"Unsupported AAS submodels path: {field_name}")

    raise AASQLPipelineError(f"Unsupported field identifier for SPARQL mapping: {field_name}")


def _value_to_sparql(value: dict[str, Any], ctx: _SparqlContext) -> str:
    if "$field" in value:
        return ctx.bind_field(value["$field"])

    if "$strVal" in value:
        return json.dumps(value["$strVal"]) + "^^xsd:string"
    if "$numVal" in value:
        return str(value["$numVal"])
    if "$hexVal" in value:
        return json.dumps(value["$hexVal"]) + "^^xsd:hexBinary"
    if "$dateTimeVal" in value:
        return json.dumps(value["$dateTimeVal"]) + "^^xsd:dateTime"
    if "$timeVal" in value:
        return json.dumps(value["$timeVal"]) + "^^xsd:time"
    if "$boolean" in value:
        return "true" if value["$boolean"] else "false"
    if "$attribute" in value:
        attr = value["$attribute"]
        if "GLOBAL" in attr and attr["GLOBAL"] in {"LOCALNOW", "UTCNOW", "CLIENTNOW"}:
            return "NOW()"
        raise AASQLPipelineError("Only GLOBAL time attributes are supported in SPARQL conversion")

    cast_map = {
        "$strCast": "STR",
        "$numCast": "xsd:decimal",
        "$hexCast": "xsd:hexBinary",
        "$boolCast": "xsd:boolean",
        "$dateTimeCast": "xsd:dateTime",
        "$timeCast": "xsd:time",
    }
    for key, fn_name in cast_map.items():
        if key in value:
            nested = _value_to_sparql(value[key], ctx)
            return f"{fn_name}({nested})"

    date_fn_map = {
        "$dayOfWeek": "DAYOFWEEK",
        "$dayOfMonth": "DAY",
        "$month": "MONTH",
        "$year": "YEAR",
    }
    for key, fn_name in date_fn_map.items():
        if key in value:
            nested = _value_to_sparql(value[key], ctx)
            return f"{fn_name}({nested})"

    raise AASQLPipelineError(f"Unsupported value expression: {value}")


def _expr_to_filter(expr: dict[str, Any], ctx: _SparqlContext) -> str:
    if "$and" in expr:
        return "(" + " && ".join(_expr_to_filter(item, ctx) for item in expr["$and"]) + ")"
    if "$or" in expr:
        return "(" + " || ".join(_expr_to_filter(item, ctx) for item in expr["$or"]) + ")"
    if "$not" in expr:
        return f"(!{_expr_to_filter(expr['$not'], ctx)})"
    if "$match" in expr:
        ctx.push_match_scope()
        try:
            return "(" + " && ".join(_expr_to_filter(item, ctx) for item in expr["$match"]) + ")"
        finally:
            ctx.pop_match_scope()
    if "$boolean" in expr:
        return "true" if expr["$boolean"] else "false"

    binary_ops = {
        "$eq": "=",
        "$ne": "!=",
        "$gt": ">",
        "$ge": ">=",
        "$lt": "<",
        "$le": "<=",
    }
    for op, sparql_op in binary_ops.items():
        if op in expr:
            left, right = expr[op]
            return f"({_value_to_sparql(left, ctx)} {sparql_op} {_value_to_sparql(right, ctx)})"

    if "$contains" in expr:
        left, right = expr["$contains"]
        return f"CONTAINS(STR({_value_to_sparql(left, ctx)}), STR({_value_to_sparql(right, ctx)}))"
    if "$starts-with" in expr:
        left, right = expr["$starts-with"]
        return f"STRSTARTS(STR({_value_to_sparql(left, ctx)}), STR({_value_to_sparql(right, ctx)}))"
    if "$ends-with" in expr:
        left, right = expr["$ends-with"]
        return f"STRENDS(STR({_value_to_sparql(left, ctx)}), STR({_value_to_sparql(right, ctx)}))"
    if "$regex" in expr:
        left, right = expr["$regex"]
        return f"REGEX(STR({_value_to_sparql(left, ctx)}), STR({_value_to_sparql(right, ctx)}))"

    raise AASQLPipelineError(f"Unsupported logical expression: {expr}")


def _parse_aasql_tree(query_text: str) -> Tree[Any]:
    try:
        return _parser.parse(query_text)
    except Exception as exc:
        raise AASQLPipelineError(f"AASQL grammar parse failed: {exc}") from exc


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def aasql_text_to_parse_tree_artifacts(query_text: str) -> tuple[str, str]:
    tree = _parse_aasql_tree(query_text)
    tree_text = tree.pretty()

    lines = ["digraph G {", "rankdir=TB;"]
    node_counter = 0
    palette = ["#f198eb", "#91eda9", "#9ec9ff", "#ffd480", "#c6b7ff", "#ffb8b8"]

    def add_node(node: Any, parent_id: int | None, depth: int) -> int:
        nonlocal node_counter
        node_id = node_counter
        node_counter += 1

        if isinstance(node, Tree):
            label = _dot_escape(str(node.data))
            color = palette[depth % len(palette)]
            lines.append(f'{node_id} [style=filled, fillcolor="{color}", label="{label}"];')
        elif isinstance(node, Token):
            token_text = f"Token('{node.type}', {node.value!r})"
            lines.append(f'{node_id} [label="{_dot_escape(token_text)}"];')
        else:
            lines.append(f'{node_id} [label="{_dot_escape(repr(node))}"];')

        if parent_id is not None:
            lines.append(f"{parent_id} -> {node_id};")

        if isinstance(node, Tree):
            for child in node.children:
                add_node(child, node_id, depth + 1)

        return node_id

    add_node(tree, None, 0)
    lines.append("}")
    return tree_text, "\n".join(lines)


def parse_aasql_text_to_json(query_text: str) -> dict[str, Any]:
    tree = _parse_aasql_tree(query_text)
    parsed = _TreeToJson().transform(tree)

    if not isinstance(parsed, dict):
        raise AASQLPipelineError("AASQL parse result was not an object")
    return parsed


def validate_aasql_json(payload: dict[str, Any]) -> dict[str, Any]:
    root = payload
    if "$condition" in root or "$select" in root:
        root = {"Query": root}

    errors = sorted(_validator.iter_errors(root), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        path = ".".join(str(p) for p in first.path)
        path_msg = f" at '{path}'" if path else ""
        raise AASQLPipelineError(f"AASQL JSON schema validation failed{path_msg}: {first.message}")

    if "Query" in root:
        query_obj = root["Query"]
        if not isinstance(query_obj, dict):
            raise AASQLPipelineError("'Query' must be an object")
        _validate_match_semantics(query_obj["$condition"])

    return root


def aasql_json_to_sparql(payload: dict[str, Any]) -> str:
    root = validate_aasql_json(payload)
    if "AllAccessPermissionRules" in root:
        raise AASQLPipelineError("AllAccessPermissionRules are validated but not convertible to SPARQL")

    query_obj = root["Query"]
    condition = query_obj["$condition"]

    ctx = _SparqlContext()
    filter_expr = _expr_to_filter(condition, ctx)

    where_lines = sorted(ctx.where_patterns)
    if not where_lines:
        where_lines = ["?aas a aas:AssetAdministrationShell"]

    query_lines = [
        "PREFIX aas: <https://admin-shell.io/aas/3/>",
        "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>",
        "",
    ]

    if query_obj.get("$select") == "id":
        if "?aas_id" not in ctx.used_vars:
            where_lines.append("?aas a aas:AssetAdministrationShell")
            where_lines.append("?aas aas:id ?aas_id")
        query_lines.append("SELECT DISTINCT ?id WHERE {")
        query_lines.extend(f"  {line} ." for line in dict.fromkeys(where_lines))
        query_lines.append("  BIND(?aas_id AS ?id)")
        query_lines.append(f"  FILTER({filter_expr})")
        query_lines.append("}")
        return "\n".join(query_lines)

    query_lines.append("SELECT DISTINCT * WHERE {")
    query_lines.extend(f"  {line} ." for line in dict.fromkeys(where_lines))
    query_lines.append(f"  FILTER({filter_expr})")
    query_lines.append("}")
    return "\n".join(query_lines)


def aasql_text_to_sparql(query_text: str) -> tuple[dict[str, Any], str]:
    query_json = parse_aasql_text_to_json(query_text)
    validated = validate_aasql_json(query_json)
    sparql = aasql_json_to_sparql(validated)
    return validated, sparql
