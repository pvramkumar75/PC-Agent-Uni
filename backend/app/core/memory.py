import sqlite3
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
import json
import os

class MemoryManager:
    def __init__(self):
        # Structured Memory (SQLite)
        os.makedirs(settings.MEMORY_DIR, exist_ok=True)
        self.sqlite_conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
        self._init_sqlite()

        # Vector Memory (ChromaDB)
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name="procurement_docs")

    def _init_sqlite(self):
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_name TEXT,
                material TEXT,
                unit_price REAL,
                qty REAL,
                total REAL,
                currency TEXT,
                delivery_weeks INTEGER,
                payment_terms TEXT,
                date TEXT,
                file_path TEXT,
                raw_json TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendor_performance (
                vendor_name TEXT PRIMARY KEY,
                avg_delay_days REAL,
                quality_score REAL,
                price_competitiveness REAL,
                last_interaction TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                fact TEXT,
                usage_count INTEGER DEFAULT 1,
                last_used TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.sqlite_conn.commit()

    def store_learned_fact(self, category: str, fact: str):
        """Stores a learned pattern, user preference, or discovered file location."""
        cursor = self.sqlite_conn.cursor()
        # Check if fact already exists to increment usage
        cursor.execute("SELECT id, usage_count FROM personal_knowledge WHERE fact = ?", (fact,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE personal_knowledge SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP WHERE id = ?", (row[0],))
        else:
            cursor.execute("INSERT INTO personal_knowledge (category, fact) VALUES (?, ?)", (category, fact))
        self.sqlite_conn.commit()

    def get_learned_facts(self, category: str = None, limit: int = 10) -> List[str]:
        cursor = self.sqlite_conn.cursor()
        if category:
            cursor.execute("SELECT fact FROM personal_knowledge WHERE category = ? ORDER BY usage_count DESC, last_used DESC LIMIT ?", (category, limit))
        else:
            cursor.execute("SELECT fact FROM personal_knowledge ORDER BY usage_count DESC, last_used DESC LIMIT ?", (limit,))
        return [row[0] for row in cursor.fetchall()]

    def store_quote(self, data: dict):
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            INSERT INTO quotes (vendor_name, material, unit_price, qty, total, currency, delivery_weeks, payment_terms, date, file_path, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('vendor_name'), data.get('material'), data.get('unit_price'),
            data.get('qty'), data.get('total'), data.get('currency'),
            data.get('delivery_weeks'), data.get('payment_terms'), data.get('date'),
            data.get('file_path'), json.dumps(data)
        ))
        self.sqlite_conn.commit()
        
        # Also store in vector DB for semantic search
        self.collection.add(
            documents=[json.dumps(data)],
            metadatas=[{"vendor": data.get('vendor_name'), "material": data.get('material')}],
            ids=[f"quote_{cursor.lastrowid}"]
        )

    def search_history(self, query: str, limit: int = 5):
        # Semantic search in ChromaDB
        results = self.collection.query(query_texts=[query], n_results=limit)
        return results['documents']

memory_manager = MemoryManager()
