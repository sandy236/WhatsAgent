import { useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Welcome to AgentWA. Type /help for commands or ask a question.' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMessage = { role: 'user' as const, content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId, prompt: userMessage.content }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Chat error');
      }
      setConversationId(data.conversation_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Error contacting backend.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const sidebarItems = useMemo(
    () => [
      { title: 'New Chat', action: () => { setConversationId(null); setMessages([{ role: 'assistant', content: 'New chat started. Ask anything or use /help.' }]); } },
      { title: 'Admin', action: () => window.location.assign('/admin') },
    ],
    []
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-[1400px] gap-4 p-4">
        <aside className="hidden w-72 flex-col gap-3 rounded-3xl border border-slate-800 bg-slate-900 p-4 md:flex">
          <div className="mb-4 text-sm uppercase tracking-[0.2em] text-slate-500">AgentWA</div>
          {sidebarItems.map((item) => (
            <button key={item.title} onClick={item.action} className="rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-left text-sm transition hover:border-slate-600">
              {item.title}
            </button>
          ))}
        </aside>

        <main className="flex-1 rounded-3xl border border-slate-800 bg-slate-900 p-4 shadow-xl shadow-black/20">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 text-slate-300">
            <div>
              <h1 className="text-2xl font-semibold">WhatsApp-style AI chat</h1>
              <p className="text-sm text-slate-500">Use /addtext, /addurl, /reindex, /stats, /apis, /runapi</p>
            </div>
            <div className="rounded-2xl bg-slate-950 px-3 py-2 text-sm text-slate-300">Backend: {BACKEND_URL}</div>
          </div>

          <div className="mx-auto max-w-4xl space-y-4 py-6">
            {messages.map((message, index) => (
              <div key={index} className={`rounded-3xl p-4 shadow-sm ${message.role === 'user' ? 'ml-auto max-w-[80%] bg-slate-800 text-slate-100' : 'max-w-[85%] bg-slate-950 text-slate-200'}`}>
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{message.role}</div>
                <div className="mt-2 whitespace-pre-wrap break-words text-sm leading-6"><ReactMarkdown>{message.content}</ReactMarkdown></div>
              </div>
            ))}
            <div ref={bottomRef}></div>
          </div>

          <div className="mt-4 rounded-3xl border border-slate-800 bg-slate-950 p-4">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className="min-h-[100px] w-full resize-none rounded-3xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-100 outline-none focus:border-cyan-500"
              placeholder="Type a message or command..."
            />
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-xs text-slate-500">Send with Enter. Use Shift+Enter for a newline.</span>
              <button
                onClick={sendMessage}
                disabled={loading}
                className="inline-flex items-center justify-center rounded-3xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
