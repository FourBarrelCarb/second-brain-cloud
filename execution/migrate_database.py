"""
Database Migration Script for Phase 2B+C
Creates new tables for insights and alerts
"""

from execution.db_manager import get_db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create new tables for insights system."""
    
    db = get_db_manager()
    
    # Table 1: insight_alerts
    logger.info("Creating insight_alerts table...")
    
    create_alerts_table = """
    CREATE TABLE IF NOT EXISTS insight_alerts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        alert_type VARCHAR(50) NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        related_conversation_ids TEXT[],
        severity VARCHAR(20) DEFAULT 'low',
        dismissed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        viewed_at TIMESTAMPTZ,
        dismissed_at TIMESTAMPTZ
    );
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_alerts_table)
        cursor.close()
    
    logger.info("✓ insight_alerts table created")
    
    # Create indexes for alerts
    logger.info("Creating indexes for insight_alerts...")
    
    create_alerts_indexes = """
    CREATE INDEX IF NOT EXISTS idx_alerts_type ON insight_alerts(alert_type);
    CREATE INDEX IF NOT EXISTS idx_alerts_dismissed ON insight_alerts(dismissed);
    CREATE INDEX IF NOT EXISTS idx_alerts_created ON insight_alerts(created_at DESC);
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_alerts_indexes)
        cursor.close()
    
    logger.info("✓ Indexes created for insight_alerts")
    
    # Table 2: weekly_digests
    logger.info("Creating weekly_digests table...")
    
    create_digests_table = """
    CREATE TABLE IF NOT EXISTS weekly_digests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        week_start DATE NOT NULL,
        week_end DATE NOT NULL,
        conversation_count INT,
        top_topics TEXT[],
        digest_content TEXT NOT NULL,
        emailed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_digests_table)
        cursor.close()
    
    logger.info("✓ weekly_digests table created")
    
    # Create indexes for digests
    logger.info("Creating indexes for weekly_digests...")
    
    create_digests_indexes = """
    CREATE INDEX IF NOT EXISTS idx_digests_week ON weekly_digests(week_start DESC);
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_digests_indexes)
        cursor.close()
    
    logger.info("✓ Indexes created for weekly_digests")
    
    logger.info("=" * 50)
    logger.info("✅ Database migration complete!")
    logger.info("=" * 50)


if __name__ == "__main__":
    logger.info("Starting Phase 2B+C database migration...")
    run_migration()
    logger.info("Migration finished successfully")
