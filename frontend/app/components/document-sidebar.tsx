"use client";

import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { UploadIcon, FileIcon, XIcon, CheckIcon } from 'lucide-react';

// Use the same MCP server URL as the chat API route
// In production, this should be set via environment variable
const MCP_SERVER_URL = typeof window !== 'undefined' 
	? (process.env.NEXT_PUBLIC_MCP_SERVER_URL || 'http://localhost:8000')
	: 'http://localhost:8000';

type Document = {
	filename: string;
	uploaded_at: string;
	text_length: number;
};

type DocumentSidebarProps = {
	selectedDocuments: string[];
	onSelectionChange: (selected: string[]) => void;
};

export function DocumentSidebar({ selectedDocuments, onSelectionChange }: DocumentSidebarProps) {
	const [documents, setDocuments] = useState<Document[]>([]);
	const [isUploading, setIsUploading] = useState(false);
	const [isLoading, setIsLoading] = useState(true);

	// Load documents on mount
	useEffect(() => {
		loadDocuments();
	}, []);

	const loadDocuments = async () => {
		try {
			const response = await fetch(`${MCP_SERVER_URL}/api/documents`);
			if (response.ok) {
				const data = await response.json();
				setDocuments(data.documents || []);
			}
		} catch (error) {
			console.error('Error loading documents:', error);
		} finally {
			setIsLoading(false);
		}
	};

	const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		if (!file) return;

		if (!file.name.endsWith('.pdf')) {
			alert('Only PDF files are supported');
			return;
		}

		setIsUploading(true);
		const formData = new FormData();
		formData.append('file', file);

		try {
			const response = await fetch(`${MCP_SERVER_URL}/api/upload`, {
				method: 'POST',
				body: formData,
			});

			if (response.ok) {
				await loadDocuments(); // Reload documents
			} else {
				const error = await response.json();
				alert(`Upload failed: ${error.detail || 'Unknown error'}`);
			}
		} catch (error: any) {
			console.error('Error uploading file:', error);
			alert(`Upload failed: ${error.message || 'Unknown error'}`);
		} finally {
			setIsUploading(false);
			// Reset file input
			event.target.value = '';
		}
	};

	const handleDelete = async (filename: string) => {
		if (!confirm(`Delete ${filename}?`)) return;

		try {
			const response = await fetch(`${MCP_SERVER_URL}/api/documents/${encodeURIComponent(filename)}`, {
				method: 'DELETE',
			});

			if (response.ok) {
				await loadDocuments();
				// Remove from selection if selected
				onSelectionChange(selectedDocuments.filter(f => f !== filename));
			} else {
				alert('Failed to delete document');
			}
		} catch (error) {
			console.error('Error deleting document:', error);
			alert('Failed to delete document');
		}
	};

	const toggleSelection = (filename: string) => {
		if (selectedDocuments.includes(filename)) {
			onSelectionChange(selectedDocuments.filter(f => f !== filename));
		} else {
			onSelectionChange([...selectedDocuments, filename]);
		}
	};

	return (
		<div className="w-80 bg-gradient-to-br from-white via-emerald-50/20 to-teal-50/30 border-r border-emerald-200/60 flex flex-col h-full rounded-2xl shadow-xl shadow-slate-900/5 backdrop-blur-sm overflow-hidden">
			{/* Header */}
			<div className="p-5 border-b border-emerald-200/60 bg-gradient-to-r from-white via-emerald-50/40 to-teal-50/40">
				<h2 className="text-xl font-bold mb-4 bg-gradient-to-r from-slate-900 via-teal-700 to-cyan-700 bg-clip-text text-transparent">Documents</h2>
				<label className="block">
					<input
						type="file"
						accept=".pdf"
						onChange={handleFileUpload}
						disabled={isUploading}
						className="hidden"
						id="file-upload"
					/>
					<Button
						asChild
						variant="outline"
						className="w-full rounded-xl border-emerald-200/60 bg-gradient-to-br from-white to-emerald-50/50 hover:from-emerald-50 hover:to-teal-50 hover:border-emerald-300/60 shadow-sm hover:shadow-md transition-all duration-200 font-semibold text-slate-900"
						disabled={isUploading}
					>
						<label htmlFor="file-upload" className="cursor-pointer flex items-center justify-center gap-2 py-2.5">
							<UploadIcon className="w-4 h-4" />
							{isUploading ? 'Uploading...' : 'Upload PDF'}
						</label>
					</Button>
				</label>
			</div>

			{/* Document List */}
			<div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gradient-to-b from-transparent to-slate-50/30">
				{isLoading ? (
					<div className="text-sm text-slate-500 text-center py-8 font-medium">
						Loading documents...
					</div>
				) : documents.length === 0 ? (
					<div className="text-sm text-slate-500 text-center py-12 px-4">
						<div className="bg-slate-100/80 rounded-xl p-6 border border-slate-200/60">
							<FileIcon className="w-12 h-12 mx-auto mb-3 text-slate-400" />
							<p className="font-semibold text-slate-600 mb-1">No documents uploaded yet.</p>
							<p className="text-slate-500">Upload a PDF to get started.</p>
						</div>
					</div>
				) : (
					documents.map((doc) => {
						const isSelected = selectedDocuments.includes(doc.filename);
						return (
							<div
								key={doc.filename}
								className={`p-4 rounded-xl border cursor-pointer transition-all duration-200 shadow-sm hover:shadow-md ${
									isSelected
										? 'bg-gradient-to-br from-emerald-100/80 via-teal-100/60 to-cyan-100/80 border-emerald-300/60 shadow-emerald-500/20 ring-2 ring-emerald-400/30'
										: 'bg-white/95 border-emerald-200/40 hover:bg-gradient-to-br hover:from-emerald-50/50 hover:to-teal-50/50 hover:border-emerald-300/60'
								}`}
								onClick={() => toggleSelection(doc.filename)}
							>
								<div className="flex items-start justify-between gap-3">
									<div className="flex items-start gap-3 flex-1 min-w-0">
										<div className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
											isSelected
												? 'bg-gradient-to-br from-emerald-500 to-teal-600 border-emerald-600 shadow-sm shadow-emerald-500/40'
												: 'border-slate-300 bg-white'
										}`}>
											{isSelected && <CheckIcon className="w-3 h-3 text-white" />}
										</div>
										<div className="flex-1 min-w-0">
											<div className="flex items-center gap-2 mb-1.5">
												<FileIcon className={`w-4 h-4 flex-shrink-0 ${isSelected ? 'text-emerald-600' : 'text-slate-500'}`} />
												<p className={`text-sm font-semibold truncate ${isSelected ? 'text-slate-900' : 'text-black'}`}>{doc.filename}</p>
											</div>
											<p className="text-xs text-slate-600 font-medium">
												{new Date(doc.uploaded_at).toLocaleDateString()} • {doc.text_length.toLocaleString()} chars
											</p>
										</div>
									</div>
									<button
										onClick={(e) => {
											e.stopPropagation();
											handleDelete(doc.filename);
										}}
										className="flex-shrink-0 p-1.5 hover:bg-red-50 rounded-lg transition-all duration-200"
										title="Delete document"
									>
										<XIcon className="w-4 h-4 text-slate-400 hover:text-red-600" />
									</button>
								</div>
							</div>
						);
					})
				)}
			</div>

			{/* Footer */}
			{selectedDocuments.length > 0 && (
				<div className="p-4 border-t border-emerald-200/60 bg-gradient-to-r from-emerald-100/60 via-teal-100/60 to-cyan-100/60">
					<p className="text-sm font-semibold text-slate-900">
						{selectedDocuments.length} document{selectedDocuments.length !== 1 ? 's' : ''} selected
					</p>
				</div>
			)}
		</div>
	);
}

