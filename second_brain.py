import streamlit as st

st.title("🧠 Second Brain - Test")
st.write("If you can see this, Streamlit is working!")

try:
    # Test secrets
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "NOT FOUND")
    db_url = st.secrets.get("SUPABASE_DB_URL", "NOT FOUND")
    
    st.success(f"API Key: {api_key[:20]}...")
    st.success(f"DB URL: {db_url[:30]}...")
    
except Exception as e:
    st.error(f"Error: {e}")

st.info("Basic test complete!")
