import json
import csv
import argparse
from pathlib import Path
from typing import List, Dict


def sanitize(text: str) -> str:
    return text.replace("\n", " ").replace("\"", "'").strip()


def write_csv(path: Path, rows: List[Dict], headers: List[str]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def export_to_neo4j_csv(book_path: str, output_dir: str):
    data = json.loads(Path(book_path).read_text(encoding="utf-8"))
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    entity_types = {}
    for ent in data["global_entities"]:
        etype = ent["type"].lower()
        entity_types.setdefault(etype, []).append(ent)

    # Write entity nodes
    for etype, entries in entity_types.items():
        rows = []
        for ent in entries:
            rows.append({
                f"id:ID({etype.capitalize()})": ent["id"],
                "canonical_name": ent["canonical_name"],
                "aliases:string[]": "|".join(ent.get("aliases", []))
            })
        write_csv(Path(output_dir) / f"nodes_{etype}s.csv", rows, list(rows[0].keys()))

    # Write chapter nodes
    chapter_rows = []
    paragraph_rows = []
    mentions = []
    part_of = []

    for chapter in data["chapters"]:
        cid = f"CH{chapter['number']}"
        chapter_rows.append({
            "id:ID(Chapter)": cid,
            "title": chapter["title"],
            "number:int": chapter["number"]
        })

        for i, para in enumerate(chapter["paragraphs"]):
            pid = f"{cid}_P{i}"
            paragraph_rows.append({
                "id:ID(Paragraph)": pid,
                "text": sanitize(para)
            })
            part_of.append({
                ":START_ID(Paragraph)": pid,
                ":END_ID(Chapter)": cid,
                ":TYPE": "PART_OF"
            })

        for em in chapter.get("entity_mentions", []):
            pid = f"{cid}_P{em['paragraph_index']}"
            for eid in em.get("entities", []):
                mentions.append({
                    ":START_ID(Paragraph)": pid,
                    ":END_ID": eid,
                    ":TYPE": "MENTIONS"
                })

    write_csv(Path(output_dir) / "nodes_chapters.csv", chapter_rows, list(chapter_rows[0].keys()))
    write_csv(Path(output_dir) / "nodes_paragraphs.csv", paragraph_rows, list(paragraph_rows[0].keys()))
    write_csv(Path(output_dir) / "rels_part_of.csv", part_of, list(part_of[0].keys()))
    write_csv(Path(output_dir) / "rels_mentions.csv", mentions, list(mentions[0].keys()))

    print(f"[✓] Exported Neo4j CSVs to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export structured novel JSON to Neo4j-compatible CSVs.")
    parser.add_argument("input", help="Path to the full structured novel JSON file")
    parser.add_argument("--out", "-o", required=True, help="Directory to write CSVs")
    args = parser.parse_args()

    export_to_neo4j_csv(args.input, args.out)
