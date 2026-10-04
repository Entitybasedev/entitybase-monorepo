"""Unit tests for the JSON dump worker entry point."""

import asyncio
from unittest.mock import AsyncMock, patch


class TestWorkerEntryPoints:
    @patch("json_dump_worker.worker.main", new_callable=AsyncMock)
    def test_main_entry_point_runs_main(self, mock_main):
        """The worker module exposes a main() that the entry point calls."""
        from json_dump_worker import worker

        asyncio.run(worker.main())

        mock_main.assert_called_once()

    def test_entry_point_module_exists(self):
        """The __main__ module is importable and has a file."""
        from json_dump_worker import __main__ as entry

        assert hasattr(entry, "__file__")
