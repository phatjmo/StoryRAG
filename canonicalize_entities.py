import json
import argparse
from pathlib import Path
from langchain_ollama import ChatOllama, OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
from collections import defaultdict
from itertools import islice

ENTITY_TYPE_MAP = {
    "PERSON": "Character",
    "GPE": "Place",
    "LOC": "Place",
    "ORG": "Organization",
    "PRODUCT": "Item",
    "WORK_OF_ART": "Item",
    "DATE": "Date",
    "TIME": "Time",
    "MONEY": "Monetary Value",
    "NORP": "Group or Culture",
    "EVENT": "Event",
    "LAW": "Theme",
    "LANGUAGE": "Theme"
}

# List of entity types to exclude from canonicalization
EXCLUDE_TYPES = {"Date", "Time", "Monetary Value", "Ordinal", "Quantity", "Cardinal", "Percent"}

class EntityData(BaseModel):
    type: str = Field(
        description="The entity type, such as Character, Place, Item, Date, etc."
    )
    canonical_name: str = Field(
        description="The canonical name of the entity, which is the preferred name used in the text."
    )
    aliases: List[str] = Field(
        description="A list of alternative names or aliases for the entity."
    )
    
class EntitiesList(BaseModel):
    entities: List[EntityData] = Field(
        description="List of entities with their canonical names and aliases."
    )
    

# Prompt to canonicalize and group global entities
OLD_PROMPT_TEMPLATE = """
You are a literary assistant helping canonicalize entities from a novel.

Given a list of extracted named entities from a chapter, group them by meaning:
- Choose a `canonical_name` for each entity group
- Group any aliases or variants under `aliases`
- Retain the `type` (Character, Place, Item, Date, etc.)

Here is the data:

{entity_input}

Return a JSON array in this format:

{format_instructions}

Example Output:

[
  {{
    "type": "Character",
    "canonical_name": "Mattie Mae Albright",
    "aliases": ["Mattie", "Mattie Mae", "Matilda"]
  }},
  ...
]

Do not explain. Just return valid JSON.
"""

PROMPT_TEMPLATE = """
You are a literary assistant helping canonicalize entities across an entire novel.

Given a list of extracted named entities grouped by type, identify canonical entity names and group any aliases or variations.

Only use the input terms exactly as provided. Do not add new entities. Do not guess or invent names.

Return a JSON array with objects of the form:
[
  {{
    "type": "Character",
    "canonical_name": "Mattie Mae Albright",
    "aliases": ["Mattie", "Mattie Mae", "Matilda"]
  }},
  ...
]

Input:
{entity_input}

Only return valid JSON. No explanation.
"""

def batch(iterable, size):
    it = iter(iterable)
    while chunk := list(islice(it, size)):
        yield chunk

def deduplicate_aliases(entities):
    for ent in entities:
        ent["aliases"] = sorted(set(ent.get("aliases", [])))
    return entities

def assign_ids(canonical_entities):
    counts = defaultdict(int)
    for ent in canonical_entities:
        print(ent)
        prefix = ent["type"].upper().replace(" ", "_")
        counts[prefix] += 1
        ent["id"] = f"{prefix}_{counts[prefix]:03d}"
    return canonical_entities

def collect_global_entities(chapters):
    output = []
    seen = set()
    for ch in chapters:
        for ent_type, values in ch.get("entities", {}).items():
            unified_type = ENTITY_TYPE_MAP.get(ent_type, ent_type.title())
            if unified_type in EXCLUDE_TYPES:
                continue
            for val in values:
                key = (unified_type, val.strip())
                if key not in seen:
                    seen.add(key)
                    output.append({
                        "type": unified_type,
                        "value": val.strip()
                    })
    return output

def canonicalize_entities_ollama(global_entities: dict, model="llama3.2", batch_size=10) -> list:
    llm = ChatOllama(model=model, temperature=0, format='json') # OllamaLLM(model=model_name, temperature=0)
    parser = PydanticOutputParser(pydantic_object=EntitiesList)
    prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)
    grouped_by_type = defaultdict(list)
    deduped_entities = deduplicate_aliases(global_entities)
    for ent in deduped_entities:
        grouped_by_type[ent["type"]].append(ent["value"])
    results = []
    for etype, aliases in grouped_by_type.items():
      print(f"[+] Processing {etype} ({len(aliases)} values)...")
      for chunk in batch(aliases, batch_size):
        entity_input = f"{etype}: {', '.join(chunk)}"
        print(f"[LLM] Canonicalizing {entity_input}")
        full_prompt = prompt.format(entity_input=entity_input, format_instructions=parser.get_format_instructions())
        structured_llm = llm.with_structured_output(EntitiesList, method="json_schema")
        response = structured_llm.invoke(full_prompt)
        dict_response = response.model_dump(mode="json")
        results.extend(dict_response["entities"])
    print(f"[LLM] Canonicalized {len(results)} entities")
    merged = {}
    for ent in results:
        print(ent)
        key = (ent["type"].lower(), ent["canonical_name"].lower())
        if key not in merged:
            merged[key] = ent
        else:
            merged[key]["aliases"] = list(set(merged[key]["aliases"] + ent["aliases"]))
    return list(merged.values())

def main():
    parser = argparse.ArgumentParser(description="Canonicalize spaCy entity output using Ollama.")
    parser.add_argument("book_json", help="Path to JSON file containing chapters with spaCy entities.")
    parser.add_argument("--model", default="llama3.2", help="Ollama model to use.")
    parser.add_argument("--output", "-o", help="Optional path to save output JSON.")
    args = parser.parse_args()

    data = json.loads(Path(args.book_json).read_text(encoding="utf-8"))
    chapters = data.get("chapters", [data])  # support full book or single chapter
    
    global_entities = collect_global_entities(chapters)
    canonical = canonicalize_entities_ollama(global_entities, model=args.model, batch_size=10)
    print(canonical)
    enriched = assign_ids(canonical)   
    
    for ch in data["chapters"]:
      del ch["entities"]    
      
    data["global_entities"] = enriched
    
    if args.output:
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[✓] Canonicalized entity data saved to {args.output}")
    else:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()