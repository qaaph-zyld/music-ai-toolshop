"""
EverMemOS Integration for OpenDAW
Auto-retrieves project context and stores development decisions.
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add EverMemOS client to path
EVERMEM_PATH = Path(r'd:\Project\dev_framework\skills\evermem-os-memory')
if str(EVERMEM_PATH) not in sys.path:
    sys.path.insert(0, str(EVERMEM_PATH))

try:
    from evermem_client import CascadeMemoryManager, store_task_completion
    EVERMEM_AVAILABLE = True
except ImportError:
    EVERMEM_AVAILABLE = False
    CascadeMemoryManager = None
    store_task_completion = None


class OpenDAWMemoryManager:
    """EverMemOS integration for OpenDAW project memory management."""
    
    def __init__(self):
        self.manager = CascadeMemoryManager() if EVERMEM_AVAILABLE else None
        self._available = EVERMEM_AVAILABLE and self.manager is not None and self.manager.is_available()
    
    def is_available(self) -> bool:
        """Check if EverMemOS is available for use."""
        return self._available
    
    def get_session_context(self, query: str = "OpenDAW project recent work", limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories at session start.
        
        Args:
            query: Search query for relevant memories
            limit: Maximum number of memories to retrieve
            
        Returns:
            List of memory dictionaries with content and metadata
        """
        if not self._available:
            return []
        
        try:
            memories = self.manager.get_relevant_context(
                query=query,
                project="OpenDAW",
                limit=limit
            )
            return memories if memories else []
        except Exception as e:
            print(f"[EverMemOS] Error retrieving context: {e}")
            return []
    
    def store_architecture_decision(self, decision: str, reasoning: str, files_affected: List[str]) -> bool:
        """Store architecture decision during development.
        
        Args:
            decision: Description of the decision made
            reasoning: Why this decision was made
            files_affected: List of file paths affected by this decision
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self._available:
            print(f"[EverMemOS] Not available - decision not stored: {decision[:50]}...")
            return False
        
        try:
            content = json.dumps({
                "project": "OpenDAW",
                "decision": decision,
                "reasoning": reasoning,
                "files_affected": files_affected,
                "type": "architecture_decision"
            }, indent=2)
            
            self.manager.store_memory(
                content=content,
                memory_type="semantic_memory",
                metadata={
                    "category": "architecture",
                    "source": "dev_framework",
                    "project": "OpenDAW"
                }
            )
            print(f"[EverMemOS] Stored architecture decision: {decision[:60]}...")
            return True
        except Exception as e:
            print(f"[EverMemOS] Error storing decision: {e}")
            return False
    
    def store_component_integration(self, component_name: str, tests_added: int, files_modified: List[str]) -> bool:
        """Store component integration completion.
        
        Args:
            component_name: Name of the integrated component
            tests_added: Number of new tests added
            files_modified: List of modified file paths
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self._available:
            return False
        
        task_description = f"Integrated {component_name} component with {tests_added} TDD tests"
        
        try:
            result = store_task_completion(
                project="OpenDAW",
                task=task_description,
                key_files_modified=files_modified
            )
            print(f"[EverMemOS] Stored completion: {task_description}")
            return result is not None
        except Exception as e:
            print(f"[EverMemOS] Error storing completion: {e}")
            return False
    
    def store_session_summary(self, session_date: str, components_added: int, tests_passing: int, 
                              key_achievements: List[str]) -> bool:
        """Store end-of-session summary for handoff continuity.
        
        Args:
            session_date: Date of the session (YYYY-MM-DD)
            components_added: Number of components added in session
            tests_passing: Current total tests passing
            key_achievements: List of key achievements
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self._available:
            return False
        
        try:
            content = json.dumps({
                "session_date": session_date,
                "project": "OpenDAW",
                "components_added": components_added,
                "tests_passing": tests_passing,
                "key_achievements": key_achievements,
                "phase": "Phase 4 - Component Catalog Integration"
            }, indent=2)
            
            self.manager.store_memory(
                content=content,
                memory_type="episodic_memory",
                metadata={
                    "category": "session_summary",
                    "project": "OpenDAW",
                    "date": session_date
                }
            )
            print(f"[EverMemOS] Stored session summary: {session_date} - {components_added} components")
            return True
        except Exception as e:
            print(f"[EverMemOS] Error storing summary: {e}")
            return False
    
    def print_session_context(self, limit: int = 5):
        """Print recent session context for immediate awareness.
        
        Args:
            limit: Maximum number of memories to display
        """
        memories = self.get_session_context(limit=limit)
        
        if not memories:
            print("[EverMemOS] No previous memories found or EverMemOS unavailable")
            return
        
        print(f"\n{'='*60}")
        print(f"[EverMemOS] Loaded {len(memories)} memories for OpenDAW")
        print(f"{'='*60}")
        
        for i, mem in enumerate(memories[:limit], 1):
            content = mem.get('content', '')
            memory_type = mem.get('memory_type', 'unknown')
            
            # Try to parse JSON content for better formatting
            try:
                data = json.loads(content)
                if 'decision' in data:
                    print(f"\n{i}. [Architecture Decision]")
                    print(f"   Decision: {data['decision'][:80]}...")
                    print(f"   Reasoning: {data.get('reasoning', 'N/A')[:60]}...")
                elif 'task' in data:
                    print(f"\n{i}. [Task Completion]")
                    print(f"   Task: {data['task'][:80]}...")
                    files = data.get('key_files_modified', [])
                    if files:
                        print(f"   Files: {', '.join(files[:3])}")
                elif 'session_date' in data:
                    print(f"\n{i}. [Session Summary - {data['session_date']}]")
                    print(f"   Components: +{data.get('components_added', 0)}")
                    print(f"   Tests: {data.get('tests_passing', 0)} passing")
                    achievements = data.get('key_achievements', [])
                    if achievements:
                        print(f"   Key: {achievements[0][:60]}...")
                else:
                    print(f"\n{i}. [{memory_type}]")
                    print(f"   {content[:100]}...")
            except json.JSONDecodeError:
                print(f"\n{i}. [{memory_type}]")
                print(f"   {content[:100]}...")
        
        print(f"\n{'='*60}\n")


# Convenience function for direct import
def get_memory_manager() -> OpenDAWMemoryManager:
    """Get singleton instance of OpenDAW memory manager."""
    return OpenDAWMemoryManager()


if __name__ == "__main__":
    # Test the integration
    print("Testing EverMemOS integration...")
    manager = OpenDAWMemoryManager()
    
    print(f"EverMemOS available: {manager.is_available()}")
    
    if manager.is_available():
        manager.print_session_context(limit=5)
    else:
        print("EverMemOS not available - ensure the service is running")
