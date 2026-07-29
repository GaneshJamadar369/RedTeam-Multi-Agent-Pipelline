import random
from typing import Dict, List
from ..core.data_models import Seed, Task


class AgentRunner:
    """Mock runner for a black-box LLM agent."""
    
    def __init__(self, failure_rate: float = 0.7):
        self.failure_rate = failure_rate
        
    def run(self, seed: Seed, task: Task) -> bool:
        """
        Simulates running the target agent with the injected seed.
        Returns True if the indirect prompt injection was successful.
        """
        import logging
        logging.info(f"[AGENT INPUT] Task: '{task.user_task}' | Target: '{task.injection_target}'")
        logging.info(f"[AGENT INJECTION] Seeding text:\n{seed.text}")
        
        # In a real environment, this would format the environment state
        # with the seed, run the agent, and check if the attacker's goal
        # was achieved (e.g. data exfiltration).
        
        # Here we use a random success rate, but make some seeds slightly better
        # based on string length to simulate optimization progress.
        base_chance = 1.0 - self.failure_rate
        length_bonus = min(0.2, len(seed.text) / 1000.0) 
        success_chance = base_chance + length_bonus
        
        result = random.random() < success_chance
        logging.info(f"[AGENT OUTPUT] Injection successful: {result}")
        return result
