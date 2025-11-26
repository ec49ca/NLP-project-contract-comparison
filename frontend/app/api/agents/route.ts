import { NextResponse } from 'next/server';

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://localhost:8000';

async function discoverAgents() {
	try {
		const resourcesResponse = await fetch(`${MCP_SERVER_URL}/mcp/resources`);
		if (resourcesResponse.ok) {
			const resourcesData = await resourcesResponse.json();
			const agents = resourcesData.resources?.filter((resource: any) => resource.type === 'agent') || [];
			return agents;
		}
		
		// Fallback to basic agents endpoint
		const agentsResponse = await fetch(`${MCP_SERVER_URL}/mcp/agents`);
		if (agentsResponse.ok) {
			const agentsData = await agentsResponse.json();
			return agentsData.agents || [];
		}
		
		throw new Error('No working endpoint found');
	} catch (error) {
		console.error('Error discovering agents:', error);
		return [];
	}
}

export async function GET() {
	try {
		const agents = await discoverAgents();
		
		return NextResponse.json({
			connected: true,
			agents,
			server_url: MCP_SERVER_URL
		});
	} catch (error) {
		console.error('Error connecting to MCP server:', error);
		return NextResponse.json(
			{ 
				error: 'Failed to connect to MCP server',
				connected: false,
				server_url: MCP_SERVER_URL
			},
			{ status: 503 }
		);
	}
}
