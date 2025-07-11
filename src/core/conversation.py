"""
Conversation management
Handles conversation state, history, and persistence
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import logging

from constants import MAX_CONVERSATION_HISTORY


class Conversation:
    """Manages a single conversation session"""
    
    def __init__(self, profile_id: str, conversation_id: str = None):
        self.profile_id = profile_id
        self.conversation_id = conversation_id or self._generate_id()
        self.messages = []
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'message_count': 0,
            'topics': [],
            'safety_incidents': 0
        }
    
    def _generate_id(self) -> str:
        """Generate unique conversation ID"""
        return f"conv_{self.profile_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add message to conversation"""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.messages.append(message)
        self.metadata['message_count'] += 1
        self.metadata['updated_at'] = datetime.now().isoformat()
        
        # Limit conversation history
        if len(self.messages) > MAX_CONVERSATION_HISTORY:
            self.messages = self.messages[-MAX_CONVERSATION_HISTORY:]
    
    def get_messages_for_model(self) -> List[Dict]:
        """Get messages formatted for Ollama API"""
        return [
            {'role': msg['role'], 'content': msg['content']}
            for msg in self.messages
        ]
    
    def to_dict(self) -> Dict:
        """Convert conversation to dictionary"""
        return {
            'conversation_id': self.conversation_id,
            'profile_id': self.profile_id,
            'messages': self.messages,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Conversation':
        """Create conversation from dictionary"""
        conv = cls(data['profile_id'], data['conversation_id'])
        conv.messages = data['messages']
        conv.metadata = data['metadata']
        return conv


class ConversationManager:
    """Manages all conversations across profiles"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db_path = self.config.data_path / "conversations.db"
        
        # Initialize database
        self._init_db()
        
        # Active conversations cache
        self.active_conversations = {}
    
    def _init_db(self):
        """Initialize conversations database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_profile_id 
                ON conversations(profile_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_updated_at 
                ON conversations(updated_at)
            ''')
    
    def create_conversation(self, profile_id: str) -> Conversation:
        """Create new conversation"""
        conv = Conversation(profile_id)
        self.active_conversations[conv.conversation_id] = conv
        self.save_conversation(conv)
        
        self.logger.info(f"Created conversation {conv.conversation_id} for profile {profile_id}")
        return conv
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        # Check cache first
        if conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]
        
        # Load from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT data FROM conversations WHERE conversation_id = ?',
                (conversation_id,)
            )
            row = cursor.fetchone()
            
            if row:
                data = json.loads(row[0])
                conv = Conversation.from_dict(data)
                self.active_conversations[conversation_id] = conv
                return conv
        
        return None
    
    def save_conversation(self, conversation: Conversation):
        """Save conversation to database"""
        data = json.dumps(conversation.to_dict())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO conversations 
                (conversation_id, profile_id, created_at, updated_at, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                conversation.conversation_id,
                conversation.profile_id,
                conversation.metadata['created_at'],
                conversation.metadata['updated_at'],
                data
            ))
    
    def get_profile_conversations(self, profile_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversations for a profile"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT conversation_id, created_at, updated_at, data
                FROM conversations
                WHERE profile_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (profile_id, limit))
            
            conversations = []
            for row in cursor:
                data = json.loads(row[3])
                conversations.append({
                    'conversation_id': row[0],
                    'created_at': row[1],
                    'updated_at': row[2],
                    'message_count': data['metadata']['message_count'],
                    'preview': self._get_preview(data)
                })
            
            return conversations
    
    def _get_preview(self, conversation_data: Dict) -> str:
        """Get conversation preview text"""
        messages = conversation_data.get('messages', [])
        
        # Find last user message
        for msg in reversed(messages):
            if msg['role'] == 'user':
                content = msg['content']
                return content[:100] + '...' if len(content) > 100 else content
        
        return "New conversation"
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation"""
        # Remove from cache
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]
        
        # Remove from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'DELETE FROM conversations WHERE conversation_id = ?',
                (conversation_id,)
            )
        
        self.logger.info(f"Deleted conversation {conversation_id}")
    
    def get_statistics(self, profile_id: str = None) -> Dict:
        """Get conversation statistics"""
        with sqlite3.connect(self.db_path) as conn:
            if profile_id:
                cursor = conn.execute('''
                    SELECT COUNT(*), SUM(json_extract(data, '$.metadata.message_count'))
                    FROM conversations
                    WHERE profile_id = ?
                ''', (profile_id,))
            else:
                cursor = conn.execute('''
                    SELECT COUNT(*), SUM(json_extract(data, '$.metadata.message_count'))
                    FROM conversations
                ''')
            
            row = cursor.fetchone()
            
            return {
                'total_conversations': row[0] or 0,
                'total_messages': int(row[1] or 0)
            }
    
    def cleanup_old_conversations(self, days: int = 90):
        """Remove conversations older than specified days"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM conversations
                WHERE updated_at < ?
            ''', (cutoff_date,))
            
            deleted = cursor.rowcount
            
        self.logger.info(f"Cleaned up {deleted} old conversations")
