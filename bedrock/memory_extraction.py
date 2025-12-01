"""
Memory Extraction: Convert short-term conversation memory to long-term structured data.

This module provides tools to automatically extract and persist important information
from conversation messages into structured long-term memory fields.
"""

from typing import Dict, List, Any
from datetime import datetime
import re
import json


class MemoryExtractor:
    """Extract structured information from conversation messages for long-term storage."""
    
    @staticmethod
    def extract_browsing_info(messages: List[Any]) -> List[Dict]:
        """
        Extract browsing information from tool messages.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            List of browsing history entries
        """
        browsing_entries = []
        
        for msg in messages:
            # Check if this is a tool message from browse_web
            if hasattr(msg, 'type') and msg.type == 'tool':
                if hasattr(msg, 'name') and msg.name == 'browse_web':
                    content = msg.content if hasattr(msg, 'content') else str(msg)
                    
                    # Extract structured data from the content
                    entry = MemoryExtractor._parse_browsing_result(content)
                    if entry:
                        browsing_entries.append(entry)
        
        return browsing_entries
    
    @staticmethod
    def _parse_browsing_result(content: str) -> Dict:
        """Parse browsing tool output into structured data."""
        entry = {}
        
        # Extract timestamp
        timestamp_match = re.search(r'Timestamp:\s*([^\n]+)', content)
        if timestamp_match:
            entry['timestamp'] = timestamp_match.group(1).strip()
        else:
            entry['timestamp'] = datetime.utcnow().isoformat()
        
        # Extract URL
        url_match = re.search(r'URL:\s*([^\n]+)', content)
        if url_match:
            entry['url'] = url_match.group(1).strip()
        else:
            # Try to find any URL in the content
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, content)
            entry['url'] = urls[0] if urls else 'N/A'
        
        # Extract session ID
        session_match = re.search(r'Session ID:\s*([^\n]+)', content)
        if session_match:
            entry['session_id'] = session_match.group(1).strip()
        
        # Extract task description
        task_match = re.search(r'Task:\s*([^\n]+)', content)
        if task_match:
            entry['task'] = task_match.group(1).strip()
        
        # Create summary
        if 'task' in entry:
            entry['summary'] = entry['task'][:100]  # First 100 chars
        else:
            entry['summary'] = content[:100]
        
        return entry if entry else None
    
    @staticmethod
    def extract_user_preferences(messages: List[Any]) -> Dict:
        """
        Extract user preferences from conversation.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Dictionary of user preferences
        """
        preferences = {}
        
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                content = msg.content if hasattr(msg, 'content') else str(msg)
                content_lower = content.lower()
                
                # Extract preferences based on common patterns
                if 'i like' in content_lower or 'i prefer' in content_lower:
                    # Extract what they like
                    patterns = [
                        r'i like ([^.,!?]+)',
                        r'i prefer ([^.,!?]+)',
                        r'my favorite is ([^.,!?]+)',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, content_lower)
                        if match:
                            preference = match.group(1).strip()
                            preferences.setdefault('likes', []).append(preference)
                
                # Extract name
                name_patterns = [
                    r'my name is ([A-Z][a-z]+)',
                    r"i'm ([A-Z][a-z]+)",
                    r'call me ([A-Z][a-z]+)',
                ]
                for pattern in name_patterns:
                    match = re.search(pattern, content)
                    if match:
                        preferences['name'] = match.group(1).strip()
        
        return preferences
    
    @staticmethod
    def extract_key_information(messages: List[Any]) -> Dict:
        """
        Extract key information from the entire conversation.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Dictionary with extracted information
        """
        return {
            'browsing_history': MemoryExtractor.extract_browsing_info(messages),
            'user_preferences': MemoryExtractor.extract_user_preferences(messages),
            'extraction_timestamp': datetime.utcnow().isoformat(),
            'message_count': len(messages)
        }


def create_memory_extraction_node(extractor: MemoryExtractor = None):
    """
    Create a LangGraph node that extracts long-term memory from short-term.
    
    Args:
        extractor: MemoryExtractor instance (creates new one if None)
        
    Returns:
        Node function that can be added to a LangGraph
    """
    if extractor is None:
        extractor = MemoryExtractor()
    
    def memory_extraction_node(state: Dict) -> Dict:
        """
        Extract structured information from conversation messages.
        
        This node runs after each conversation turn to update long-term memory.
        """
        messages = state.get("messages", [])
        
        # Extract browsing information
        new_browsing_entries = extractor.extract_browsing_info(messages)
        if new_browsing_entries:
            # Append to existing browsing history
            existing_history = state.get("browsing_history", [])
            updated_history = existing_history + new_browsing_entries
            
            # Keep only last 20 entries to avoid memory bloat
            if len(updated_history) > 20:
                updated_history = updated_history[-20:]
            
            state["browsing_history"] = updated_history
        
        # Extract and merge user preferences
        new_preferences = extractor.extract_user_preferences(messages)
        if new_preferences:
            existing_prefs = state.get("user_preferences", {})
            
            # Merge preferences (new ones override old ones)
            for key, value in new_preferences.items():
                if key == 'likes' and key in existing_prefs:
                    # Append to likes list, avoiding duplicates
                    existing_prefs['likes'] = list(set(
                        existing_prefs.get('likes', []) + value
                    ))
                else:
                    existing_prefs[key] = value
            
            state["user_preferences"] = existing_prefs
        
        return state
    
    return memory_extraction_node


# Example usage functions
def consolidate_conversation_memory(messages: List[Any]) -> Dict:
    """
    One-shot function to extract all long-term memory from a conversation.
    
    Args:
        messages: List of conversation messages
        
    Returns:
        Dictionary with all extracted long-term memory
    """
    extractor = MemoryExtractor()
    return extractor.extract_key_information(messages)


def update_long_term_memory(state: Dict) -> Dict:
    """
    Update long-term memory fields based on recent messages.
    
    Args:
        state: Current agent state with messages
        
    Returns:
        Updated state with long-term memory fields populated
    """
    extractor = MemoryExtractor()
    node = create_memory_extraction_node(extractor)
    return node(state)

