import sqlite3
import json
from pathlib import Path
from config.settings import DB_PATH, NPCS_PATH, OPINIONS_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id      TEXT NOT NULL,
            content     TEXT NOT NULL,
            importance  INTEGER DEFAULT 5,
            tags        TEXT DEFAULT '',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_memories_npc
            ON memories(npc_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS emotions (
            npc_id      TEXT PRIMARY KEY,
            happy       INTEGER DEFAULT 50,
            angry       INTEGER DEFAULT 0,
            suspicious  INTEGER DEFAULT 0,
            stressed    INTEGER DEFAULT 30,
            excited     INTEGER DEFAULT 40,
            annoyed     INTEGER DEFAULT 0,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS relationships (
            npc_id              TEXT PRIMARY KEY,
            trust               INTEGER DEFAULT 50,
            friendship          INTEGER DEFAULT 30,
            hostility           INTEGER DEFAULT 0,
            respect             INTEGER DEFAULT 30,
            interactions_count  INTEGER DEFAULT 0,
            updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_id      TEXT NOT NULL,
            role        TEXT NOT NULL,
            message     TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_chat_npc
            ON chat_history(npc_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS npc_opinions (
            npc_id        TEXT NOT NULL,
            other_npc_id  TEXT NOT NULL,
            trust         INTEGER DEFAULT 50,
            respect       INTEGER DEFAULT 50,
            irritation    INTEGER DEFAULT 0,
            note          TEXT DEFAULT '',
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (npc_id, other_npc_id)
        );

        CREATE TABLE IF NOT EXISTS campus_facts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_text       TEXT NOT NULL,
            source_npc_id   TEXT,
            about_player    INTEGER DEFAULT 1,
            about_npc_id    TEXT,
            sensitivity     INTEGER DEFAULT 40,
            keep_secret     INTEGER DEFAULT 0,
            distorted_text  TEXT DEFAULT '',
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at      DATETIME
        );

        CREATE INDEX IF NOT EXISTS idx_facts_created
            ON campus_facts(created_at DESC);

        CREATE TABLE IF NOT EXISTS npc_knowledge (
            npc_id      TEXT NOT NULL,
            fact_id     INTEGER NOT NULL,
            status      TEXT NOT NULL DEFAULT 'known',
            hop         INTEGER DEFAULT 0,
            learned_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (npc_id, fact_id),
            FOREIGN KEY (fact_id) REFERENCES campus_facts(id)
        );

        CREATE INDEX IF NOT EXISTS idx_knowledge_npc
            ON npc_knowledge(npc_id, learned_at DESC);

        CREATE TABLE IF NOT EXISTS campus_state (
            id    INTEGER PRIMARY KEY CHECK (id = 1),
            tick  INTEGER DEFAULT 0
        );

        INSERT OR IGNORE INTO campus_state (id, tick) VALUES (1, 0);

        CREATE TABLE IF NOT EXISTS pending_gossip (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id      INTEGER NOT NULL,
            from_npc_id  TEXT NOT NULL,
            to_npc_id    TEXT NOT NULL,
            hop          INTEGER NOT NULL,
            status       TEXT NOT NULL,
            due_tick     INTEGER NOT NULL,
            UNIQUE(fact_id, to_npc_id)
        );

        CREATE TABLE IF NOT EXISTS gossip_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id      INTEGER NOT NULL,
            from_npc_id  TEXT NOT NULL,
            to_npc_id    TEXT NOT NULL,
            hop          INTEGER NOT NULL,
            tick         INTEGER NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Seed default emotion and relationship rows for each NPC
    with open(NPCS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for npc in data["npcs"]:
        mood = npc["initial_mood"]
        cursor.execute("""
            INSERT OR IGNORE INTO emotions (npc_id, happy, angry, suspicious, stressed, excited, annoyed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            npc["id"],
            mood["happy"], mood["angry"], mood["suspicious"],
            mood["stressed"], mood["excited"], mood["annoyed"]
        ))
        cursor.execute("""
            INSERT OR IGNORE INTO relationships (npc_id)
            VALUES (?)
        """, (npc["id"],))

    if OPINIONS_PATH.exists():
        with open(OPINIONS_PATH, "r", encoding="utf-8") as f:
            opinions = json.load(f).get("opinions", [])
        for opinion in opinions:
            cursor.execute(
                """
                INSERT OR IGNORE INTO npc_opinions
                    (npc_id, other_npc_id, trust, respect, irritation, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    opinion["npc_id"],
                    opinion["other_npc_id"],
                    opinion["trust"],
                    opinion["respect"],
                    opinion["irritation"],
                    opinion.get("note", ""),
                ),
            )

    conn.commit()
    conn.close()
