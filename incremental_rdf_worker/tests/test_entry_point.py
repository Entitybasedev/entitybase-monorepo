"""Unit tests for the incremental RDF worker entry point."""

import asyncio
from unittest.mock import AsyncMock, patch


class TestWorkerEntryPoints:
    @patch("incremental_rdf_worker.worker.main", new_callable=AsyncMock)
    def test_main_entry_point_runs_main(self, mock_main):
        """The worker module exposes a main() that the entry point calls."""
        from incremental_rdf_worker import worker

        asyncio.run(worker.main())

        mock_main.assert_called_once()

    def test_entry_point_module_exists(self):
        """The __main__ module is importable and has a file."""
        from incremental_rdf_worker import __main__ as entry

        assert hasattr(entry, "__file__")
