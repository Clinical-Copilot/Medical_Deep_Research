import logging
import re
import requests

logger = logging.getLogger(__name__)

class BioPortalStandardizer:
    def __init__(self):
        self.api_key = "bf67e073-1a3e-40be-96ff-f66d3bbe113e"
        self.api_url = "https://data.bioontology.org/search"

    def standardize_query(self, query: str) -> tuple[list[str], str, list[str]]:
        headers = {"Authorization": f"apikey token={self.api_key}"}
        params = {
            "q": query,
            "require_exact_match": "false",
            "include": "prefLabel,synonym,cui",
            "ontologies": "SNOMEDCT,MESH,RXNORM,LNC",
            "pagesize": 50
        }

        response = requests.get(self.api_url, params=params, headers=headers, timeout=20)
        if response.status_code != 200:
            raise Exception(f"BioPortal API error: {response.status_code} - {response.text}")

        data = response.json()
        seen_ids = set()
        human_readable_concepts = []
        first_replacement = None

        for result in data.get("collection", []):
            label = result.get("prefLabel")
            id_uri = result.get("@id")
            synonyms = result.get("synonym", [])

            if not label or not id_uri:
                continue

            match = re.search(r"/ontology/([^/]+)/([^/]+)$", id_uri)
            if not match:
                continue
            ontology, concept_id = match.groups()
            readable = f"{label} ({ontology}:{concept_id})"

            if id_uri not in seen_ids:
                seen_ids.add(id_uri)
                human_readable_concepts.append(readable)

                for term in synonyms + [label]:
                    if not first_replacement and re.search(rf'\b{re.escape(term)}\b', query, flags=re.IGNORECASE):
                        first_replacement = (term, label)

        updated_query = query
        if first_replacement:
            term, label = first_replacement
            updated_query = re.sub(rf'\b{re.escape(term)}\b', label, query, flags=re.IGNORECASE)

        return list(seen_ids), updated_query, human_readable_concepts
