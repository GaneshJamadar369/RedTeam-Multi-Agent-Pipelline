import os
from openai import OpenAI
from typing import Optional

class LLMWrapper:
    """Wrapper for real LLM calls using OpenAI."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        # Expects OPENAI_API_KEY to be set in the environment
        self.client = OpenAI()
        self.model_name = model_name
        
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Calls the OpenAI API and returns the text response."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            # Fallback to returning the original prompt heavily marked, to avoid crashing the fuzz loop
            return f"[LLM ERROR] {user_prompt[:50]}..."
