"""
Database Manager - Cloud-Native Version
Uses Streamlit secrets instead of environment variables
"""

import psycopg2
from psycopg2 import pool, extras
from contextlib import contextmanager
import logging
import streamlit as st

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL connection pool for Supabase."""
    
    def __init__(self):
        self._pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Create connection pool using Streamlit secrets."""
        try:
            db_url = st.secrets["SUPABASE_DB_URL"]
            
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,  # Lower for cloud (shared resources)
                dsn=db_url,
                cursor_factory=extras.RealDictCursor
            )
            logger.info("✓ Database pool initialized")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for safe database connections."""
        if self._pool is None:
            raise RuntimeError("Database pool not initialized")
        
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    def execute_query(self, query: str, params=None, fetch=True):
        """Execute query and return results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch:
                results = cursor.fetchall()
                cursor.close()
                return results
            else:
                conn.commit()
                cursor.close()
                return None
    
    def execute_insert(self, query: str, params, return_id=True):
        """Execute INSERT and return new ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if return_id:
                result = cursor.fetchone()
                conn.commit()
                cursor.close()
                return result['id'] if result else None
            else:
                conn.commit()
                cursor.close()
                return None


@st.cache_resource
def get_db_manager():
    """Cached database manager - creates once per session."""
    return DatabaseManager()
