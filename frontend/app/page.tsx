import React from 'react';
import { Chat } from './components/chat';

export default function Home() {
	return (
		<div className="min-h-screen bg-gradient-to-br from-background to-muted/20 flex flex-col items-center justify-center p-4">
			<div className="w-full max-w-4xl mx-auto space-y-8">
				<header className="text-center space-y-4">
					<h1 className="text-4xl font-bold">
						Contract <span className="text-primary">Comparisons</span>
					</h1>
					<p className="text-lg text-muted-foreground">
						Using WIPO to give recommendations
					</p>
				</header>
				
				<main className="w-full">
					<Chat />
				</main>
			</div>
		</div>
	);
}
