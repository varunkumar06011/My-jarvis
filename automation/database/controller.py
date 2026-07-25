import csv
import io
import json
import sqlite3
from typing import Any, Optional

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager


class DatabaseEngine:
    """Database automation — initially read-only. Supports SQLite, MySQL, PostgreSQL."""

    SUPPORTED_DRIVERS = {
        "sqlite": "sqlite3",
        "mysql": "pymysql",
        "postgresql": "psycopg2",
    }

    def _connect(self, params: dict):
        db_type = params.get("type", "sqlite")
        if db_type == "sqlite":
            path = params.get("path", params.get("database", ""))
            return sqlite3.connect(path)
        elif db_type == "mysql":
            import pymysql
            return pymysql.connect(
                host=params.get("host", "localhost"),
                port=params.get("port", 3306),
                user=params.get("user", "root"),
                password=params.get("password", ""),
                database=params.get("database", ""),
            )
        elif db_type == "postgresql":
            import psycopg2
            return psycopg2.connect(
                host=params.get("host", "localhost"),
                port=params.get("port", 5432),
                user=params.get("user", "postgres"),
                password=params.get("password", ""),
                dbname=params.get("database", ""),
            )
        raise ValueError(f"Unsupported database type: {db_type}")

    def query(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        sql = params.get("sql", "").strip()
        if not sql:
            return {"status": "error", "error": "No SQL provided"}

        # Enforce read-only
        sql_upper = sql.upper()
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
        for kw in forbidden:
            if kw in sql_upper:
                return {"status": "blocked", "error": f"Write operation '{kw}' not allowed in read-only mode"}

        try:
            conn = self._connect(params)
            conn.row_factory = sqlite3.Row if params.get("type", "sqlite") == "sqlite" else None
            cursor = conn.cursor()
            cursor.execute(sql)

            if params.get("type", "sqlite") == "sqlite":
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [dict(row) for row in cursor.fetchall()]
            else:
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

            conn.close()
            return {"status": "ok", "columns": columns, "rows": rows[:100], "row_count": len(rows)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def schema(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        try:
            conn = self._connect(params)
            cursor = conn.cursor()
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'" if params.get("type", "sqlite") == "sqlite" else
                          "SELECT table_name FROM information_schema.tables")
            tables = cursor.fetchall()
            conn.close()
            return {"status": "ok", "tables": [t[0] for t in tables]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def explain(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        sql = params.get("sql", "")
        try:
            conn = self._connect(params)
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}" if params.get("type", "sqlite") == "sqlite" else f"EXPLAIN {sql}")
            rows = cursor.fetchall()
            conn.close()
            return {"status": "ok", "plan": [str(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def export_csv(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        sql = params.get("sql", "")
        try:
            conn = self._connect(params)
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()

            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(columns)
            writer.writerows(rows)

            artifact = artifact_manager.save_file(
                name=params.get("name", "query_export"),
                content=buf.getvalue().encode("utf-8"),
                automation_id=ctx.automation_id,
                extension="csv",
            )
            return {"status": "ok", "artifact_id": artifact.id, "rows": len(rows)}
        except Exception as e:
            return {"status": "error", "error": str(e)}


database_engine = DatabaseEngine()
