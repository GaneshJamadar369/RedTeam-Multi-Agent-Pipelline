import logging
from typing import List, Dict
from .data_models import Seed, Task
from .mcts_selector import MCTSSelector
from ..mutator.mutator import Mutator
from ..evaluator.scorer import Scorer
from ..agent.agent_runner import AgentRunner

logging.basicConfig(
    level=logging.INFO, 
    format='\n%(asctime)s | %(levelname)s | File: %(pathname)s | Func: %(funcName)s()\n -> %(message)s'
)


class AgentVigil:
    """Orchestrator for the AGENTVIGIL framework."""
    
    def __init__(self, agent_runner: AgentRunner, mutator: Mutator, scorer: Scorer, selector: MCTSSelector):
        self.agent_runner = agent_runner
        self.mutator = mutator
        self.scorer = scorer
        self.selector = selector
        self.best_seed: Seed = None

    def run_fuzzing_loop(self, initial_seeds: List[Seed], task_suites: Dict[str, List[Task]], num_iterations: int = 10, num_mutations_per_iter: int = 3):
        """
        Runs the end-to-end genetic optimization process.
        """
        logging.info("Starting AGENTVIGIL Fuzzing Loop...")
        
        # 1. Initialize seeds and score them
        logging.info("Evaluating initial corpus...")
        for seed in initial_seeds:
            score = self.scorer.evaluate_seed(seed, task_suites, self.agent_runner)
            self.selector.update(seed)
            self._update_best_seed(seed)
            logging.info(f"Initial seed '{seed.id}' scored: {score:.2f}")

        # 2. Iterative optimization loop
        for i in range(num_iterations):
            logging.info(f"--- Iteration {i+1}/{num_iterations} ---")
            
            # a. Select promising seeds
            # Based on mutation strategies, we might select 1 or 2 seeds (for crossover)
            # We'll select up to 2 seeds.
            selected_seeds = self.selector.select(n=2)
            if not selected_seeds:
                logging.warning("No seeds selected. Breaking loop.")
                break
                
            logging.info(f"Selected {len(selected_seeds)} seed(s) for mutation.")
            
            # b. Mutate seeds
            # Generate multiple mutations in each iteration
            mutated_seeds = []
            for _ in range(num_mutations_per_iter):
                # The mutator might do crossover if 2 seeds are passed, or individual mutations
                mutants = self.mutator.mutate(selected_seeds)
                mutated_seeds.extend(mutants)
                
            logging.info(f"Generated {len(mutated_seeds)} new variant(s).")
            
            # c. Test and Score new seeds
            for variant in mutated_seeds:
                score = self.scorer.evaluate_seed(variant, task_suites, self.agent_runner)
                
                # d. Update MCTS tree
                self.selector.update(variant)
                self._update_best_seed(variant)
                logging.info(f"Variant '{variant.id}' (from {variant.mutation_history[-1]}) scored: {score:.2f}")

        logging.info("Fuzzing Loop Complete.")
        if self.best_seed:
            logging.info(f"Best Seed ID: {self.best_seed.id} with Score: {self.best_seed.score:.2f}")
            logging.info(f"Best Seed Text: {self.best_seed.text}")
            
        self.save_state("agentvigil_results.json")
            
        return self.best_seed

    def _update_best_seed(self, seed: Seed):
        if self.best_seed is None or seed.score > self.best_seed.score:
            self.best_seed = seed
            
    def save_state(self, filepath: str):
        """Exports the MCTS tree and mutation histories to a JSON file."""
        import json
        
        state = {
            "best_seed": {
                "id": self.best_seed.id if self.best_seed else None,
                "text": self.best_seed.text if self.best_seed else None,
                "score": self.best_seed.score if self.best_seed else None,
                "history": self.best_seed.mutation_history if self.best_seed else []
            },
            "mcts_nodes": []
        }
        
        for node in self.selector.nodes:
            state["mcts_nodes"].append({
                "id": node.id,
                "text": node.text,
                "score": node.score,
                "visits": node.visits,
                "history": node.mutation_history,
                "parent_id": node.parent.id if node.parent else None,
                "children_ids": [c.id for c in node.children]
            })
            
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        logging.info(f"State saved to {filepath}")
