"""Seed script: generate text chunks from graph → embed → store in ChromaDB.

Usage:
    python -m scripts.seed_vectors
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.connection import verify_connection, close_driver
from app.rag.chunker import generate_all_chunks
from app.rag.vector_store import store_chunks, clear_collection, get_collection_stats


def main() -> None:
    print("=" * 60)
    print("  SAP O2C Vector Seeder")
    print("=" * 60)

    # 1. Verify Neo4j (needed for chunk generation)
    print("\n[1/3] Verifying Neo4j connection...")
    if not verify_connection():
        print("[FATAL] Cannot connect to Neo4j. Run seed_graph.py first.")
        sys.exit(1)
    print("  Connected.")

    # 2. Clear existing vectors
    print("\n[2/3] Clearing existing vector data...")
    clear_collection()

    # 3. Generate chunks and store
    print("\n[3/3] Generating chunks and embedding...")
    start = time.time()
    chunks = generate_all_chunks()

    if not chunks:
        print("[WARN] No chunks generated. Is the graph populated?")
        sys.exit(1)

    stored = store_chunks(chunks)
    elapsed = time.time() - start

    # Summary
    stats = get_collection_stats()
    print("\n" + "=" * 60)
    print(f"  Vector seeding complete! ({elapsed:.1f}s)")
    print(f"  Chunks stored: {stats['count']}")
    print("=" * 60)

    close_driver()


if __name__ == "__main__":
    main()
