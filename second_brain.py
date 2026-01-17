"""
Second Brain - Cloud-Native Application with Error Logging
"""

import streamlit as st
import sys
import traceback

st.set_page_config(
    page_title="Second Brain",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Second Brain - Startup Diagnostics")

# Step 1: Test basic imports
st.write("**Step 1:** Testing basic imports...")
try:
    from datetime import datetime
    from uuid import uuid4
    import logging
    st.success("✓ Basic imports OK")
except Exception as e:
    st.error(f"✗ Basic imports failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

# Step 2: Test secrets
st.write("**Step 2:** Testing secrets...")
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
    db_url = st.secrets["SUPABASE_DB_URL"]
    st.success(f"✓ Secrets loaded (API: {api_key[:20]}..., DB: {db_url[:30]}...)")
except Exception as e:
    st.error(f"✗ Secrets failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

# Step 3: Test execution imports
st.write("**Step 3:** Testing execution module imports...")
try:
    from execution.db_manager import get_db_manager
    st.success("✓ db_manager imported")
except Exception as e:
    st.error(f"✗ db_manager import failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

try:
    from execution.local_embeddings import LocalEmbeddings
    st.success("✓ local_embeddings imported")
except Exception as e:
    st.error(f"✗ local_embeddings import failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

try:
    from execution.call_claude import get_claude_client
    st.success("✓ call_claude imported")
except Exception as e:
    st.error(f"✗ call_claude import failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

try:
    from execution.retrieve_chats import hybrid_retrieve
    st.success("✓ retrieve_chats imported")
except Exception as e:
    st.error(f"✗ retrieve_chats import failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

try:
    from execution.save_conversation import save_conversation
    st.success("✓ save_conversation imported")
except Exception as e:
    st.error(f"✗ save_conversation import failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

# Step 4: Test database connection
st.write("**Step 4:** Testing database connection...")
try:
    db = get_db_manager()
    st.success("✓ Database manager created")
except Exception as e:
    st.error(f"✗ Database manager failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

# Step 5: Test embeddings model
st.write("**Step 5:** Testing embeddings model (may take 30-60 seconds first time)...")
try:
    embeddings = LocalEmbeddings()
    st.success("✓ Embeddings model loaded")
except Exception as e:
    st.error(f"✗ Embeddings model failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

# Step 6: Test Claude client
st.write("**Step 6:** Testing Claude client...")
try:
    claude = get_claude_client()
    st.success("✓ Claude client created")
except Exception as e:
    st.error(f"✗ Claude client failed: {e}")
    st.code(traceback.format_exc())
    st.stop()

# All tests passed
st.success("🎉 ALL STARTUP CHECKS PASSED!")
st.info("The app can now be updated with the full chat interface.")
st.balloons()
