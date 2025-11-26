"use client";

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { SendIcon, BotIcon, UserIcon } from 'lucide-react';

type Message = {
	id: string;
	content: string;
	role: 'user' | 'assistant';
	timestamp: Date;
};

// Client-only timestamp component to prevent hydration mismatches
function ClientTimestamp({ timestamp }: { timestamp: Date }) {
	const [mounted, setMounted] = useState(false);
	const [timeString, setTimeString] = useState('');

	useEffect(() => {
		setMounted(true);
		setTimeString(timestamp.toLocaleTimeString());
	}, [timestamp]);

	if (!mounted) {
		return <span className="text-xs opacity-70 mt-1 block">Loading...</span>;
	}

	return <span className="text-xs opacity-70 mt-1 block">{timeString}</span>;
}

type ChatProps = {
	selectedDocuments?: string[];
};

// Use the same MCP server URL as the chat API route
const MCP_SERVER_URL = typeof window !== 'undefined' 
	? (process.env.NEXT_PUBLIC_MCP_SERVER_URL || 'http://localhost:8000')
	: 'http://localhost:8000';

type ModelInfo = {
	provider: string;
	default_model: string;
	available_models: string[];
};

type ProviderInfo = {
	current_provider: string;
	available_providers: string[];
};

export function Chat({ selectedDocuments = [] }: ChatProps) {
	const [messages, setMessages] = useState<Message[]>([
		{
			id: '1',
			content: 'Hello! I can help you query the MCP server. Ask me anything!',
			role: 'assistant',
			timestamp: new Date(),
		},
	]);
	const [input, setInput] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
	const [selectedModel, setSelectedModel] = useState<string | null>(null);
	const [availableProviders, setAvailableProviders] = useState<ProviderInfo | null>(null);
	const [availableModels, setAvailableModels] = useState<ModelInfo | null>(null);
	const messagesEndRef = useRef<HTMLDivElement>(null);
	
	// Fetch available providers on component mount
	useEffect(() => {
		const fetchProviders = async () => {
			try {
				const response = await fetch(`${MCP_SERVER_URL}/api/providers`);
				if (response.ok) {
					const data = await response.json();
					setAvailableProviders(data);
					setSelectedProvider(data.current_provider);
					// Fetch models for the current provider
					fetchModels(data.current_provider);
				}
			} catch (error) {
				console.error('Error fetching providers:', error);
			}
		};
		fetchProviders();
	}, []);
	
	// Fetch models for a specific provider
	const fetchModels = async (provider: string) => {
		try {
			const response = await fetch(`${MCP_SERVER_URL}/api/models?provider=${provider}`);
			if (response.ok) {
				const data = await response.json();
				setAvailableModels(data);
				setSelectedModel(data.default_model);
			}
		} catch (error) {
			console.error('Error fetching models:', error);
		}
	};
	
	// When provider changes, fetch its models
	useEffect(() => {
		if (selectedProvider) {
			fetchModels(selectedProvider);
		}
	}, [selectedProvider]);

	const scrollToBottom = () => {
		messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
	};

	useEffect(() => {
		scrollToBottom();
	}, [messages]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		
		if (!input.trim() || isLoading) return;
		
		// Add user message
		const userMessage: Message = {
			id: Date.now().toString(),
			content: input,
			role: 'user',
			timestamp: new Date(),
		};
		
		setMessages((prev) => [...prev, userMessage]);
		const currentInput = input;
		setInput('');
		setIsLoading(true);
		
		// Add temporary loading message
		const tempBotId = (Date.now() + 1).toString();
		const tempBotMessage: Message = {
			id: tempBotId,
			content: '🔄 Processing...',
			role: 'assistant',
			timestamp: new Date(),
		};
		setMessages((prev) => [...prev, tempBotMessage]);
		
		try {
			const response = await fetch('/api/chat', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ 
					message: currentInput,
					selectedDocuments: selectedDocuments.length > 0 ? selectedDocuments : undefined,
					provider: selectedProvider || undefined,
					model: selectedModel || undefined
				}),
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}

			const data = await response.json();
			
			// Update the temporary message with the actual response
			setMessages((prev) => prev.map(msg => 
				msg.id === tempBotId 
					? { ...msg, content: data.response || 'No response received' }
					: msg
			));
		} catch (error: any) {
			console.error('Error:', error);
			setMessages((prev) => prev.map(msg => 
				msg.id === tempBotId 
					? { ...msg, content: `❌ Error: ${error.message || 'Failed to process request'}` }
					: msg
			));
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="flex flex-col h-[700px] max-h-[85vh] w-full bg-background border rounded-lg shadow-lg">
			{/* Provider and Model Selectors */}
			{(availableProviders || availableModels) && (
				<div className="border-b p-3 bg-muted/30">
					<div className="flex gap-3 items-end">
						{availableProviders && availableProviders.available_providers.length > 0 && (
							<div className="flex-1">
								<label className="text-sm font-medium mb-1 block">Provider:</label>
								<select
									value={selectedProvider || availableProviders.current_provider}
									onChange={(e) => setSelectedProvider(e.target.value)}
									className="w-full px-3 py-2 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
									disabled={isLoading}
								>
									{availableProviders.available_providers.map((provider) => (
										<option key={provider} value={provider}>
											{provider} {provider === availableProviders.current_provider ? '(default)' : ''}
										</option>
									))}
								</select>
							</div>
						)}
						{availableModels && availableModels.available_models.length > 0 && (
							<div className="flex-1">
								<label className="text-sm font-medium mb-1 block">Model:</label>
								<select
									value={selectedModel || availableModels.default_model}
									onChange={(e) => setSelectedModel(e.target.value)}
									className="w-full px-3 py-2 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
									disabled={isLoading}
								>
									{availableModels.available_models.map((model) => (
										<option key={model} value={model}>
											{model} {model === availableModels.default_model ? '(default)' : ''}
										</option>
									))}
								</select>
							</div>
						)}
					</div>
				</div>
			)}
			{/* Messages */}
			<div className="flex-1 overflow-y-auto p-4 space-y-4">
				{messages.map((message) => (
					<div
						key={message.id}
						className={`flex gap-3 ${
							message.role === 'user' ? 'justify-end' : 'justify-start'
						}`}
					>
						{message.role === 'assistant' && (
							<div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
								<BotIcon className="w-5 h-5 text-primary" />
							</div>
						)}
						<div
							className={`max-w-[80%] rounded-lg px-4 py-2 ${
								message.role === 'user'
									? 'bg-primary text-primary-foreground'
									: 'bg-muted'
							}`}
						>
							<div className="prose prose-sm dark:prose-invert max-w-none">
								<ReactMarkdown>{message.content}</ReactMarkdown>
							</div>
							<ClientTimestamp timestamp={message.timestamp} />
						</div>
						{message.role === 'user' && (
							<div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
								<UserIcon className="w-5 h-5 text-primary" />
							</div>
						)}
					</div>
				))}
				<div ref={messagesEndRef} />
			</div>

			{/* Input */}
			<form onSubmit={handleSubmit} className="border-t p-4">
				<div className="flex gap-2">
					<Input
						value={input}
						onChange={(e) => setInput(e.target.value)}
						placeholder="Type your message..."
						disabled={isLoading}
						className="flex-1"
					/>
					<Button type="submit" disabled={isLoading || !input.trim()}>
						<SendIcon className="w-4 h-4" />
					</Button>
				</div>
			</form>
		</div>
	);
}
