"""Unit tests for general stats service."""

import re

import pytest
from unittest.mock import MagicMock


class TestGeneralStatsService:
    """Unit tests for GeneralStatsService."""

    @pytest.fixture
    def mock_state(self):
        """Create a mock state object."""
        state = MagicMock()
        state.db_client = MagicMock()
        return state

    @pytest.fixture
    def service(self, mock_state):
        """Create service with mock state."""
        from models.rest_api.entitybase.v1.services.general_stats_service import (
            GeneralStatsService,
        )

        svc = GeneralStatsService(state=mock_state)
        return svc

    def test_get_total_statements(self, service, mock_state):
        """Test get_total_statements returns count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [100]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_total_statements()
        assert result == 100

    def test_get_total_qualifiers(self, service, mock_state):
        """Test get_total_qualifiers returns count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [50]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_total_qualifiers()
        assert result == 50

    def test_get_total_references(self, service, mock_state):
        """Test get_total_references returns count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [25]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_total_references()
        assert result == 25

    def test_get_total_items(self, service, mock_state):
        """Test get_total_items returns count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [200]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_total_items()
        assert result == 200

    def test_get_total_lexemes(self, service, mock_state):
        """Test get_total_lexemes returns count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [75]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_total_lexemes()
        assert result == 75

    def test_get_total_properties(self, service, mock_state):
        """Test get_total_properties returns count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [30]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_total_properties()
        assert result == 30

    def test_get_total_sitelinks(self, service, mock_state):
        """Test get_total_sitelinks returns count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [150]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_total_sitelinks()
        assert result == 150

    def test_get_total_terms(self, service, mock_state):
        """Test get_total_terms returns count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [500]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_total_terms()
        assert result == 500


class TestDeduplicationStats:
    """Unit tests for deduplication stats methods."""

    @pytest.fixture
    def mock_state(self):
        """Create a mock state object."""
        state = MagicMock()
        state.db_client = MagicMock()
        return state

    @pytest.fixture
    def service(self, mock_state):
        """Create service with mock state."""
        from models.rest_api.entitybase.v1.services.general_stats_service import (
            GeneralStatsService,
        )

        svc = GeneralStatsService(state=mock_state)
        return svc

    def test_get_table_deduplication_stats_with_data(self, service, mock_state):
        """Test _get_table_deduplication_stats returns correct stats."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [100, 500]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service._get_table_deduplication_stats("statements")

        assert result.unique_hashes == 100
        assert result.total_ref_count == 500
        assert result.deduplication_factor == 80.0
        assert result.space_saved == 400

    def test_get_table_deduplication_stats_no_data(self, service, mock_state):
        """Test _get_table_deduplication_stats returns zeros when no data."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [0, 0]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service._get_table_deduplication_stats("statements")

        assert result.unique_hashes == 0
        assert result.total_ref_count == 0
        assert result.deduplication_factor == 0.0
        assert result.space_saved == 0

    def test_get_table_deduplication_stats_exception(self, service, mock_state):
        """Test _get_table_deduplication_stats handles exceptions."""
        mock_state.db_client.cursor.__enter__.side_effect = Exception("Table not found")

        result = service._get_table_deduplication_stats("nonexistent_table")

        assert result.unique_hashes == 0
        assert result.total_ref_count == 0
        assert result.deduplication_factor == 0.0

    def test_get_terms_deduplication_stats(self, service, mock_state):
        """Terms deduplicate across every row of the term ledger."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [100, 200]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service._get_terms_deduplication_stats()

        assert result.unique_hashes == 100
        assert result.total_ref_count == 200
        assert result.deduplication_factor == 50.0
        assert result.space_saved == 100

    def test_get_terms_deduplication_counts_shared_term_text(self, service, mock_state):
        """One text used as a label and a description is one hash, two refs.

        entity_terms is keyed by the hash of the term text, so a text reused
        across term types is a single row with ref_count 2.
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [1, 2]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service._get_terms_deduplication_stats()

        assert result.unique_hashes == 1
        assert result.total_ref_count == 2
        assert result.deduplication_factor == 50.0
        assert result.space_saved == 1

    def test_get_terms_deduplication_stats_no_terms(self, service, mock_state):
        """No terms yet means zeroed stats, not an error."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [0, 0]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service._get_terms_deduplication_stats()

        assert result.unique_hashes == 0
        assert result.total_ref_count == 0
        assert result.deduplication_factor == 0.0

    def test_get_terms_deduplication_stats_no_table(self, service, mock_state):
        """Test _get_terms_deduplication_stats when the table doesn't exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Table not found")
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service._get_terms_deduplication_stats()

        assert result.unique_hashes == 0
        assert result.total_ref_count == 0

    def test_compute_deduplication_stats(self, service, mock_state):
        """Test compute_deduplication_stats returns stats for all types."""
        mock_cursor = MagicMock()
        # One row per table: statements, qualifiers, refs, snaks, sitelinks
        # and entity_terms
        mock_cursor.fetchone.side_effect = [
            [100, 500],
            [80, 400],
            [60, 300],
            [40, 200],
            [30, 150],
            [50, 100],
        ]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.compute_deduplication_stats()

        assert result.statements.unique_hashes == 100
        assert result.qualifiers.unique_hashes == 80
        assert result.references.unique_hashes == 60
        assert result.snaks.unique_hashes == 40
        assert result.sitelinks.unique_hashes == 30
        assert result.terms.unique_hashes == 50
        assert result.terms.total_ref_count == 100


class TestComputeDailyStats:
    """Unit tests for compute_daily_stats method."""

    @pytest.fixture
    def mock_state(self):
        """Create a mock state object."""
        state = MagicMock()
        state.db_client = MagicMock()
        return state

    @pytest.fixture
    def service(self, mock_state):
        """Create service with mock state."""
        from models.rest_api.entitybase.v1.services.general_stats_service import (
            GeneralStatsService,
        )

        svc = GeneralStatsService(state=mock_state)
        return svc

    def test_compute_daily_stats(self, service, mock_state):
        """Test compute_daily_stats method exists and is callable."""
        assert hasattr(service, "compute_daily_stats")
        assert callable(service.compute_daily_stats)


class TestExceptionHandling:
    """Unit tests for exception handling in stats methods."""

    @pytest.fixture
    def mock_state(self):
        """Create a mock state object."""
        state = MagicMock()
        state.db_client = MagicMock()
        return state

    @pytest.fixture
    def service(self, mock_state):
        """Create service with mock state."""
        from models.rest_api.entitybase.v1.services.general_stats_service import (
            GeneralStatsService,
        )

        svc = GeneralStatsService(state=mock_state)
        return svc

    def test_get_total_statements_exception(self, service, mock_state):
        """Test get_total_statements returns 0 on exception."""
        mock_state.db_client.cursor.__enter__.side_effect = Exception("Table not found")

        result = service.get_total_statements()
        assert result == 0

    def test_get_total_qualifiers_exception(self, service, mock_state):
        """Test get_total_qualifiers returns 0 on exception."""
        mock_state.db_client.cursor.__enter__.side_effect = Exception("Table not found")

        result = service.get_total_qualifiers()
        assert result == 0

    def test_get_total_references_exception(self, service, mock_state):
        """Test get_total_references returns 0 on exception."""
        mock_state.db_client.cursor.__enter__.side_effect = Exception("Table not found")

        result = service.get_total_references()
        assert result == 0

    def test_get_total_sitelinks_exception(self, service, mock_state):
        """Test get_total_sitelinks returns 0 on exception."""
        mock_state.db_client.cursor.__enter__.side_effect = Exception("Table not found")

        result = service.get_total_sitelinks()
        assert result == 0

    def test_get_total_terms_exception(self, service, mock_state):
        """Test get_total_terms returns 0 on exception."""
        mock_state.db_client.cursor.__enter__.side_effect = Exception("Table not found")

        result = service.get_total_terms()
        assert result == 0


class TestTermsPerLanguage:
    """Unit tests for get_terms_per_language method."""

    @pytest.fixture
    def mock_state(self):
        """Create a mock state object."""
        state = MagicMock()
        state.db_client = MagicMock()
        return state

    @pytest.fixture
    def service(self, mock_state):
        """Create service with mock state."""
        from models.rest_api.entitybase.v1.services.general_stats_service import (
            GeneralStatsService,
        )

        svc = GeneralStatsService(state=mock_state)
        return svc

    def test_get_terms_per_language_success(self, service, mock_state):
        """Test get_terms_per_language aggregates from all term tables."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [["en", 100], ["de", 50]],
            [["en", 80], ["de", 30]],
            [["en", 20], ["de", 10]],
        ]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_terms_per_language()

        assert result.terms["en"] == 200
        assert result.terms["de"] == 90

    def test_get_terms_per_language_partial_tables(self, service, mock_state):
        """Test get_terms_per_language handles missing tables gracefully."""
        call_count = 0

        def fetchall_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("labels table not found")
            if call_count == 2:
                raise Exception("descriptions table not found")
            return [["en", 100]]

        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = fetchall_side_effect
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_terms_per_language()

        assert result.terms["en"] == 100

    def test_get_terms_per_language_outer_exception(self, service, mock_state):
        """Test get_terms_per_language handles outer exception."""
        mock_state.db_client.cursor.__enter__.side_effect = Exception(
            "Connection error"
        )

        result = service.get_terms_per_language()
        assert result.terms == {}


class TestTermsByType:
    """Unit tests for get_terms_by_type method."""

    @pytest.fixture
    def mock_state(self):
        """Create a mock state object."""
        state = MagicMock()
        state.db_client = MagicMock()
        return state

    @pytest.fixture
    def service(self, mock_state):
        """Create service with mock state."""
        from models.rest_api.entitybase.v1.services.general_stats_service import (
            GeneralStatsService,
        )

        svc = GeneralStatsService(state=mock_state)
        return svc

    def test_get_terms_by_type_success(self, service, mock_state):
        """Counts per term type, reported under their plural names."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ["label", 1000],
            ["description", 500],
            ["alias", 300],
        ]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_terms_by_type()

        assert result.counts["labels"] == 1000
        assert result.counts["descriptions"] == 500
        assert result.counts["aliases"] == 300

    def test_get_terms_by_type_includes_lexeme_terms(self, service, mock_state):
        """Form representations and sense glosses are terms too."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ["label", 2],
            ["form_representation", 4],
            ["sense_gloss", 6],
        ]
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor

        result = service.get_terms_by_type()

        assert result.counts["form_representations"] == 4
        assert result.counts["sense_glosses"] == 6

    def test_get_terms_by_type_outer_exception(self, service, mock_state):
        """Test get_terms_by_type handles outer exception."""
        mock_state.db_client.cursor.__enter__.side_effect = Exception(
            "Connection error"
        )

        result = service.get_terms_by_type()
        assert result.counts == {}


class TestStatsQueryTables:
    """Stats queries must read tables that exist.

    Terms live in entity_terms and references in refs. There are no
    labels/descriptions/aliases/terms/references tables, so querying those
    raised, was swallowed, and every such figure silently reported zero. These
    tests assert the SQL, because mocked cursors are happy with any table name.
    """

    # Tables that exist and hold terms and references
    TERMS_TABLE = "entity_terms"
    REFERENCES_TABLE = "refs"

    @pytest.fixture
    def mock_state(self):
        """Create a mock state object with a recording cursor."""
        state = MagicMock()
        state.db_client = MagicMock()
        return state

    @pytest.fixture
    def cursor(self, mock_state):
        """Mock cursor that records the SQL it is given."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [1, 1]
        mock_cursor.fetchall.return_value = []
        mock_state.db_client.cursor.__enter__.return_value = mock_cursor
        return mock_cursor

    @pytest.fixture
    def service(self, mock_state):
        """Create service with mock state."""
        from models.rest_api.entitybase.v1.services.general_stats_service import (
            GeneralStatsService,
        )

        return GeneralStatsService(state=mock_state)

    @staticmethod
    def _sql(cursor):
        """All SQL statements the cursor was asked to run."""
        return [call.args[0] for call in cursor.execute.call_args_list]

    def test_terms_deduplication_reads_the_term_ledger(
        self, service, mock_state, cursor
    ):
        """Terms deduplication reads entity_terms, summing ref_count."""
        service._get_terms_deduplication_stats()

        sql = " ".join(self._sql(cursor))
        assert f"FROM {self.TERMS_TABLE}" in sql
        assert "SUM(ref_count)" in sql

    def test_total_terms_reads_the_term_ledger(self, service, mock_state, cursor):
        """Total terms reads entity_terms, summing ref_count."""
        service.get_total_terms()

        sql = " ".join(self._sql(cursor))
        assert f"FROM {self.TERMS_TABLE}" in sql
        assert "SUM(ref_count)" in sql

    def test_terms_by_type_reads_the_term_ledger(self, service, mock_state, cursor):
        """Terms by type groups the term ledger by term_type."""
        service.get_terms_by_type()

        sql = " ".join(self._sql(cursor))
        assert f"FROM {self.TERMS_TABLE}" in sql
        assert "GROUP BY term_type" in sql

    def test_total_references_reads_the_refs_table(self, service, mock_state, cursor):
        """References are counted from refs, not from a references table."""
        service.get_total_references()

        sql = " ".join(self._sql(cursor))
        assert f"FROM {self.REFERENCES_TABLE}" in sql

    def test_no_query_targets_a_table_that_does_not_exist(
        self, service, mock_state, cursor
    ):
        """None of the stats queries may name a non-existent table."""
        service.compute_deduplication_stats()
        service.get_total_terms()
        service.get_total_references()
        service.get_terms_by_type()

        missing = ("labels", "descriptions", "aliases", "references", "terms")
        for statement in self._sql(cursor):
            for table in missing:
                assert not re.search(rf"\bFROM\s+{table}\b", statement), (
                    f"{statement!r} reads the non-existent table {table!r}"
                )
