import os
import sqlalchemy

from pathlib import Path

class Database:
    """ Database session """
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

        self.create_database(self.database_path)

    def engine(self) -> sqlalchemy.create_engine:
        """
        Creates a database engine

        Args:
            None.

        Returns:
            sqlalchemy.create_engine: An Engine instance
        """
        database_engine = sqlalchemy.create_engine(
            url=self.database_uri(),
            pool_size=10,
            max_overflow=8
        )

        return database_engine

    def create_database(self, database_path: str) -> None:
        """
        Creates the SQLite database at the given path 
        
        Args:
            database_path (str): The path of the SQLite database.
        
        Returns:
            None.
        """
        if not os.path.exists(database_path):
            os.mkdir(database_path.replace("nyt.db", ""))
            Path(database_path).touch()

    def database_uri(self) -> str:
        """
        Returns the database uri
        """
        return f"sqlite:///{self.database_path}"
