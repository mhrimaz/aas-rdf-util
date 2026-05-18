from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JsonToRdfRequest(BaseModel):
    data: dict[str, Any]


class RdfToJsonRequest(BaseModel):
    turtle: str = Field(min_length=1)


class AASQLConvertRequest(BaseModel):
    query: str | None = None
    query_json: dict[str, Any] | None = None


class ConversionResponse(BaseModel):
    output: str


class AASQLParseTreeResponse(BaseModel):
    tree_text: str
    tree_dot: str
