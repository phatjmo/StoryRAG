import argparse
import os
from pathlib import Path
import json
import dotenv
from llama_parse import LlamaParse
from llama_index.core.node_parser import MarkdownElementNodeParser
from langchain_ollama import ChatOllama, OllamaLLM

dotenv.load_dotenv()
# Set the environment variable for LlamaParse API key
# This should be set in your environment or .env file
LLAMA_PARSE_KEY=os.environ.get("LLAMA_PARSE_KEY", None)

def parse_with_llama(file_path, model_name="llama3.2", output=None):
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Instantiate LLM for Markdown parsing
    llm = OllamaLLM(model=model_name)

    # Load document and parse with llama-parse
    print(f"[+] Loading file with LlamaParse: {file_path}")
    documents = LlamaParse(api_key=LLAMA_PARSE_KEY, result_type="markdown").load_data(file_path)

    print("[+] Parsing markdown into semantic nodes and objects...")
    node_parser = MarkdownElementNodeParser(llm=llm, num_workers=8)
    nodes = node_parser.get_nodes_from_documents(documents)
    base_nodes, objects = node_parser.get_nodes_and_objects(nodes)

    results = {
        "nodes": [n.to_dict() for n in base_nodes],
        "objects": [o.to_dict() for o in objects],
    }

    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[✓] Parsed output written to {output}")
    else:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse documents using LlamaParse + MarkdownElementNodeParser + Ollama")
    parser.add_argument("file", type=str, help="Path to PDF or markdown file")
    parser.add_argument("--model", type=str, default="llama3.2", help="Ollama model name")
    parser.add_argument("--out", type=str, help="Output JSON file")

    args = parser.parse_args()
    parse_with_llama(args.file, model_name=args.model, output=args.out)