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
		<div className="w-80 bg-muted/50 border-r border-border flex flex-col h-full">
			{/* Header */}
			<div className="p-4 border-b border-border">
				<h2 className="text-lg font-semibold mb-3">Documents</h2>
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
						className="w-full"
						disabled={isUploading}
					>
						<label htmlFor="file-upload" className="cursor-pointer flex items-center justify-center gap-2">
							<UploadIcon className="w-4 h-4" />
							{isUploading ? 'Uploading...' : 'Upload PDF'}
						</label>
					</Button>
				</label>
			</div>

			{/* Document List */}
			<div className="flex-1 overflow-y-auto p-4 space-y-2">
				{isLoading ? (
					<div className="text-sm text-muted-foreground text-center py-4">
						Loading documents...
					</div>
				) : documents.length === 0 ? (
					<div className="text-sm text-muted-foreground text-center py-8">
						No documents uploaded yet.
						<br />
						Upload a PDF to get started.
					</div>
				) : (
					documents.map((doc) => {
						const isSelected = selectedDocuments.includes(doc.filename);
						return (
							<div
								key={doc.filename}
								className={`p-3 rounded-lg border cursor-pointer transition-colors ${
									isSelected
										? 'bg-primary/10 border-primary'
										: 'bg-background border-border hover:bg-muted/50'
								}`}
								onClick={() => toggleSelection(doc.filename)}
							>
								<div className="flex items-start justify-between gap-2">
									<div className="flex items-start gap-2 flex-1 min-w-0">
										<div className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center ${
											isSelected
												? 'bg-primary border-primary'
												: 'border-border'
										}`}>
											{isSelected && <CheckIcon className="w-3 h-3 text-primary-foreground" />}
										</div>
										<div className="flex-1 min-w-0">
											<div className="flex items-center gap-2 mb-1">
												<FileIcon className="w-4 h-4 text-muted-foreground flex-shrink-0" />
												<p className="text-sm font-medium truncate">{doc.filename}</p>
											</div>
											<p className="text-xs text-muted-foreground">
												{new Date(doc.uploaded_at).toLocaleDateString()} • {doc.text_length.toLocaleString()} chars
											</p>
										</div>
									</div>
									<button
										onClick={(e) => {
											e.stopPropagation();
											handleDelete(doc.filename);
										}}
										className="flex-shrink-0 p-1 hover:bg-destructive/10 rounded transition-colors"
										title="Delete document"
									>
										<XIcon className="w-4 h-4 text-muted-foreground hover:text-destructive" />
									</button>
								</div>
							</div>
						);
					})
				)}
			</div>

			{/* Footer */}
			{selectedDocuments.length > 0 && (
				<div className="p-4 border-t border-border bg-primary/5">
					<p className="text-sm text-muted-foreground">
						{selectedDocuments.length} document{selectedDocuments.length !== 1 ? 's' : ''} selected
					</p>
				</div>
			)}
		</div>
	);
}

