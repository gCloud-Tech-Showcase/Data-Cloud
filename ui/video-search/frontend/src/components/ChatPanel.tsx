import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, X, Send, Loader2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AgentAvatar } from "@/components/AgentAvatar";
import { ChatMessage } from "@/components/ChatMessage";
import { agentChat } from "@/lib/api";
import type { AgentAction, ChatMessage as ChatMessageType } from "@/types";

interface ChatPanelProps {
  onAction: (action: AgentAction) => void;
}

export function ChatPanel({ onAction }: ChatPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleReset = useCallback(() => {
    setMessages([]);
    setSessionId(crypto.randomUUID());
    setInput("");
  }, []);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [isOpen]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const text = input.trim();
      if (!text || isLoading) return;

      setInput("");
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "user", text },
      ]);
      setIsLoading(true);

      try {
        const response = await agentChat(text, sessionId);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "agent",
            text: response.text,
            actions: response.actions,
          },
        ]);
        for (const action of response.actions) {
          onAction(action);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "agent",
            text: "Sorry, something went wrong. Please try again.",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [input, isLoading, sessionId, onAction]
  );

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-200 flex items-center justify-center"
        aria-label="Open chat"
      >
        <Sparkles className="w-6 h-6" />
      </button>
    );
  }

  return (
    <div
      role="dialog"
      aria-label="The Archivist chat"
      className="fixed bottom-0 right-0 sm:bottom-6 sm:right-6 z-50 w-full sm:w-[400px] h-[100dvh] sm:h-[600px] sm:max-h-[calc(100vh-3rem)] bg-background sm:rounded-xl border border-border shadow-2xl flex flex-col animate-in slide-in-from-bottom-5 fade-in"
    >
      {/* Header */}
      <div className="sm:rounded-t-xl bg-background/95 backdrop-blur border-b border-border px-5 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h2 className="text-sm font-medium text-foreground">
              The Archivist
            </h2>
            <p className="text-[11px] text-muted-foreground">
              Search, explore, and analyze your library
            </p>
          </div>
        </div>
        <div className="flex items-center gap-0.5">
          {messages.length > 0 && (
            <Button variant="ghost" size="sm" onClick={handleReset} aria-label="New conversation">
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)} aria-label="Close chat">
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-3 py-12">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-primary" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">
                How can I help?
              </p>
              <p className="text-xs text-muted-foreground max-w-[240px]">
                Ask me to search for videos, apply filters, get details, or
                answer questions about the library.
              </p>
            </div>
            <div className="flex flex-wrap gap-1.5 justify-center max-w-[300px]">
              {[
                "Find cartoons about animals",
                "What percentage of the library is cartoons?",
                "Show me educational films in black and white",
                "What categories exist?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="text-[11px] px-2.5 py-1 rounded-full border border-border text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-primary/5 transition-colors"
                  onClick={() => {
                    setInput(suggestion);
                    inputRef.current?.focus();
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex items-start gap-2.5">
            <AgentAvatar />
            <div className="bg-muted rounded-lg rounded-tl-sm px-3.5 py-2.5">
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-pulse" />
                <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-pulse [animation-delay:150ms]" />
                <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-pulse [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border px-4 py-3">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your video library..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            type="submit"
            size="sm"
            disabled={!input.trim() || isLoading}
            className="px-3"
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </form>
      </div>

      {/* Footer */}
      <div className="sm:rounded-b-xl px-4 py-2 border-t border-border">
        <p className="text-[10px] text-muted-foreground/50 text-center">
          Powered by Gemini
        </p>
      </div>
    </div>
  );
}
