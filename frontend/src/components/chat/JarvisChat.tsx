"use client";

import { useState, useRef, useEffect, useMemo } from "react";
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

// Parse inline formatting (bold, italic, code)
function parseInlineFormatting(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Check for bold **text**
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Check for italic *text* (but not **)
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/);
    // Check for inline code `text`
    const codeMatch = remaining.match(/`([^`]+)`/);
    // Check for currency $X,XXX.XX
    const currencyMatch = remaining.match(/\$[\d,]+\.?\d*/);

    // Find the earliest match
    const matches = [
      boldMatch ? { type: "bold", match: boldMatch, index: boldMatch.index! } : null,
      italicMatch ? { type: "italic", match: italicMatch, index: italicMatch.index! } : null,
      codeMatch ? { type: "code", match: codeMatch, index: codeMatch.index! } : null,
    ].filter(Boolean).sort((a, b) => a!.index - b!.index);

    if (matches.length === 0) {
      parts.push(<span key={key++}>{remaining}</span>);
      break;
    }

    const first = matches[0]!;

    // Add text before the match
    if (first.index > 0) {
      parts.push(<span key={key++}>{remaining.slice(0, first.index)}</span>);
    }

    // Add the formatted text
    if (first.type === "bold") {
      parts.push(<strong key={key++} className="font-semibold">{first.match[1]}</strong>);
    } else if (first.type === "italic") {
      parts.push(<em key={key++}>{first.match[1]}</em>);
    } else if (first.type === "code") {
      parts.push(
        <code key={key++} className="bg-muted-foreground/10 px-1.5 py-0.5 rounded text-sm font-mono">
          {first.match[1]}
        </code>
      );
    }

    remaining = remaining.slice(first.index + first.match[0].length);
  }

  return parts;
}

// Parse a markdown table
function parseTable(lines: string[], startIndex: number): { element: React.ReactNode; endIndex: number } {
  const tableLines: string[] = [];
  let i = startIndex;

  // Collect all table lines
  while (i < lines.length && (lines[i].includes("|") || lines[i].match(/^[\s\-|:]+$/))) {
    tableLines.push(lines[i]);
    i++;
  }

  if (tableLines.length < 2) {
    return { element: null, endIndex: startIndex };
  }

  // Parse header
  const headerLine = tableLines[0];
  const headers = headerLine.split("|").map(h => h.trim()).filter(Boolean);

  // Skip separator line
  const dataLines = tableLines.slice(2);

  const rows = dataLines.map(line =>
    line.split("|").map(cell => cell.trim()).filter(Boolean)
  ).filter(row => row.length > 0);

  const element = (
    <div key={`table-${startIndex}`} className="my-4 overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            {headers.map((header, idx) => (
              <th key={idx} className="px-4 py-2 text-left font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} className="border-b border-border/50 hover:bg-muted/30">
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} className="px-4 py-2">
                  {parseInlineFormatting(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return { element, endIndex: i - 1 };
}

// Parse code blocks
function parseCodeBlock(lines: string[], startIndex: number): { element: React.ReactNode; endIndex: number } {
  const startLine = lines[startIndex];
  const language = startLine.replace(/```/g, "").trim();
  const codeLines: string[] = [];
  let i = startIndex + 1;

  while (i < lines.length && !lines[i].startsWith("```")) {
    codeLines.push(lines[i]);
    i++;
  }

  const element = (
    <div key={`code-${startIndex}`} className="my-4">
      {language && (
        <div className="bg-muted/80 px-3 py-1 text-xs font-mono text-muted-foreground rounded-t-lg border border-b-0 border-border">
          {language}
        </div>
      )}
      <pre className={cn(
        "bg-muted/50 p-4 overflow-x-auto text-sm font-mono border border-border",
        language ? "rounded-b-lg" : "rounded-lg"
      )}>
        <code>{codeLines.join("\n")}</code>
      </pre>
    </div>
  );

  return { element, endIndex: i };
}

// Main message formatter
function formatMessage(content: string): React.ReactNode {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;
  let listItems: React.ReactNode[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushList = () => {
    if (listItems.length > 0) {
      if (listType === "ul") {
        elements.push(
          <ul key={`list-${elements.length}`} className="my-3 ml-4 space-y-1 list-disc">
            {listItems}
          </ul>
        );
      } else {
        elements.push(
          <ol key={`list-${elements.length}`} className="my-3 ml-4 space-y-1 list-decimal">
            {listItems}
          </ol>
        );
      }
      listItems = [];
      listType = null;
    }
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmedLine = line.trim();

    // Code block
    if (trimmedLine.startsWith("```")) {
      flushList();
      const { element, endIndex } = parseCodeBlock(lines, i);
      elements.push(element);
      i = endIndex + 1;
      continue;
    }

    // Table (line contains | and next line is separator)
    if (trimmedLine.includes("|") && i + 1 < lines.length && lines[i + 1].match(/^[\s\-|:]+$/)) {
      flushList();
      const { element, endIndex } = parseTable(lines, i);
      if (element) {
        elements.push(element);
        i = endIndex + 1;
        continue;
      }
    }

    // Headers
    if (trimmedLine.startsWith("### ")) {
      flushList();
      elements.push(
        <h3 key={i} className="text-base font-bold mt-5 mb-2 text-foreground">
          {parseInlineFormatting(trimmedLine.slice(4))}
        </h3>
      );
      i++;
      continue;
    }
    if (trimmedLine.startsWith("## ")) {
      flushList();
      elements.push(
        <h2 key={i} className="text-lg font-bold mt-6 mb-3 text-foreground border-b border-border pb-2">
          {parseInlineFormatting(trimmedLine.slice(3))}
        </h2>
      );
      i++;
      continue;
    }
    if (trimmedLine.startsWith("# ")) {
      flushList();
      elements.push(
        <h1 key={i} className="text-xl font-bold mt-6 mb-3 text-foreground">
          {parseInlineFormatting(trimmedLine.slice(2))}
        </h1>
      );
      i++;
      continue;
    }

    // Horizontal rule
    if (trimmedLine.match(/^[-*_]{3,}$/)) {
      flushList();
      elements.push(<hr key={i} className="my-4 border-border" />);
      i++;
      continue;
    }

    // Unordered list item
    if (trimmedLine.match(/^[-*•]\s+/)) {
      if (listType !== "ul") {
        flushList();
        listType = "ul";
      }
      const itemContent = trimmedLine.replace(/^[-*•]\s+/, "");
      listItems.push(
        <li key={`li-${i}`} className="text-sm leading-relaxed">
          {parseInlineFormatting(itemContent)}
        </li>
      );
      i++;
      continue;
    }

    // Ordered list item
    if (trimmedLine.match(/^\d+\.\s+/)) {
      if (listType !== "ol") {
        flushList();
        listType = "ol";
      }
      const itemContent = trimmedLine.replace(/^\d+\.\s+/, "");
      listItems.push(
        <li key={`li-${i}`} className="text-sm leading-relaxed">
          {parseInlineFormatting(itemContent)}
        </li>
      );
      i++;
      continue;
    }

    // Empty line
    if (!trimmedLine) {
      flushList();
      // Only add spacing if not consecutive empty lines
      const lastEl = elements[elements.length - 1];
      if (elements.length > 0 && (lastEl as React.ReactElement)?.key !== `space-${i - 1}`) {
        elements.push(<div key={`space-${i}`} className="h-2" />);
      }
      i++;
      continue;
    }

    // Regular paragraph
    flushList();
    elements.push(
      <p key={i} className="text-sm leading-relaxed mb-2">
        {parseInlineFormatting(trimmedLine)}
      </p>
    );
    i++;
  }

  flushList();
  return <div className="space-y-1">{elements}</div>;
}

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

  return (
    <Card className="flex flex-col h-[calc(100vh-8rem)]">
      <CardHeader className="border-b flex-shrink-0 py-4">
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
              I&apos;m your AI-powered Paid Media Analyst. Ask me about campaign
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
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              )}
              <div
                className={cn(
                  "rounded-lg max-w-[85%]",
                  message.role === "user"
                    ? "bg-primary text-primary-foreground px-4 py-3"
                    : "bg-muted/50 border border-border px-5 py-4"
                )}
              >
                {message.role === "user" ? (
                  <p className="text-sm">{message.content}</p>
                ) : (
                  <div className="text-foreground">
                    {formatMessage(message.content)}
                  </div>
                )}
                {message.dataSource && (
                  <p className="text-xs mt-3 pt-2 border-t border-border/50 text-muted-foreground">
                    📊 Data source: {message.dataSource}
                  </p>
                )}
              </div>
              {message.role === "user" && (
                <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
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
            <div className="bg-muted/50 border border-border rounded-lg px-5 py-4">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Analyzing...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </CardContent>

      <div className="border-t p-4 flex-shrink-0 bg-background">
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
