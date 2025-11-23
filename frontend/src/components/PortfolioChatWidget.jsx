import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Settings, RotateCcw, Bot, User, Loader2 } from 'lucide-react';
import { useAgentContext } from '../contexts/AgentContext';
import { useAuth } from '../contexts/AuthContext';
import { useLocation, useNavigate } from 'react-router-dom';
import { tools, executeTool } from '../tools/agentTools';
import { GoogleGenerativeAI } from "@google/generative-ai";
import ReactMarkdown from 'react-markdown';
import html2canvas from 'html2canvas';

const PortfolioChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your Portfolio Pilot. How can I help you manage your investments today?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiKey, setApiKey] = useState(localStorage.getItem('gemini_api_key') || '');
  const [showSettings, setShowSettings] = useState(false);
  
  const messagesEndRef = useRef(null);
  const { isAgentActive, resetAllParams, ...agentContext } = useAgentContext();
  const { api } = useAuth(); // Access to backend API
  const location = useLocation();
  const navigate = useNavigate();

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSaveApiKey = (key) => {
    localStorage.setItem('gemini_api_key', key);
    setApiKey(key);
    setShowSettings(false);
  };

  const handleResetSimulation = () => {
    resetAllParams();
    setMessages(prev => [...prev, { role: 'assistant', content: 'Simulation mode reset. Showing real-time data.' }]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    if (!apiKey) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Please set your Gemini API Key in settings to continue.' }]);
      setShowSettings(true);
      return;
    }

    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Capture dashboard screenshot for context
      let imagePart = null;
      try {
        // Hide widget temporarily for clean screenshot
        const widget = document.getElementById('portfolio-chat-widget');
        if (widget) widget.style.display = 'none';
        
        const canvas = await html2canvas(document.body, {
          ignoreElements: (element) => element.id === 'portfolio-chat-widget',
          logging: false,
          useCORS: true // Important for external images if any
        });
        
        if (widget) widget.style.display = 'flex';

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

      // Construct system prompt with context
      const systemPrompt = `
        You are Portfolio Pilot, an expert AI financial assistant integrated into a Portfolio Management Dashboard.
        
        CURRENT CONTEXT:
        - User is currently on page: ${location.pathname}
        - Simulation Mode: ${isAgentActive ? 'ACTIVE' : 'INACTIVE'}
        - VISUAL CONTEXT: You have access to a screenshot of the current dashboard state. Use this to understand what the user is looking at (charts, data, etc.).
        
        YOUR CAPABILITIES:
        1. You can control the dashboard using the provided tools (navigate, update charts, run simulations).
        2. You can answer general financial questions (e.g., "What is Alpha?", "How to hedge?") directly without tools.
        3. You can SEE the dashboard. If the user asks "Is this efficient?", look at the chart in the image.
        
        GUIDELINES:
        - If the user asks to change a view or parameter, USE A TOOL.
        - If the user asks a general question, ANSWER DIRECTLY.
        - Be concise, professional, and helpful.
        - If you run a simulation, explain briefly what you did.
      `;

      const genAI = new GoogleGenerativeAI(apiKey);
      
      // Select model based on whether image context is available
      // Use gemini-3-pro-image-preview for vision tasks, gemini-3-pro-preview for text/tools
      const modelName = imagePart ? "gemini-3-pro-image-preview" : "gemini-3-pro-preview";
      
      const model = genAI.getGenerativeModel({ 
        model: modelName,
        systemInstruction: systemPrompt,
        tools: [{ functionDeclarations: tools }]
      });

      // Filter out the initial greeting and ensure history starts with user
      // Also ensure we don't send the current user message in history (it's sent in sendMessage)
      const history = messages
        .filter((_, index) => index > 0) // Skip the first message (Greeting)
        .map(m => ({
          role: m.role === 'user' ? 'user' : 'model',
          parts: [{ text: m.content }]
        }));

      const chat = model.startChat({
        history: history,
      });

      // Send message with image if available
      const parts = [{ text: userMessage }];
      if (imagePart) {
        parts.push(imagePart);
      }

      const result = await chat.sendMessage(parts);
      const response = await result.response;
      const functionCalls = response.functionCalls();

      if (functionCalls && functionCalls.length > 0) {
        // Handle function calls
        for (const call of functionCalls) {
          const functionName = call.name;
          const functionArgs = call.args;
          
          // Execute the tool
          const toolResult = await executeTool(functionName, functionArgs, {
            navigate,
            api,
            ...agentContext
          });

          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: `Action: ${toolResult}` 
          }]);
        }
      } else {
        // Normal text response
        const text = response.text();
        setMessages(prev => [...prev, { role: 'assistant', content: text }]);
      }

    } catch (error) {
      console.error('Gemini Error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 h-14 w-14 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-lg flex items-center justify-center transition-all duration-200 hover:scale-105 z-50"
      >
        <MessageSquare className="h-6 w-6" />
      </button>
    );
  }

  return (
    <div id="portfolio-chat-widget" className="fixed bottom-6 right-6 w-96 h-[600px] max-h-[calc(100vh-6rem)] bg-white dark:bg-gray-800 rounded-2xl shadow-2xl flex flex-col border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">
      {/* Header */}
      <div className="p-4 bg-indigo-600 text-white flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5" />
          <h3 className="font-semibold">Portfolio Pilot</h3>
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
            onClick={() => setShowSettings(!showSettings)}
            className="p-1.5 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <Settings className="h-4 w-4" />
          </button>
          <button 
            onClick={() => setIsOpen(false)}
            className="p-1.5 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="p-4 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Gemini API Key
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Enter your API key"
            className="w-full p-2 rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white mb-2 text-sm"
          />
          <button
            onClick={() => handleSaveApiKey(apiKey)}
            className="w-full py-2 bg-indigo-600 text-white rounded text-sm font-medium hover:bg-indigo-700"
          >
            Save Key
          </button>
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
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-gray-800 p-3 rounded-lg rounded-bl-none border border-gray-200 dark:border-gray-700 shadow-sm">
              <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything..."
            className="flex-1 p-2 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </form>
    </div>
  );
};

export default PortfolioChatWidget;
