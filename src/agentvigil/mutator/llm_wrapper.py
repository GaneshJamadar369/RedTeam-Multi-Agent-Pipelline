import os
import requests
import json
from openai import OpenAI
from typing import Optional

class LLMWrapper:
    """Wrapper for real LLM calls using OpenAI or Local Inference (e.g., vLLM)."""
    
    def __init__(self, model_name: str = "gpt-4o-mini", local_endpoint: Optional[str] = None):
        """
        Args:
            model_name: The name of the model to use.
            local_endpoint: The URL for local inference (e.g., http://localhost:8000/v1). 
                            If provided, uses local vLLM/Ollama instead of OpenAI.
        """
        self.model_name = model_name
        self.local_endpoint = local_endpoint
        
        if self.local_endpoint:
            self.client = None # Use requests for local endpoint
        elif os.environ.get("OPENAI_API_KEY"):
            self.client = OpenAI()
        else:
            self.client = None
        
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Calls the LLM API and returns the text response."""
        try:
            if self.local_endpoint:
                return self._generate_local(system_prompt, user_prompt)
                
            if self.client is None:
                # Deterministic fallback used for tests when no API key is present
                return f"[MOCK LLM RESPONSE] {user_prompt}"

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
            
    def _generate_local(self, system_prompt: str, user_prompt: str) -> str:
        """Calls a local inference endpoint (OpenAI compatible)."""
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(f"{self.local_endpoint}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
