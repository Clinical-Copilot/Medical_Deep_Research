import { useState, useRef, useEffect } from 'react';
import './styles/App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [activeTools, setActiveTools] = useState(new Map());
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStep]);

  const cleanMarkdown = (text) => {
    return text
      .replace(/^#{1,6}\s*/gm, '')
      .replace(/^\s*[-*]\s*/gm, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/^\*\[(.*?)\]\*\*/gm, '[$1]')
      .replace(/(\[[^\]]+\])\*/g, '$1')
      .replace(/\n{3,}/g, '\n\n');
  };

  const formatPlanText = (planObj) => {
    if (typeof planObj === 'string') return planObj;
    
    // Handle error case - don't show plan block for errors
    if (planObj.error) {
      return null; // Return null to indicate no plan should be shown
    }
    
    let text = `Research Plan:\n\n`;
    if (planObj.title) text += `Title: ${planObj.title}\n\n`;
    if (planObj.thought) text += `Approach: ${planObj.thought}\n\n`;
    if (Array.isArray(planObj.steps)) {
      text += `Steps:\n`;
      planObj.steps.forEach((step, i) => {
        text += `${i + 1}. ${step.title}\n`;
        if (step.description) {
          text += `   ${step.description}\n`;
        }
      });
    }
    return text;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { type: 'user', content: userMessage }]);
    setIsLoading(true);
    setCurrentStep('Processing your request...');

    try {
      console.log('[FETCH] Starting request to backend...');
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMessage,
          max_plan_iterations: 1,
          max_step_num: 3
        }),
      });

      console.log('[FETCH] Response status:', response.status);
      console.log('[FETCH] Response headers:', response.headers);

      if (!response.ok || !response.body) {
        throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      console.log('[STREAM] Starting to read stream...');
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('[STREAM] Stream ended');
          break;
        }
        
        const chunk = decoder.decode(value, { stream: true });
        console.log('[STREAM] Raw chunk:', chunk);
        buffer += chunk;

        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // keep incomplete

        for (let line of lines) {
          console.log('[STREAM] Processing line:', line);
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            console.log('[STREAM] JSON string:', jsonStr);
            try {
              const parsed = JSON.parse(jsonStr);
              console.log('[STREAM] Parsed data:', parsed);
              const { type, content, step_title } = parsed;

              if (type === 'plan' && content) {
                console.log('[PLAN]', content);
                const formattedPlan = formatPlanText(content);
                // Only add plan message if formatting didn't return null (i.e., no error)
                if (formattedPlan !== null) {
                  setMessages(prev => [...prev, {
                    type: 'plan',
                    content: formattedPlan,
                    name: 'planner'
                  }]);
                }
              } else if (type === 'execution_res' && content) {
                console.log('[EXECUTION RESULT]', step_title, content);
                setMessages(prev => [...prev, {
                  type: 'report',
                  content,
                  name: step_title || 'step'
                }]);
              } else if (
                type === 'message' &&
                content &&
                content.role !== 'user'
              ) {
                console.log('[MESSAGE]', content.role, content.name, content.content);
                setMessages(prev => [...prev, {
                  type: 'assistant',
                  content: content.content,
                  name: content.name || 'system'
                }]);
              } else if (type === 'tool_start' && content && content.tool_name) {
                console.log('[TOOL START]', content);
                setActiveTools(prev => {
                  const newMap = new Map(prev);
                  newMap.set(content.tool_name, {
                    name: content.display_name || content.tool_name,
                    status: 'running',
                    startTime: Date.now()
                  });
                  return newMap;
                });
              } else if (type === 'tool_complete' && content && content.tool_name) {
                console.log('[TOOL COMPLETE]', content);
                setActiveTools(prev => {
                  const newMap = new Map(prev);
                  const tool = newMap.get(content.tool_name);
                  if (tool) {
                    newMap.set(content.tool_name, {
                      ...tool,
                      status: 'completed',
                      endTime: Date.now()
                    });
                    // Remove completed tool after 2 seconds
                    setTimeout(() => {
                      setActiveTools(current => {
                        const updated = new Map(current);
                        updated.delete(content.tool_name);
                        return updated;
                      });
                    }, 2000);
                  }
                  return newMap;
                });
              } else if (type === 'error') {
                console.error('[ERROR]', content);
                setMessages(prev => [...prev, {
                  type: 'error',
                  content: content || 'An unknown error occurred'
                }]);
              }
            } catch (err) {
              console.warn('[STREAM PARSE ERROR]', line, err);
            }
          }
        }
      }
    } catch (error) {
      console.error('[SUBMIT ERROR]', error);
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`
      }]);
    } finally {
      setIsLoading(false);
      setCurrentStep('');
      setActiveTools(new Map()); // Clear any remaining tools
    }
  };

  const getToolIcon = (toolName) => {
    const icons = {
      'Web Search': '🔍',
      'Web Crawling': '🌐',
      'Academic Search': '📚',
      'Code Execution': '💻',
      'GitHub Trending': '⭐'
    };
    return icons[toolName] || '🔧';
  };

  const renderActiveTools = () => {
    try {
      if (!activeTools || activeTools.size === 0) return null;

      return (
        <div className="active-tools-container">
          <div className="active-tools-header">
            <span className="tools-label">Active Tools</span>
          </div>
          <div className="active-tools-list">
            {Array.from(activeTools.entries()).map(([toolName, tool]) => {
              if (!tool || !toolName) return null;
              return (
                <div 
                  key={toolName} 
                  className={`tool-indicator ${tool.status || 'running'}`}
                >
                  <span className="tool-icon">{getToolIcon(tool.name || toolName)}</span>
                  <span className="tool-name">{tool.name || toolName}</span>
                  <div className="tool-status">
                    {tool.status === 'running' && (
                      <div className="tool-spinner"></div>
                    )}
                    {tool.status === 'completed' && (
                      <div className="tool-checkmark">✓</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    } catch (error) {
      console.error('Error rendering active tools:', error);
      return null;
    }
  };

  const renderMessage = (message) => {
    const getMessageIcon = (type, name) => {
      if (type === 'plan') return '📋';
      if (type === 'report') return '📝';
      if (type === 'error') return '❌';
      if (type === 'user') return '👤';
      switch (name) {
        case 'coordinator': return '👨‍💼';
        case 'planner': return '📋';
        case 'researcher': return '🔍';
        case 'coder': return '💻';
        case 'reporter': return '📝';
        default: return '🤖';
      }
    };

    const getMessageTitle = (type, name) => {
      if (type === 'plan') return 'Research Plan';
      if (type === 'report') return 'Research Result';
      if (type === 'user') return 'You';
      if (type === 'error') return 'Error';
      switch (name) {
        case 'coordinator': return 'Coordinator';
        case 'planner': return 'Planner';
        case 'researcher': return 'Researcher';
        case 'coder': return 'Coder';
        case 'reporter': return 'Reporter';
        default: return 'Assistant';
      }
    };

    const isMarkdownContent = (
      message.type === 'plan' ||
      message.type === 'report' ||
      message.name === 'coordinator' ||
      message.name === 'assistant'
    );

    return (
      <div className={`message-bubble ${message.type}`}>
        <div className="message-header">
          <span className="message-icon">{getMessageIcon(message.type, message.name)}</span>
          <span className="message-title">{getMessageTitle(message.type, message.name)}</span>
        </div>
        <div className="message-content">
          {isMarkdownContent ? (
            <pre className="formatted-content">{cleanMarkdown(message.content)}</pre>
          ) : (
            <div className="regular-content">{message.content}</div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      <div className="chat-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h1>Medical Deep Research</h1>
            <p>
              I can help you with medical research questions. Ask me anything about medical conditions,
              treatments, research findings, or healthcare topics.
            </p>
          </div>
        ) : (
          <div className="messages">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.type}`}>
                {renderMessage(message)}
              </div>
            ))}
            {(() => {
              try {
                return renderActiveTools();
              } catch (error) {
                console.error('Tool render error:', error);
                return null;
              }
            })()}
            {isLoading && (
              <div className="message system">
                <div className="loading">
                  <div className="loading-spinner"></div>
                  <span className="status-message">{currentStep}</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a medical research question..."
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading ? '...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
