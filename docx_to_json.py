import re
import json
import argparse
from docx import Document
from pathlib import Path
from typing import List, Dict, Optional

def parse_heading(text: str) -> Optional[Dict]:
    """Parse a heading of format 'Chapter 1: Title' into number and title."""
    print(f"[DEBUG] Parsing heading: {text}")  # Debug output
    match = re.match(r"Chapter\s+(\d+)\s*:\s*(.+)", text, re.IGNORECASE)
    if not match:
        return None
    return {
        "number": int(match.group(1)),
        "title": match.group(2).strip()
    }

def split_docx_by_heading(path: str, heading_level: str = "Heading") -> List[Dict]:
    doc = Document(path)
    chapters = []
    current = None
    book_title = None

    for para in doc.paragraphs:
        style = para.style.name
        text = para.text.strip()
        if not style.startswith("Body"):
            print(f"[DEBUG] Style: {style}, Text: {text}")  # Debug output
        if not text:
            continue
        if style == "Title":
            book_title = text
            continue
        
        if style == heading_level:
            if text == "":
                continue
            heading_info = parse_heading(text)
            if heading_info:
                # Save the previous chapter
                if current:
                    chapters.append(current)

                current = {
                    "number": heading_info["number"],
                    "title": heading_info["title"],
                    "paragraphs": []
                }
        elif current:
            current["paragraphs"].append(text)

    # Add the last chapter if one is still open
    if current:
        chapters.append(current)

    return book_title, chapters

def main():
    parser = argparse.ArgumentParser(description="Split DOCX into chapter JSON using H2 headers.")
    parser.add_argument("input", type=str, help="Path to .docx file")
    parser.add_argument("--output", "-o", type=str, help="Path to output .json file")
    parser.add_argument("--level", "-l", type=str, default="Heading", help="Heading style to split on (default: Heading 2)")
    args = parser.parse_args()

    book_title, chapters = split_docx_by_heading(args.input, heading_level=args.level)
    book_dict = {
        "book_title": book_title,
        "chapters": chapters
    }
    if args.output:
        Path(args.output).write_text(json.dumps(book_dict, indent=2), encoding="utf-8")
        print(f"[✓] Chapters written to {args.output}")
    else:
        print(json.dumps(chapters, indent=2))


if __name__ == "__main__":
    main()