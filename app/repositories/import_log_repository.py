from app.repositories.base_repository import BaseRepository

class ImportLogRepository(BaseRepository):
    """Centralized repository for IMPORT_LOG table access."""

    @classmethod
    def log_import(cls, import_type, filename, total_records, successful_records, failed_records, imported_by, status):
        return cls.execute(
            "INSERT INTO IMPORT_LOG (import_type, filename, total_records, successful_records, failed_records, imported_by, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (import_type, filename, total_records, successful_records, failed_records, imported_by, status)
        )
