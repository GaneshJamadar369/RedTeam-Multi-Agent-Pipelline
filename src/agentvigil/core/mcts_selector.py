import math
from typing import List, Set
from .data_models import Seed


class MCTSSelector:
    """Implements Monte Carlo Tree Search seed selection (Algorithm 2 & 3)."""
    
    def __init__(self, exploration_factor: float = 1.414, epsilon: float = 1e-6):
        self.exploration_factor = exploration_factor
        self.epsilon = epsilon
        self.nodes: Set[Seed] = set()
        
    def _calculate_ucb(self, node: Seed, total_visits: int) -> float:
        """Calculates the Upper Confidence Bound 1 (UCB1) for a given node."""
        exploration_term = self.exploration_factor * math.sqrt(
            math.log(total_visits + 1) / (node.visits + self.epsilon)
        )
        return node.score + exploration_term

    def select(self, n: int = 1) -> List[Seed]:
        """
        Algorithm 2: MCTS-based seed selection
        Selects top `n` nodes based on UCB score.
        """
        if not self.nodes:
            return []
            
        total_visits = sum(node.visits for node in self.nodes)
        
        # Calculate UCB for all nodes
        scored_nodes = [(self._calculate_ucb(node, total_visits), node) for node in self.nodes]
        
        # Sort in descending order
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        
        # Select top n
        selected_nodes = [node for _, node in scored_nodes[:n]]
        return selected_nodes

    def update(self, node: Seed):
        """
        Algorithm 3: MCTS-based seed selection: Update
        Backpropagates visits up the ancestor chain and adds node to set of nodes.
        """
        # Add node to tracked set if not already present
        self.nodes.add(node)
        
        # Update all ancestors
        ancestors = []
        if node.parent:
            ancestors.append(node.parent)
            
        while ancestors:
            p = ancestors.pop(0)
            p.visits += 1
            if p.parent:
                ancestors.append(p.parent)
