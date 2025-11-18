import { NextRequest, NextResponse } from 'next/server';

// MCP Server configuration
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://localhost:8000';

export async function POST(request: Request) {
	try {
		const { message } = await request.json();

		if (!message) {
			return NextResponse.json(
				{ error: 'Message is required' },
				{ status: 400 }
			);
		}

		// Forward query to MCP server orchestrator endpoint
		const response = await fetch(`${MCP_SERVER_URL}/orchestrate`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({ query: message }),
		});

		if (!response.ok) {
			const errorText = await response.text();
			throw new Error(`MCP server error: ${response.status} - ${errorText}`);
		}

		const result = await response.json();

		return NextResponse.json({
			response: result.interpreted_response || result.response || 'No response received',
			agents_used: result.agents_used || [],
			internal_results: result.internal_results,
			external_results: result.external_results,
		});

	} catch (error: any) {
		console.error('Error:', error);
		return NextResponse.json(
			{ 
				error: 'Failed to process request',
				message: error.message || 'Unknown error'
			},
			{ status: 500 }
		);
	}
}
