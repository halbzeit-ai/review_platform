"""
Processing Worker Service Entry Point

This module allows running the processing worker as a standalone service:
python -m app.services.processing_worker
"""

import asyncio
from .processing_worker import main

if __name__ == "__main__":
    asyncio.run(main())