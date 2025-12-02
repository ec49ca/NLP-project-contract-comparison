"use client";

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { SendIcon, BotIcon, UserIcon, ChevronDown, ChevronRight } from 'lucide-react';

type StructuredQuote = {
	agent_id: string;
	document: string;
	topic: string;
	section: string;
	quote: string;
	type: 'key_term' | 'country_specific';
};

type Message = {
	id: string;
	content: string;
	role: 'user' | 'assistant';
	timestamp: Date;
	structured_quotes?: StructuredQuote[];
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

// Component to display structured quotes references
function QuoteReferences({ quotes }: { quotes: StructuredQuote[] }) {
	const [expandedRefs, setExpandedRefs] = useState<Set<string>>(new Set());
	
	if (!quotes || quotes.length === 0) {
		return null;
	}
	
	// Group quotes by agent_id and document
	const groupedQuotes = quotes.reduce((acc, quote) => {
		const key = `${quote.agent_id}-${quote.document}`;
		if (!acc[key]) {
			acc[key] = {
				agent_id: quote.agent_id,
				document: quote.document,
				quotes: []
			};
		}
		acc[key].quotes.push(quote);
		return acc;
	}, {} as Record<string, { agent_id: string; document: string; quotes: StructuredQuote[] }>);
	
	const toggleExpand = (key: string) => {
		setExpandedRefs(prev => {
			const next = new Set(prev);
			if (next.has(key)) {
				next.delete(key);
			} else {
				next.add(key);
			}
			return next;
		});
	};
	
	// Group quotes by section within each reference
	const groupQuotesBySection = (quotes: StructuredQuote[]) => {
		return quotes.reduce((acc, quote) => {
			if (!acc[quote.section]) {
				acc[quote.section] = [];
			}
			acc[quote.section].push(quote);
			return acc;
		}, {} as Record<string, StructuredQuote[]>);
	};
	
	return (
		<div className="mt-3 space-y-2">
			<div className="text-xs font-semibold text-muted-foreground mb-2">References:</div>
			{Object.entries(groupedQuotes).map(([key, group]) => {
				const isExpanded = expandedRefs.has(key);
				const sectionGroups = groupQuotesBySection(group.quotes);
				const agentNum = group.agent_id.replace('internal_', '');
				
				return (
					<div key={key} className="border border-border rounded-md overflow-hidden">
						<button
							onClick={() => toggleExpand(key)}
							className="w-full px-3 py-2 bg-muted/50 hover:bg-muted/70 flex items-center justify-between text-sm transition-colors"
						>
							<span className="font-medium">
								Internal Agent {agentNum} - {group.document}
							</span>
							{isExpanded ? (
								<ChevronDown className="w-4 h-4" />
							) : (
								<ChevronRight className="w-4 h-4" />
							)}
						</button>
						{isExpanded && (
							<div className="bg-background border-t">
								{Object.entries(sectionGroups).map(([section, sectionQuotes]) => (
									<div key={section} className="p-3 border-b last:border-b-0">
										<div className="text-xs font-semibold text-primary mb-2">
											{section}
										</div>
										<div className="space-y-2">
											{sectionQuotes.map((quote, idx) => (
												<div key={idx} className="text-xs pl-2 border-l-2 border-primary/20">
													<div className="text-muted-foreground mb-1">
														{quote.topic !== 'Country-Specific Reference' && (
															<span className="font-medium">{quote.topic}: </span>
														)}
													</div>
													<div className="text-foreground italic">
														"{quote.quote}"
													</div>
												</div>
											))}
										</div>
									</div>
								))}
							</div>
						)}
					</div>
				);
			})}
		</div>
	);
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
	type TimelineStep = {
		id: string;
		step: string;
		message: string;
		status: 'pending' | 'active' | 'completed';
		progress?: number;
		documents?: string[];
		agents?: string[];
		agent_tasks?: Array<{
			task_id: string;
			agent_type: string;
			document?: string;
			status: 'pending' | 'running' | 'completed';
		}>;
	};
	
	const [timeline, setTimeline] = useState<TimelineStep[]>([]);
	const [isStreaming, setIsStreaming] = useState(false);
	const [activeMessageId, setActiveMessageId] = useState<string | null>(null);
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
		setTimeline([]);
		setIsStreaming(false);
		
		// Add temporary loading message
		const tempBotId = (Date.now() + 1).toString();
		setActiveMessageId(tempBotId);
		const tempBotMessage: Message = {
			id: tempBotId,
			content: '',
			role: 'assistant',
			timestamp: new Date(),
		};
		setMessages((prev) => [...prev, tempBotMessage]);
		
		try {
			// Use streaming endpoint
			const response = await fetch(`${MCP_SERVER_URL}/orchestrate/stream`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ 
					query: currentInput,
					selected_documents: selectedDocuments.length > 0 ? selectedDocuments : undefined,
					provider: selectedProvider || undefined,
					model: selectedModel || undefined
				}),
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}

			const reader = response.body?.getReader();
			const decoder = new TextDecoder();
			let buffer = '';
			let accumulatedContent = '';

			if (!reader) {
				throw new Error('No response body');
			}

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (line.startsWith('data: ')) {
						try {
							const data = JSON.parse(line.slice(6));
							
							if (data.type === 'status') {
								// Update or create timeline step
								setTimeline((prev) => {
									const existingIndex = prev.findIndex(s => s.step === data.step);
									const newStep: TimelineStep = {
										id: data.step,
										step: data.step,
										message: data.message,
										status: 'active',
										progress: data.progress || 0,
										documents: data.documents,
										agents: data.agents,
										agent_tasks: data.agent_tasks
									};
									
									if (existingIndex >= 0) {
										// Update existing step
										const updated = [...prev];
										updated[existingIndex] = { ...updated[existingIndex], ...newStep };
										// Mark previous steps as completed
										for (let i = 0; i < existingIndex; i++) {
											updated[i] = { ...updated[i], status: 'completed' as const };
										}
										return updated;
									} else {
										// Add new step
										const updated = prev.map(s => ({ ...s, status: s.step === data.step ? 'active' : (s.status === 'active' ? 'completed' : s.status) as 'pending' | 'active' | 'completed' }));
										return [...updated, newStep];
									}
								});
								
								// Update message with status
								setMessages((prev) => prev.map(msg => 
									msg.id === tempBotId 
										? { ...msg, content: `🔄 ${data.message}` }
										: msg
								));
							} else if (data.type === 'agent_status') {
								// Update specific agent task status in timeline
								setTimeline((prev) => {
									return prev.map(step => {
										if (step.step === 'executing' && step.agent_tasks) {
											const updatedTasks = step.agent_tasks.map(task => 
												task.task_id === data.task_id
													? { ...task, status: data.status as 'pending' | 'running' | 'completed' }
													: task
											);
											return { ...step, agent_tasks: updatedTasks };
										}
										return step;
									});
								});
							} else if (data.type === 'content') {
								// Start streaming - hide timeline
								setIsStreaming(true);
								// Stream content chunks
								accumulatedContent += data.chunk;
								setMessages((prev) => prev.map(msg => 
									msg.id === tempBotId 
										? { ...msg, content: accumulatedContent }
										: msg
								));
							} else if (data.type === 'complete') {
								// Final result
								setIsStreaming(false);
								setTimeline([]);
								setActiveMessageId(null);
								const result = data.data;
			setMessages((prev) => prev.map(msg => 
				msg.id === tempBotId 
										? { 
											...msg, 
											content: result.interpreted_response || accumulatedContent,
											structured_quotes: result.structured_quotes || []
										}
					: msg
			));
							} else if (data.type === 'error') {
								throw new Error(data.message);
							}
						} catch (parseError) {
							console.error('Error parsing SSE data:', parseError);
						}
					}
				}
			}
		} catch (error: any) {
			console.error('Error:', error);
			setMessages((prev) => prev.map(msg => 
				msg.id === tempBotId 
					? { ...msg, content: `❌ Error: ${error.message || 'Failed to process request'}` }
					: msg
			));
			setTimeline([]);
			setIsStreaming(false);
			setActiveMessageId(null);
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
						<div className="max-w-[80%]">
						<div
								className={`rounded-lg px-4 py-2 ${
								message.role === 'user'
									? 'bg-primary text-primary-foreground'
									: 'bg-muted'
							}`}
						>
								{/* Show timeline if this is the active message and timeline exists and not streaming */}
								{message.role === 'assistant' && !isStreaming && timeline.length > 0 && message.id === activeMessageId ? (
									<div className="space-y-4 py-2">
										{timeline.map((step, index) => (
											<div key={step.id} className="flex gap-3">
												{/* Timeline line */}
												<div className="flex flex-col items-center">
													<div className={`w-3 h-3 rounded-full border-2 ${
														step.status === 'completed' 
															? 'bg-primary border-primary' 
															: step.status === 'active'
															? 'bg-primary border-primary animate-pulse'
															: 'bg-transparent border-muted-foreground'
													}`} />
													{index < timeline.length - 1 && (
														<div className={`w-0.5 h-8 mt-1 ${
															step.status === 'completed' ? 'bg-primary' : 'bg-muted'
														}`} />
													)}
												</div>
												
												{/* Step content */}
												<div className="flex-1 space-y-2">
													<div className="flex items-center justify-between">
														<span className={`text-sm font-medium ${
															step.status === 'completed' 
																? 'text-muted-foreground' 
																: step.status === 'active'
																? 'text-foreground'
																: 'text-muted-foreground'
														}`}>
															{step.step === 'analyzing' && '🔍 Analyzing Query'}
															{step.step === 'planning' && '📋 Planning Agent Calls'}
															{step.step === 'executing' && '🤖 Executing Agents'}
															{step.step === 'synthesizing' && '🔄 Synthesizing Results'}
														</span>
														{step.progress !== undefined && (
															<span className="text-xs text-muted-foreground">{step.progress}%</span>
														)}
													</div>
													<div className="text-xs text-muted-foreground">{step.message}</div>
													
													{/* Agent tasks detail */}
													{step.agent_tasks && step.agent_tasks.length > 0 && (
														<div className="ml-4 space-y-1 mt-2">
															{step.agent_tasks.map((task) => (
																<div key={task.task_id} className="flex items-center gap-2 text-xs">
																	<span className={`w-2 h-2 rounded-full ${
																		task.status === 'completed'
																			? 'bg-green-500'
																			: task.status === 'running'
																			? 'bg-blue-500 animate-pulse'
																			: 'bg-gray-400'
																	}`} />
																	<span className="text-muted-foreground">
																		{task.agent_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
																		{task.document && ` → ${task.document}`}
																	</span>
																</div>
															))}
														</div>
													)}
													
													{/* Documents and agents info */}
													{step.documents && step.documents.length > 0 && (
														<div className="text-xs text-muted-foreground ml-4">
															📄 Documents: {step.documents.join(', ')}
														</div>
													)}
													{step.agents && step.agents.length > 0 && (
														<div className="text-xs text-muted-foreground ml-4">
															🤖 Agents: {step.agents.join(', ')}
														</div>
													)}
												</div>
											</div>
										))}
									</div>
								) : (
									<div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-bold prose-headings:text-foreground prose-h2:text-lg prose-h2:mt-6 prose-h2:mb-3 prose-h3:text-base prose-h3:mt-4 prose-h3:mb-2 prose-p:my-2 prose-strong:text-foreground prose-strong:font-semibold prose-ul:my-2 prose-li:my-1 prose-blockquote:border-l-4 prose-blockquote:border-primary prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:my-2">
								<ReactMarkdown>{message.content}</ReactMarkdown>
									</div>
								)}
								<ClientTimestamp timestamp={message.timestamp} />
							</div>
							{message.role === 'assistant' && message.structured_quotes && message.structured_quotes.length > 0 && (
								<QuoteReferences quotes={message.structured_quotes} />
							)}
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
