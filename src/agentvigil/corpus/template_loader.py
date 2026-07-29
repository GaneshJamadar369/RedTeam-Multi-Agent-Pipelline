import json
import os
import uuid
from typing import List
from ..core.data_models import Seed, Task

class TemplateLoader:
    """Loads and instantiates adversarial prompt templates."""
    
    def __init__(self, templates_path: str = None):
        if templates_path is None:
            templates_path = os.path.join(os.path.dirname(__file__), 'templates.json')
        
        with open(templates_path, 'r') as f:
            self.templates = json.load(f)
            
    def generate_initial_corpus(self, tasks: List[Task]) -> List[Seed]:
        """
        Instantiates templates with user tasks and attacker goals 
        to create the initial seed corpus.
        """
        seeds = []
        for task in tasks:
            for tmpl in self.templates:
                text = tmpl['template']
                text = text.replace('{{user_task}}', task.user_task)
                text = text.replace('{{attacker_goal}}', task.injection_target)
                
                seed = Seed(
                    id=str(uuid.uuid4()),
                    text=text,
                    mutation_history=[f"Init({tmpl['id']})"]
                )
                seeds.append(seed)
        return seeds
