import json
import argparse
from pathlib import Path
from collections import defaultdict
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate

# Maps spaCy labels to broader entity categories
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

# Prompt to canonicalize and group global entities
PROMPT_TEMPLATE = """
You are a literary assistant helping canonicalize entities across an entire novel.

Given a list of extracted named entities grouped by type, identify canonical entity names and group any aliases or variations.

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

def collect_global_entities(chapters):
    grouped = defaultdict(set)
    for ch in chapters:
        for ent_type, values in ch.get("entities", {}).items():
            unified_type = ENTITY_TYPE_MAP.get(ent_type, ent_type.title())
            for val in values:
                grouped[unified_type].add(val.strip())
    return {k: sorted(v) for k, v in grouped.items()}

def canonicalize_entities_ollama(global_entities, model="llama3"):
    llm = Ollama(model=model)
    prompt_template = PromptTemplate.from_template(PROMPT_TEMPLATE)
    entity_input = "\n".join([f"{etype}: {', '.join(aliases)}" for etype, aliases in global_entities.items()])
    full_prompt = prompt_template.format(entity_input=entity_input)

    result = llm.invoke(full_prompt)
    try:
        json_start = result.index("[")
        json_end = result.rindex("]") + 1
        return json.loads(result[json_start:json_end])
    except Exception as e:
        raise ValueError(f"Failed to parse JSON output:\n\n{result}") from e

def assign_ids(canonical_entities):
    counts = defaultdict(int)
    for ent in canonical_entities:
        prefix = ent["type"].upper().replace(" ", "_")
        counts[prefix] += 1
        ent["id"] = f"{prefix}_{counts[prefix]:03d}"
    return canonical_entities

def main():
    parser = argparse.ArgumentParser(description="Canonicalize and index entities across chapters.")
    parser.add_argument("input", help="Path to full book JSON (with chapters and entities)")
    parser.add_argument("--output", "-o", help="Output path for enriched global entity list")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    chapters = data.get("chapters", [])

    global_entities = collect_global_entities(chapters)
    canonical = canonicalize_entities_ollama(global_entities)
    enriched = assign_ids(canonical)

    if args.output:
        Path(args.output).write_text(json.dumps(enriched, indent=2), encoding="utf-8")
        print(f"[✓] Canonicalized entity registry saved to {args.output}")
    else:
        print(json.dumps(enriched, indent=2))

if __name__ == "__main__":
    main()
