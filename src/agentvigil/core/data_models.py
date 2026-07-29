from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Task:
    """Represents a combination of a user task and an injection task."""
    id: str
    user_task: str
    injection_target: str
    # Environment-specific details can be added here (e.g., environment state placeholders)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Seed:
    """Represents an adversarial prompt in the MCTS tree."""
    id: str
    text: str
    parent: Optional['Seed'] = None
    children: List['Seed'] = field(default_factory=list)
    
    # MCTS statistics
    score: float = 0.0
    visits: int = 0
    
    # Tracking for evaluation and mutation
    mutation_history: List[str] = field(default_factory=list)
    
    def add_child(self, child: 'Seed'):
        self.children.append(child)
        child.parent = self
        
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Seed):
            return False
        return self.id == other.id
