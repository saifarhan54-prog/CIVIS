"""
Database Manager for CIVIS
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "civis_enhanced.db"):
        self.db_path = Path(__file__).parent.parent / db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database with all tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                object_ids TEXT NOT NULL,
                reason TEXT,
                risk_score INTEGER,
                status TEXT DEFAULT 'REVIEW REQUIRED',
                is_demo INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # Zones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                zone_type TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                width REAL NOT NULL,
                height REAL NOT NULL,
                enabled INTEGER DEFAULT 1,
                config TEXT
            )
        """)
        
        # Vehicles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_plate TEXT UNIQUE,
                vehicle_type TEXT,
                color TEXT,
                authorized INTEGER DEFAULT 0,
                watchlist INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT,
                notes TEXT
            )
        """)
        
        # Faces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id TEXT UNIQUE,
                name TEXT,
                authorized INTEGER DEFAULT 0,
                encoding TEXT,
                liveness_score REAL,
                created_at TEXT,
                last_seen TEXT
            )
        """)
        
        # Access logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id TEXT,
                face_id INTEGER,
                access_granted INTEGER,
                spoofing_detected INTEGER DEFAULT 0,
                method TEXT,
                location TEXT,
                timestamp TEXT,
                FOREIGN KEY (face_id) REFERENCES faces(id)
            )
        """)
        
        # Behavioral events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS behavioral_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                object_id TEXT,
                duration REAL,
                location TEXT,
                severity TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Database initialized with all tables")
    
    def add_event(self, event: Dict) -> int:
        """Add new event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO events (type, severity, timestamp, object_ids, reason, risk_score, is_demo, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("type"),
            event.get("severity", "MEDIUM"),
            datetime.utcnow().isoformat(),
            json.dumps(event.get("object_ids", [])),
            event.get("reason", ""),
            event.get("risk_score", 50),
            event.get("is_demo", 0),
            json.dumps(event.get("metadata", {}))
        ))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id
    
    def get_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM events 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            event = dict(row)
            event["object_ids"] = json.loads(event["object_ids"])
            event["metadata"] = json.loads(event.get("metadata") or "{}")
            event["is_demo"] = bool(event["is_demo"])
            events.append(event)
        
        return events
    
    def get_event(self, event_id: int) -> Optional[Dict]:
        """Get specific event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        event = dict(row)
        event["object_ids"] = json.loads(event["object_ids"])
        event["metadata"] = json.loads(event.get("metadata") or "{}")
        return event
    
    def add_zone(self, zone: Dict) -> int:
        """Add monitoring zone"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO zones (name, zone_type, x, y, width, height, enabled, config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            zone.get("name"),
            zone.get("zone_type"),
            zone.get("x"),
            zone.get("y"),
            zone.get("width"),
            zone.get("height"),
            zone.get("enabled", 1),
            json.dumps(zone.get("config", {}))
        ))
        
        zone_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return zone_id
    
    def get_zones(self) -> List[Dict]:
        """Get all zones"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM zones")
        rows = cursor.fetchall()
        conn.close()
        
        zones = []
        for row in rows:
            zone = dict(row)
            zone["enabled"] = bool(zone["enabled"])
            zone["config"] = json.loads(zone.get("config") or "{}")
            zones.append(zone)
        
        return zones
    
    def delete_zone(self, zone_id: int):
        """Delete zone"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM zones WHERE id = ?", (zone_id,))
        conn.commit()
        conn.close()
    
    def add_vehicle(self, vehicle: Dict) -> int:
        """Add or update vehicle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO vehicles (license_plate, vehicle_type, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(license_plate) DO UPDATE SET last_seen = ?
        """, (
            vehicle.get("license_plate"),
            vehicle.get("vehicle_type", "unknown"),
            now,
            now,
            now
        ))
        
        vehicle_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return vehicle_id
    
    def get_vehicles(self) -> List[Dict]:
        """Get all detected vehicles"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM vehicles ORDER BY last_seen DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_faces(self) -> List[Dict]:
        """Get all recognized faces"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM faces ORDER BY last_seen DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
