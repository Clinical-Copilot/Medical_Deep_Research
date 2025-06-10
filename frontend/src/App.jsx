import React, { useState } from 'react';
import './styles/App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [plan, setPlan] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [intermediateSteps, setIntermediateSteps] = useState([]);
  const [researchStatus, setResearchStatus] = useState('idle'); // 'idle', 'planning', 'researching', 'complete'

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmedInput = input.trim();
    if (!trimmedInput) return;

    // Reset states
    setError(null);
    setIntermediateSteps([]);
    setPlan(null);
    setReport(null);
    setResearchStatus('planning');

    // Add user message
    const userMessage = { type: 'user', content: trimmedInput };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      console.log('Sending request to backend...', { query: trimmedInput });
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: trimmedInput }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Server error' }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Received response:', data);
      
      // Handle plan
      if (data.plan) {
        setPlan(data.plan);
        setMessages(prev => [...prev, { 
          type: 'system', 
          content: 'INFO: Planner generating full plan', 
          plan: data.plan 
        }]);
        setResearchStatus('researching');
      }
      
      // Handle intermediate steps
      if (data.intermediate_steps && Array.isArray(data.intermediate_steps)) {
        setIntermediateSteps(data.intermediate_steps);
        data.intermediate_steps.forEach(step => {
          if (step.type === 'plan') {
            setMessages(prev => [...prev, { 
              type: 'plan', 
              content: 'INFO: Research plan updated', 
              plan: step.content 
            }]);
          } else if (step.type === 'research') {
            setMessages(prev => [...prev, { 
              type: 'system', 
              content: `INFO: Research team executing step: ${step.content}` 
            }]);
          } else if (step.type === 'coordinator') {
            setMessages(prev => [...prev, { 
              type: 'system', 
              content: `INFO: Coordinator evaluating results: ${step.content}` 
            }]);
          } else if (step.type === 'human_feedback') {
            setMessages(prev => [...prev, { 
              type: 'system', 
              content: `INFO: Awaiting human feedback: ${step.content}` 
            }]);
          }
        });
      }

      // Handle final report
      if (data.report) {
        setReport(data.report);
        setMessages(prev => [...prev, { 
          type: 'system', 
          content: `INFO: Research complete. Final report:\n${data.report}` 
        }]);
        setResearchStatus('complete');
      }
    } catch (error) {
      console.error('Error details:', error);
      const errorMessage = error.message || 'An error occurred while processing your request.';
      setError(errorMessage);
      setMessages(prev => [...prev, { 
        type: 'error', 
        content: `ERROR: ${errorMessage}` 
      }]);
      setResearchStatus('idle');
    } finally {
      setIsLoading(false);
    }
  };

  const renderLoadingState = () => {
    if (researchStatus === 'planning') {
      return (
        <div className="message system">
          <div className="loading">INFO: Initializing research workflow...</div>
        </div>
      );
    } else if (researchStatus === 'researching') {
      return (
        <div className="message system">
          <div className="loading">
            <div className="loading-spinner"></div>
            <div>INFO: Research in progress...</div>
          </div>
        </div>
      );
    }
    return null;
  };

  const renderMessage = (message, index) => {
    const messageContent = message.content;
    const messageType = message.type;

    return (
      <div key={index} className={`message ${messageType}`}>
        {messageType === 'system' && message.plan && (
          <div className="plan-section">
            <h3>Research Plan</h3>
            <pre>{JSON.stringify(message.plan, null, 2)}</pre>
          </div>
        )}
        {messageType === 'plan' && (
          <div className="plan-section">
            <h3>Updated Research Plan</h3>
            <pre>{JSON.stringify(message.plan, null, 2)}</pre>
          </div>
        )}
        <div className="message-content">{messageContent}</div>
      </div>
    );
  };

  return (
    <div className="app">
      <div className="chat-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h1>Welcome to MedDR</h1>
            <p>Your AI-powered medical research assistant. Ask me anything about medical research, clinical trials, or healthcare developments.</p>
          </div>
        ) : (
          <div className="messages">
            {messages.map((message, index) => renderMessage(message, index))}
            {renderLoadingState()}
            {error && (
              <div className="message error">
                <div className="error-content">{error}</div>
              </div>
            )}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask your medical research question..."
            disabled={isLoading}
            maxLength={1000}
          />
          <button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading ? 'Processing...' : 'Submit'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App; 