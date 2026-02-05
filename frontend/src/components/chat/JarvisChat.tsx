"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Send, Bot, User, Loader2, Trash2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  dataSource?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export function JarvisChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `web-${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat/message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
        dataSource: data.data_source,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const clearChat = async () => {
    try {
      await fetch(`${API_BASE}/api/chat/clear?session_id=${sessionId}`, {
        method: "POST",
      });
    } catch (error) {
      console.error("Clear error:", error);
    }
    setMessages([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatMessage = (content: string) => {
    // Convert markdown-like formatting to HTML
    return content
      .split("\n")
      .map((line, i) => {
        // Headers
        if (line.startsWith("### ")) {
          return (
            <h3 key={i} className="text-lg font-bold mt-4 mb-2">
              {line.slice(4)}
            </h3>
          );
        }
        if (line.startsWith("## ")) {
          return (
            <h2 key={i} className="text-xl font-bold mt-4 mb-2">
              {line.slice(3)}
            </h2>
          );
        }
        if (line.startsWith("# ")) {
          return (
            <h1 key={i} className="text-2xl font-bold mt-4 mb-2">
              {line.slice(2)}
            </h1>
          );
        }
        // Bold
        if (line.includes("**")) {
          const parts = line.split(/\*\*(.*?)\*\*/g);
          return (
            <p key={i} className="mb-1">
              {parts.map((part, j) =>
                j % 2 === 1 ? (
                  <strong key={j}>{part}</strong>
                ) : (
                  <span key={j}>{part}</span>
                )
              )}
            </p>
          );
        }
        // List items
        if (line.startsWith("- ")) {
          return (
            <li key={i} className="ml-4 list-disc">
              {line.slice(2)}
            </li>
          );
        }
        if (line.match(/^\d+\. /)) {
          return (
            <li key={i} className="ml-4 list-decimal">
              {line.replace(/^\d+\. /, "")}
            </li>
          );
        }
        // Empty lines
        if (!line.trim()) {
          return <br key={i} />;
        }
        // Regular paragraphs
        return (
          <p key={i} className="mb-1">
            {line}
          </p>
        );
      });
  };

  return (
    <Card className="flex flex-col h-[calc(100vh-8rem)]">
      <CardHeader className="border-b flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div>
              <CardTitle className="flex items-center gap-2">
                JARVIS
                <Sparkles className="h-4 w-4 text-yellow-500" />
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Paid Media Intelligence Assistant
              </p>
            </div>
          </div>
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
            <Bot className="h-16 w-16 mb-4 opacity-20" />
            <h3 className="text-lg font-medium mb-2">Welcome to JARVIS</h3>
            <p className="text-sm max-w-md">
              I'm your AI-powered Paid Media Analyst. Ask me about campaign
              performance, budget allocation, or optimization strategies.
            </p>
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
              <button
                onClick={() => setInput("How did we perform last 7 days?")}
                className="px-3 py-2 rounded-lg bg-muted hover:bg-muted/80 transition-colors text-left"
              >
                📊 How did we perform last 7 days?
              </button>
              <button
                onClick={() => setInput("Which campaigns should I pause?")}
                className="px-3 py-2 rounded-lg bg-muted hover:bg-muted/80 transition-colors text-left"
              >
                🔍 Which campaigns should I pause?
              </button>
              <button
                onClick={() =>
                  setInput("How should I reallocate the remaining budget?")
                }
                className="px-3 py-2 rounded-lg bg-muted hover:bg-muted/80 transition-colors text-left"
              >
                💰 How should I reallocate budget?
              </button>
              <button
                onClick={() => setInput("Compare MTD vs last month")}
                className="px-3 py-2 rounded-lg bg-muted hover:bg-muted/80 transition-colors text-left"
              >
                📈 Compare MTD vs last month
              </button>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-3",
                message.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {message.role === "assistant" && (
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              )}
              <div
                className={cn(
                  "rounded-lg px-4 py-3 max-w-[80%]",
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}
              >
                {message.role === "user" ? (
                  <p>{message.content}</p>
                ) : (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    {formatMessage(message.content)}
                  </div>
                )}
                {message.dataSource && (
                  <p className="text-xs mt-2 opacity-60">
                    Data source: {message.dataSource}
                  </p>
                )}
              </div>
              {message.role === "user" && (
                <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                  <User className="h-4 w-4 text-primary-foreground" />
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="bg-muted rounded-lg px-4 py-3">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </CardContent>

      <div className="border-t p-4 flex-shrink-0">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask JARVIS about your campaign performance..."
            className="flex-1 resize-none rounded-lg border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary min-h-[48px] max-h-[120px]"
            rows={1}
            disabled={isLoading}
          />
          <Button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            size="lg"
            className="px-4"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          JARVIS can analyze performance data, suggest optimizations, and help
          with budget allocation.
        </p>
      </div>
    </Card>
  );
}
