import pytest

from huggingface_hub.errors import HfHubHTTPError

from app.llm import LLMConfigurationError, LangChainHuggingFaceGenerator


class FakeEndpoint:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.prompt = None

    def __call__(self, prompt):
        self.prompt = prompt.to_string()
        return "The API routes requests [design.md::0]."


class FakeChain:
    def __init__(self, response):
        self.response = response
        self.inputs = []

    def invoke(self, inputs):
        self.inputs.append(inputs)
        return self.response


def test_generator_requires_huggingface_token(monkeypatch):
    monkeypatch.delenv("HUGGINGFACEHUB_API_TOKEN", raising=False)
    generator = LangChainHuggingFaceGenerator()

    with pytest.raises(RuntimeError, match="HUGGINGFACEHUB_API_TOKEN is required"):
        generator.generate("question", "[doc::0]\nevidence", [])


def test_model_uses_huggingface_chat_completion_for_chat_only_models(monkeypatch):
    import langchain_huggingface

    monkeypatch.setenv("HUGGINGFACEHUB_API_TOKEN", "test-token")
    endpoint = FakeEndpoint()
    monkeypatch.setattr(
        langchain_huggingface,
        "HuggingFaceEndpoint",
        lambda **kwargs: endpoint,
    )
    wrappers = []

    class FakeChatHuggingFace:
        def __init__(self, llm):
            wrappers.append(llm)

    monkeypatch.setattr(
        langchain_huggingface, "ChatHuggingFace", FakeChatHuggingFace
    )

    model = LangChainHuggingFaceGenerator()._get_model()

    assert isinstance(model, FakeChatHuggingFace)
    assert wrappers == [endpoint]


def test_huggingface_credit_errors_are_reported_without_upstream_details():
    class FailedChain:
        def invoke(self, inputs):
            import httpx

            response = httpx.Response(
                402,
                request=httpx.Request(
                    "POST", "https://router.huggingface.co/v1/chat/completions"
                ),
            )
            raise HfHubHTTPError("private upstream error", response=response)

    generator = LangChainHuggingFaceGenerator()
    generator._query_chain = FailedChain()

    with pytest.raises(LLMConfigurationError, match="no available inference credits") as error:
        generator.expand("What does the API do?", [])

    assert "private upstream error" not in str(error.value)


def test_generator_passes_question_context_and_history_to_chain(monkeypatch):
    monkeypatch.setenv("HUGGINGFACEHUB_API_TOKEN", "test-token")
    generator = LangChainHuggingFaceGenerator()
    chain = FakeChain("Evidence-grounded answer.")
    generator._chain = chain

    answer = generator.generate(
        "How does the API work?",
        "[design.md::0]\nThe API routes requests.",
        [{"question": "What is the entry point?", "answer": "The API."}],
    )

    assert answer == "Evidence-grounded answer."
    assert chain.inputs == [
        {
            "question": "How does the API work?",
            "context": "[design.md::0]\nThe API routes requests.",
            "history": "User: What is the entry point?\nAssistant: The API.",
        }
    ]


def test_query_expansion_parses_multiple_queries_and_includes_history():
    generator = LangChainHuggingFaceGenerator()
    chain = FakeChain("1. PDF ingestion flow\n- document parsing pipeline\n3) PDF upload processing")
    generator._query_chain = chain

    queries = generator.expand(
        "How are PDFs ingested?",
        [{"question": "What is uploaded?", "answer": "Technical PDFs."}],
    )

    assert queries == [
        "PDF ingestion flow",
        "document parsing pipeline",
        "PDF upload processing",
    ]
    assert chain.inputs[0]["history"] == (
        "User: What is uploaded?\nAssistant: Technical PDFs."
    )


def test_langchain_prompt_contains_question_history_and_retrieved_evidence(
    monkeypatch,
):
    import langchain_huggingface

    monkeypatch.setenv("HUGGINGFACEHUB_API_TOKEN", "test-token")
    endpoint = FakeEndpoint()
    monkeypatch.setattr(
        langchain_huggingface,
        "HuggingFaceEndpoint",
        lambda **kwargs: endpoint,
    )
    monkeypatch.setattr(
        langchain_huggingface, "ChatHuggingFace", lambda llm: llm
    )
    generator = LangChainHuggingFaceGenerator()

    answer = generator.generate(
        "What does the API do?",
        "[design.md::0]\nThe API routes requests.",
        [{"question": "What is the entry point?", "answer": "The API."}],
    )

    assert answer == "The API routes requests [design.md::0]."
    assert "using only the retrieved evidence" in endpoint.prompt.lower()
    assert "senior architect" in endpoint.prompt.lower()
    assert "[design.md::0]\nThe API routes requests." in endpoint.prompt
    assert "What does the API do?" in endpoint.prompt
    assert "User: What is the entry point?" in endpoint.prompt


def test_compliance_prompt_requires_standard_evidence_and_citations(monkeypatch):
    import langchain_huggingface

    monkeypatch.setenv("HUGGINGFACEHUB_API_TOKEN", "test-token")
    endpoint = FakeEndpoint()
    monkeypatch.setattr(
        langchain_huggingface,
        "HuggingFaceEndpoint",
        lambda **kwargs: endpoint,
    )
    monkeypatch.setattr(
        langchain_huggingface, "ChatHuggingFace", lambda llm: llm
    )

    review = LangChainHuggingFaceGenerator().generate_compliance(
        "The service stores customer data.",
        "[standard.md::0]\nCustomer data must be encrypted at rest.",
    )

    assert review == "The API routes requests [design.md::0]."
    assert "only with the retrieved internal standards" in endpoint.prompt.lower()
    assert "Status: COMPLIANT, PARTIAL, or NON_COMPLIANT" in endpoint.prompt
    assert "[standard.md::0]\nCustomer data must be encrypted at rest." in endpoint.prompt
