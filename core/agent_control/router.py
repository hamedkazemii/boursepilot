from core.agent_control.quota import quota_manager

class ModelRouter:
    MODELS = [
        "google/gemini-3.1-pro-preview",
        "google/gemini-2.5-flash-lite",
        "google/gemini-2.5-flash",
        "openrouter/moonshotai/kimi-k2.6",
        "ollama"
    ]

    def get_best_model(self, current_model: str) -> str:
        if not quota_manager.should_fallback(current_model):
            return current_model
        
        try:
            idx = self.MODELS.index(current_model)
            if idx + 1 < len(self.MODELS):
                return self.MODELS[idx + 1]
        except ValueError:
            pass
        return self.MODELS[0] # Default to pro if unknown
