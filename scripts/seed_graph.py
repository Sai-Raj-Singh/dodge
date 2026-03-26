"""Seed script: ingest dataset → build Neo4j graph → create indexes.

Usage:
    python -m scripts.seed_graph
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.graph.connection import clear_database, verify_connection, close_driver
from app.graph.builder import build_graph
from app.graph.indexes import create_indexes
from app.ingestion.normalizer import ingest


def main() -> None:
    print("=" * 60)
    print("  SAP O2C Graph Seeder")
    print("=" * 60)

    # 1. Verify Neo4j connection
    print("\n[1/4] Verifying Neo4j connection...")
    if not verify_connection():
        print("[FATAL] Cannot connect to Neo4j. Is the container running?")
        print("        Run: docker-compose up -d")
        sys.exit(1)
    print("  Connected to Neo4j successfully.")

    # 2. Clear existing data
    print("\n[2/4] Clearing existing graph data...")
    clear_database()

    # 3. Ingest dataset
    print("\n[3/4] Ingesting dataset...")
    start = time.time()
    dataset_path = Path(settings.dataset_path)
    data = ingest(dataset_path)
    ingest_time = time.time() - start
    print(f"  Ingestion completed in {ingest_time:.1f}s")

    # 4. Build graph
    print("\n[4/4] Building graph...")
    start = time.time()
    build_graph(data)
    build_time = time.time() - start
    print(f"  Graph built in {build_time:.1f}s")

    # 5. Create indexes
    print("\n[BONUS] Creating indexes...")
    create_indexes()

    # Done
    print("\n" + "=" * 60)
    print(f"  Seeding complete! ({ingest_time + build_time:.1f}s total)")
    print(f"  Neo4j Browser: http://localhost:7474")
    print("=" * 60)

    close_driver()


if __name__ == "__main__":
    main()
