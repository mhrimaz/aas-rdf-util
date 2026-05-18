from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.aasql_pipeline import (
    AASQLPipelineError,
    aasql_json_to_sparql,
    aasql_text_to_parse_tree_artifacts,
    aasql_text_to_sparql,
    parse_aasql_text_to_json,
    validate_aasql_json,
)
from app.converters import json_to_rdf_turtle, rdf_turtle_to_json
from app.schemas import AASQLConvertRequest, AASQLParseTreeResponse, ConversionResponse, JsonToRdfRequest, RdfToJsonRequest


def _normalize_root_path(value: str | None) -> str:
    if not value:
        return ""
    stripped = value.strip()
    if not stripped or stripped == "/":
        return ""
    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    return stripped.rstrip("/")


FASTAPI_ROOT_PATH = _normalize_root_path(os.getenv("FASTAPI_ROOT_PATH"))

app = FastAPI(
    title="py-aas-rdf utility API",
    description="Convert AAS JSON to RDF, RDF to JSON, and AASQL/AASQL-JSON to SPARQL.",
    version="0.1.0",
    root_path=FASTAPI_ROOT_PATH,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/convert/json-to-rdf", response_model=ConversionResponse)
async def convert_json_to_rdf(request: JsonToRdfRequest) -> ConversionResponse:
    try:
        output = json_to_rdf_turtle(request.data)
        return ConversionResponse(output=output)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"JSON to RDF conversion failed: {exc}") from exc


@app.post("/api/convert/rdf-to-json", response_model=ConversionResponse)
async def convert_rdf_to_json(request: RdfToJsonRequest) -> ConversionResponse:
    try:
        output = rdf_turtle_to_json(request.turtle)
        return ConversionResponse(output=output)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"RDF to JSON conversion failed: {exc}") from exc


@app.post("/api/query/aasql-to-sparql", response_model=ConversionResponse)
async def convert_aasql_to_sparql(request: AASQLConvertRequest) -> ConversionResponse:
    if request.query_json is not None:
        try:
            validated = validate_aasql_json(request.query_json)
            return ConversionResponse(output=aasql_json_to_sparql(validated))
        except AASQLPipelineError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    query_text: str | None = request.query
    if not query_text:
        raise HTTPException(status_code=422, detail="Provide either 'query' or 'query_json'.")

    try:
        _, sparql = aasql_text_to_sparql(query_text)
        return ConversionResponse(output=sparql)
    except AASQLPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AASQL to SPARQL conversion failed: {exc}") from exc


@app.post("/api/query/aasql-to-json", response_model=ConversionResponse)
async def convert_aasql_to_json(request: AASQLConvertRequest) -> ConversionResponse:
    if not request.query:
        raise HTTPException(status_code=422, detail="Provide 'query' for AASQL text.")

    try:
        query_json = parse_aasql_text_to_json(request.query)
        validated = validate_aasql_json(query_json)
        return ConversionResponse(output=json.dumps(validated, indent=2, sort_keys=True))
    except AASQLPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AASQL to JSON conversion failed: {exc}") from exc


@app.post("/api/query/aasql-json-to-sparql", response_model=ConversionResponse)
async def convert_aasql_json_to_sparql(payload: dict[str, Any]) -> ConversionResponse:
    try:
        sparql = aasql_json_to_sparql(payload)
        return ConversionResponse(output=sparql)
    except AASQLPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AASQL JSON to SPARQL conversion failed: {exc}") from exc


@app.post("/api/query/aasql-parse-tree", response_model=AASQLParseTreeResponse)
async def aasql_parse_tree(request: AASQLConvertRequest) -> AASQLParseTreeResponse:
    if not request.query:
        raise HTTPException(status_code=422, detail="Provide 'query' for AASQL text.")

    try:
        tree_text, tree_dot = aasql_text_to_parse_tree_artifacts(request.query)
        return AASQLParseTreeResponse(tree_text=tree_text, tree_dot=tree_dot)
    except AASQLPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AASQL parse tree generation failed: {exc}") from exc


FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    def _render_index_html() -> HTMLResponse:
        index_file = FRONTEND_DIST / "index.html"
        html = index_file.read_text(encoding="utf-8")

        if FASTAPI_ROOT_PATH:
            html = html.replace('src="/assets/', f'src="{FASTAPI_ROOT_PATH}/assets/')
            html = html.replace('href="/assets/', f'href="{FASTAPI_ROOT_PATH}/assets/')

        config_script = f"<script>window.__APP_BASE_PATH__ = {json.dumps(FASTAPI_ROOT_PATH)};</script>"
        html = html.replace("</head>", f"{config_script}</head>")
        return HTMLResponse(content=html)

    @app.get("/", include_in_schema=False)
    async def frontend_index() -> HTMLResponse:
        return _render_index_html()

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def frontend_spa(full_path: str) -> Response:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        target = FRONTEND_DIST / full_path
        if full_path and target.exists() and target.is_file():
            return FileResponse(target)

        return _render_index_html()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
