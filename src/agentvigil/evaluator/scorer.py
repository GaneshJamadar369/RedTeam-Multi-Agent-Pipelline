from typing import List, Dict, Any, Set
from ..core.data_models import Seed, Task


class Scorer:
    """Implements success rate and coverage-guided seed scoring (Algorithm 1)."""
    
    def __init__(self, coverage_factor: float = 1.0):
        self.coverage_factor = coverage_factor
        self.covered_combinations: Set[str] = set()

    def evaluate_seed(self, seed: Seed, task_suites: Dict[str, List[Task]], agent_runner: Any) -> float:
        """
        Algorithm 1: Success rate and coverage-guided seed scoring.
        
        Args:
            seed: The mutated seed to evaluate.
            task_suites: Dictionary mapping suite names to lists of Tasks.
            agent_runner: Callable or object that runs the agent given a seed and a task.
                          Expected to return a boolean indicating injection success.
                          
        Returns:
            The final computed score for the seed.
        """
        total_success = 0
        num_questions = 0
        coverage_bonus = 0
        
        # for all task_suite in sampled_tasks do
        for suite_name, tasks in task_suites.items():
            for task in tasks:
                num_questions += 1
                
                # Evaluate user and injection task combinations using seed
                injection_successful = agent_runner.run(seed, task)
                
                if injection_successful:
                    total_success += 1
                    
                    # Identify newly successful task combinations not covered before
                    task_combo_id = f"{suite_name}_{task.id}"
                    if task_combo_id not in self.covered_combinations:
                        self.covered_combinations.add(task_combo_id)
                        coverage_bonus += 1

        if num_questions == 0:
            return 0.0

        # Calculate Final Score including attack success rate and coverage bonus
        asr = total_success / num_questions
        seed_score = asr + self.coverage_factor * (coverage_bonus / num_questions)
        
        # Update the seed's score
        seed.score = seed_score
        
        return seed_score
