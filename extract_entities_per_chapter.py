import json
import argparse
import spacy
from pathlib import Path
from collections import defaultdict

def extract_entities(text: str, nlp) -> dict:
    doc = nlp(text)
    entities = defaultdict(set)

    for ent in doc.ents:
        entities[ent.label_].add(ent.text)

    # Convert sets to sorted lists
    return {label: sorted(list(values)) for label, values in entities.items()}

def process_chapters(chapter_json_path: str, model="en_core_web_sm") -> list:
    with open(chapter_json_path, 'r', encoding='utf-8') as f:
        book = json.load(f)

    chapters = book.get("chapters", [])
    book_title = book.get("book_title", "Unknown Book")
    
    nlp = spacy.load(model)
    enriched_chapters = []

    for chapter in chapters:
        full_text = "\n".join(chapter["paragraphs"])
        entities = extract_entities(full_text, nlp)

        enriched_chapters.append({
            "number": chapter["number"],
            "title": chapter["title"],
            "entities": entities,
            "paragraphs": chapter["paragraphs"]  # optional: remove if not needed
        })

    return { "book_title": book_title, "chapters": enriched_chapters }

def main():
    parser = argparse.ArgumentParser(description="Extract spaCy entities from chapter JSON.")
    parser.add_argument("input", type=str, help="Path to input chapters.json")
    parser.add_argument("--output", "-o", type=str, help="Output path for enriched chapters JSON")
    parser.add_argument("--model", "-m", type=str, default="en_core_web_sm", help="spaCy model to use (default: en_core_web_sm)")
    args = parser.parse_args()

    results = process_chapters(args.input, model=args.model)

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"[✓] Entity-enriched chapters written to {args.output}")
    else:
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()