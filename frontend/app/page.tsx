"use client";

import React, { useState } from 'react';
import { Chat } from './components/chat';
import { DocumentSidebar } from './components/document-sidebar';

export default function Home() {
	const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);

	return (
		<div className="min-h-screen bg-gradient-to-br from-background to-muted/20 flex flex-col">
			<div className="w-full max-w-7xl mx-auto flex-1 flex flex-col px-4 pt-3 pb-4">
				<header className="text-center space-y-1 mb-2">
					<h1 className="text-3xl font-bold">
						Contract <span className="text-primary">Comparisons</span>
					</h1>
					<p className="text-base text-muted-foreground">
						Using WIPO to give recommendations
					</p>
				</header>
				
				<main className="flex-1 flex gap-4 min-h-0 -mt-2">
					<DocumentSidebar 
						selectedDocuments={selectedDocuments}
						onSelectionChange={setSelectedDocuments}
					/>
					<div className="flex-1 flex items-start justify-center">
						<div className="w-full max-w-4xl">
							<Chat selectedDocuments={selectedDocuments} />
						</div>
					</div>
				</main>
			</div>
		</div>
	);
}
