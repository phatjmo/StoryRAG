#!/bin/bash

# Configuration
DB_NAME="novel.db"
NEO4J_HOME="$HOME/Library/Application Support/Neo4j Desktop"
TARGET_DIR=$(find "$NEO4J_HOME" -type d -name "databases" | head -n 1)
IMPORT_DIR="$(pwd)/databases/$DB_NAME"

if [[ -z "$TARGET_DIR" ]]; then
  echo "[✗] Could not locate Neo4j Desktop databases folder."
  exit 1
fi

if [[ ! -d "$IMPORT_DIR" ]]; then
  echo "[✗] Expected database folder not found at: $IMPORT_DIR"
  echo "Make sure you've already run neo4j-admin import."
  exit 1
fi

DEST="$TARGET_DIR/$DB_NAME"

if [[ -d "$DEST" ]]; then
  read -p "[!] '$DB_NAME' already exists in Neo4j. Overwrite? (y/n): " confirm
  if [[ "$confirm" != "y" ]]; then
    echo "Aborted."
    exit 1
  fi
  rm -rf "$DEST"
fi

cp -R "$IMPORT_DIR" "$DEST"

echo "[✓] Installed '$DB_NAME' into Neo4j at: $DEST"
echo "Open Neo4j Desktop, add a new project, and select '$DB_NAME' from existing databases to activate it."
echo "You can now start Neo4j and explore your database."