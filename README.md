# StoryRAG
This is an experiment in parsing a story and generating a summary using a RAG (Retrieval-Augmented Generation) approach. The goal is to create a system that can take a story as input and generate a summary that captures the main points of the story with semantics that can then be imported into Neo4j for a more comprehensive RAG solution.

```
python parse_chapter_llm.py ./examples/1\ -\ Black\ and\ Red.md --output ./test.json --model deepseek-r1
```
