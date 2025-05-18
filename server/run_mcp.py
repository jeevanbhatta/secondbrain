#!/usr/bin/env python3
"""
SecondBrain MCP Server
Run this script to start the MCP server for responding to AI assistant queries
"""

import os
import sys
import logging
from mcp_server import run_mcp_server, search_database, conversational_search
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
def load_environment():
    # Load .env file from project root (one directory up from server)
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    if env_path.exists():
        logger.info(f"Loading environment variables from {env_path}")
        load_dotenv(dotenv_path=env_path, override=True)
        logger.info(f"ANTHROPIC_API_KEY found: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
    else:
        logger.warning(f".env file not found at {env_path}")

# Execute this when imported
load_environment()

if __name__ == "__main__":
    logger.info("Starting SecondBrain MCP Server...")
    try:
        run_mcp_server()
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        sys.exit(1) 