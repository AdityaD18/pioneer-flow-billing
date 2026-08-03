from app.models.database import query_db, execute_db, get_db_connection, get_db, execute_transaction

class BaseRepository:
    """Base Data Repository providing query and execution wrappers."""

    @staticmethod
    def query(query_str, args=(), one=False):
        return query_db(query_str, args=args, one=one)

    @staticmethod
    def execute(query_str, args=()):
        return execute_db(query_str, args=args)

    @staticmethod
    def get_connection():
        return get_db_connection()

    @staticmethod
    def execute_tx(queries_with_args):
        return execute_transaction(queries_with_args)
