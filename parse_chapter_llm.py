import json
import frontmatter
from pathlib import Path
from langchain_ollama import ChatOllama, OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List


"""This script uses the Ollama LLM to parse a chapter of a novel from a markdown file."""

class ChapterMetadata(BaseModel):
    think: str = Field(
        description="Think though how to tell a good joke about the subject"
    )
    reasoning: str = Field(
        description="Reasoning about the chapter, including the main events and character arcs."
    )
    characters: List[str] = Field(
        description="List of characters mentioned in the chapter, including their roles and relationships."
    )
    places: List[str] = Field(
        description="List of places mentioned in the chapter, including their significance."
    )
    items: List[str] = Field(
        description="List of items mentioned in the chapter, including their significance."
    )
    themes: List[str] = Field(
        description="List of themes or motifs present in the chapter."
    )
    summary: str
    

def ask_llm_for_metadata(text: str, model_name: str = "llama3.2:latest") -> dict:
    llm = ChatOllama(model=model_name, temperature=0, format='json') # OllamaLLM(model=model_name, temperature=0)
    parser = PydanticOutputParser(pydantic_object=ChapterMetadata)
    
    prompt = PromptTemplate(
        template="""
    You are a helpful literary assistant.

    Given the following chapter, extract structured information about it. Your response must strictly match this JSON format:

    {format_instructions}
    DO NOT include any explanation, markdown, or notes. Just output JSON.

    --- BEGIN TEXT ---
    {text}
    --- END TEXT ---
    """,
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    txtPrompt = prompt.invoke({"text": text[:8000]})  # Truncate if needed for model limits
    structured_llm = llm.with_structured_output(ChapterMetadata, method="json_schema")
    # chain = prompt | llm.with_structured_output(ChapterMetadata, method="json_schema") | parser
    response = structured_llm.invoke(txtPrompt) #chain.invoke({"text": text[:8000]})  # Truncate if needed for model limits
    dictResponse = response.model_dump(mode="json")
    return dictResponse

def parse_chapter_with_ollama(file_path: str, model_name: str = "llama3.2:latest") -> dict:
    path = Path(file_path)
    post = frontmatter.load(path)

    full_text = post.content.strip()
    metadata = post.metadata

    llm_metadata = ask_llm_for_metadata(full_text, model_name)

    return {
        "id": f"chapter_{metadata.get('number', 0)}",
        "title": metadata.get("title", path.stem),
        "chapter_number": metadata.get("number", 0),
        "date": metadata.get("historical_date").isoformat() if metadata.get("historical_date") else None,
        "word_count": metadata.get("word_count"),
        "entities": {
            "characters": llm_metadata.get("characters", []),
            "places": llm_metadata.get("places", []),
            "items": llm_metadata.get("items", []),
            "themes": llm_metadata.get("themes", [])
        },
        "summary": llm_metadata.get("summary", ""),
        "full_text": full_text
    }

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse a novel chapter into graph-ready JSON using Ollama.")
    parser.add_argument("file", type=str, help="Path to the markdown file")
    parser.add_argument("--output", type=str, help="Optional output file to write JSON to")
    parser.add_argument("--model", type=str, default="llama3.2:latest", help="Ollama model name to use")

    args = parser.parse_args()
    result = parse_chapter_with_ollama(args.file, model_name=args.model)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Written to {args.output}")
    else:
        print(json.dumps(result, indent=2))