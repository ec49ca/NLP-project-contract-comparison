import { ChatMessage } from './chat-message';
import { ChatInput } from './chat-input';

export function ChatContainer({
  messages,
  isThinking,
  onSendMessage,
}: {
  messages: ChatMessage[];
  isThinking: boolean;
  onSendMessage: (message: string) => void;
}) {
  return (
    <div className="bg-gray-900 rounded-lg p-6">
      <div className="h-[600px] overflow-y-auto mb-4">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {isThinking && (
          <div className="flex justify-start gap-3 py-4">
            <div className="rounded-lg px-4 py-3 max-w-[85%] text-sm bg-gray-700 text-gray-200">
              <div className="flex gap-2">
                <div className="animate-pulse w-3 h-3 rounded-full bg-gray-400"></div>
                <div className="animate-pulse w-3 h-3 rounded-full bg-gray-400"></div>
                <div className="animate-pulse w-3 h-3 rounded-full bg-gray-400"></div>
              </div>
            </div>
          </div>
        )}
      </div>
      <ChatInput onSendMessage={onSendMessage} />
    </div>
  );
}
