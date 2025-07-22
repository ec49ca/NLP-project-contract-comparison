# 🔄 LLM Provider Hotswapping Guide

## Overview

This system allows you to easily switch between different LLM providers (OpenAI, Claude, Grok) without changing your application code. You can hotswap providers globally or override them per API call.

## 🏗️ Architecture

```
┌─────────────────────┐
│   Your Application │
├─────────────────────┤
│   LLMService        │ ← Single unified interface
├─────────────────────┤
│ OpenAI │ Claude │ Grok │ ← Pluggable providers
└─────────────────────┘
```

### Key Components:

1. **`LLMInterface`** (`src/interfaces/`) - Abstract interface all providers implement
2. **`LLMService`** (`src/services/`) - Single service that manages all providers
3. **Provider Implementations** (`src/providers/`) - OpenAI, Claude, Grok implementations

## 🚀 Quick Start

### 1. Configuration

Add to your `.env` file:
```bash
# Global LLM provider (default for all calls)
LLM_PROVIDER=openai

# OpenAI (always available)
OPENAI_API_KEY=your-openai-key-here

# Claude (optional)
CLAUDE_API_KEY=your-claude-key-here

# Grok (when available)
GROK_API_KEY=your-grok-key-here
```

### 2. Basic Usage

```python
from src.services.llm_service import llm_service

# Use current provider (set by LLM_PROVIDER env var)
response = await llm_service.simple_completion("Hello world")

# Override provider for specific call
response = await llm_service.simple_completion(
    "Hello world",
    provider="claude"
)

# Switch global provider
llm_service.set_provider("grok")
```

### 3. Unified Service Usage

```python
# UNIFIED APPROACH - Single LLM service for everything
from src.services.llm_service import llm_service

# Extract entities (replace old OpenAI service calls)
response = await llm_service.simple_completion(
    "Extract entities from: 'John works at OpenAI' Return JSON.",
    provider="openai",  # Optional provider override
    response_format={"type": "json_object"}
)

# Switch providers for different tasks
summary = await llm_service.simple_completion(
    "Summarize this text...",
    provider="claude"
)
```

## 🔧 Implementation Details

### Adding a New Provider

1. **Create provider class**:
```python
# src/providers/grok_provider.py
class GrokProvider(LLMInterface):
    async def chat_completion(self, messages, **kwargs):
        # Implement Grok API call
        pass

    async def simple_completion(self, prompt, **kwargs):
        # Implement simple completion
        pass
```

2. **Register in LLMService**:
```python
# src/services/llm_service.py
from ..providers.grok_provider import GrokProvider

def _register_providers(self):
    if os.getenv("GROK_API_KEY"):
        self.providers["grok"] = GrokProvider()
```

### Per-Call Provider Override

```python
# Use different providers for different tasks
entities = await llm_service.simple_completion(
    "Extract entities...",
    provider="openai"
)

summary = await llm_service.simple_completion(
    "Summarize this...",
    provider="claude"
)

code = await llm_service.simple_completion(
    "Generate code...",
    provider="grok"
)
```

## 🔍 Current Integration Points

### Files that use LLM services:
- `src/agents/tools/extract_triples.py`
- `src/agents/tools/ner_el_tool.py`
- `src/agents/tools/relation_extraction_tool.py`
- `src/agents/tool_generator_agent.py`

### Migration Strategy:

1. **Replace OpenAI service imports**: Change to `llm_service`
2. **Update method calls**: Use `simple_completion` or `chat_completion`
3. **Add provider-specific optimizations**: Use provider parameter for different tasks

## 📊 Benefits

### ✅ **Simple**:
- Same API, different backends
- Environment variable configuration
- Backward compatibility

### ✅ **Flexible**:
- Global or per-call provider switching
- Easy to add new providers
- Provider-specific model selection

### ✅ **Robust**:
- Automatic provider registration
- Connection validation
- Graceful fallbacks

## 🧪 Testing

Run the demo:
```bash
python example_llm_hotswap_usage.py
```

Expected output:
```
🚀 LLM Provider Hotswapping Demo
📋 Available providers: ['openai']
🎯 Current provider: openai
✅ OpenAI override: One, two, three
📊 Provider Information:
  openai:
    Default model: gpt-4o
    Available models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4', 'gpt-3.5-turbo']
```

## 🔮 Future Enhancements

### Provider-Specific Features:
```python
# OpenAI-specific features
response = await llm_service.chat_completion(
    messages=messages,
    provider="openai",
    response_format={"type": "json_object"}  # OpenAI-specific
)

# Claude-specific features
response = await llm_service.chat_completion(
    messages=messages,
    provider="claude",
    system_prompt="You are helpful assistant"  # Claude-specific
)
```

### Smart Provider Selection:
```python
# Auto-select best provider for task
entities = await llm_service.extract_entities(
    text,
    auto_select_provider=True,  # Choose based on task type
    task_type="entity_extraction"
)
```

### Cost Optimization:
```python
# Use cheaper models for simple tasks
response = await llm_service.simple_completion(
    "Simple question",
    cost_optimize=True  # Automatically select cheapest suitable model
)
```

## 🏃‍♂️ Next Steps

1. **Add Claude Provider**: Implement actual Claude API integration
2. **Add Grok Provider**: When Grok API becomes available
3. **Migrate Existing Tools**: Update tools to use unified `llm_service`
4. **Add Model-Specific Logic**: Optimize prompts per provider
5. **Add Cost Tracking**: Monitor usage across providers

## 📝 Environment Variables Summary

```bash
# Required
OPENAI_API_KEY=sk-...

# Provider selection
LLM_PROVIDER=openai  # openai|claude|grok

# Optional providers
CLAUDE_API_KEY=...
GROK_API_KEY=...

# OpenAI specific
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.1
```

---

This system provides a **simple, clean way** to hotswap LLM providers while maintaining full backward compatibility! 🎉