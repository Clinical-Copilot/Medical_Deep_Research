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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { type: 'user', content: userMessage }]);
    setIsLoading(true);
    setCurrentStep('Initializing research process...');

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
      
      // ===== DEBUG LOGGING START =====
      console.log('========== RESPONSE DATA START ==========');
      console.log('Full response data:', JSON.stringify(data, null, 2));
      console.log('Data status:', data.status);
      console.log('Data data:', JSON.stringify(data.data, null, 2));
      console.log('Workflow steps:', JSON.stringify(data.data?.workflow_steps, null, 2));
      console.log('========== RESPONSE DATA END ============');
      // ===== DEBUG LOGGING END =====
      
      if (data.status === 'success' && data.data) {
        // Handle the case when workflow terminates early
        if (!data.data.workflow_steps || data.data.workflow_steps.length === 0) {
          console.log('No workflow steps found');
          setMessages(prev => [...prev, {
            type: 'info',
            content: 'I am Biomedical Deep Research, a specialized AI assistant focused on comprehensive biomedical and healthcare research and analysis. How can I assist you today?',
            name: 'system'
          }]);
          
          setIsLoading(false);
          setCurrentStep('');
          return;
        }

        // Process workflow steps
        if (data.data.workflow_steps) {
          console.log('Processing workflow steps:', JSON.stringify(data.data.workflow_steps, null, 2));
          let planShown = false;
          let finalReport = null;

          // First pass: collect the final report
          data.data.workflow_steps.forEach(step => {
            console.log('Processing step in first pass:', JSON.stringify(step, null, 2));
            if (step.role === 'assistant' && step.name === 'reporter') {
              console.log('Found report message:', JSON.stringify(step, null, 2));
              finalReport = step;
            }
          });

          // Second pass: show messages in order, but skip the report
          data.data.workflow_steps.forEach(step => {
            console.log('Processing step in second pass:', JSON.stringify(step, null, 2));
            
            // Update current step based on the workflow step
            if (step.role === 'assistant') {
              console.log('Processing assistant step:', {
                name: step.name,
                content: step.content,
                role: step.role
              });

              // Set status message based on the agent's role
              let statusMessage = '';
              switch (step.name) {
                case 'planner':
                  statusMessage = '📋 Planning research approach...';
                  break;
                case 'researcher':
                  statusMessage = '🔍 Researching medical information...';
                  break;
                case 'coder':
                  statusMessage = '💻 Processing research data...';
                  break;
                case 'reporter':
                  statusMessage = '📝 Generating final report...';
                  break;
                case 'coordinator':
                  statusMessage = '👨‍💼 Coordinating research process...';
                  break;
                default:
                  statusMessage = 'Processing...';
              }
              console.log('Setting status message:', statusMessage);
              
              // Use setTimeout to ensure state updates are processed
              setTimeout(() => {
                setCurrentStep(statusMessage);
              }, 0);

              if (step.name === 'planner') {
                // Show plan immediately when received from planner
                if (!planShown) {
                  console.log('Adding plan message:', JSON.stringify(step, null, 2));
                  setMessages(prev => [...prev, {
                    type: 'plan',
                    content: step.content,
                    name: step.name
                  }]);
                  planShown = true;
                }
              } else if (step.name === 'reporter') {
                // Skip showing report here, we'll show it at the end
                console.log('Skipping reporter message for now');
              } else {
                console.log('Adding info message:', JSON.stringify(step, null, 2));
                setMessages(prev => [...prev, {
                  type: 'info',
                  content: step.content,
                  name: step.name
                }]);
              }
            }
          });

          // Show the final report last and remove the plan
          if (finalReport) {
            console.log('Adding final report:', JSON.stringify(finalReport, null, 2));
            setTimeout(() => {
              setCurrentStep('📝 Generating final report...');
            }, 0);
            setMessages(prev => {
              // Create new array without plan and with final report
              const messagesWithoutPlan = prev.filter(msg => msg.type !== 'plan');
              return [...messagesWithoutPlan, {
                type: 'report',
                content: finalReport.content,
                name: finalReport.name
              }];
            });
          }
        }

        // If we have a final report but it wasn't in the workflow steps
        if (data.data.report && !data.data.workflow_steps.some(step => step.role === 'assistant' && step.name === 'reporter')) {
          console.log('Adding report from data.report:', JSON.stringify(data.data.report, null, 2));
          setTimeout(() => {
            setCurrentStep('📝 Generating final report...');
          }, 0);
          setMessages(prev => {
            // Create new array without plan and with final report
            const messagesWithoutPlan = prev.filter(msg => msg.type !== 'plan');
            return [...messagesWithoutPlan, {
              type: 'report',
              content: data.data.report,
              name: 'reporter'
            }];
          });
        }

        // If we have a coordinator response, add it as the final message
        if (data.data.coordinator_response) {
          console.log('Adding coordinator response:', JSON.stringify(data.data.coordinator_response, null, 2));
          setMessages(prev => [...prev, {
            type: 'info',
            content: data.data.coordinator_response,
            name: 'coordinator'
          }]);
        }
      } else {
        console.error('Error in response:', JSON.stringify(data, null, 2));
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

  // Helper function to get default status messages
  const getDefaultStatusMessage = (name) => {
    switch (name) {
      case 'planner':
        return 'Analyzing research requirements...';
      case 'researcher':
        return 'Gathering medical information...';
      case 'coder':
        return 'Processing research data...';
      case 'reporter':
        return 'Compiling research findings...';
      case 'coordinator':
        return 'Coordinating research process...';
      default:
        return 'Processing...';
    }
  };

  const renderMessage = (message) => {
    // Helper function to get message header based on type and name
    const getMessageHeader = (type, name) => {
      switch (type) {
        case 'plan':
          return '📋 Research Plan';
        case 'report':
          return '📝 Research Report';
        case 'info':
          switch (name) {
            case 'planner':
              return '📋 Planner';
            case 'researcher':
              return '🔍 Researcher';
            case 'coder':
              return '💻 Data Processor';
            case 'reporter':
              return '📝 Reporter';
            case 'coordinator':
              return '👨‍💼 Coordinator';
            default:
              return '💡 System';
          }
        default:
          return '💡 Message';
      }
    };

    // Helper function to get message status
    const getMessageStatus = (type, name, content) => {
      if (type === 'info') {
        if (name === 'planner') {
          return 'Planning research approach...';
        } else if (name === 'researcher') {
          return 'Researching medical information...';
        } else if (name === 'coder') {
          return 'Processing research data...';
        } else if (name === 'reporter') {
          return 'Writing research report...';
        } else if (name === 'coordinator') {
          return 'Coordinating research process...';
        }
      }
      return null;
    };

    switch (message.type) {
      case 'plan':
        return (
          <div className="plan-section">
            <h3>{getMessageHeader(message.type)}</h3>
            <div className="message-status">{getMessageStatus(message.type, message.name)}</div>
            <pre>{message.content}</pre>
          </div>
        );
      case 'report':
        return (
          <div className="report-section">
            <h3>{getMessageHeader(message.type)}</h3>
            <div className="message-status">{getMessageStatus(message.type, message.name)}</div>
            <div className="report-content" style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
          </div>
        );
      case 'info':
        return (
          <div className="info-section">
            <div className="info-header">
              <span className="info-icon">{getMessageHeader(message.type, message.name)}</span>
              <span className="info-name">{message.name || 'system'}</span>
            </div>
            <div className="message-status">{getMessageStatus(message.type, message.name)}</div>
            <div className="message-content" style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
          </div>
        );
      case 'error':
        return <div className="message-content error">{message.content}</div>;
      default:
        return <div className="message-content">{message.content}</div>;
    }
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
          </button>
        </form>
      </div>
    </div>
  );
}

export default App; 