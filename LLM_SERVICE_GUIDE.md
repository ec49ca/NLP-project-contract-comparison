# LLM Service Usage Guide

Simple guide for using the flexible LLM service that supports multiple providers (OpenAI, Claude, Grok).

## 🚀 Quick Start

```python
from services.llm_service import llm_service

# Basic usage - uses global default from .env
response = await llm_service.simple_completion("Hello, how are you?")
print(response)  # "I'm doing well, thank you! How can I help you today?"
```

## ⚙️ Global Defaults

Set your default model in `.env`:
```bash
DEFAULT_LLM_MODEL=openai:gpt-4o
# or
DEFAULT_LLM_MODEL=claude:claude-3-5-sonnet
```

All LLM calls will use this by default unless overridden.

## 📝 Simple Text Completion

### Basic Usage
```python
# Uses global default model
response = await llm_service.simple_completion(
    "Summarize this text: [your text here]"
)
```

### With JSON Response
```python
response = await llm_service.simple_completion(
    "Extract entities from: John works at OpenAI in San Francisco.",
    response_format={"type": "json_object"}
)
# Returns: '{"entities": [{"name": "John", "type": "Person"}, ...]}'
```

### Override Model
```python
# Use a cheaper model for simple tasks
response = await llm_service.simple_completion(
    "What is 2+2?",
    model="gpt-4o-mini"  # Cheaper option
)
```

### Override Provider
```python
# Use Claude for better reasoning
response = await llm_service.simple_completion(
    "Explain quantum computing in simple terms",
    provider="claude"
)
```

## 💬 Chat Completion

### Basic Chat
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather like?"}
]

response = await llm_service.chat_completion(messages)
print(response["choices"][0]["message"]["content"])
```

### With Specific Model
```python
response = await llm_service.chat_completion(
    messages=messages,
    model="gpt-4o",
    temperature=0.7,
    max_tokens=150
)
```

### Switch Provider Mid-Conversation
```python
# Start with OpenAI
response1 = await llm_service.chat_completion(
    messages=[{"role": "user", "content": "Write a poem"}],
    provider="openai"
)

# Switch to Claude for analysis
response2 = await llm_service.chat_completion(
    messages=[{"role": "user", "content": "Analyze this poem: [poem]"}],
    provider="claude"
)
```

## 🔄 Provider Management

### Check Current Provider
```python
current = llm_service.get_current_provider()
print(f"Currently using: {current}")  # "openai"
```

### See Available Providers
```python
providers = llm_service.get_available_providers()
print(providers)  # ["openai", "claude"]
```

### Switch Default Provider
```python
llm_service.set_provider("claude")
# Now all calls without provider= will use Claude
```

### Check Global Default
```python
default = llm_service.get_global_default_model()
print(default)  # "openai:gpt-4o"
```

## 💰 Cost Optimization Examples

### Use Cheap Models for Simple Tasks
```python
# Quick entity extraction with mini model
entities = await llm_service.simple_completion(
    "Extract names from: John and Mary went shopping",
    model="gpt-4o-mini",  # 60% cheaper than gpt-4o
    response_format={"type": "json_object"}
)
```

### Use Powerful Models for Complex Tasks
```python
# Complex analysis with full model
analysis = await llm_service.simple_completion(
    "Provide detailed market analysis of the tech sector",
    model="gpt-4o",  # Full power model
    provider="openai"
)
```

### Smart Provider Selection
```python
# Use Claude for reasoning tasks
reasoning = await llm_service.simple_completion(
    "Solve this logic puzzle: [puzzle]",
    provider="claude"  # Better at reasoning
)

# Use OpenAI for code generation
code = await llm_service.simple_completion(
    "Write Python code to sort a list",
    provider="openai"  # Good at code
)
```

## 🛠️ Practical Examples

### Entity Extraction Tool
```python
async def extract_entities(text: str):
    prompt = f"""
    Extract entities from: {text}

    Return JSON format:
    {{"entities": [{{"name": "entity", "type": "Person|Org|Location", "confidence": 0.9}}]}}
    """

    response = await llm_service.simple_completion(
        prompt=prompt,
        response_format={"type": "json_object"},
        model="gpt-4o-mini"  # Cheap for extraction
    )

    import json
    return json.loads(response)
```

### Multi-Provider Analysis
```python
async def get_multiple_perspectives(question: str):
    """Get answers from different providers for comparison"""

    # OpenAI perspective
    openai_response = await llm_service.simple_completion(
        question,
        provider="openai",
        model="gpt-4o"
    )

    # Claude perspective
    claude_response = await llm_service.simple_completion(
        question,
        provider="claude"
    )

    return {
        "openai": openai_response,
        "claude": claude_response
    }
```

### Adaptive Model Selection
```python
async def smart_completion(prompt: str, complexity: str = "medium"):
    """Choose model based on task complexity"""

    if complexity == "simple":
        return await llm_service.simple_completion(
            prompt,
            model="gpt-4o-mini"  # Fast & cheap
        )
    elif complexity == "complex":
        return await llm_service.simple_completion(
            prompt,
            provider="claude",  # Better reasoning
            model="claude-3-5-sonnet"
        )
    else:
        return await llm_service.simple_completion(prompt)  # Use default
```

## 📊 Error Handling

```python
try:
    response = await llm_service.simple_completion("Hello")
except Exception as e:
    print(f"LLM call failed: {e}")
    # Fallback to different provider
    response = await llm_service.simple_completion(
        "Hello",
        provider="claude"  # Try different provider
    )
```

## 🎯 Best Practices

1. **Set global defaults** in `.env` for your most common use case
2. **Use cheaper models** (`gpt-4o-mini`) for simple tasks like extraction
3. **Use Claude** for complex reasoning and analysis
4. **Use OpenAI** for code generation and structured outputs
5. **Override per call** only when needed - let defaults handle most cases
6. **Add error handling** with fallback to different providers

## 🔧 Configuration

Your `.env` should have:
```bash
# Required
OPENAI_API_KEY=sk-...
DEFAULT_LLM_MODEL=openai:gpt-4o

# Optional
CLAUDE_API_KEY=sk-ant-...
# GROK_API_KEY=...  # When available
```

That's it! The LLM service handles provider management, model selection, and gives you flexibility to optimize for cost and performance. 🚀