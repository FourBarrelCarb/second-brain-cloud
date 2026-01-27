from execution.db_manager import get_db_manager
from execution.local_embeddings import get_embeddings

def main():
    db = get_db_manager()
    embeddings = get_embeddings()

    rows = db.execute_query("""
        SELECT id, full_transcript
        FROM conversations
        WHERE embedding IS NULL
    """)

    print(f"Found {len(rows)} conversations to re-embed")

    for i, row in enumerate(rows, 1):
        emb = embeddings.embed_query(row["full_transcript"])
        emb_str = "[" + ",".join(map(str, emb)) + "]"

        db.execute("""
            UPDATE conversations
            SET embedding = %s::vector
            WHERE id = %s
        """, (emb_str, row["id"]))

        print(f"[{i}/{len(rows)}] Updated {row['id']}")

    print("✅ Re-embedding complete")

if __name__ == "__main__":
    main()
