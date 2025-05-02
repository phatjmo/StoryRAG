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
docx_to_json.py | extract_entities_per_chapter.py | canonicalize_entities.py | global_entity_indexer.py | json_to_neo4jcsv.py
```

### Import CSVs
```bash
cd path/to/neo4j_csv_files

neo4j-admin import \
  --database=novel_name.db \
  --nodes=Character=nodes_characters.csv \
  --nodes=Place=nodes_places.csv \
  --nodes=Item=nodes_items.csv \
  --nodes=Theme=nodes_themes.csv \
  --nodes=Chapter=nodes_chapters.csv \
  --nodes=Paragraph=nodes_paragraphs.csv \
  --relationships=PART_OF=rels_part_of.csv \
  --relationships=MENTIONS=rels_mentions.csv \
  --multiline-fields=true \
  --quote="\""
```
Note:
•	You must run this when Neo4j is not running (shutdown first)
•	--multiline-fields=true allows long paragraphs
•	--quote="\"" ensures quoted fields are handled properly

To use the imported data:
1.	Move the generated databases/novel.db folder into Neo4j’s data directory (usually ~/Library/Application Support/Neo4j Desktop)
2.	Point Neo4j Desktop or config to novel.db
3.	Open Neo4j Desktop → your new graph is ready to explore

