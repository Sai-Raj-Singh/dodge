"""Reset script: clear Neo4j database and ChromaDB.

Usage:
    python -m scripts.reset_db
"""

import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.graph.connection import clear_database, verify_connection, close_driver
from app.graph.indexes import drop_indexes


def main() -> None:
    print("=" * 60)
    print("  Database Reset")
    print("=" * 60)

    # Neo4j
    print("\n[1/2] Resetting Neo4j...")
    if verify_connection():
        drop_indexes()
        clear_database()
        print("  Neo4j cleared.")
    else:
        print("  Neo4j not reachable, skipping.")

    # ChromaDB
    print("\n[2/2] Resetting ChromaDB...")
    chroma_dir = Path(settings.chroma_persist_dir)
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        chroma_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Deleted {chroma_dir}")
    else:
        print("  No ChromaDB data found.")

    print("\n  Reset complete.")
    close_driver()


if __name__ == "__main__":
    main()
