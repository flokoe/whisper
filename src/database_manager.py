"""SQLite database manager for the Whisper application."""

import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class DatabaseManager:
    """A manager class for SQLite database operations.

    This class provides a simple interface for database operations
    and handles database connections, transactions, and migrations.
    """

    MIGRATION_FILE_PATTERN = r"^\d{14}_([a-z0-9_]+)\.sql$"  # YYYYMMDDHHMMSS format

    def __init__(self, db_path: Union[str, Path]) -> None:
        """Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self.logger = logging.getLogger(__name__)

    @property
    def conn(self) -> sqlite3.Connection:
        """Get the database connection, creating it if necessary."""
        if self._conn is None:
            # Ensure the parent directory exists
            os.makedirs(self.db_path.parent, exist_ok=True)

            # Create a new connection with row factory
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row

            # Enable foreign keys support
            self._conn.execute("PRAGMA foreign_keys = ON")

            self.logger.debug(f"Connected to database at {self.db_path}")

        return self._conn

    def close(self) -> None:
        """Close the database connection if it's open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self.logger.debug("Database connection closed")

    def execute(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> sqlite3.Cursor:
        """Execute an SQL query with optional parameters.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            The cursor object for the executed query
        """
        if params is None:
            return self.conn.execute(query)
        return self.conn.execute(query, params)

    def executemany(
        self, query: str, params_list: List[Tuple[Any, ...]]
    ) -> sqlite3.Cursor:
        """Execute an SQL query with multiple sets of parameters.

        Args:
            query: SQL query string
            params_list: List of parameter tuples

        Returns:
            The cursor object for the executed query
        """
        return self.conn.executemany(query, params_list)

    def executescript(self, script: str) -> sqlite3.Cursor:
        """Execute an SQL script.

        Args:
            script: SQL script string

        Returns:
            The cursor object for the executed script
        """
        return self.conn.executescript(script)

    def query(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a query and return all results as a list of dictionaries.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            List of result rows as dictionaries
        """
        cursor = self.execute(query, params)
        results = cursor.fetchall()
        # Convert sqlite3.Row objects to dictionaries
        return [dict(row) for row in results]

    def query_one(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute a query and return the first result as a dictionary.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            First result row as a dictionary, or None if no results
        """
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def commit(self) -> None:
        """Commit the current transaction."""
        self.conn.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self.conn.rollback()

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if the table exists, False otherwise
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = self.query_one(query, (table_name,))
        return result is not None

    def migrations(self, migrations_dir: Optional[Path] = None) -> int:
        """Execute database migrations from SQL files.

        This method:
        1. Creates the migrations tracking table if it doesn't exist
        2. Finds and executes pending migrations in order
        3. Tracks applied migrations

        Args:
            migrations_dir: Directory containing migration SQL files (optional)
                If not provided, uses a default 'migrations' directory in the src folder

        Returns:
            Number of migrations applied
        """

        # Set up migrations directory
        if migrations_dir is None:
            current_dir = Path(__file__).parent
            migrations_dir = current_dir / "migrations"

        # Ensure migrations table exists
        create_migrations_table_sql = """
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """
        with self.conn:
            self.execute(create_migrations_table_sql)

        # Get applied migrations
        applied_migrations = [row['name'] for row in self.query('SELECT name FROM migrations;')]
        pattern = re.compile(self.MIGRATION_FILE_PATTERN)

        # Apply migrations
        for filename in sorted(os.listdir(migrations_dir)):
            match = pattern.match(filename)
            if match:
                name = match.groups()
                
                if name not in applied_migrations:
                    file_path = migrations_dir / filename

                    with open(file_path, "r") as f:
                        sql = f.read()

                    # Execute migration in a transaction
                    with self.conn:
                        # Execute the migration SQL
                        self.executescript(sql)

                        # Record that this migration was applied
                        self.execute('INSERT INTO migrations (name) VALUES (?);', (name,))

                    self.logger.info(f"Successfully applied migration `{filename}`")
                else:
                    self.logger.debug(f"Skipping migration `{filename}`")
