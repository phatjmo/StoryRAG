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
import re

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
You are a literary assistant helping canonicalize entities from a novel.

Given a list of extracted named entities from a chapter, group them by meaning:
- Choose a `canonical_name` for each entity group
- Group any aliases or variants under `aliases`, use only the provided names, only match similar names or short forms
- Retain the `type` (Character, Place, Item, Date, etc.)

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
        if ent.get("aliases"):
            ent["aliases"] = [
              re.sub(r"'s\b", "", re.sub(r"[^\w\s]", "", alias.strip())) for alias in ent["aliases"]
            ]
            if ent["canonical_name"].strip() not in ent["aliases"]:
                ent["aliases"].append(ent["canonical_name"].strip())
            if len(ent["aliases"]) == 0:
                ent["aliases"].append(ent["canonical_name"].strip())
                continue
            if len(ent["aliases"]) == 1:
                continue
        ent["aliases"] = sorted(set(ent.get("aliases", [])))
    return entities
  
def filter_aliases_by_paragraphs(entities, chapters):
    """
    Filters aliases for each entity by checking if they exist in the paragraphs of each chapter.
    
    Args:
        entities (list): List of entities, each containing a "type", "canonical_name", and "aliases".
        chapters (list): List of chapters, each containing a "paragraphs" key with an array of strings.
    
    Returns:
        list: Updated list of entities with filtered aliases.
    """
    filtered_entities = []
    for entity in entities:
        if len(entity["canonical_name"]) < 3:
            print(f"[!] Skipping short canonical name '{entity['canonical_name']}' due to length.")
            continue
        if "aliases" in entity:
            filtered_aliases = []
            for alias in entity["aliases"]:
                if len(alias) < 3:
                    print(f"[!] Skipping short alias '{alias}' for entity '{entity['canonical_name']}' due to length.")
                    continue
                alias_found = any(
                    alias in paragraph for chapter in chapters for paragraph in chapter.get("paragraphs", [])
                )
                if alias_found:
                    print(f"[✓] Found alias '{alias}' in paragraphs.")
                    filtered_aliases.append(alias)

            if len(filtered_aliases) == 0:
              print(f"[!] No aliases remaining for entity '{entity['canonical_name']}', leaving out.")
            else:
              entity["aliases"] = filtered_aliases
              filtered_entities.append(entity)
              
        else:
            print(f"[!] No aliases found for entity '{entity['canonical_name']}'")     
    return filtered_entities

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
        # print(f"[LLM] Canonicalizing {entity_input}")
        full_prompt = prompt.format(entity_input=entity_input, format_instructions=parser.get_format_instructions())
        structured_llm = llm.with_structured_output(EntitiesList, method="json_schema")
        response = structured_llm.invoke(full_prompt)
        dict_response = response.model_dump(mode="json")
        results.extend(dict_response["entities"])
    # print(f"[LLM] Canonicalized {len(results)} entities")
    merged = {}
    for ent in results:
        # print(ent)
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
    # print(canonical)
    enriched = assign_ids(canonical)
    deduped_enriched = deduplicate_aliases(enriched)   
    filtered = filter_aliases_by_paragraphs(deduped_enriched, chapters)
    
    for ch in data["chapters"]:
      del ch["entities"]    
      
    data["global_entities"] = filtered
    
    if args.output:
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[✓] Canonicalized entity data saved to {args.output}")
    else:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()