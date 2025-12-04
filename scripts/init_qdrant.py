"""
Qdrant initialization script.

This script initializes Qdrant collections for ContextIQ.
It creates all necessary collections with proper configuration.

Usage:
    python scripts/init_qdrant.py [--host HOST] [--port PORT] [--recreate]

Options:
    --host HOST      Qdrant host (default: localhost)
    --port PORT      Qdrant port (default: 6333)
    --recreate       Delete and recreate existing collections
"""

import argparse
import logging
import sys
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from shared.vector_store import get_collection_configs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_qdrant_client(host: str, port: int) -> QdrantClient:
    """
    Create and test Qdrant client connection.

    Args:
        host: Qdrant server host
        port: Qdrant server port

    Returns:
        Connected QdrantClient instance

    Raises:
        ConnectionError: If unable to connect to Qdrant
    """
    try:
        client = QdrantClient(host=host, port=port)
        # Test connection
        client.get_collections()
        logger.info(f"Successfully connected to Qdrant at {host}:{port}")
        return client
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Qdrant at {host}:{port}: {e}") from e


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    """
    Check if a collection exists.

    Args:
        client: Qdrant client
        collection_name: Name of the collection

    Returns:
        True if collection exists, False otherwise
    """
    try:
        client.get_collection(collection_name)
        return True
    except UnexpectedResponse:
        return False


def create_collection(
    client: QdrantClient,
    collection_name: str,
    config: dict[str, Any],
    recreate: bool = False,
) -> bool:
    """
    Create a Qdrant collection with the given configuration.

    Args:
        client: Qdrant client
        collection_name: Name of the collection
        config: Collection configuration dictionary
        recreate: If True, delete existing collection before creating

    Returns:
        True if collection was created, False if already existed
    """
    exists = collection_exists(client, collection_name)

    if exists:
        if recreate:
            logger.info(f"Deleting existing collection: {collection_name}")
            client.delete_collection(collection_name)
        else:
            logger.info(f"Collection already exists: {collection_name}")
            return False

    logger.info(f"Creating collection: {collection_name}")

    # Extract vector config
    vector_config = config["vectors"]
    vectors_config = models.VectorParams(
        size=vector_config["size"],
        distance=models.Distance[vector_config["distance"].upper()],
        on_disk=vector_config.get("on_disk", False),
    )

    # Extract HNSW config if provided
    hnsw_config = None
    if "hnsw_config" in config:
        hnsw_params = config["hnsw_config"]
        hnsw_config = models.HnswConfigDiff(
            m=hnsw_params.get("m"),
            ef_construct=hnsw_params.get("ef_construct"),
            full_scan_threshold=hnsw_params.get("full_scan_threshold"),
        )

    # Extract optimizer config if provided
    optimizer_config = None
    if "optimizers_config" in config:
        optimizer_params = config["optimizers_config"]
        optimizer_config = models.OptimizersConfigDiff(
            indexing_threshold=optimizer_params.get("indexing_threshold"),
        )

    # Create collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config=vectors_config,
        hnsw_config=hnsw_config,
        optimizers_config=optimizer_config,
    )

    logger.info(f"Successfully created collection: {collection_name}")
    return True


def init_collections(
    host: str = "localhost",
    port: int = 6333,
    recreate: bool = False,
) -> tuple[int, int]:
    """
    Initialize all Qdrant collections.

    Args:
        host: Qdrant server host
        port: Qdrant server port
        recreate: If True, delete and recreate existing collections

    Returns:
        Tuple of (created_count, skipped_count)

    Raises:
        ConnectionError: If unable to connect to Qdrant
    """
    client = create_qdrant_client(host, port)
    configs = get_collection_configs()

    created = 0
    skipped = 0

    for config in configs:
        was_created = create_collection(
            client,
            config.name,
            config.to_dict(),
            recreate=recreate,
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    return created, skipped


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Initialize Qdrant collections for ContextIQ"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Qdrant host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6333,
        help="Qdrant port (default: 6333)",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate existing collections",
    )

    args = parser.parse_args()

    try:
        created, skipped = init_collections(
            host=args.host,
            port=args.port,
            recreate=args.recreate,
        )

        logger.info(f"Initialization complete: {created} created, {skipped} skipped")
        return 0

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
