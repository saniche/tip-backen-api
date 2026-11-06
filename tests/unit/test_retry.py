from shared.llm_structured import StructuredProviderError
from shared.retry import is_transient_failure


def test_transient_cause_is_recognized_without_retrying_permanent_provider_errors():
    transient = StructuredProviderError("External processing failed")
    transient.__cause__ = TimeoutError("provider timed out")
    assert is_transient_failure(transient)
    assert not is_transient_failure(StructuredProviderError("External processing is not configured"))
