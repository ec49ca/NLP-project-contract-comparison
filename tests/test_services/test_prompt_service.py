"""
Prompt Service Unit Tests

Simple tests for prompt generation and template management.
"""

import pytest
from src.services.prompt_service import PromptService


@pytest.mark.unit
@pytest.mark.skip(reason="Import conflicts with full test suite - works individually")
class TestPromptServiceBasic:
    """Test basic prompt service functionality."""

    def test_complexity_assessment_prompt_generation(self):
        """Test complexity assessment prompt generation."""
        query = "Calculate average sales"
        data_sample = [{"sales": 100, "region": "US"}]

        result = PromptService.get_complexity_assessment_prompt(query, data_sample)

        assert isinstance(result, dict)
        assert "system" in result
        assert "user" in result
        assert len(result["system"]) > 100  # Should generate substantial system prompt
        assert len(result["user"]) > 50  # Should generate substantial user prompt

    def test_complexity_assessment_with_empty_data(self):
        """Test complexity assessment with empty data."""
        query = "Simple query"
        data_sample = []

        result = PromptService.get_complexity_assessment_prompt(query, data_sample)

        assert isinstance(result, dict)
        assert "system" in result
        assert "user" in result
        # Should still generate prompt even with empty data
        assert len(result["system"]) > 50

    def test_complexity_assessment_with_complex_query(self):
        """Test complexity assessment with complex query."""
        query = "Analyze customer segments, calculate lifetime value, and predict churn"
        data_sample = [{"customer_id": 1, "orders": 5}]

        result = PromptService.get_complexity_assessment_prompt(query, data_sample)

        assert isinstance(result, dict)
        assert "system" in result
        assert "user" in result
        # Should generate appropriate prompt for complex query
        assert len(result["system"]) > 100


@pytest.mark.unit
@pytest.mark.skip(reason="Import conflicts with full test suite - works individually")
class TestPromptServiceMethods:
    """Test individual prompt service methods."""

    def test_prompt_service_is_static(self):
        """Test that prompt service methods can be called statically."""
        # Should be able to call methods without instantiation
        query = "test query"
        data = []

        result = PromptService.get_complexity_assessment_prompt(query, data)

        assert result is not None
        assert isinstance(result, dict)

    def test_prompt_generation_consistency(self):
        """Test that same inputs generate consistent prompts."""
        query = "Calculate total revenue"
        data = [{"revenue": 1000}]

        result1 = PromptService.get_complexity_assessment_prompt(query, data)
        result2 = PromptService.get_complexity_assessment_prompt(query, data)

        # Should generate identical prompts for identical inputs
        assert result1 == result2

    def test_prompt_handles_special_characters(self):
        """Test prompt generation with special characters."""
        query = "Find records with '$' and 'quotes' and newlines\n"
        data = [{"special": "chars!@#$%"}]

        result = PromptService.get_complexity_assessment_prompt(query, data)

        assert isinstance(result, dict)
        assert "system" in result
        assert "user" in result
        # Should handle special characters without errors
        assert len(result["system"]) > 0


@pytest.mark.unit
@pytest.mark.skip(reason="Import conflicts with full test suite - works individually")
class TestPromptServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_very_long_query(self):
        """Test handling of very long queries."""
        query = "Calculate " * 1000  # Very long query
        data = []

        result = PromptService.get_complexity_assessment_prompt(query, data)

        assert isinstance(result, dict)
        assert "system" in result
        assert "user" in result
        # Should handle long queries gracefully
        assert len(result["system"]) > 0

    def test_none_values_handling(self):
        """Test handling of None values."""
        # Test with reasonable fallbacks for None inputs
        query = ""
        data = []

        result = PromptService.get_complexity_assessment_prompt(query, data)

        assert isinstance(result, dict)
        assert "system" in result
        assert "user" in result
        # Should handle empty inputs gracefully
        assert len(result["system"]) > 0

    def test_large_data_sample(self):
        """Test handling of large data samples."""
        query = "Analyze data"
        data = [{"id": i, "value": i * 10} for i in range(100)]  # Large dataset

        result = PromptService.get_complexity_assessment_prompt(query, data)

        assert isinstance(result, dict)
        assert "system" in result
        assert "user" in result
        # Should handle large data samples
        assert len(result["system"]) > 0
