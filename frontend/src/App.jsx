import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './styles/App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [activeTools, setActiveTools] = useState(new Map());
  const messagesEndRef = useRef(null);
  const stepCounter = useRef(0);
  const resultTimer = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStep]);

  const renderMarkdown = (text) => {
    return (
      <ReactMarkdown
        components={{
          // Custom styling for different elements
          h1: ({children}) => <h1 className="markdown-h1">{children}</h1>,
          h2: ({children}) => <h2 className="markdown-h2">{children}</h2>,
          h3: ({children}) => <h3 className="markdown-h3">{children}</h3>,
          h4: ({children}) => <h4 className="markdown-h4">{children}</h4>,
          p: ({children}) => <p className="markdown-p">{children}</p>,
          ul: ({children}) => <ul className="markdown-ul">{children}</ul>,
          ol: ({children}) => <ol className="markdown-ol">{children}</ol>,
          li: ({children}) => <li className="markdown-li">{children}</li>,
          strong: ({children}) => <strong className="markdown-strong">{children}</strong>,
          em: ({children}) => <em className="markdown-em">{children}</em>,
          code: ({children}) => <code className="markdown-code">{children}</code>,
          pre: ({children}) => <pre className="markdown-pre">{children}</pre>,
          blockquote: ({children}) => <blockquote className="markdown-blockquote">{children}</blockquote>,
          a: ({href, children}) => <a href={href} className="markdown-link" target="_blank" rel="noopener noreferrer">{children}</a>,
          table: ({children}) => <table className="markdown-table">{children}</table>,
          thead: ({children}) => <thead className="markdown-thead">{children}</thead>,
          tbody: ({children}) => <tbody className="markdown-tbody">{children}</tbody>,
          tr: ({children}) => <tr className="markdown-tr">{children}</tr>,
          th: ({children}) => <th className="markdown-th">{children}</th>,
          td: ({children}) => <td className="markdown-td">{children}</td>,
        }}
      >
        {text}
      </ReactMarkdown>
    );
  };

  const formatPlanText = (planObj) => {
    if (typeof planObj === 'string') return planObj;
    if (planObj.error) return null;

    let text = `# Research Plan\n\n`;
    if (planObj.title) text += `**Title:** ${planObj.title}\n\n`;
    if (planObj.thought) text += `**Approach:** ${planObj.thought}\n\n`;
    if (Array.isArray(planObj.steps)) {
      text += `## Steps:\n\n`;
      planObj.steps.forEach((step, i) => {
        text += `### ${i + 1}. ${step.title}\n`;
        if (step.description) {
          text += `${step.description}\n\n`;
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
    setCurrentStep('Creating your research plan...');

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMessage,
          max_plan_iterations: 1,
          max_step_num: 3
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        const lines = buffer.split('\n\n');
        buffer = lines.pop();

        for (let line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const parsed = JSON.parse(jsonStr);
              console.log('[STREAM] Received event:', parsed);
              const { type, content, step_title } = parsed;

              if (type === 'plan' && content) {
                const formattedPlan = formatPlanText(content);
                if (formattedPlan !== null) {
                  setMessages(prev => [...prev, {
                    type: 'plan',
                    content: formattedPlan,
                    name: 'planner'
                  }]);
                }
                setCurrentStep('Research plan created. Preparing first step...');
                stepCounter.current = 1;

                if (resultTimer.current) clearTimeout(resultTimer.current);
                resultTimer.current = setTimeout(() => {
                  setCurrentStep('Generating research result #1...');
                }, 15000);
              } else if (type === 'tool_start' && content && content.tool_name) {
                setCurrentStep(`Running tools for step ${stepCounter.current} in the research plan...`);
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
                setActiveTools(prev => {
                  const newMap = new Map(prev);
                  const tool = newMap.get(content.tool_name);
                  if (tool) {
                    newMap.set(content.tool_name, {
                      ...tool,
                      status: 'completed',
                      endTime: Date.now()
                    });
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
              } else if (type === 'execution_res' && content) {
                setMessages(prev => [...prev, {
                  type: 'report',
                  content,
                  name: step_title || 'step'
                }]);

                stepCounter.current += 1;
                if (stepCounter.current <= 3) {
                  setCurrentStep(`Preparing step ${stepCounter.current} of the research plan...`);
                  if (resultTimer.current) clearTimeout(resultTimer.current);
                  // Only allow loading message if stepCounter is still within 3 steps
                  if (stepCounter.current < 4) {
                    resultTimer.current = setTimeout(() => {
                      setCurrentStep(`Generating research result #${stepCounter.current}...`);
                    }, 15000);
                  }
                } else {
                  setCurrentStep('');
                }
              } else if (
                type === 'message' &&
                content &&
                content.role !== 'user'
              ) {
                setMessages(prev => [...prev, {
                  type: 'assistant',
                  content: content.content,
                  name: content.name || 'system'
                }]);
              } else if (type === 'final_report' && content) {
                setMessages(prev => [...prev, {
                  type: 'conclusion',
                  content,
                  name: 'reporter'
                }]);
              } else if (type === 'error') {
                setMessages(prev => [...prev, {
                  type: 'error',
                  content: content || 'An unknown error occurred'
                }]);
                setCurrentStep('An error occurred.');
              }
            } catch (err) {
              console.warn('[STREAM PARSE ERROR]', line, err);
            }
          }
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`
      }]);
      setCurrentStep('An error occurred.');
    } finally {
      setIsLoading(false);
      setTimeout(() => setCurrentStep('All steps completed.'), 300);
      setTimeout(() => setCurrentStep(''), 1500);
      setActiveTools(new Map());
      if (resultTimer.current) clearTimeout(resultTimer.current);
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
      if (type === 'conclusion') return '✅';
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
      if (type === 'conclusion') return 'Final Report';
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
      message.type === 'conclusion' ||
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
            <div className="markdown-content">{renderMarkdown(message.content)}</div>
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
            {renderActiveTools()}
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
