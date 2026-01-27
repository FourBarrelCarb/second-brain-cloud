"""
Database Connection Manager - FINAL FIXED VERSION
Handles PostgreSQL connection pooling with proper lifecycle management
"""

import psycopg2
from psycopg2 import pool, extras
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connection pool with proper connection lifecycle.
    Uses connection pooling for performance and proper cleanup.
    """
    
    def __init__(self):
        """Initialize database connection pool."""
        self._pool: Optional[pool.ThreadedConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Create the connection pool."""
        try:
            db_url = st.secrets["SUPABASE_DB_URL"]
            
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=db_url,
                cursor_factory=extras.RealDictCursor
            )
            logger.info("✓ Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise ConnectionError(f"Cannot connect to database: {e}")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for safe database connections.
        
        Connection is automatically returned to pool when done.
        """
        if self._pool is None:
            raise RuntimeError("Database pool not initialized")
        
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
            conn.commit()  # CRITICAL: Commit before returning to pool
            
    except psycopg2.Error as e:
        try:
            if conn and not conn.closed:
                conn.rollback()
        except Exception:
            pass
        raise

            
        finally:
            if conn:
                self._pool.putconn(conn)
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
    
    def execute_insert(
        self,
        query: str,
        params: tuple
    ) -> Optional[str]:
        """Execute an INSERT query and return the new ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            cursor.close()
            return result['id'] if result else None
    
    def test_connection(self) -> bool:
        """Test if database connection is working."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def close_pool(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("✓ Database connection pool closed")


# CRITICAL: Global database manager with caching
@st.cache_resource
def get_db_manager():
    """
    Get or create the global database manager instance.
    Cached by Streamlit so only one pool exists per session.
    
    THIS DECORATOR IS CRITICAL - Without it, connections fail.
    """
    return DatabaseManager()
