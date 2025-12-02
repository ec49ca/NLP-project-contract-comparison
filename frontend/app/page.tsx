"use client";

import React, { useState } from 'react';
import { Chat } from './components/chat';
import { DocumentSidebar } from './components/document-sidebar';

export default function Home() {
	const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);

	return (
		<div className="min-h-screen bg-gradient-to-br from-white via-cyan-50/20 via-teal-50/20 to-emerald-50/20 flex flex-col">
			<div className="w-full max-w-7xl mx-auto flex-1 flex flex-col px-6 pt-6 pb-6">
				<header className="text-center space-y-2 mb-6">
					<h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 via-teal-700 to-cyan-700 bg-clip-text text-transparent">
						Contract <span className="bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 bg-clip-text text-transparent">Comparisons</span>
					</h1>
					<p className="text-base text-slate-700 font-semibold">
						Using WIPO to give recommendations
					</p>
				</header>
				
				<main className="flex-1 flex gap-6 min-h-0">
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
