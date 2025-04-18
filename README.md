# StoryRAG
This is an experiment in parsing a story and generating a summary using a RAG (Retrieval-Augmented Generation) approach. The goal is to create a system that can take a story as input and generate a summary that captures the main points of the story with semantics that can then be imported into Neo4j for a more comprehensive RAG solution.

## Requirements
- Python 3.10+
- Ollama
- Neo4j (soon)


## Run the thing

```
python parse_chapter_llm.py ./examples/chapter1.md --output ./test.json --model deepseek-r1
```

## Using SpaCy
```
### Get the model
python -m spacy download en_core_web_sm

## For the bigger model - use with --model en_core_web_trf
python -m spacy download en_core_web_trf


```


## Pipeline So Far

```
docx_to_json.py | extract_entities_per_chapter.py | canonicalize_entities.py | 
```