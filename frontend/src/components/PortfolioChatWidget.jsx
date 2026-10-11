import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Settings, RotateCcw, Bot, User, Loader2 } from 'lucide-react';
import { useAgentContext } from '../contexts/AgentContext';
import { usePortfolioScenario } from '../contexts/PortfolioScenarioContext';
import ScenarioComparisonCard from './ScenarioComparisonCard';
import { resolveAgentTools } from '../tools/agentConversation';
import { useAuth } from '../contexts/AuthContext';
import { useLocation, useNavigate } from 'react-router-dom';
import { tools, executeTool } from '../tools/agentTools';
import { createChatClient, chatErrorMessage } from '../services/chatClient';
import ReactMarkdown from 'react-markdown';
import Logo from '../assets/portfolio_pilot_logo.png';

const DataCard = ({ tool, data }) => {
  if (data.ui_type === 'allocation_scenario') return <ScenarioComparisonCard data={data} />;
  const formatValue = (key, val) => {
    if (val === null || val === undefined) return '—';
    if (typeof val === 'boolean') return val ? 'Yes' : 'No';
    if (typeof val === 'number') {
      const k = key.toLowerCase();
      if (k.includes('value') || k.includes('balance') || k.includes('gain') || k.includes('cost') || k.includes('cash')) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(val);
      }
      if (k.includes('percent') || k.includes('return') || k.includes('ratio') || k.includes('ytd')) {
        return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
      }
      return val.toLocaleString();
    }
    if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}/)) {
      return new Date(val).toLocaleString();
    }
    return String(val);
  };

  const flatEntries = Object.entries(data)
    .filter(([, v]) => v !== null && v !== undefined && typeof v !== 'object' && !Array.isArray(v))
    .slice(0, 8);

  if (flatEntries.length === 0) return null;

  const title = tool.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="mt-2 rounded-lg border border-indigo-100 dark:border-indigo-900/40 overflow-hidden text-xs">
      <div className="bg-indigo-50 dark:bg-indigo-900/30 px-3 py-1.5 font-semibold text-indigo-700 dark:text-indigo-300">
        {title}
      </div>
      <div className="bg-white dark:bg-gray-800 divide-y divide-gray-100 dark:divide-gray-700/50">
        {flatEntries.map(([key, val]) => (
          <div key={key} className="flex justify-between items-center px-3 py-1.5">
            <span className="text-gray-500 dark:text-gray-400">
              {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </span>
            <span className="font-medium text-gray-800 dark:text-gray-200">
              {formatValue(key, val)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const ThinkingIndicator = () => (
  <div className="flex justify-start">
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-bl-none p-4 shadow-sm flex items-center gap-2">
      <span className="text-sm text-gray-500 dark:text-gray-400 font-medium">Thinking</span>
      <div className="flex gap-1">
        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
      </div>
    </div>
  </div>
);

const PortfolioChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(() => {
    const defaultMsg = [{ role: 'assistant', content: 'Hello! I am your Portfolio Pilot. How can I help you manage your investments today?' }];
    try {
      const saved = localStorage.getItem('portfolio_chat_history');
      if (saved) {
        const parsed = JSON.parse(saved);
        return Array.isArray(parsed) && parsed.length > 0 ? parsed : defaultMsg;
      }
    } catch {
      // ignore parse errors
    }
    return defaultMsg;
  });
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [keyConfigured, setKeyConfigured] = useState(false);
  const [keyBusy, setKeyBusy] = useState(false);
  const [keyError, setKeyError] = useState('');
  const accountController = useRef(null);
  const chatController = useRef(null);
  const previousUserId = useRef(undefined);
  const [showSettings, setShowSettings] = useState(false);
  
  const messagesEndRef = useRef(null);
  const { isAgentActive: agentActive, resetAllParams, ...agentContext } = useAgentContext();
  const scenario = usePortfolioScenario();
  const isAgentActive = agentActive || (scenario && scenario.activeMode !== 'current');
  const { api, portfolioId, user } = useAuth(); // Access to backend API and portfolio ID
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();
    accountController.current = controller;
    // Legacy credentials are discarded; users save them under their own account.
    localStorage.removeItem('gemini_api_key');
    setApiKey('');
    setKeyConfigured(false);
    setKeyError('');
    setKeyBusy(false);
    setIsLoading(false);
    setInput('');
    setShowSettings(false);
    if (previousUserId.current !== undefined && previousUserId.current !== user?.id) {
      setMessages([{ role: 'assistant', content: 'Hello! I am your Portfolio Pilot. How can I help you manage your investments today?' }]);
    }
    previousUserId.current = user?.id;
    if (user?.id) {
      setKeyBusy(true);
      api.get('/chat/api-key', { signal: controller.signal }).then(({ data }) => {
        if (!controller.signal.aborted) setKeyConfigured(data.configured);
      }).catch(error => {
        if (!controller.signal.aborted) setKeyError(chatErrorMessage(error));
      }).finally(() => {
        if (!controller.signal.aborted) setKeyBusy(false);
      });
    }
    return () => {
      controller.abort();
      chatController.current?.abort();
    };
  }, [api, user?.id]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Persist messages to localStorage (cap at 50 to stay within storage limits)
  useEffect(() => {
    try {
      localStorage.setItem('portfolio_chat_history', JSON.stringify(messages.slice(-50)));
    } catch {
      // localStorage may be full — try with fewer messages
      try {
        localStorage.setItem('portfolio_chat_history', JSON.stringify(messages.slice(-20)));
      } catch {
        // ignore
      }
    }
  }, [messages]);

  const handleSaveApiKey = async (key) => {
    const signal = accountController.current?.signal;
    if (!user?.id || keyBusy || !key.trim()) return;
    setKeyBusy(true);
    setKeyError('');
    try {
      await api.put('/chat/api-key', { api_key: key.trim() }, { signal });
      if (signal?.aborted) return;
      setApiKey('');
      setKeyConfigured(true);
      setShowSettings(false);
    } catch {
      if (!signal?.aborted) setKeyError('The key could not be saved. Please try again.');
    } finally {
      if (!signal?.aborted) setKeyBusy(false);
    }
  };

  const handleDeleteApiKey = async () => {
    const signal = accountController.current?.signal;
    setKeyBusy(true);
    setKeyError('');
    chatController.current?.abort();
    try {
      await api.delete('/chat/api-key', { signal });
      if (signal?.aborted) return;
      setApiKey('');
      setKeyConfigured(false);
    } catch {
      if (!signal?.aborted) setKeyError('The key could not be removed. Please try again.');
    } finally {
      if (!signal?.aborted) setKeyBusy(false);
    }
  };

  const handleResetSimulation = () => {
    if (scenario) scenario.reset(); else resetAllParams();
    setMessages(prev => [...prev, { role: 'assistant', content: 'Analytics reset to actual portfolio weights and default simulation parameters.' }]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading || keyBusy || !user?.id) return;

    if (!keyConfigured) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Please set your Gemini API Key in settings to continue.' }]);
      setShowSettings(true);
      return;
    }

    const controller = new AbortController();
    chatController.current = controller;
    const userMessage = input;
    setInput(''); // Clear input immediately
    // Optimistically add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Check if message needs visual context (chart, graph, etc.)
      const needsScreenshot = /\b(chart|graph|see|showing|visual|display|image|picture|screenshot)\b/i.test(userMessage);

      // Capture dashboard screenshot only if needed for context
      let imagePart = null;
      if (needsScreenshot) {
        // Lazy load html2canvas only when needed
        const html2canvas = (await import('html2canvas')).default;

        // Defer screenshot to allow UI to update (show spinner) first
        await new Promise(resolve => setTimeout(resolve, 100));

        try {
          const canvas = await html2canvas(document.body, {
            ignoreElements: (element) => element.id === 'portfolio-chat-widget',
            logging: false,
            useCORS: true
          });

          const base64Data = canvas.toDataURL('image/jpeg', 0.5).split(',')[1];
          imagePart = {
            inlineData: {
              data: base64Data,
              mimeType: "image/jpeg",
            },
          };
        } catch (err) {
          console.warn("Failed to capture screenshot:", err);
        }
      }

      const systemPrompt = `
        You are Portfolio Pilot, an expert AI financial assistant integrated into a Portfolio Management Dashboard.
        
        CURRENT CONTEXT:
        - User is currently on page: ${location.pathname}
        - Simulation Mode: ${isAgentActive ? 'ACTIVE' : 'INACTIVE'}
        - VISUAL CONTEXT: You have access to a screenshot of the current dashboard state.
        
        YOUR CAPABILITIES:
        1. You can control the dashboard using the provided tools.
        2. You can answer general financial questions directly.
        3. You can SEE the dashboard.
        4. You can fetch and analyze portfolio data using specialized tools.
        
        AVAILABLE DATA TOOLS:
        - get_portfolio_summary: Get overall portfolio performance summary, including portfolio-level YTD return fields when available
        - analyze_portfolio: Perform analysis with these query_type options:
          * "largest_holding" - single largest by market value
          * "smallest_holding" - single smallest by market value  
          * "top_performers" - best performers by period return (use limit param)
          * "worst_performers" - worst performers by period return (use limit param)
          * "holdings_summary" - ALL holdings sorted by market value (use this for 2nd, 3rd, Nth largest!)
          * "sector_breakdown" - allocation by sector
        - get_holding_performance: Get detailed performance for a specific holding by ticker
        - get_all_holdings_performance: Get performance metrics for ALL holdings at once
        
        CRITICAL WORKFLOW RULES:
        1. For portfolio-level YTD return questions, call get_portfolio_summary and use ytd_return_percentage or ytd_message from the result.
        2. For "largest holding" → use analyze_portfolio with query_type="largest_holding"
        3. For "second largest", "third largest", "Nth largest" → use analyze_portfolio with query_type="holdings_summary", then pick the Nth item from the sorted list (index 1 for 2nd, index 2 for 3rd, etc.)
        4. For YTD/performance of a specific ticker → use get_holding_performance with that ticker
        5. For "YTD of largest holding" → call analyze_portfolio FIRST, then call get_holding_performance with the ticker from the result
        6. For "YTD of second largest" → call analyze_portfolio with holdings_summary, identify the 2nd item, then call get_holding_performance with that ticker
        7. For best/worst performers → use analyze_portfolio with query_type="top_performers" or "worst_performers"
        
        IMPORTANT LIMITATIONS:
        - For mutual funds (tickers ending in .CF like PHN9756.CF), historical period returns (YTD, 1M, 3M, 1Y) are NOT available.
        - For mutual funds, you can only report their cost-basis gain/loss (gain_loss_percent), not period returns.
        
        GUIDELINES:
        - Always use tools to get real data - never guess or make up numbers.
        - When you need multiple pieces of data, call multiple tools.
        - Format numbers clearly: $10,234.56 for currency, +15.2% for percentages.
        - Be concise and direct in your responses.
      `;

      const model = createChatClient(api, {
        systemInstruction: systemPrompt,
        tools: [{ functionDeclarations: tools }],
        signal: controller.signal,
      });

      // Build history excluding the initial assistant greeting (index 0)
      // and ensuring it starts with a user message
      const filteredMessages = messages.filter((m, index) => {
        // Skip the initial greeting
        if (index === 0 && m.role === 'assistant') return false;
        return true;
      });

      // Ensure history starts with a user message (Gemini requirement)
      let startIndex = 0;
      for (let i = 0; i < filteredMessages.length; i++) {
        if (filteredMessages[i].role === 'user') {
          startIndex = i;
          break;
        }
      }

      const history = filteredMessages
        .slice(startIndex)
        .map(m => ({
          role: m.role === 'user' ? 'user' : 'model',
          parts: [{ text: m.content }]
        }));

      let chat = model.startChat({ history: history });

      const parts = [{ text: userMessage }];
      if (imagePart) parts.push(imagePart);

      const result = await chat.sendMessageStream(parts);

      let fullText = '';
      let isFirstChunk = true;
      
      // Stream the text
      for await (const chunk of result.stream) {
        const chunkText = chunk.text();
        fullText += chunkText;
        
        if (isFirstChunk) {
          isFirstChunk = false;
          setMessages(prev => [...prev, { role: 'assistant', content: fullText }]);
        } else {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];
            if (lastMessage.role === 'assistant') {
              lastMessage.content = fullText;
            }
            return newMessages;
          });
        }
      }

      // Check for function calls after stream
      const response = await result.response;
      const functionCalls = response.functionCalls();

      if (functionCalls && functionCalls.length > 0) {
        // Collect all tool results
        const toolResults = [];
        
        // Show fetching indicator once (not per tool)
        let baseMessageContent = '';
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage.role === 'assistant') {
            baseMessageContent = lastMessage.content;
            lastMessage.content = lastMessage.content + '\n\n*Fetching data...*';
          }
          return newMessages;
        });
        
        const completed = await resolveAgentTools(chat, response, (name, args) => {
          controller.signal.throwIfAborted();
          return executeTool(name, args, { scenario, navigate, api, portfolioId, ...agentContext });
        });
        controller.signal.throwIfAborted();
        toolResults.push(...completed.results);

        // Extract structured data from tool results for card rendering
        const richData = toolResults
          .map(tr => {
            try {
              const parsed = JSON.parse(tr.result);
              if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                const flatKeys = Object.entries(parsed).filter(([, v]) => typeof v !== 'object' && !Array.isArray(v));
                if (flatKeys.length > 0) return { tool: tr.name, data: parsed };
              }
            } catch { /* not JSON */ }
            return null;
          })
          .filter(Boolean);
        
        const followUpText = completed.limitReached
          ? 'The calculated results are shown below. Please send another message to continue the analysis.'
          : completed.response.text();
        setMessages(prev => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === 'assistant') updated[updated.length - 1] = { ...last, content: baseMessageContent + '\n\n' + followUpText };
          return updated;
        });

        // Attach structured data cards to the final message
        if (richData.length > 0) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];
            if (lastMessage.role === 'assistant') {
              lastMessage.richData = richData;
            }
            return newMessages;
          });
        }
      }

    } catch (error) {
      if (controller.signal.aborted) return;
      if (error.response?.status === 409) { setKeyConfigured(false); setShowSettings(true); }
      setMessages(prev => {
        // If we have a partial message, append error. If not, add new error message.
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage.role === 'assistant' && !lastMessage.content.startsWith('Error')) {
           // If the last message was the streaming one, maybe just leave it and add error?
           // Or replace it? Let's add a new error message to be safe.
           return [...prev, { role: 'assistant', content: `I encountered an error. (Error: ${chatErrorMessage(error)})` }];
        }
        return [...prev, { role: 'assistant', content: `Error: ${chatErrorMessage(error)}` }];
      });
    } finally {
      if (chatController.current === controller) setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!isOpen) {
    return (
      <button
        aria-label="Portfolio Pilot"
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 h-14 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-lg flex items-center justify-center gap-3 transition-all duration-200 hover:scale-105 z-50"
      >
        <img src={Logo} alt="Portfolio Pilot" className="h-9 w-9 object-contain" />
        <span className="font-semibold text-sm whitespace-nowrap">Portfolio Pilot</span>
      </button>
    );
  }

  return (
    <div id="portfolio-chat-widget" className="fixed bottom-6 right-6 w-96 h-[600px] max-h-[calc(100vh-6rem)] bg-white dark:bg-gray-800 rounded-2xl shadow-2xl flex flex-col border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">
      {/* Header */}
      <div className="p-4 bg-indigo-600 text-white flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src={Logo} alt="Portfolio Pilot" className="h-10 w-10 object-contain bg-white/10 rounded-full" />
          <h3 className="font-semibold text-lg">Portfolio Pilot</h3>
        </div>
        <div className="flex items-center gap-2">
            <button 
              onClick={handleResetSimulation}
              disabled={!isAgentActive}
              className={`p-1.5 rounded-lg transition-colors ${
                isAgentActive 
                  ? 'hover:bg-indigo-500 text-white' 
                  : 'text-indigo-400 cursor-not-allowed opacity-50'
              }`}
              title="Reset Simulation"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          <button 
            aria-label="Chat settings"
            onClick={() => setShowSettings(!showSettings)}
            className="p-1.5 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <Settings className="h-4 w-4" />
          </button>
          <button 
            aria-label="Close chat"
            onClick={() => { chatController.current?.abort(); setIsOpen(false); }}
            className="p-1.5 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="p-4 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
          <label htmlFor="chat-api-key" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Gemini API Key
          </label>
          <input
            id="chat-api-key"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={keyConfigured ? "Enter a replacement API key" : "Enter your API key"}
            autoComplete="off"
            disabled={keyBusy || !user?.id}
            className="w-full p-2 rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white mb-2 text-sm"
          />
          <p className="text-xs text-gray-500 mb-2">{keyConfigured ? 'Key saved securely to your account.' : 'Save your key to your account to enable chat.'}</p>
          {keyError && <p role="alert" className="text-xs text-red-500 mb-2">{keyError}</p>}
          <button
            disabled={keyBusy || !user?.id || !apiKey.trim()}
            onClick={() => handleSaveApiKey(apiKey)}
            className="w-full py-2 bg-indigo-600 text-white rounded text-sm font-medium hover:bg-indigo-700"
          >
            {keyBusy ? 'Please wait...' : 'Save Key'}
          </button>
          {keyConfigured && <button onClick={handleDeleteApiKey} disabled={keyBusy} className="w-full mt-2 py-2 text-red-600 text-sm">Remove Key</button>}
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 dark:bg-gray-900/50">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-lg text-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-none'
                  : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700 rounded-bl-none shadow-sm'
              }`}
            >
              <div className="prose dark:prose-invert max-w-none text-sm">
                <ReactMarkdown 
                  components={{
                    p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                    ul: ({node, ...props}) => <ul className="list-disc ml-4 mb-2" {...props} />,
                    ol: ({node, ...props}) => <ol className="list-decimal ml-4 mb-2" {...props} />,
                    li: ({node, ...props}) => <li className="mb-1" {...props} />,
                    strong: ({node, ...props}) => <span className="font-bold" {...props} />,
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>
              {msg.richData && msg.richData.map((rd, i) => (
                <DataCard key={i} tool={rd.tool} data={rd.data} />
              ))}
            </div>
          </div>
        ))}
        {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
           <ThinkingIndicator />
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            rows={3}
            className="flex-1 p-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />
          <button
            type="submit"
            disabled={isLoading || keyBusy || !user?.id || !input.trim()}
            className="p-2 mb-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </form>
    </div>
  );
};

export default PortfolioChatWidget;
