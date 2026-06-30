from api.core.config import settings


_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_ollama import ChatOllama

        _llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_url,
            temperature=0.1,
            num_predict=512,
            top_p=0.9,
        )
    return _llm


# ==========================================================
# NEW API
# ==========================================================

def ask_llm(prompt: str):
    response = _get_llm().invoke(prompt)
    return response.content


# ==========================================================
# BACKWARD COMPATIBILITY
# ==========================================================

def generate_response(prompt: str):
    return ask_llm(prompt)


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":
    print(generate_response("Explain Expected Loss in credit risk."))
