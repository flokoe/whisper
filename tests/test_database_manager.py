"""Tests for the DatabaseManager class."""

import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.db.manager import DatabaseManager


def test_database_manager_connection() -> None:
    """Test that DatabaseManager can create and manage a connection."""
    # Create a temporary directory for the database
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a database path in the temporary directory
        db_path: Path = Path(temp_dir) / "test.db"

        # Create a new database manager instance
        db_manager: DatabaseManager = DatabaseManager(db_path)

        # Check that the database file doesn't exist yet
        assert not db_path.exists()

        # Access the connection which should create the database file
        conn: sqlite3.Connection = db_manager.conn
        assert conn is not None
        assert db_path.exists()

        # Execute a simple query to create a table
        db_manager.execute("""
            CREATE TABLE test (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        # Insert some data
        db_manager.execute("INSERT INTO test (name) VALUES (?)", ("test_name",))
        db_manager.commit()

        # Query the data back
        result: Optional[Dict[str, Any]] = db_manager.query_one(
            "SELECT * FROM test WHERE name = ?", ("test_name",)
        )

        # Check we got the right data back
        assert result is not None
        assert result["name"] == "test_name"

        # Store the connection for checking
        original_conn: sqlite3.Connection = db_manager.conn

        # Close the connection
        db_manager.close()

        # Verify that after closing, accessing conn creates a new connection
        assert db_manager.conn is not original_conn


def test_executemany() -> None:
    """Test the executemany method for batch operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path: Path = Path(temp_dir) / "test.db"
        db_manager: DatabaseManager = DatabaseManager(db_path)

        # Create test table
        db_manager.execute("""
            CREATE TABLE test_many (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER NOT NULL
            )
        """)

        # Prepare batch data
        data: List[Tuple[str, int]] = [("item1", 10), ("item2", 20), ("item3", 30)]

        # Use executemany to insert multiple rows
        db_manager.executemany(
            "INSERT INTO test_many (name, value) VALUES (?, ?)", data
        )
        db_manager.commit()

        # Query all data back
        results: List[Dict[str, Any]] = db_manager.query(
            "SELECT * FROM test_many ORDER BY id"
        )

        # Verify correct number of rows and data
        assert len(results) == 3
        assert results[0]["name"] == "item1"
        assert results[0]["value"] == 10
        assert results[1]["name"] == "item2"
        assert results[2]["name"] == "item3"


def test_executescript() -> None:
    """Test the executescript method for running SQL scripts."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path: Path = Path(temp_dir) / "test.db"
        db_manager: DatabaseManager = DatabaseManager(db_path)

        # Create multiple tables and insert data in a single script
        script: str = """
            CREATE TABLE table1 (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE table2 (id INTEGER PRIMARY KEY, value INTEGER);
            INSERT INTO table1 (name) VALUES ('test1'), ('test2');
            INSERT INTO table2 (value) VALUES (100), (200);
        """

        # Execute the script
        db_manager.executescript(script)

        # Verify tables were created and data was inserted
        table1_results: List[Dict[str, Any]] = db_manager.query("SELECT * FROM table1")
        table2_results: List[Dict[str, Any]] = db_manager.query("SELECT * FROM table2")

        assert len(table1_results) == 2
        assert len(table2_results) == 2
        assert table1_results[0]["name"] == "test1"
        assert table2_results[1]["value"] == 200


def test_query() -> None:
    """Test the query method for retrieving multiple rows."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path: Path = Path(temp_dir) / "test.db"
        db_manager: DatabaseManager = DatabaseManager(db_path)

        # Create test table and insert sample data
        db_manager.execute(
            "CREATE TABLE test_query (id INTEGER PRIMARY KEY, name TEXT)"
        )
        db_manager.executemany(
            "INSERT INTO test_query (name) VALUES (?)",
            [("row1",), ("row2",), ("row3",)],
        )
        db_manager.commit()

        # Test query with no parameters
        all_results: List[Dict[str, Any]] = db_manager.query("SELECT * FROM test_query")
        assert len(all_results) == 3

        # Test query with parameters
        filtered_results: List[Dict[str, Any]] = db_manager.query(
            "SELECT * FROM test_query WHERE id > ?", (1,)
        )
        assert len(filtered_results) == 2
        assert filtered_results[0]["name"] == "row2"
        assert filtered_results[1]["name"] == "row3"

        # Test query with no results
        empty_results: List[Dict[str, Any]] = db_manager.query(
            "SELECT * FROM test_query WHERE name = ?", ("nonexistent",)
        )
        assert len(empty_results) == 0


def test_transaction_commit() -> None:
    """Test the transaction context manager with successful commit."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path: Path = Path(temp_dir) / "test.db"
        db_manager: DatabaseManager = DatabaseManager(db_path)

        # Create test table
        db_manager.execute(
            "CREATE TABLE test_transaction (id INTEGER PRIMARY KEY, name TEXT)"
        )

        # Use transaction context manager
        with db_manager.transaction():
            db_manager.execute(
                "INSERT INTO test_transaction (name) VALUES (?)", ("transaction_item",)
            )

        # Verify data was committed
        result: Optional[Dict[str, Any]] = db_manager.query_one(
            "SELECT * FROM test_transaction"
        )
        assert result is not None
        assert result["name"] == "transaction_item"


def test_transaction_rollback() -> None:
    """Test the transaction context manager with rollback on exception."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path: Path = Path(temp_dir) / "test.db"
        db_manager: DatabaseManager = DatabaseManager(db_path)

        # Create test table
        db_manager.execute(
            "CREATE TABLE test_rollback (id INTEGER PRIMARY KEY, name TEXT)"
        )

        # Insert initial data
        db_manager.execute("INSERT INTO test_rollback (name) VALUES (?)", ("initial",))
        db_manager.commit()

        # Transaction with exception
        try:
            with db_manager.transaction():
                db_manager.execute(
                    "INSERT INTO test_rollback (name) VALUES (?)",
                    ("will_be_rolled_back",),
                )
                # Raise an exception to trigger rollback
                raise ValueError("Test exception to trigger rollback")
        except ValueError:
            pass  # Expected exception

        # Verify data was rolled back
        results: List[Dict[str, Any]] = db_manager.query("SELECT * FROM test_rollback")
        assert len(results) == 1  # Only the initial insert should remain
        assert results[0]["name"] == "initial"


def test_manual_rollback() -> None:
    """Test manual rollback functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path: Path = Path(temp_dir) / "test.db"
        db_manager: DatabaseManager = DatabaseManager(db_path)

        # Create test table
        db_manager.execute(
            "CREATE TABLE test_manual_rollback (id INTEGER PRIMARY KEY, name TEXT)"
        )

        # Insert initial data and commit
        db_manager.execute(
            "INSERT INTO test_manual_rollback (name) VALUES (?)", ("initial",)
        )
        db_manager.commit()

        # Insert more data but roll back
        db_manager.execute(
            "INSERT INTO test_manual_rollback (name) VALUES (?)", ("will_roll_back",)
        )
        db_manager.rollback()

        # Verify rollback worked
        results: List[Dict[str, Any]] = db_manager.query(
            "SELECT * FROM test_manual_rollback"
        )
        assert len(results) == 1  # Only the initial insert should remain
        assert results[0]["name"] == "initial"


def test_table_exists() -> None:
    """Test the table_exists method."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path: Path = Path(temp_dir) / "test.db"
        db_manager: DatabaseManager = DatabaseManager(db_path)

        # Check non-existent table
        assert not db_manager.table_exists("nonexistent_table")

        # Create table
        db_manager.execute("CREATE TABLE existing_table (id INTEGER PRIMARY KEY)")

        # Check existing table
        assert db_manager.table_exists("existing_table")
        assert not db_manager.table_exists("still_nonexistent")
