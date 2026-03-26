"""Neo4j driver and session management."""

from contextlib import contextmanager
from typing import Generator

from neo4j import GraphDatabase, Driver, Session

from app.config import settings


_driver: Driver | None = None


def get_driver() -> Driver:
    """Get or create a singleton Neo4j driver instance."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close_driver() -> None:
    """Close the Neo4j driver connection."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager that yields a Neo4j session."""
    driver = get_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


def verify_connection() -> bool:
    """Test the Neo4j connection and return True if successful."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        with get_session() as session:
            result = session.run("RETURN 1 AS n")
            record = result.single()
            return record is not None and record["n"] == 1
    except Exception as e:
        print(f"[ERR] Neo4j connection failed: {e}")
        return False


def clear_database() -> None:
    """Delete all nodes and relationships from the database."""
    with get_session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("[NEO4J] Database cleared.")
