import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

interface ExecutionStep {
  step: string;
  message: string;
  status: 'pending' | 'active' | 'completed' | 'error';
}

interface ExecutionStatusProps {
  steps: ExecutionStep[];
  className?: string;
}

export function ExecutionStatus({ steps, className }: ExecutionStatusProps) {
  if (steps.length === 0) return null;

  return (
    <div className={cn("bg-gray-50 dark:bg-gray-900 border rounded-lg p-3 text-sm", className)}>
      <div className="flex items-center gap-2 mb-2">
        <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
        <span className="font-medium text-gray-700 dark:text-gray-300">Execution Path</span>
      </div>
      
      <div className="space-y-2">
        {steps.map((step, index) => (
          <div key={index} className="flex items-center gap-3">
            <div className="flex-shrink-0">
              {step.status === 'completed' ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : step.status === 'active' ? (
                <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
              ) : step.status === 'error' ? (
                <Circle className="h-4 w-4 text-red-500" />
              ) : (
                <Circle className="h-4 w-4 text-gray-400" />
              )}
            </div>
            
            <div className="flex-1 min-w-0">
              <span className={cn(
                "text-sm",
                step.status === 'completed' ? "text-green-700 dark:text-green-400" :
                step.status === 'active' ? "text-blue-700 dark:text-blue-400" :
                step.status === 'error' ? "text-red-700 dark:text-red-400" :
                "text-gray-500 dark:text-gray-400"
              )}>
                {step.message}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 