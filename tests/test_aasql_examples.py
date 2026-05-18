import pytest

from app.aasql_pipeline import aasql_json_to_sparql, parse_aasql_text_to_json, validate_aasql_json


EXAMPLES = [
    (
        "single comparison",
        "$aas#idShort $eq $aas#assetInformation.assetType",
        {
            "$eq": [
                {"$field": "$aas#idShort"},
                {"$field": "$aas#assetInformation.assetType"},
            ]
        },
    ),
    (
        "handover documentation",
        """
        $match(
          $sme.Documents[].DocumentClassification.Class#value $eq "03-01",
          $sme.Documents[].DocumentVersion.SMLLanguages[]#language $eq "nl"
        )
        """,
        {
            "$match": [
                {
                    "$eq": [
                        {"$field": "$sme.Documents[].DocumentClassification.Class#value"},
                        {"$strVal": "03-01"},
                    ]
                },
                {
                    "$eq": [
                        {"$field": "$sme.Documents[].DocumentVersion.SMLLanguages[]#language"},
                        {"$strVal": "nl"},
                    ]
                },
            ]
        },
    ),
    (
        "technical data",
        """
        $and(
          $match(
            $sm#idShort $eq "TechnicalData",
            $sme.ProductClassifications[].ProductClassId#value $eq "27-37-09-05"
          ),
          $match(
            $sm#idShort $eq "TechnicalData",
            $sme#semanticId $eq "0173-1#02-BAF016#006",
            $sme#value $lt 100
          )
        )
        """,
        {
            "$and": [
                {
                    "$match": [
                        {
                            "$eq": [
                                {"$field": "$sm#idShort"},
                                {"$strVal": "TechnicalData"},
                            ]
                        },
                        {
                            "$eq": [
                                {"$field": "$sme.ProductClassifications[].ProductClassId#value"},
                                {"$strVal": "27-37-09-05"},
                            ]
                        },
                    ]
                },
                {
                    "$match": [
                        {
                            "$eq": [
                                {"$field": "$sm#idShort"},
                                {"$strVal": "TechnicalData"},
                            ]
                        },
                        {
                            "$eq": [
                                {"$field": "$sme#semanticId"},
                                {"$strVal": "0173-1#02-BAF016#006"},
                            ]
                        },
                        {
                            "$lt": [
                                {"$field": "$sme#value"},
                                {"$numVal": 100},
                            ]
                        },
                    ]
                },
            ]
        },
    ),
    (
        "match specificAssetIds",
        """
        $or(
          $match(
            $aas#assetInformation.specificAssetIds[].name $eq "supplierId",
            $aas#assetInformation.specificAssetIds[].value $eq "aas-1"
          ),
          $match(
            $aas#assetInformation.specificAssetIds[].name $eq "customerId",
            $aas#assetInformation.specificAssetIds[].value $eq "aas-2"
          )
        )
        """,
        {
            "$or": [
                {
                    "$match": [
                        {
                            "$eq": [
                                {"$field": "$aas#assetInformation.specificAssetIds[].name"},
                                {"$strVal": "supplierId"},
                            ]
                        },
                        {
                            "$eq": [
                                {"$field": "$aas#assetInformation.specificAssetIds[].value"},
                                {"$strVal": "aas-1"},
                            ]
                        },
                    ]
                },
                {
                    "$match": [
                        {
                            "$eq": [
                                {"$field": "$aas#assetInformation.specificAssetIds[].name"},
                                {"$strVal": "customerId"},
                            ]
                        },
                        {
                            "$eq": [
                                {"$field": "$aas#assetInformation.specificAssetIds[].value"},
                                {"$strVal": "aas-2"},
                            ]
                        },
                    ]
                },
            ]
        },
    ),
]


@pytest.mark.parametrize("_name, grammar_query, expected_condition", EXAMPLES)
def test_grammar_to_json_examples(_name: str, grammar_query: str, expected_condition: dict) -> None:
    parsed = parse_aasql_text_to_json(grammar_query)
    assert parsed == {"Query": {"$condition": expected_condition}}


@pytest.mark.parametrize("_name, _grammar_query, expected_condition", EXAMPLES)
def test_schema_validation_examples_flat_payload(_name: str, _grammar_query: str, expected_condition: dict) -> None:
    validated = validate_aasql_json({"$condition": expected_condition})
    assert validated == {"Query": {"$condition": expected_condition}}


@pytest.mark.parametrize("_name, _grammar_query, expected_condition", EXAMPLES)
def test_schema_validation_examples_query_payload(_name: str, _grammar_query: str, expected_condition: dict) -> None:
    validated = validate_aasql_json({"Query": {"$condition": expected_condition}})
    assert validated == {"Query": {"$condition": expected_condition}}


@pytest.mark.parametrize("_name, _grammar_query, expected_condition", EXAMPLES)
def test_examples_convert_to_sparql(_name: str, _grammar_query: str, expected_condition: dict) -> None:
    sparql = aasql_json_to_sparql({"$condition": expected_condition})
    assert "SELECT DISTINCT * WHERE" in sparql
    assert "FILTER(" in sparql
