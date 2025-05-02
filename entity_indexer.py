import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import re


def load_entity_registry(path: str) -> List[Dict]:
    with open(path, encoding='utf-8') as f:
        global_entity_source = json.load(f)
        global_entities = global_entity_source.get("global_entities", [])
        return global_entities


def build_alias_lookup(entities: List[Dict]) -> Tuple[Dict[str, str], Dict[str, str]]:
    alias_map = {}
    id_to_name = {}
    for ent in entities:
        for alias in ent.get("aliases", []):
            alias_map[alias.lower()] = ent["id"]
        alias_map[ent["canonical_name"].lower()] = ent["id"]
        id_to_name[ent["id"]] = ent["canonical_name"]
    return alias_map, id_to_name


def tag_paragraph(paragraph: str, alias_map: Dict[str, str], markdown_style=False) -> Tuple[str, List[str]]:
    found_ids = set()
    spans = sorted(alias_map.keys(), key=lambda x: -len(x))  # longest first
    matches = []

    for span in spans:
        pattern = re.compile(rf"({re.escape(span)})", re.IGNORECASE)
        for match in pattern.finditer(paragraph):
            start, end = match.span()

            # Ensure we're not inside existing tag
            if paragraph[max(0, start - 3):start] in ("[[", "["):
                continue

            # Ensure full word match (strict boundary check)
            char_before = paragraph[start - 1] if start > 0 else ' '
            char_after = paragraph[end] if end < len(paragraph) else ' '
            if char_before.isalpha() or char_after.isalpha():
                continue

            if any(s <= start < e or s < end <= e for s, e in matches):
                continue  # skip overlapping

            eid = alias_map[span]
            found_ids.add(eid)
            tag = f"[[{eid}]]" if markdown_style else f"[{eid}]"
            replacement = f"{match.group(1)} {tag}"
            paragraph = paragraph[:start] + replacement + paragraph[end:]
            matches.append((start, start + len(replacement)))

    return paragraph, sorted(found_ids)


def process_book_with_entities(book_path: str, entity_path: str, output_path: str, markdown_style=False):
    book = json.loads(Path(book_path).read_text(encoding='utf-8'))
    entity_list = load_entity_registry(entity_path)
    alias_map, id_to_name = build_alias_lookup(entity_list)

    for chapter in book.get("chapters", []):
        tagged = []
        mention_map = []
        for i, p in enumerate(chapter.get("paragraphs", [])):
            tagged_p, entity_ids = tag_paragraph(p, alias_map, markdown_style=markdown_style)
            tagged.append(tagged_p)
            mention_map.append({"paragraph_index": i, "entities": entity_ids})
        chapter["tagged_paragraphs"] = tagged
        chapter["entity_mentions"] = mention_map

    # Add entity list to book
    book["global_entities"] = entity_list
    Path(output_path).write_text(json.dumps(book, indent=2), encoding='utf-8')
    print(f"[✓] Tagged book written to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply canonical entity IDs into book paragraphs.")
    parser.add_argument("book", help="Path to original book JSON file")
    parser.add_argument("entities", help="Path to global canonical entity list")
    parser.add_argument("--output", "-o", required=True, help="Output path for tagged book")
    parser.add_argument("--markdown-style", action="store_true", help="Use [[ID]] markdown-style tags (e.g., Obsidian style)")
    args = parser.parse_args()

    # print(tag_paragraph("Mattie walked through Ganser Harbor with her father's watch.", {
    # "mattie": "CHAR_001",
    # "ganser harbor": "PLACE_002",
    # "watch": "ITEM_001"
    # }))
    
    process_book_with_entities(args.book, args.entities, args.output, markdown_style=args.markdown_style)
    