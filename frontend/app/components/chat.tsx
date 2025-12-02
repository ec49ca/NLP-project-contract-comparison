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
		<div className="mt-4 space-y-3">
			<div className="text-xs font-bold text-slate-800 uppercase tracking-wide mb-3 flex items-center gap-2">
				<span className="w-1 h-4 bg-gradient-to-b from-cyan-500 via-teal-500 to-emerald-500 rounded-full"></span>
				References
			</div>
			{Object.entries(groupedQuotes).map(([key, group]) => {
				const isExpanded = expandedRefs.has(key);
				const sectionGroups = groupQuotesBySection(group.quotes);
				const agentNum = group.agent_id.replace('internal_', '');
				
				return (
					<div key={key} className="border border-teal-200/60 rounded-xl overflow-hidden bg-gradient-to-br from-white via-cyan-50/30 to-teal-50/30 shadow-md hover:shadow-lg transition-all duration-200">
						<button
							onClick={() => toggleExpand(key)}
							className="w-full px-4 py-3 bg-gradient-to-r from-cyan-100/60 via-teal-100/60 to-emerald-100/60 hover:from-cyan-200/80 hover:via-teal-200/80 hover:to-emerald-200/80 flex items-center justify-between text-sm font-semibold transition-all duration-200 group border-b border-teal-200/40"
						>
							<span className="text-slate-900 group-hover:text-teal-700 transition-colors">
								Internal Agent {agentNum} - <span className="text-teal-700 font-bold">{group.document}</span>
							</span>
							<div className={`transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>
								{isExpanded ? (
									<ChevronDown className="w-4 h-4 text-teal-600" />
								) : (
									<ChevronRight className="w-4 h-4 text-slate-500" />
								)}
							</div>
						</button>
						{isExpanded && (
							<div className="bg-white/90 backdrop-blur-sm border-t border-teal-200/40">
								{Object.entries(sectionGroups).map(([section, sectionQuotes]) => (
									<div key={section} className="p-4 border-b border-teal-200/30 last:border-b-0 hover:bg-gradient-to-r hover:from-cyan-50/50 hover:to-teal-50/50 transition-colors">
										<div className="text-xs font-bold text-teal-700 mb-3 flex items-center gap-2">
											<span className="w-1.5 h-1.5 bg-gradient-to-br from-cyan-500 to-teal-600 rounded-full shadow-sm"></span>
											{section}
										</div>
										<div className="space-y-3">
											{sectionQuotes.map((quote, idx) => (
												<div key={idx} className="text-xs pl-4 border-l-3 border-teal-400/50 bg-gradient-to-r from-cyan-50/80 to-teal-50/80 rounded-r-lg p-3 hover:from-cyan-100/80 hover:to-teal-100/80 transition-colors">
													{quote.topic !== 'Country-Specific Reference' && (
														<div className="text-slate-800 font-bold mb-1.5">
															{quote.topic}
														</div>
													)}
													<div className="text-black italic leading-relaxed">
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
		<div className="flex flex-col h-[700px] max-h-[85vh] w-full bg-gradient-to-br from-white via-slate-50 to-cyan-50/20 border border-slate-200/50 rounded-2xl shadow-2xl shadow-slate-900/5 backdrop-blur-sm">
			{/* Provider and Model Selectors */}
			{(availableProviders || availableModels) && (
				<div className="border-b border-slate-200/60 p-4 bg-gradient-to-r from-teal-50/60 via-cyan-50/40 to-blue-50/60 backdrop-blur-sm">
					<div className="flex gap-3 items-end">
						{availableProviders && availableProviders.available_providers.length > 0 && (
							<div className="flex-1">
								<label className="text-xs font-semibold mb-1.5 block text-slate-700 uppercase tracking-wide">Provider</label>
								<select
									value={selectedProvider || availableProviders.current_provider}
									onChange={(e) => setSelectedProvider(e.target.value)}
									className="w-full px-4 py-2.5 border border-teal-200/60 rounded-xl bg-white/90 backdrop-blur-sm text-sm font-medium text-slate-900 shadow-sm hover:shadow-md hover:border-teal-300/60 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-teal-400/50 transition-all duration-200"
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
								<label className="text-xs font-semibold mb-1.5 block text-slate-700 uppercase tracking-wide">Model</label>
								<select
									value={selectedModel || availableModels.default_model}
									onChange={(e) => setSelectedModel(e.target.value)}
									className="w-full px-4 py-2.5 border border-cyan-200/60 rounded-xl bg-white/90 backdrop-blur-sm text-sm font-medium text-slate-900 shadow-sm hover:shadow-md hover:border-cyan-300/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 transition-all duration-200"
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
			<div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-transparent via-white to-emerald-50/10">
				{messages.map((message) => (
					<div
						key={message.id}
						className={`flex gap-4 ${
							message.role === 'user' ? 'justify-end' : 'justify-start'
						}`}
					>
						{message.role === 'assistant' && (
							<div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500/20 via-cyan-500/20 to-blue-500/20 border border-teal-300/30 flex items-center justify-center shadow-lg shadow-teal-500/10">
								<BotIcon className="w-5 h-5 text-teal-600" />
							</div>
						)}
						<div className="max-w-[80%]">
						<div
								className={`rounded-2xl px-5 py-3 shadow-lg transition-all duration-200 ${
								message.role === 'user'
									? 'bg-gradient-to-br from-blue-700 via-blue-600 to-cyan-600 text-white shadow-primary/30'
									: 'bg-white border border-slate-200/60 shadow-slate-200/50'
							}`}
						>
								{/* Show timeline if this is the active message and timeline exists and not streaming */}
								{message.role === 'assistant' && !isStreaming && timeline.length > 0 && message.id === activeMessageId ? (
									<div className="space-y-5 py-3">
										{timeline.map((step, index) => (
											<div key={step.id} className="flex gap-4 group">
												{/* Timeline line with enhanced styling */}
												<div className="flex flex-col items-center">
													<div className={`w-4 h-4 rounded-full border-2 shadow-lg transition-all duration-300 ${
														step.status === 'completed' 
															? 'bg-gradient-to-br from-emerald-500 to-teal-600 border-emerald-600 shadow-emerald-500/40' 
															: step.status === 'active'
															? 'bg-gradient-to-br from-cyan-500 via-teal-500 to-blue-500 border-cyan-600 shadow-cyan-500/50 animate-pulse ring-2 ring-cyan-400/30'
															: 'bg-white border-slate-300 shadow-slate-200/50'
													}`} />
													{index < timeline.length - 1 && (
														<div className={`w-1 h-10 mt-2 rounded-full transition-all duration-300 ${
															step.status === 'completed' 
																? 'bg-gradient-to-b from-emerald-500 via-teal-500 to-cyan-500' 
																: 'bg-gradient-to-b from-slate-200 to-slate-100'
														}`} />
													)}
												</div>
												
												{/* Step content with card styling */}
												<div className="flex-1 space-y-3 bg-gradient-to-br from-white to-slate-50/50 border border-slate-200/60 rounded-xl p-4 shadow-md hover:shadow-lg transition-all duration-200">
													<div className="flex items-center justify-between">
														<span className={`text-sm font-semibold ${
															step.status === 'completed' 
																? 'text-slate-600' 
																: step.status === 'active'
																? 'text-slate-900 bg-gradient-to-r from-cyan-100 via-teal-100 to-blue-100 px-3 py-1 rounded-lg border border-cyan-200/60'
																: 'text-slate-500'
														}`}>
															{step.step === 'analyzing' && '🔍 Analyzing Query'}
															{step.step === 'planning' && '📋 Planning Agent Calls'}
															{step.step === 'executing' && '🤖 Executing Agents'}
															{step.step === 'synthesizing' && '🔄 Synthesizing Results'}
														</span>
														{step.progress !== undefined && (
															<span className="text-xs font-bold text-cyan-700 bg-gradient-to-r from-cyan-100 to-teal-100 px-3 py-1 rounded-full border border-cyan-200/60">{step.progress}%</span>
														)}
													</div>
													<div className="text-xs text-slate-700 font-medium">{step.message}</div>
													
													{/* Agent tasks detail with enhanced styling */}
													{step.agent_tasks && step.agent_tasks.length > 0 && (
														<div className="ml-2 space-y-2 mt-3 pt-3 border-t border-slate-200/60">
															{step.agent_tasks.map((task) => (
																<div key={task.task_id} className="flex items-center gap-3 text-xs bg-gradient-to-r from-emerald-50/80 via-teal-50/80 to-cyan-50/80 rounded-lg px-3 py-2 border border-emerald-200/40">
																	<span className={`w-2.5 h-2.5 rounded-full shadow-sm ${
																		task.status === 'completed'
																			? 'bg-gradient-to-br from-emerald-500 to-teal-600 shadow-emerald-500/50'
																			: task.status === 'running'
																			? 'bg-gradient-to-br from-cyan-500 via-teal-500 to-blue-500 shadow-cyan-500/50 animate-pulse'
																			: 'bg-slate-300'
																	}`} />
																	<span className="text-slate-800 font-medium">
																		<span className="font-semibold text-slate-900">{task.agent_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
																		{task.document && <span className="text-teal-700 font-semibold"> → {task.document}</span>}
																	</span>
																</div>
															))}
														</div>
													)}
													
													{/* Documents and agents info with badges */}
													{step.documents && step.documents.length > 0 && (
														<div className="text-xs ml-2 flex flex-wrap gap-2">
															<span className="text-slate-700 font-semibold">📄 Documents:</span>
															{step.documents.map((doc, i) => (
																<span key={i} className="bg-gradient-to-r from-cyan-100 to-teal-100 text-cyan-800 px-3 py-1 rounded-lg border border-cyan-300/60 font-semibold shadow-sm">{doc}</span>
															))}
														</div>
													)}
													{step.agents && step.agents.length > 0 && (
														<div className="text-xs ml-2 flex flex-wrap gap-2">
															<span className="text-slate-700 font-semibold">🤖 Agents:</span>
															{step.agents.map((agent, i) => (
																<span key={i} className="bg-gradient-to-r from-emerald-100 to-teal-100 text-emerald-800 px-3 py-1 rounded-lg border border-emerald-300/60 font-semibold shadow-sm">{agent}</span>
															))}
														</div>
													)}
												</div>
											</div>
										))}
									</div>
								) : (
									<div className="prose prose-sm dark:prose-invert max-w-none 
										prose-headings:font-bold prose-headings:text-black 
										prose-h2:text-xl prose-h2:mt-6 prose-h2:mb-4 prose-h2:text-black
										prose-h3:text-lg prose-h3:mt-5 prose-h3:mb-3 prose-h3:text-slate-900
										prose-p:my-3 prose-p:text-black prose-p:leading-relaxed
										prose-strong:text-black prose-strong:font-bold
										prose-ul:my-3 prose-ul:space-y-2
										prose-li:my-1 prose-li:text-black
										prose-blockquote:border-l-4 prose-blockquote:border-teal-400 prose-blockquote:pl-5 prose-blockquote:italic prose-blockquote:my-4 prose-blockquote:bg-gradient-to-r prose-blockquote:from-teal-50 prose-blockquote:to-cyan-50 prose-blockquote:py-2 prose-blockquote:rounded-r-lg prose-blockquote:text-black
										prose-code:text-teal-700 prose-code:bg-teal-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-semibold
										prose-a:text-teal-600 prose-a:font-medium hover:prose-a:text-teal-700 hover:prose-a:underline">
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
							<div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 via-cyan-500/20 to-teal-500/20 border border-blue-300/30 flex items-center justify-center shadow-lg shadow-blue-500/10">
								<UserIcon className="w-5 h-5 text-blue-600" />
							</div>
						)}
					</div>
				))}
				<div ref={messagesEndRef} />
			</div>

			{/* Input */}
			<form onSubmit={handleSubmit} className="border-t border-slate-200/60 p-5 bg-gradient-to-r from-white via-cyan-50/30 to-teal-50/30 backdrop-blur-sm">
				<div className="flex gap-3">
					<Input
						value={input}
						onChange={(e) => setInput(e.target.value)}
						placeholder="Type your message..."
						disabled={isLoading}
						className="flex-1 px-5 py-3 rounded-xl border-teal-200/60 bg-white/95 backdrop-blur-sm shadow-sm hover:shadow-md hover:border-teal-300/60 focus:shadow-lg focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 transition-all duration-200 text-sm font-medium text-black placeholder:text-slate-400"
					/>
					<Button 
						type="submit" 
						disabled={isLoading || !input.trim()}
						className="px-6 py-3 rounded-xl bg-gradient-to-br from-cyan-500 via-teal-500 to-blue-600 hover:from-cyan-600 hover:via-teal-600 hover:to-blue-700 shadow-lg shadow-cyan-500/30 hover:shadow-xl hover:shadow-cyan-500/40 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
					>
						<SendIcon className="w-4 h-4" />
					</Button>
				</div>
			</form>
		</div>
	);
}
