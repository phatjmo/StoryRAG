import argparse
from docx import Document
from pathlib import Path

def docx_to_markdown(docx_path: str) -> str:
    document = Document(docx_path)
    md_lines = []

    for para in document.paragraphs:
        style = para.style.name
        text = para.text.strip()

        if not text:
            continue

        # Map heading levels
        if style.startswith("Heading"):
            level = style.replace("Heading", "").strip()
            if level.isdigit():
                md_lines.append(f"{'#' * int(level)} {text}")
            else:
                md_lines.append(f"## {text}")  # fallback
        else:
            md_lines.append(text)

    return "\n\n".join(md_lines)


def main():
    parser = argparse.ArgumentParser(description="Convert a DOCX file to Markdown with headings.")
    parser.add_argument("input", type=str, help="Path to the input .docx file")
    parser.add_argument("--output", "-o", type=str, help="Path to save the .md output (optional)")

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists() or not input_path.suffix.lower() == ".docx":
        raise FileNotFoundError("Input file must be a .docx file and must exist.")

    markdown = docx_to_markdown(str(input_path))

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(markdown, encoding="utf-8")
        print(f"[✓] Markdown written to {output_path}")
    else:
        print(markdown)


if __name__ == "__main__":
    main()