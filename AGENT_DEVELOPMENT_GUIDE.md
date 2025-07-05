# Agent Development Guide

This guide walks you through creating new agents for the multi-agent system using the standardized template and structure.

## Quick Start

1. **Copy the template**: `cp src/agents/template_agent.py src/agents/your_agent_name_agent.py`
2. **Customize the template** following the checklist below
3. **Register your agent** in the system
4. **Test your agent** with the provided examples

## Step-by-Step Instructions

### 1. Create Your Agent File

```bash
# Copy the template
cp src/agents/template_agent.py src/agents/my_new_agent.py
```

### 2. Customize the Template

Open your new agent file and update the following sections:

#### Required Changes:
- [ ] **Class Name**: Change `TemplateAgent` to `YourAgentNameAgent`
- [ ] **Agent ID**: Update `_agent_id_str` and `agent_id` to unique identifier
- [ ] **Name & Description**: Update `_name` and `_description`
- [ ] **Category**: Choose appropriate category (see categories below)
- [ ] **Process Request Logic**: Implement your agent's core functionality
- [ ] **Capabilities**: Define what tools/commands your agent provides
- [ ] **Custom Methods**: Add your specific business logic

#### Standard Agent Categories:
- `analysis` - Data analysis and statistical operations
- `search` - Search and retrieval operations
- `financial_modeling` - Financial calculations and modeling
- `knowledge_management` - Knowledge graphs and information extraction
- `tool_generation` - Dynamic tool creation
- `communication` - External API integrations
- `data_processing` - Data transformation and processing
- `machine_learning` - ML model training and inference

### 3. Example Customization

Here's how to transform the template into a "Weather Agent":

```python
class WeatherAgent(AgentInterface):
	"""Weather agent for fetching weather data and forecasts"""

	def __init__(self):
		# Standard attributes
		self._agent_id_str = "weather"
		self._uuid = None
		self.agent_id = "weather"
		self._name = "Weather Agent"
		self._description = "Fetches weather data and provides forecasts"
		self._initialized = False
		self.category = "communication"  # External API category
		self.status = "initialized"
		self._tools = {}

		# Custom attributes
		self.api_key = None
		self.base_url = "https://api.openweathermap.org/data/2.5"

	async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Process weather-related requests"""
		if not self._initialized:
			return {"error": "Agent not initialized"}

		command = request.get("command", "")

		if command == "current_weather":
			return await self._get_current_weather(request)
		elif command == "forecast":
			return await self._get_forecast(request)
		else:
			return {
				"error": f"Unknown command: {command}",
				"available_commands": ["current_weather", "forecast"]
			}

	def get_capabilities(self) -> List[Dict[str, Any]]:
		"""Define weather agent capabilities"""
		return [
			{
				"name": "current_weather",
				"description": "Get current weather for a location",
				"parameters": {
					"location": "string - City name or coordinates",
					"units": "string - Temperature units (metric/imperial, default: metric)"
				}
			},
			{
				"name": "forecast",
				"description": "Get weather forecast for a location",
				"parameters": {
					"location": "string - City name or coordinates",
					"days": "integer - Number of days (1-7, default: 5)"
				}
			}
		]
```

### 4. Register Your Agent

#### A. Add to `__init__.py`

Add your agent to `src/agents/__init__.py`:

```python
from .your_agent_name_agent import YourAgentNameAgent

__all__ = [
    "KnowledgeGraphAgent",
    "MetaAgent",
    "OptionsAgent",
    "StatsAgent",
    "ToolGeneratorAgent",
    "VectorSearchAgent",
    "YourAgentNameAgent",  # Add your agent here
]
```

#### B. Register in Discovery System

If your system uses agent discovery, add your agent to the discovery configuration:

```python
# In your discovery/registry configuration
AVAILABLE_AGENTS = {
    # ... existing agents ...
    "your_agent_name": YourAgentNameAgent,
}
```

### 5. Agent Integration Points

#### Service Dependencies
If your agent needs external services, add them to the initialization:

```python
async def initialize(self, config: Dict[str, Any]) -> None:
    """Initialize with external services"""
    # API keys
    self.api_key = config.get("your_api_key") or os.getenv("YOUR_API_KEY")

    # Database connections
    self.db_service = SomeService(config.get("db_config"))

    # Initialize tools
    for tool_name, tool in self._tools.items():
        if hasattr(tool, 'initialize'):
            await tool.initialize(config)

    self.status = "ready"
    self._initialized = True
```

#### Error Handling Pattern
Follow the standardized error handling pattern:

```python
async def _your_method(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """Your custom method with proper error handling"""
    try:
        # Input validation
        required_param = request.get("required_param")
        if not required_param:
            return {"error": "Missing required parameter: required_param"}

        # Your logic here
        result = self._process_data(required_param)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error in _your_method: {str(e)}")
        return {
            "status": "error",
            "message": f"Error processing request: {str(e)}"
        }
```

### 6. Testing Your Agent

#### Unit Tests
Create tests for your agent:

```python
# tests/test_your_agent.py
import pytest
from src.agents.your_agent_name_agent import YourAgentNameAgent

@pytest.mark.asyncio
async def test_agent_initialization():
    agent = YourAgentNameAgent()
    config = {"your_api_key": "test_key"}

    await agent.initialize(config)
    assert agent.status == "ready"
    assert agent._initialized == True

@pytest.mark.asyncio
async def test_process_request():
    agent = YourAgentNameAgent()
    await agent.initialize({})

    request = {"command": "your_command", "param1": "test"}
    result = await agent.process_request(request)

    assert result["status"] == "success"
```

#### Manual Testing
Test your agent with a simple script:

```python
# test_my_agent.py
import asyncio
from src.agents.your_agent_name_agent import YourAgentNameAgent

async def test_agent():
    agent = YourAgentNameAgent()
    await agent.initialize({})

    # Test basic functionality
    result = await agent.process_request({
        "command": "your_command",
        "param1": "test_value"
    })

    print("Result:", result)

    # Test capabilities
    capabilities = agent.get_capabilities()
    print("Capabilities:", capabilities)

    # Test status
    status = agent.get_status()
    print("Status:", status)

if __name__ == "__main__":
    asyncio.run(test_agent())
```

## Best Practices

### 1. Naming Conventions
- **File names**: `your_agent_name_agent.py` (lowercase with underscores)
- **Class names**: `YourAgentNameAgent` (PascalCase)
- **Agent IDs**: `your_agent_name` (lowercase with underscores)
- **Method names**: `_your_method_name` (private methods with underscore prefix)

### 2. Documentation
- Add comprehensive docstrings to all methods
- Document parameters and return values
- Include usage examples in docstrings
- Update README with your agent's capabilities

### 3. Error Handling
- Always validate inputs
- Use try-catch blocks for external API calls
- Return consistent error response format
- Log errors with appropriate detail level

### 4. Performance
- Use async/await for I/O operations
- Implement caching where appropriate
- Consider rate limiting for external APIs
- Clean up resources in shutdown method

### 5. Configuration
- Use environment variables for secrets
- Accept configuration through initialize method
- Provide sensible defaults
- Validate configuration on startup

## Common Agent Patterns

### API Integration Agent
```python
class APIAgent(AgentInterface):
    def __init__(self):
        # Standard setup
        self.client = None
        self.base_url = ""
        self.headers = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        import aiohttp
        self.client = aiohttp.ClientSession()
        self.headers = {"Authorization": f"Bearer {config['api_key']}"}
```

### Data Processing Agent
```python
class DataProcessingAgent(AgentInterface):
    def __init__(self):
        # Standard setup
        self.processors = {}
        self.cache = {}

    async def _process_data(self, data: List[Dict], operation: str):
        # Implement data transformations
        pass
```

### Machine Learning Agent
```python
class MLAgent(AgentInterface):
    def __init__(self):
        # Standard setup
        self.models = {}
        self.model_cache = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        # Load pre-trained models
        pass
```

## Troubleshooting

### Common Issues

1. **Agent Not Found**: Ensure agent is added to `__init__.py`
2. **Import Errors**: Check relative imports and dependencies
3. **Initialization Failures**: Verify configuration parameters
4. **Method Not Found**: Check command routing in `process_request`

### Debug Tips
- Enable debug logging: `logger.setLevel(logging.DEBUG)`
- Test initialization separately from request processing
- Use print statements for debugging during development
- Check agent status and capabilities through `get_status()`

## Advanced Features

### Tool Integration
```python
# Add custom tools to your agent
from .tools.your_custom_tool import YourCustomTool

class YourAgent(AgentInterface):
    def __init__(self):
        # Standard setup
        self._tools = {
            "custom_tool": YourCustomTool()
        }
```

### State Management
```python
class StatefulAgent(AgentInterface):
    def __init__(self):
        # Standard setup
        self.state = {}
        self.session_data = {}

    async def _save_state(self):
        # Implement state persistence
        pass
```

### Multi-Agent Coordination
```python
class CoordinatingAgent(AgentInterface):
    def __init__(self):
        # Standard setup
        self.other_agents = {}

    async def _coordinate_with_agent(self, agent_id: str, request: Dict):
        # Implement agent-to-agent communication
        pass
```

## Need Help?

- Check existing agents for reference implementations
- Review the agent interface definition
- Look at test files for usage examples
- Consult the main README for system architecture

Happy coding! 🚀