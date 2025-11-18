"""
Server Endpoint Tests

Basic tests to verify that the core API endpoints work properly.
These tests focus on the most critical server functionality.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.server
@pytest.mark.integration
class TestHealthEndpoints:
    """Test basic server health and status endpoints."""

    def test_health_endpoint_returns_200(self, client: TestClient):
        """Test that the health endpoint is accessible and returns 200."""
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_structure(self, client: TestClient):
        """Test that the health endpoint returns expected data structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check for expected fields
        expected_fields = [
            "status",
            "server_initialized",
            "agents_count",
            "active_agents",
            "version",
        ]
        for field in expected_fields:
            assert (
                field in data
            ), f"Expected field '{field}' not found in health response"

        # Check basic data types
        assert isinstance(data["status"], str)
        assert isinstance(data["server_initialized"], bool)
        assert isinstance(data["agents_count"], int)
        assert isinstance(data["active_agents"], int)


@pytest.mark.server
@pytest.mark.integration
class TestAgentListingEndpoints:
    """Test agent discovery and listing endpoints."""

    def test_list_agents_endpoint(self, client: TestClient):
        """Test that the agents listing endpoint works."""
        response = client.get("/mcp/agents")

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)

        # Check expected structure
        expected_fields = ["total_agents", "active_agents", "agents"]
        for field in expected_fields:
            assert (
                field in data
            ), f"Expected field '{field}' not found in agents response"

        # Check data types
        assert isinstance(data["total_agents"], int)
        assert isinstance(data["active_agents"], int)
        assert isinstance(data["agents"], list)

    def test_list_agents_contains_valid_agents(self, client: TestClient):
        """Test that the agents list contains properly structured agent data."""
        response = client.get("/mcp/agents")

        assert response.status_code == 200
        data = response.json()

        # If there are agents, check their structure
        if data["agents"]:
            agent = data["agents"][0]

            # Check agent has expected fields
            expected_agent_fields = ["agent_id", "name", "description", "status", "tools"]
            for field in expected_agent_fields:
                assert (
                    field in agent
                ), f"Expected field '{field}' not found in agent data"

            # Check tools structure
            assert isinstance(agent["tools"], list)

            # If there are tools, check their structure
            if agent["tools"]:
                tool = agent["tools"][0]
                assert isinstance(tool, dict)
                assert "name" in tool


@pytest.mark.server
@pytest.mark.integration
class TestMCPResourcesEndpoint:
    """Test MCP resources discovery endpoint."""

    def test_mcp_resources_endpoint(self, client: TestClient):
        """Test that the MCP resources endpoint works."""
        response = client.get("/mcp/resources")

        assert response.status_code == 200

        data = response.json()
        # The endpoint returns {"resources": [...]} not just [...]
        assert isinstance(data, dict)
        assert "resources" in data
        assert isinstance(data["resources"], list)

        # If there are resources, check their structure
        if data["resources"]:
            resource = data["resources"][0]
            assert isinstance(resource, dict)

            # Check for expected resource fields
            expected_fields = ["name", "description", "type"]
            for field in expected_fields:
                assert (
                    field in resource
                ), f"Expected field '{field}' not found in resource"


@pytest.mark.server
@pytest.mark.integration
class TestBasicErrorHandling:
    """Test basic error handling for server endpoints."""

    def test_nonexistent_endpoint_returns_404(self, client: TestClient):
        """Test that accessing non-existent endpoints returns 404."""
        response = client.get("/this-endpoint-does-not-exist")

        assert response.status_code == 404

    def test_invalid_agent_id_returns_400(self, client: TestClient):
        """Test that invalid agent IDs return proper error."""
        response = client.post("/mcp/execute/not-a-valid-uuid", json={"tool": "test"})

        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "Invalid agent ID" in data["detail"]

    def test_nonexistent_agent_returns_404(self, client: TestClient):
        """Test that requesting non-existent agent returns 404."""
        fake_uuid = "12345678-1234-5678-9abc-123456789abc"
        response = client.post(f"/mcp/execute/{fake_uuid}", json={"tool": "test"})

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


@pytest.mark.server
@pytest.mark.unit
class TestDocumentationEndpoints:
    """Test that documentation endpoints are accessible."""

    def test_docs_endpoint_accessible(self, client: TestClient):
        """Test that the OpenAPI docs endpoint is accessible."""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_json_accessible(self, client: TestClient):
        """Test that the OpenAPI JSON schema is accessible."""
        response = client.get("/openapi.json")

        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
