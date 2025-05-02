#!/bin/bash

# Configuration
DB_NAME="novel.db"
CSV_DIR="$(pwd)"
NEO4J_ADMIN="neo4j-admin"

# Ensure Neo4j is stopped before import
echo "[!] Make sure Neo4j is NOT running before using neo4j-admin import"
read -p "Proceed with import to $DB_NAME from $CSV_DIR? (y/n): " confirm

if [[ "$confirm" != "y" ]]; then
  echo "Aborted."
  exit 1
fi

# Run neo4j-admin import
$NEO4J_ADMIN database import full $DB_NAME \
  --nodes=Character=nodes_characters.csv \
  --nodes=Place=nodes_places.csv \
  --nodes=Culture=nodes_cultures.csv \
  --nodes=Organization=nodes_organizations.csv \
  --nodes=Person=nodes_persons.csv \
  --nodes=Item=nodes_items.csv \
  --nodes=Chapter=nodes_chapters.csv \
  --nodes=Paragraph=nodes_paragraphs.csv \
  --nodes=Date=nodes_dates.csv \
  --nodes=Group=nodes_groups.csv \
  --relationships=PART_OF=rels_part_of.csv \
  --relationships=MENTIONS=rels_mentions.csv \
  --multiline-fields=true \
  --verbose \
  --quote='"'

if [[ $? -eq 0 ]]; then
  echo "[✓] Import complete. Your database '$DB_NAME' is ready."
  echo "You can now move it into your Neo4j data directory if needed."
else
  echo "[✗] Import failed. Check your CSVs and Neo4j installation."
fi
