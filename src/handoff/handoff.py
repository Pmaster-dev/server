"""
Handoff system for Pmaster AI Operator.

Enables seamless task transition between agents, systems, and execution environments:
- Task context preservation
- State serialization
- Progress tracking
- Handoff validation
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid


class HandoffStatus(Enum):
    """Status of a handoff."""
    INITIATED = "initiated"
    PREPARED = "prepared"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass
class HandoffContext:
    """Complete context for handoff."""
    handoff_id: str
    task_id: str
    source_agent: str
    target_agent: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Task state
    task_state: Dict[str, Any] = field(default_factory=dict)
    task_progress: float = 0.0
    task_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    priority: int = 3
    deadline: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    blocked_by: List[str] = field(default_factory=list)
    
    # Resources
    required_resources: Dict[str, Any] = field(default_factory=dict)
    allocated_resources: Dict[str, Any] = field(default_factory=dict)
    
    # Validation
    checksum: Optional[str] = None
    encryption_key: Optional[str] = None
    
    def compute_checksum(self) -> str:
        """Compute checksum for integrity verification."""
        import hashlib
        content = json.dumps({
            "task_id": self.task_id,
            "task_state": self.task_state,
            "task_progress": self.task_progress,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "handoff_id": self.handoff_id,
            "task_id": self.task_id,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "timestamp": self.timestamp.isoformat(),
            "task_state": self.task_state,
            "task_progress": self.task_progress,
            "task_history": self.task_history,
            "priority": self.priority,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "tags": self.tags,
            "labels": self.labels,
            "dependencies": self.dependencies,
            "blocked_by": self.blocked_by,
            "required_resources": self.required_resources,
            "allocated_resources": self.allocated_resources,
            "checksum": self.checksum,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "HandoffContext":
        """Create from dictionary."""
        context = HandoffContext(
            handoff_id=data["handoff_id"],
            task_id=data["task_id"],
            source_agent=data["source_agent"],
            target_agent=data["target_agent"],
            task_state=data.get("task_state", {}),
            task_progress=data.get("task_progress", 0.0),
            task_history=data.get("task_history", []),
            priority=data.get("priority", 3),
            tags=data.get("tags", []),
            labels=data.get("labels", []),
            dependencies=data.get("dependencies", []),
            blocked_by=data.get("blocked_by", []),
            required_resources=data.get("required_resources", {}),
            allocated_resources=data.get("allocated_resources", {}),
            checksum=data.get("checksum"),
        )
        
        if data.get("deadline"):
            context.deadline = datetime.fromisoformat(data["deadline"])
        
        return context


@dataclass
class HandoffRecord:
    """Record of a handoff event."""
    handoff_id: str
    status: HandoffStatus
    timestamp: datetime = field(default_factory=datetime.now)
    source_agent: str = ""
    target_agent: str = ""
    task_id: str = ""
    message: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "handoff_id": self.handoff_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "task_id": self.task_id,
            "message": self.message,
            "error": self.error,
        }


class HandoffManager:
    """
    Manages task handoffs between agents and systems.
    
    Features:
    - Create and track handoffs
    - Context preservation
    - Validation and integrity checking
    - Event notifications
    - Retry mechanism
    """
    
    def __init__(self):
        self.handoffs: Dict[str, HandoffContext] = {}
        self.records: List[HandoffRecord] = []
        self.listeners: Dict[str, List[Callable]] = {
            "initiated": [],
            "accepted": [],
            "rejected": [],
            "failed": [],
            "completed": [],
        }
        self.max_retries = 3
    
    def initiate_handoff(self, task_id: str, source_agent: str, 
                        target_agent: str, task_state: Dict[str, Any],
                        **kwargs) -> HandoffContext:
        """
        Initiate a handoff.
        
        Args:
            task_id: Task to handoff
            source_agent: Source agent/system
            target_agent: Target agent/system
            task_state: Current task state
            **kwargs: Additional context (priority, deadline, tags, etc.)
            
        Returns:
            HandoffContext object
        """
        handoff_id = f"handoff-{uuid.uuid4().hex[:12]}"
        
        context = HandoffContext(
            handoff_id=handoff_id,
            task_id=task_id,
            source_agent=source_agent,
            target_agent=target_agent,
            task_state=task_state,
            **kwargs
        )
        
        context.checksum = context.compute_checksum()
        self.handoffs[handoff_id] = context
        
        # Record event
        self._record_handoff(handoff_id, HandoffStatus.INITIATED, 
                            source_agent, target_agent, task_id,
                            f"Handoff initiated from {source_agent} to {target_agent}")
        
        # Notify listeners
        self._notify_listeners("initiated", context)
        
        return context
    
    def prepare_handoff(self, handoff_id: str) -> bool:
        """Prepare handoff for transmission."""
        if handoff_id not in self.handoffs:
            return False
        
        context = self.handoffs[handoff_id]
        
        # Validate context
        if not self._validate_context(context):
            self._record_handoff(handoff_id, HandoffStatus.FAILED,
                                context.source_agent, context.target_agent,
                                context.task_id, "Context validation failed")
            return False
        
        self._record_handoff(handoff_id, HandoffStatus.PREPARED,
                            context.source_agent, context.target_agent,
                            context.task_id, "Handoff prepared")
        
        return True
    
    def transmit_handoff(self, handoff_id: str) -> bool:
        """Begin handoff transmission."""
        if handoff_id not in self.handoffs:
            return False
        
        context = self.handoffs[handoff_id]
        self._record_handoff(handoff_id, HandoffStatus.IN_TRANSIT,
                            context.source_agent, context.target_agent,
                            context.task_id, "Handoff in transit")
        
        return True
    
    def receive_handoff(self, handoff_id: str) -> bool:
        """Receive handoff at target."""
        if handoff_id not in self.handoffs:
            return False
        
        context = self.handoffs[handoff_id]
        
        # Verify integrity
        if not self._verify_integrity(context):
            self._record_handoff(handoff_id, HandoffStatus.FAILED,
                                context.source_agent, context.target_agent,
                                context.task_id, "Integrity verification failed")
            return False
        
        self._record_handoff(handoff_id, HandoffStatus.RECEIVED,
                            context.source_agent, context.target_agent,
                            context.task_id, "Handoff received")
        
        return True
    
    def accept_handoff(self, handoff_id: str) -> bool:
        """Accept handoff at target."""
        if handoff_id not in self.handoffs:
            return False
        
        context = self.handoffs[handoff_id]
        self._record_handoff(handoff_id, HandoffStatus.ACCEPTED,
                            context.source_agent, context.target_agent,
                            context.task_id, "Handoff accepted by target")
        
        # Notify listeners
        self._notify_listeners("accepted", context)
        
        return True
    
    def reject_handoff(self, handoff_id: str, reason: str = "") -> bool:
        """Reject handoff at target."""
        if handoff_id not in self.handoffs:
            return False
        
        context = self.handoffs[handoff_id]
        self._record_handoff(handoff_id, HandoffStatus.REJECTED,
                            context.source_agent, context.target_agent,
                            context.task_id, f"Handoff rejected: {reason}")
        
        # Notify listeners
        self._notify_listeners("rejected", context)
        
        return True
    
    def complete_handoff(self, handoff_id: str) -> bool:
        """Mark handoff as complete."""
        if handoff_id not in self.handoffs:
            return False
        
        context = self.handoffs[handoff_id]
        self._record_handoff(handoff_id, HandoffStatus.COMPLETED,
                            context.source_agent, context.target_agent,
                            context.task_id, "Handoff completed")
        
        # Notify listeners
        self._notify_listeners("completed", context)
        
        return True
    
    def get_handoff(self, handoff_id: str) -> Optional[HandoffContext]:
        """Get handoff context."""
        return self.handoffs.get(handoff_id)
    
    def get_task_handoffs(self, task_id: str) -> List[HandoffContext]:
        """Get all handoffs for task."""
        return [h for h in self.handoffs.values() if h.task_id == task_id]
    
    def get_agent_handoffs(self, agent_id: str, direction: str = "any") -> List[HandoffContext]:
        """
        Get handoffs for agent.
        
        Args:
            agent_id: Agent identifier
            direction: "source", "target", or "any"
        """
        if direction == "source":
            return [h for h in self.handoffs.values() if h.source_agent == agent_id]
        elif direction == "target":
            return [h for h in self.handoffs.values() if h.target_agent == agent_id]
        else:
            return [h for h in self.handoffs.values() 
                   if h.source_agent == agent_id or h.target_agent == agent_id]
    
    def get_handoff_status(self, handoff_id: str) -> Optional[HandoffStatus]:
        """Get current handoff status from latest record."""
        for record in reversed(self.records):
            if record.handoff_id == handoff_id:
                return record.status
        return None
    
    def get_handoff_history(self, handoff_id: str) -> List[HandoffRecord]:
        """Get handoff history."""
        return [r for r in self.records if r.handoff_id == handoff_id]
    
    def add_listener(self, event: str, callback: Callable) -> None:
        """Add event listener."""
        if event in self.listeners:
            self.listeners[event].append(callback)
    
    def _validate_context(self, context: HandoffContext) -> bool:
        """Validate handoff context."""
        if not context.task_id or not context.source_agent or not context.target_agent:
            return False
        
        if not context.task_state:
            return False
        
        return True
    
    def _verify_integrity(self, context: HandoffContext) -> bool:
        """Verify handoff integrity."""
        if not context.checksum:
            return False
        
        current_checksum = context.compute_checksum()
        return current_checksum == context.checksum
    
    def _record_handoff(self, handoff_id: str, status: HandoffStatus,
                       source_agent: str, target_agent: str, task_id: str,
                       message: str = "", error: Optional[str] = None) -> None:
        """Record handoff event."""
        record = HandoffRecord(
            handoff_id=handoff_id,
            status=status,
            source_agent=source_agent,
            target_agent=target_agent,
            task_id=task_id,
            message=message,
            error=error,
        )
        self.records.append(record)
    
    def _notify_listeners(self, event: str, context: HandoffContext) -> None:
        """Notify event listeners."""
        for callback in self.listeners.get(event, []):
            try:
                callback(context)
            except Exception as e:
                print(f"Listener error: {e}")
    
    def export_handoffs(self) -> Dict[str, Any]:
        """Export all handoffs and records."""
        return {
            "handoffs": {hid: h.to_dict() for hid, h in self.handoffs.items()},
            "records": [r.to_dict() for r in self.records],
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handoff statistics."""
        total = len(self.records)
        status_counts = {}
        
        for record in self.records:
            status = record.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_handoffs": len(self.handoffs),
            "total_events": total,
            "status_breakdown": status_counts,
        }


if __name__ == "__main__":
    # Example usage
    manager = HandoffManager()
    
    # Initiate handoff
    context = manager.initiate_handoff(
        task_id="task:123",
        source_agent="agent-1",
        target_agent="agent-2",
        task_state={"step": 1, "data": "processing"},
        priority=2,
        tags=["critical"],
    )
    
    print(f"Handoff ID: {context.handoff_id}")
    
    # Prepare and transmit
    manager.prepare_handoff(context.handoff_id)
    manager.transmit_handoff(context.handoff_id)
    
    # Receive and accept
    manager.receive_handoff(context.handoff_id)
    manager.accept_handoff(context.handoff_id)
    manager.complete_handoff(context.handoff_id)
    
    # Check history
    print("Handoff history:")
    for record in manager.get_handoff_history(context.handoff_id):
        print(f"  {record.status.value}: {record.message}")
