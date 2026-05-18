from __future__ import annotations

from typing import Any

from rdflib import Graph, Namespace, RDF

from py_aas_rdf.models.aas_namespace import AASNameSpace
from py_aas_rdf.models.asset_administraion_shell import AssetAdministrationShell
from py_aas_rdf.models.concept_description import ConceptDescription
from py_aas_rdf.models.environment import Environment
from py_aas_rdf.models.submodel import Submodel


def json_to_rdf_turtle(payload: dict[str, Any]) -> str:
    graph: Graph

    model_type = payload.get("modelType")
    if model_type == "Submodel":
        graph, _ = Submodel(**payload).to_rdf()
    elif model_type == "ConceptDescription":
        graph, _ = ConceptDescription(**payload).to_rdf()
    elif model_type == "AssetAdministrationShell":
        graph, _ = AssetAdministrationShell(**payload).to_rdf()
    else:
        graph = Graph()
        graph, _ = Environment(**payload).to_rdf(graph)

    graph = graph.skolemize(authority="https://aas.metaphacts.com/aas/", basepath="/.well-known/genid/aas/")
    graph.bind("aas", Namespace("https://admin-shell.io/aas/3/"))
    graph.bind("aas-ex", Namespace("https://admin-shell.io/aas/3/extended/"))
    graph.bind(
        "aas-iec61360",
        Namespace("https://admin-shell.io/DataSpecificationTemplates/DataSpecificationIec61360/3/"),
    )

    return graph.serialize(format="turtle_custom", base="https://aas.metaphacts.com/aas/")


def rdf_turtle_to_json(turtle: str) -> str:
    graph = Graph().parse(data=turtle, format="turtle")

    env_subjects = list(graph.subjects(predicate=RDF.type, object=AASNameSpace.AAS_3["Environment"]))
    if env_subjects:
        return Environment.from_rdf(graph, env_subjects[0]).model_dump_json(exclude_none=True, indent=2)

    aas_subjects = list(graph.subjects(predicate=RDF.type, object=AASNameSpace.AAS_3["AssetAdministrationShell"]))
    if aas_subjects:
        return AssetAdministrationShell.from_rdf(graph, aas_subjects[0]).model_dump_json(exclude_none=True, indent=2)

    submodel_subjects = list(graph.subjects(predicate=RDF.type, object=AASNameSpace.AAS_3["Submodel"]))
    if submodel_subjects:
        return Submodel.from_rdf(graph, submodel_subjects[0]).model_dump_json(exclude_none=True, indent=2)

    concept_subjects = list(graph.subjects(predicate=RDF.type, object=AASNameSpace.AAS_3["ConceptDescription"]))
    if concept_subjects:
        return ConceptDescription.from_rdf(graph, concept_subjects[0]).model_dump_json(exclude_none=True, indent=2)

    raise ValueError("No known AAS resource type found in RDF graph")
