import { cn } from '@/lib/utils';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: Date;
}

export function ChatMessage({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  return (
    <div
      className={cn(
        'flex items-start gap-3 py-4',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'rounded-lg px-4 py-3 max-w-[85%] text-sm',
          isUser ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-200'
        )}
      >
        {message.content}
      </div>
    </div>
  );
}
