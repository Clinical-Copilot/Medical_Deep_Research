import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import logo from './logo.png';
import './styles/App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [activeTools, setActiveTools] = useState(new Map());
  const [selectedModel, setSelectedModel] = useState('OpenAI o1');
  const [outputFormat, setOutputFormat] = useState('long_report');
  const [customFormat, setCustomFormat] = useState('');
  const [humanFeedback, setHumanFeedback] = useState('no');
  const [thinkMode, setThinkMode] = useState('medium');
  const [maxSteps, setMaxSteps] = useState(3);
  const [openConfig, setOpenConfig] = useState(null);
  const [collapsedMessages, setCollapsedMessages] = useState(new Set());
  const [isLoadingPage, setIsLoadingPage] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const messagesEndRef = useRef(null);
  const stepCounter = useRef(0);
  const resultTimer = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const toggleMessageCollapse = (messageIndex) => {
    setCollapsedMessages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageIndex)) {
        newSet.delete(messageIndex);
      } else {
        newSet.add(messageIndex);
      }
      return newSet;
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStep]);

  useEffect(() => {
    // Simulate loading process
    const loadingSteps = [
      { progress: 20, text: "Initializing Medical AI..." },
      { progress: 40, text: "Loading Research Models..." },
      { progress: 60, text: "Preparing Analysis Tools..." },
      { progress: 80, text: "Setting Up Interface..." },
      { progress: 100, text: "Ready!" }
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < loadingSteps.length) {
        setLoadingProgress(loadingSteps[currentStep].progress);
        currentStep++;
      } else {
        clearInterval(interval);
        setTimeout(() => {
          setIsLoadingPage(false);
        }, 300);
      }
    }, 400);

    return () => clearInterval(interval);
  }, []);

  const renderMarkdown = (text) => {
    // Preprocess the text to ensure proper table formatting
    let processedText = text
      .replace(/\\n/g, '\n')  // Convert literal \n to actual newlines
      .trim();

    // Better table processing - ensure proper spacing around tables
    const tableRegex = /(\|.*\|)\n(\|[-\s|]+\|)\n((?:\|.*\|\n?)*)/g;
    processedText = processedText.replace(tableRegex, (match, header, separator, rows) => {
      // Ensure proper table formatting with newlines
      const cleanHeader = header.trim();
      const cleanSeparator = separator.trim();
      const cleanRows = rows.trim();
      
      return `\n${cleanHeader}\n${cleanSeparator}\n${cleanRows}\n`;
    });

    // Final cleanup
    processedText = processedText.replace(/\n{3,}/g, '\n\n');

    // Debug: Log if text contains tables
    if (text.includes('|') && text.includes('---')) {
      console.log('[MARKDOWN TABLE] Original:', text.substring(0, 300));
      console.log('[MARKDOWN TABLE] Processed:', processedText.substring(0, 300));
    }

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}  // Enable GitHub Flavored Markdown for tables
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
        {processedText}
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
      const requestBody = {
        query: userMessage,
        max_plan_iterations: thinkMode === 'high' ? 7 : thinkMode === 'medium' ? 3 : 1,
        max_step_num: maxSteps,
        model: selectedModel,
        output_format: outputFormat,
        human_feedback: humanFeedback
      };

      // Add custom format if selected
      if (outputFormat === 'custom' && customFormat.trim()) {
        requestBody.custom_format = customFormat.trim();
      }

      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
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
                  setMessages(prev => {
                    const newMessages = [...prev, {
                      type: 'plan',
                      content: formattedPlan,
                      name: 'planner'
                    }];
                    // Auto-collapse plan messages - use the new length as index
                    setCollapsedMessages(collapsed => new Set([...collapsed, newMessages.length - 1]));
                    return newMessages;
                  });
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
                setMessages(prev => {
                  const newMessages = [...prev, {
                    type: 'report',
                    content,
                    name: step_title || 'step'
                  }];
                  // Auto-collapse report messages - use the new length as index
                  setCollapsedMessages(collapsed => new Set([...collapsed, newMessages.length - 1]));
                  return newMessages;
                });

                stepCounter.current += 1;
                if (stepCounter.current <= maxSteps) {
                  setCurrentStep(`Preparing step ${stepCounter.current} of the research plan...`);
                  if (resultTimer.current) clearTimeout(resultTimer.current);
                  // Only allow loading message if stepCounter is still within maxSteps
                  if (stepCounter.current < maxSteps + 1) {
                    resultTimer.current = setTimeout(() => {
                      setCurrentStep(`Generating research result #${stepCounter.current}...`);
                    }, 15000);
                  }
                } else {
                  setCurrentStep('Generating final report...');
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
                console.log('[FINAL REPORT]', content);
                setCurrentStep('Final report completed!');
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

  const renderMessage = (message, index) => {
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
      if (type === 'report') return 'Intermediary Findings';
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

    const isCollapsible = message.type === 'plan' || message.type === 'report';
    const isCollapsed = collapsedMessages.has(index);

    return (
      <div className={`message-bubble ${message.type}`}>
        <div 
          className={`message-header ${isCollapsible ? 'collapsible' : ''}`}
          onClick={isCollapsible ? () => toggleMessageCollapse(index) : undefined}
        >
          <span className="message-icon">{getMessageIcon(message.type, message.name)}</span>
          <span className="message-title">{getMessageTitle(message.type, message.name)}</span>
          {isCollapsible && (
            <span className={`collapse-arrow ${isCollapsed ? 'collapsed' : ''}`}>
              {isCollapsed ? '▶' : '▼'}
            </span>
          )}
        </div>
        {(!isCollapsible || !isCollapsed) && (
          <div className="message-content">
            {isMarkdownContent ? (
              <div className="markdown-content">{renderMarkdown(message.content)}</div>
            ) : (
              <div className="regular-content">{message.content}</div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderLoadingPage = () => {
    const loadingSteps = [
      "Initializing Medical AI...",
      "Loading Research Models...",
      "Preparing Analysis Tools...",
      "Setting Up Interface...",
      "Ready!"
    ];

    const currentStepIndex = Math.floor(loadingProgress / 20);
    const currentText = loadingSteps[currentStepIndex] || loadingSteps[loadingSteps.length - 1];

    return (
      <div className="loading-page">
        <div className="loading-container">
          <div className="loading-logo">
            <img src={logo} alt="Medical Deep Research Logo" />
          </div>
          <h1 className="loading-title">Medical Deep Research</h1>
          <div className="loading-progress-container">
            <div className="loading-progress-bar">
              <div 
                className="loading-progress-fill"
                style={{ width: `${loadingProgress}%` }}
              ></div>
            </div>
            <div className="loading-progress-text">{currentText}</div>
            <div className="loading-progress-percentage">{loadingProgress}%</div>
          </div>
          <div className="loading-animation">
            <div className="loading-dots">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      {isLoadingPage ? (
        renderLoadingPage()
      ) : (
        <div className="chat-container">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <img src={logo} alt="Medical Deep Research Logo" />
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
                  {renderMessage(message, index)}
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
          
          <div className="configuration-bar">
            <div className="config-section">
              <label 
                className="config-label"
                onClick={() => setOpenConfig(openConfig === 'model' ? null : 'model')}
              >
                <span className="config-name">Model</span>
                <span className="selected-value">{selectedModel}</span>
                <span className={`dropdown-arrow ${openConfig === 'model' ? 'open' : ''}`}>▼</span>
              </label>
              {openConfig === 'model' && (
                <div className="config-options">
                  {['OpenAI o1', 'OpenAI o3-mini', 'Claude Sonnet 4', 'Gemini 2.5 pro'].map((model) => (
                    <label key={model} className={`radio-option ${selectedModel === model ? 'selected' : ''}`}>
                      <input
                        type="radio"
                        name="model"
                        value={model}
                        checked={selectedModel === model}
                        onChange={(e) => {
                          setSelectedModel(e.target.value);
                          setOpenConfig(null);
                        }}
                      />
                      <span className="radio-label">{model}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="config-section">
              <label 
                className="config-label"
                onClick={() => setOpenConfig(openConfig === 'format' ? null : 'format')}
              >
                <span className="config-name">Output</span>
                <span className="selected-value">
                  {outputFormat === 'long_report' ? 'Long' : 
                   outputFormat === 'short_report' ? 'Short' : 
                   outputFormat === 'custom' ? 'Custom' : 'Long'}
                </span>
                <span className={`dropdown-arrow ${openConfig === 'format' ? 'open' : ''}`}>▼</span>
              </label>
              {openConfig === 'format' && (
                <div className="config-options">
                  <label className={`radio-option ${outputFormat === 'long_report' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="format"
                      value="long_report"
                      checked={outputFormat === 'long_report'}
                      onChange={(e) => {
                        setOutputFormat(e.target.value);
                        setOpenConfig(null);
                      }}
                    />
                    <span className="radio-label">Long Report</span>
                  </label>
                  <label className={`radio-option ${outputFormat === 'short_report' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="format"
                      value="short_report"
                      checked={outputFormat === 'short_report'}
                      onChange={(e) => {
                        setOutputFormat(e.target.value);
                        setOpenConfig(null);
                      }}
                    />
                    <span className="radio-label">Short Summary</span>
                  </label>
                  <label className={`radio-option ${outputFormat === 'custom' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="format"
                      value="custom"
                      checked={outputFormat === 'custom'}
                      onChange={(e) => {
                        setOutputFormat(e.target.value);
                        setOpenConfig(null);
                      }}
                    />
                    <span className="radio-label">Custom Format</span>
                  </label>
                  {outputFormat === 'custom' && (
                    <div className="custom-format-input">
                      <input
                        type="text"
                        placeholder="Type your custom format here..."
                        value={customFormat}
                        onChange={(e) => setCustomFormat(e.target.value)}
                        className="format-input"
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="config-section">
              <label 
                className="config-label"
                onClick={() => setOpenConfig(openConfig === 'feedback' ? null : 'feedback')}
              >
                <span className="config-name">Feedback</span>
                <span className="selected-value">{humanFeedback === 'yes' ? 'Yes' : 'No'}</span>
                <span className={`dropdown-arrow ${openConfig === 'feedback' ? 'open' : ''}`}>▼</span>
              </label>
              {openConfig === 'feedback' && (
                <div className="config-options">
                  <label className={`radio-option ${humanFeedback === 'yes' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="feedback"
                      value="yes"
                      checked={humanFeedback === 'yes'}
                      onChange={(e) => {
                        setHumanFeedback(e.target.value);
                        setOpenConfig(null);
                      }}
                    />
                    <span className="radio-label">Yes</span>
                  </label>
                  <label className={`radio-option ${humanFeedback === 'no' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="feedback"
                      value="no"
                      checked={humanFeedback === 'no'}
                      onChange={(e) => {
                        setHumanFeedback(e.target.value);
                        setOpenConfig(null);
                      }}
                    />
                    <span className="radio-label">No</span>
                  </label>
                </div>
              )}
            </div>

            <div className="config-section">
              <label 
                className="config-label"
                onClick={() => setOpenConfig(openConfig === 'thinkMode' ? null : 'thinkMode')}
              >
                <span className="config-name">Mode</span>
                <span className="selected-value">
                  {thinkMode === 'high' ? 'High' : 
                   thinkMode === 'medium' ? 'Medium' : 'Low'}
                </span>
                <span className={`dropdown-arrow ${openConfig === 'thinkMode' ? 'open' : ''}`}>▼</span>
              </label>
              {openConfig === 'thinkMode' && (
                <div className="config-options">
                  <label className={`radio-option ${thinkMode === 'high' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="thinkMode"
                      value="high"
                      checked={thinkMode === 'high'}
                      onChange={(e) => {
                        setThinkMode(e.target.value);
                        setOpenConfig(null);
                      }}
                    />
                    <span className="radio-label">High</span>
                  </label>
                  <label className={`radio-option ${thinkMode === 'medium' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="thinkMode"
                      value="medium"
                      checked={thinkMode === 'medium'}
                      onChange={(e) => {
                        setThinkMode(e.target.value);
                        setOpenConfig(null);
                      }}
                    />
                    <span className="radio-label">Medium</span>
                  </label>
                  <label className={`radio-option ${thinkMode === 'low' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="thinkMode"
                      value="low"
                      checked={thinkMode === 'low'}
                      onChange={(e) => {
                        setThinkMode(e.target.value);
                        setOpenConfig(null);
                      }}
                    />
                    <span className="radio-label">Low</span>
                  </label>
                </div>
              )}
            </div>
          </div>

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
      )}
    </div>
  );
}

export default App;