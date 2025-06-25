import { useState, useRef, useEffect } from 'react';
import './styles/App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { type: 'user', content: userMessage }]);
    setIsLoading(true);
    setCurrentStep('Processing your request...');

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

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      console.log('Response data:', JSON.stringify(data, null, 2));

      if (data.status === 'success') {
        if (data.data?.workflow_steps?.length > 0) {
          data.data.workflow_steps.forEach(step => {
            if (
              step.type === 'plan' &&
              step.content?.trim() &&
              step.content.trim() !== 'Research Plan:' &&
              step.content.trim() !== 'Plan:'
            ) {
              setMessages(prev => [...prev, {
                type: 'plan',
                content: step.content,
                name: step.name || 'planner'
              }]);
            } else if (step.type === 'report' && step.content?.trim()) {
              setMessages(prev => [...prev, {
                type: 'report',
                content: step.content,
                name: step.name || 'reporter'
              }]);
            } else if (step.content?.trim()) {
              setMessages(prev => [...prev, {
                type: 'assistant',
                content: step.content,
                name: step.name || 'system'
              }]);
            }
          });
        }

        if (data.data?.plan?.steps?.length > 0) {
          data.data.plan.steps.forEach(step => {
            if (step.execution_res?.trim()) {
              setMessages(prev => [...prev, {
                type: 'report',
                content: step.execution_res,
                name: step.title || 'step'
              }]);
            }
          });
        }

        if (data.data?.coordinator_response?.trim()) {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: data.data.coordinator_response,
            name: 'coordinator'
          }]);
        }

        if (!data.data?.workflow_steps && !data.data?.coordinator_response) {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: 'I am Biomedical Deep Research. How can I help you today?',
            name: 'system'
          }]);
        }
      } else {
        throw new Error(data.message || 'Failed to get response');
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`
      }]);
    } finally {
      setIsLoading(false);
      setCurrentStep('');
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