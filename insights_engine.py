"""
Insights Engine - Proactive Analysis System
Generates weekly digests, detects contradictions, identifies patterns
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import json
from execution.db_manager import get_db_manager
from execution.call_claude import get_claude_client
from execution.local_embeddings import get_embeddings

logger = logging.getLogger(__name__)


class InsightsEngine:
    """Generates proactive insights from conversation history."""
    
    def __init__(self):
        self.db = get_db_manager()
        self.claude = get_claude_client()
        self.embeddings = get_embeddings()
    
    def should_generate_weekly_digest(self) -> bool:
        """
        Check if it's time to generate a new weekly digest.
        Runs on Sundays after 6pm.
        
        Returns:
            True if digest should be generated
        """
        now = datetime.now()
        
        # Check if it's Sunday and after 6pm
        if now.weekday() != 6 or now.hour < 18:  # 6 = Sunday
            return False
        
        # Check if we already generated one this week
        query = """
        SELECT MAX(created_at) as last_digest
        FROM weekly_digests
        """
        
        try:
            result = self.db.execute_query(query)
            if result and result[0]['last_digest']:
                last_digest = datetime.fromisoformat(result[0]['last_digest'])
                days_since = (now - last_digest).days
                
                # Only generate if more than 6 days since last digest
                return days_since >= 6
            
            # No digest found, generate one
            return True
            
        except Exception as e:
            logger.error(f"Error checking digest status: {e}")
            return False
    
    def generate_weekly_digest(self) -> Optional[str]:
        """
        Generate weekly digest of conversation patterns.
        
        Returns:
            Digest ID if successful, None otherwise
        """
        try:
            # Get conversations from past 7 days
            week_ago = datetime.now() - timedelta(days=7)
            
            query = """
            SELECT id, title, full_transcript, metadata, created_at
            FROM conversations
            WHERE created_at >= %s
            ORDER BY created_at DESC
            """
            
            conversations = self.db.execute_query(query, (week_ago.isoformat(),))
            
            if not conversations:
                logger.info("No conversations in past week, skipping digest")
                return None
            
            # Extract topics and patterns
            topics = self._extract_topics(conversations)
            patterns = self._identify_patterns(conversations)
            
            # Generate digest using Claude
            digest_prompt = f"""Analyze these conversation patterns from the past week and create a concise weekly digest.

CONVERSATION COUNT: {len(conversations)}

TOP TOPICS:
{json.dumps(topics, indent=2)}

PATTERNS:
{json.dumps(patterns, indent=2)}

Create a weekly digest with:
1. Summary of conversation activity
2. Top 3 insights or patterns
3. Notable themes or shifts in thinking
4. 1-2 actionable suggestions

Be concise, insightful, and investor-focused. Format in clear sections."""

            # Generate digest
            digest_text = ""
            for chunk in self.claude.chat_stream(
                messages=[{"role": "user", "content": digest_prompt}],
                system_prompt="You are generating a weekly insight digest for an investor. Be concise and actionable."
            ):
                digest_text += chunk
            
            # Save to database
            week_start = week_ago.date()
            week_end = datetime.now().date()
            
            save_query = """
            INSERT INTO weekly_digests 
            (week_start, week_end, conversation_count, top_topics, digest_content)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """
            
            digest_id = self.db.execute_insert(
                save_query,
                (week_start, week_end, len(conversations), topics, digest_text)
            )
            
            logger.info(f"✓ Weekly digest generated: {digest_id}")
            
            # Send email if configured
            self._send_digest_email(digest_text, week_start, week_end)
            
            return digest_id
            
        except Exception as e:
            logger.error(f"Error generating weekly digest: {e}", exc_info=True)
            return None
    
    def check_for_contradictions(
        self, 
        new_message: str, 
        current_conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if new message contradicts past conversations.
        Conservative detection - only flags clear contradictions.
        
        Args:
            new_message: New user message to check
            current_conversation_id: Current conversation ID to exclude
            
        Returns:
            Contradiction alert dict if found, None otherwise
        """
        try:
            # Generate embedding for new message
            message_embedding = self.embeddings.embed_query(new_message)
            embedding_str = '[' + ','.join(str(float(x)) for x in message_embedding) + ']'
            
            # Find similar past conversations (exclude last 30 days to avoid rapid iteration)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            query = """
            SELECT 
                id, title, full_transcript, created_at,
                1 - (embedding <=> %s::vector) AS similarity
            FROM conversations
            WHERE created_at < %s
            AND id::text != %s
            ORDER BY similarity DESC
            LIMIT 5
            """
            
            similar_convs = self.db.execute_query(
                query,
                (embedding_str, thirty_days_ago.isoformat(), current_conversation_id)
            )
            
            if not similar_convs or similar_convs[0]['similarity'] < 0.7:
                # No sufficiently similar past conversations
                return None
            
            # Check for contradictions using Claude
            for past_conv in similar_convs[:3]:  # Check top 3 most similar
                contradiction_check = f"""Compare these two statements for CLEAR contradictions only:

CURRENT (Today): "{new_message}"

PAST ({past_conv['created_at'][:10]}): "{past_conv['title']}"

Are these CLEARLY contradictory? Only flag if they express opposite views on the same topic.

Respond ONLY with:
- "YES: [brief explanation]" if clearly contradictory
- "NO" if not contradictory or just nuanced differences"""

                response = ""
                for chunk in self.claude.chat_stream(
                    messages=[{"role": "user", "content": contradiction_check}],
                    system_prompt="You detect clear contradictions. Be conservative - only flag obvious opposites."
                ):
                    response += chunk
                
                if response.strip().upper().startswith("YES"):
                    # Contradiction found!
                    explanation = response.split(":", 1)[1].strip() if ":" in response else "Views conflict"
                    
                    alert = {
                        "alert_type": "contradiction",
                        "title": "Potential Contradiction Detected",
                        "content": f"Today: {new_message}\n\nPast ({past_conv['created_at'][:10]}): {past_conv['title']}\n\nNote: {explanation}",
                        "related_conversation_ids": [current_conversation_id, str(past_conv['id'])],
                        "severity": "medium"
                    }
                    
                    # Save alert to database
                    self._save_alert(alert)
                    
                    logger.info(f"✓ Contradiction detected and saved")
                    return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking contradictions: {e}", exc_info=True)
            return None
    
    def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """
        Get all unviewed, non-dismissed alerts.
        
        Returns:
            List of alert dicts
        """
        try:
            query = """
            SELECT *
            FROM insight_alerts
            WHERE dismissed = FALSE
            ORDER BY created_at DESC
            LIMIT 10
            """
            
            alerts = self.db.execute_query(query)
            return alerts if alerts else []
            
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert."""
        try:
            query = """
            UPDATE insight_alerts
            SET dismissed = TRUE, dismissed_at = NOW()
            WHERE id = %s
            """
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (alert_id,))
                cursor.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error dismissing alert: {e}")
            return False
    
    def get_latest_digest(self) -> Optional[Dict[str, Any]]:
        """Get the most recent weekly digest."""
        try:
            query = """
            SELECT *
            FROM weekly_digests
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            result = self.db.execute_query(query)
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error fetching digest: {e}")
            return None
    
    def _extract_topics(self, conversations: List[Dict]) -> List[str]:
        """Extract top topics from conversations."""
        topic_counts = {}
        
        for conv in conversations:
            metadata = conv.get('metadata', {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            topics = metadata.get('topics', [])
            for topic in topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Return top 10 topics
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, count in sorted_topics[:10]]
    
    def _identify_patterns(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Identify patterns in conversation data."""
        return {
            "total_conversations": len(conversations),
            "avg_per_day": round(len(conversations) / 7, 1),
            "most_active_day": self._get_most_active_day(conversations)
        }
    
    def _get_most_active_day(self, conversations: List[Dict]) -> str:
        """Find most active day of the week."""
        day_counts = {}
        
        for conv in conversations:
            created_at = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
            day_name = created_at.strftime('%A')
            day_counts[day_name] = day_counts.get(day_name, 0) + 1
        
        if not day_counts:
            return "Unknown"
        
        most_active = max(day_counts.items(), key=lambda x: x[1])
        return most_active[0]
    
    def _save_alert(self, alert: Dict[str, Any]) -> Optional[str]:
        """Save alert to database."""
        try:
            query = """
            INSERT INTO insight_alerts
            (alert_type, title, content, related_conversation_ids, severity)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """
            
            alert_id = self.db.execute_insert(
                query,
                (
                    alert['alert_type'],
                    alert['title'],
                    alert['content'],
                    alert.get('related_conversation_ids', []),
                    alert.get('severity', 'low')
                )
            )
            
            return alert_id
            
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
            return None
    
    def _send_digest_email(self, digest: str, week_start, week_end):
        """Send digest via email if configured."""
        try:
            # Check if email is configured
            if "EMAIL_ADDRESS" not in st.secrets:
                logger.info("Email not configured, skipping digest email")
                return
            
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Athena Weekly Digest - {week_start} to {week_end}"
            msg['From'] = st.secrets.get("EMAIL_FROM", "athena@yourdomain.com")
            msg['To'] = st.secrets["EMAIL_ADDRESS"]
            
            # Create HTML version
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #667eea;">🧠 Athena Weekly Digest</h2>
                <p style="color: #666;">Week of {week_start} to {week_end}</p>
                <hr style="border: 1px solid #eee;">
                <div style="white-space: pre-wrap;">{digest}</div>
                <hr style="border: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">
                  <a href="{st.secrets.get('ATHENA_URL', '#')}">Open Athena</a> to view more details
                </p>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            # Send email
            with smtplib.SMTP(st.secrets.get("SMTP_HOST", "smtp.gmail.com"), 
                            st.secrets.get("SMTP_PORT", 587)) as server:
                server.starttls()
                server.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
                server.send_message(msg)
            
            logger.info("✓ Digest email sent")
            
        except Exception as e:
            logger.warning(f"Could not send digest email: {e}")


@st.cache_resource
def get_insights_engine():
    """Get or create the global insights engine instance."""
    return InsightsEngine()
