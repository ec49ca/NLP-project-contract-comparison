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

export function Chat() {
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
	const messagesEndRef = useRef<HTMLDivElement>(null);

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
				body: JSON.stringify({ message: currentInput }),
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
		<div className="flex flex-col h-[600px] max-h-[80vh] w-full bg-background border rounded-lg shadow-lg">
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
