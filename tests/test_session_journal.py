"""Tests for session journal (Feature 2)."""

import pytest
import threading
import time
from pathlib import Path


class TestSessionJournal:
    """Tests for SessionJournal class."""

    def test_record_read_appears_in_context(self):
        """Record one read, verify files_accessed has correct info."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()  # Fresh instance, not singleton
        journal.record_read("src/main.py", "get_symbol_source")
        ctx = journal.get_context()
        assert len(ctx["files_accessed"]) == 1
        entry = ctx["files_accessed"][0]
        assert entry["file"] == "src/main.py"
        assert entry["reads"] == 1
        assert entry["last_tool"] == "get_symbol_source"

    def test_duplicate_reads_increment_count(self):
        """Same file read twice → reads == 2, last_tool updated."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()
        journal.record_read("src/utils.py", "get_file_content")
        journal.record_read("src/utils.py", "get_symbol_source")
        ctx = journal.get_context()
        assert len(ctx["files_accessed"]) == 1
        entry = ctx["files_accessed"][0]
        assert entry["reads"] == 2
        assert entry["last_tool"] == "get_symbol_source"

    def test_record_search_appears(self):
        """Record a search, verify recent_searches."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()
        journal.record_search("my_func", 5)
        ctx = journal.get_context()
        assert len(ctx["recent_searches"]) == 1
        entry = ctx["recent_searches"][0]
        assert entry["query"] == "my_func"
        assert entry["result_count"] == 5

    def test_record_edit_appears(self):
        """Record an edit, verify files_edited."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()
        journal.record_edit("src/auth.py")
        ctx = journal.get_context()
        assert len(ctx["files_edited"]) == 1
        entry = ctx["files_edited"][0]
        assert entry["file"] == "src/auth.py"
        assert entry["edits"] == 1

    def test_record_tool_call_counted(self):
        """Count tool calls."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()
        journal.record_tool_call("search_symbols")
        journal.record_tool_call("search_symbols")
        journal.record_tool_call("get_symbol_source")
        ctx = journal.get_context()
        assert ctx["tool_calls"]["search_symbols"] == 2
        assert ctx["tool_calls"]["get_symbol_source"] == 1

    def test_max_files_limit(self):
        """get_context(max_files=N) limits output, not total_unique_files."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()
        for i in range(30):
            journal.record_read(f"src/file{i}.py", "get_symbol_source")
        ctx = journal.get_context(max_files=10)
        assert len(ctx["files_accessed"]) == 10
        assert ctx["total_unique_files"] == 30

    def test_max_queries_limit(self):
        """get_context(max_queries=N) limits searches output."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()
        for i in range(30):
            journal.record_search(f"query{i}", i)
        ctx = journal.get_context(max_queries=10)
        assert len(ctx["recent_searches"]) == 10
        assert ctx["total_unique_queries"] == 30

    def test_session_duration_positive(self):
        """session_duration_s >= 0."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()
        time.sleep(0.01)  # tiny delay
        ctx = journal.get_context()
        assert ctx["session_duration_s"] >= 0

    def test_thread_safety(self):
        """5 threads × 100 writes each, no exceptions, correct totals."""
        from jcodemunch_mcp.tools.session_journal import SessionJournal
        journal = SessionJournal()
        errors = []

        def writer(thread_id: int):
            try:
                for i in range(100):
                    journal.record_read(f"src/file{thread_id}_{i}.py", "get_symbol_source")
                    journal.record_search(f"query{thread_id}_{i}", i)
                    journal.record_tool_call("search_symbols")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        ctx = journal.get_context(max_files=1000, max_queries=1000)
        assert ctx["total_unique_files"] == 500
        assert ctx["total_unique_queries"] == 500
        assert ctx["tool_calls"]["search_symbols"] == 500


class TestSessionJournalSingleton:
    """Tests for get_journal() singleton."""

    def test_get_journal_returns_same_instance(self):
        """get_journal() returns the same instance."""
        from jcodemunch_mcp.tools.session_journal import get_journal
        j1 = get_journal()
        j2 = get_journal()
        assert j1 is j2

    def test_singleton_records_persist(self):
        """Records via singleton persist across calls."""
        from jcodemunch_mcp.tools.session_journal import get_journal
        journal = get_journal()
        # Clear any existing state
        journal._files.clear()
        journal._queries.clear()
        journal._edits.clear()
        journal._tool_calls.clear()
        
        journal.record_read("src/test.py", "get_symbol_source")
        journal2 = get_journal()
        ctx = journal2.get_context()
        assert len(ctx["files_accessed"]) == 1