from __future__ import annotations

import os
from typing import Optional

from neo4j import GraphDatabase, Driver


def get_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> Driver:
    """
    Construct a Neo4j driver using environment defaults.

    Defaults are safe for local docker-compose:
    - bolt://neo4j:7687
    - neo4j / signalforge
    """
    uri = uri or os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = user or os.getenv("NEO4J_USER", "neo4j")
    password = password or os.getenv("NEO4J_PASSWORD", "signalforge")
    return GraphDatabase.driver(uri, auth=(user, password))
