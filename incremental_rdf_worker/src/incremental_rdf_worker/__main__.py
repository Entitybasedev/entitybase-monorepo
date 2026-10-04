"""Entry point for the Incremental RDF worker."""

import asyncio

from incremental_rdf_worker.worker import main

if __name__ == "__main__":
    asyncio.run(main())
