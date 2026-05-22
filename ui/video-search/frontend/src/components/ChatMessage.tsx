import { lazy, Suspense } from "react";
import { type LucideIcon, Search, Filter, Play, Info, Layers, RotateCcw } from "lucide-react";
import { AgentAvatar } from "@/components/AgentAvatar";
import type { ChatMessage as ChatMessageType, AgentAction } from "@/types";

const VegaChart = lazy(() => import("@/components/VegaChart"));

interface ChatMessageProps {
  message: ChatMessageType;
}

const ACTION_LABELS: Record<string, { label: string; icon: LucideIcon }> = {
  search: { label: "Searched", icon: Search },
  apply_filter: { label: "Applied filter", icon: Filter },
  clear_filters: { label: "Cleared filters", icon: RotateCcw },
  show_details: { label: "Opened details", icon: Info },
  find_similar: { label: "Finding similar", icon: Layers },
  play: { label: "Playing video", icon: Play },
  create_collection: { label: "Created collection", icon: Layers },
};

function getActionDetail(action: AgentAction): string {
  switch (action.type) {
    case "search":
      return ` "${action.query}"`;
    case "apply_filter":
      return ` ${action.field}=${action.value}`;
    default:
      return "";
  }
}

function ActionBadge({ action }: { action: AgentAction }) {
  const config = ACTION_LABELS[action.type];
  if (!config) return null;
  const Icon = config.icon;

  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-primary/70 bg-primary/5 rounded px-1.5 py-0.5">
      <Icon className="w-2.5 h-2.5" />
      {config.label}
      {getActionDetail(action)}
    </span>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="bg-primary text-primary-foreground rounded-lg rounded-tr-sm px-3.5 py-2.5 max-w-[85%]">
          <p className="text-sm whitespace-pre-wrap">{message.text}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <AgentAvatar />
      <div className="space-y-1.5 max-w-[85%] min-w-0 flex-1">
        <div className="bg-muted rounded-lg rounded-tl-sm px-3.5 py-2.5">
          <p className="text-sm text-foreground whitespace-pre-wrap">
            {message.text}
          </p>
        </div>
        {message.chart && (
          <Suspense
            fallback={<div className="h-48 animate-pulse bg-muted rounded" />}
          >
            <VegaChart spec={message.chart} />
          </Suspense>
        )}
        {message.actions && message.actions.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {message.actions.map((action, i) => (
              <ActionBadge key={`${action.type}-${i}`} action={action} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
