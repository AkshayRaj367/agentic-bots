from groq import Groq as _Groq
from src.config import Config


class Groq:
    def __init__(self):
        config = Config()
        api_key = (config.get_groq_api_key() or "").strip()
        self.client = _Groq(api_key=api_key)
        
        # System prompt for detailed, creative, and thorough responses
        self.system_prompt = """You are an expert AI assistant that provides comprehensive, detailed, and creative solutions. 
Your response should be:
- THOROUGH: Include all relevant details, edge cases, and considerations
- CREATIVE: Propose innovative approaches and best practices
- COMPLETE: Don't give partial solutions - always finish what you start
- THOUGHTFUL: Explain your reasoning and trade-offs
- WELL-STRUCTURED: Use clear formatting, code blocks, and explanations

Never provide half-baked or incomplete solutions. Always go deeper and provide a comprehensive answer."""

    def inference(self, model_id: str, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """
        Generate a response with improved creativity and detail.
        
        Args:
            model_id: The Groq model to use
            prompt: The user prompt
            temperature: Creativity level (0.0-1.0, default 0.7 for creativity)
            max_tokens: Maximum response length (default 4096 for detailed responses)
        
        Returns:
            Generated response
        """
        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": prompt.strip(),
                }
            ],
            model=model_id,
            temperature=temperature,  # Higher = more creative
            max_tokens=max_tokens,     # Allow longer responses
            top_p=0.95                 # Nucleus sampling for diversity
        )

        return chat_completion.choices[0].message.content

    def inference_iterative(self, model_id: str, prompt: str, refinement_prompt: str = None) -> str:
        """
        Generate a response and optionally refine it for better quality.
        
        Args:
            model_id: The Groq model to use
            prompt: The initial prompt
            refinement_prompt: Optional prompt to refine/expand the response
        
        Returns:
            Final refined response
        """
        # First pass: Generate initial response
        initial_response = self.inference(model_id, prompt, temperature=0.7, max_tokens=4096)
        
        # If refinement prompt provided, iterate for better solution
        if refinement_prompt:
            refine_instruction = f"""Previous response:
{initial_response}

Refinement request: {refinement_prompt}

Provide a more complete, detailed, and creative solution. Build upon the previous response and make it more comprehensive."""
            
            refined_response = self.inference(model_id, refine_instruction, temperature=0.8, max_tokens=4096)
            return refined_response
        
        return initial_response

    def inference_with_context(self, model_id: str, prompt: str, context: str = "", examples: list = None) -> str:
        """
        Generate response with additional context and examples.
        
        Args:
            model_id: The Groq model to use
            prompt: The main prompt
            context: Background context/information
            examples: List of examples to guide the response
        
        Returns:
            Generated response
        """
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            }
        ]
        
        if context:
            messages.append({
                "role": "system",
                "content": f"Context:\n{context}"
            })
        
        if examples:
            for i, example in enumerate(examples, 1):
                messages.append({
                    "role": "system",
                    "content": f"Example {i}:\n{example}"
                })
        
        messages.append({
            "role": "user",
            "content": prompt.strip()
        })
        
        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=model_id,
            temperature=0.8,
            max_tokens=4096,
            top_p=0.95
        )

        return chat_completion.choices[0].message.content
