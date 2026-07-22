// ============================================================
// ADD THESE TO YOUR PORTFOLIO page.tsx
// ============================================================

// STEP 1: Add these imports at the top of page.tsx
// (alongside existing FaIcons)
import { FaRobot, FaUsers, FaFileAlt, FaCalendarCheck, FaChartBar } from 'react-icons/fa'

// STEP 2: Add RushChatbot import and component
// At the top of page.tsx, add:
// import RushChatbot from './components/RushChatbot'

// At the very bottom of the JSX (before the closing >), add:
// <RushChatbot />

// STEP 3: Add these 5 projects to the 'projects' array (after existing projects):
const aiAutomationProjects = [
  {
    title: 'AI Chatbot - Rush',
    description: 'AI-powered customer support butler with conversation memory, DeepSeek AI integration, and webhook support for n8n/Zapier/Make/GoHighLevel.',
    tech: ['Python', 'FastAPI', 'DeepSeek', 'Neon PostgreSQL', 'Vercel'],
    github: 'https://github.com/emmanalcazarjr-ops/chatbot-api',
    icon: FaRobot,
    gradient: 'from-violet-500 via-purple-500 to-fuchsia-500',
  },
  {
    title: 'Lead Follow-up API',
    description: 'Automated lead qualification and personalized email follow-up generation using AI. Supports webhook integration for CRM pipelines.',
    tech: ['Python', 'FastAPI', 'DeepSeek', 'Neon PostgreSQL', 'Vercel'],
    github: 'https://github.com/emmanalcazarjr-ops/lead-api',
    icon: FaUsers,
    gradient: 'from-blue-500 via-cyan-500 to-teal-500',
  },
  {
    title: 'Document Processing API',
    description: 'AI-powered document analysis with smart summarization, key point extraction, and document classification. Supports custom analysis prompts.',
    tech: ['Python', 'FastAPI', 'DeepSeek', 'Neon PostgreSQL', 'Vercel'],
    github: 'https://github.com/emmanalcazarjr-ops/document-api',
    icon: FaFileAlt,
    gradient: 'from-emerald-500 via-teal-500 to-cyan-500',
  },
  {
    title: 'Appointment Booking API',
    description: 'Smart scheduling system for interviews and business meetings with AI-generated confirmations and availability management.',
    tech: ['Python', 'FastAPI', 'DeepSeek', 'Neon PostgreSQL', 'Vercel'],
    github: 'https://github.com/emmanalcazarjr-ops/appointment-api',
    icon: FaCalendarCheck,
    gradient: 'from-orange-500 via-amber-500 to-yellow-500',
  },
  {
    title: 'Report Generation API',
    description: 'Automated business report generation including weekly summaries, project status, meeting notes, and client pipeline reports.',
    tech: ['Python', 'FastAPI', 'DeepSeek', 'Neon PostgreSQL', 'Vercel'],
    github: 'https://github.com/emmanalcazarjr-ops/report-api',
    icon: FaChartBar,
    gradient: 'from-rose-500 via-pink-500 to-fuchsia-500',
  },
]

// STEP 4: Add these demo types to the existing 'demos' Record type:
// Update the DemoType to include new types:
// type DemoType = 'fraud' | 'credit' | 'stock' | 'churn' | 'chatbot' | 'lead' | 'document' | 'appointment' | 'report'

// Add these to the demos object:
const aiAutomationDemos = {
  chatbot: {
    title: 'Rush AI Butler',
    endpoint: 'https://rush-ai-butler.vercel.app/api/chat',
    fields: [
      { name: 'session_id', label: 'Session ID (optional)', type: 'text', placeholder: 'Auto-generated if empty' },
      { name: 'message', label: 'Message', type: 'text', placeholder: 'Ask Rush anything about Emmanuel...' },
    ],
  },
  lead: {
    title: 'Lead Follow-up',
    endpoint: 'https://lead-followup.vercel.app/api/leads',
    fields: [
      { name: 'name', label: 'Lead Name', type: 'text', placeholder: 'John Doe' },
      { name: 'email', label: 'Email', type: 'text', placeholder: 'john@example.com' },
      { name: 'source', label: 'Source', type: 'text', placeholder: 'website' },
      { name: 'notes', label: 'Notes', type: 'text', placeholder: 'Interested in ML consulting...' },
    ],
  },
  document: {
    title: 'Document Processing',
    endpoint: 'https://doc-processing-api.vercel.app/api/documents',
    fields: [
      { name: 'filename', label: 'Filename', type: 'text', placeholder: 'meeting-notes.txt' },
      { name: 'text', label: 'Document Text', type: 'text', placeholder: 'Paste document text here...' },
      { name: 'analysis_type', label: 'Analysis Type', type: 'text', placeholder: 'all (or: summary, extract, classify)' },
    ],
  },
  appointment: {
    title: 'Appointment Booking',
    endpoint: 'https://appointment-api-vercel.vercel.app/api/appointments',
    fields: [
      { name: 'client_name', label: 'Your Name', type: 'text', placeholder: 'Jane Smith' },
      { name: 'client_email', label: 'Your Email', type: 'text', placeholder: 'jane@company.com' },
      { name: 'service', label: 'Service', type: 'text', placeholder: 'Technical Interview' },
      { name: 'date', label: 'Date', type: 'text', placeholder: '2026-08-01' },
      { name: 'time', label: 'Time', type: 'text', placeholder: '10:00' },
      { name: 'notes', label: 'Notes', type: 'text', placeholder: 'Discussing ML engineering role...' },
    ],
  },
  report: {
    title: 'Report Generation',
    endpoint: 'https://business-report-api.vercel.app/api/reports',
    fields: [
      { name: 'type', label: 'Report Type', type: 'text', placeholder: 'weekly_summary (or: project_status, meeting_notes, client_pipeline)' },
      { name: 'title', label: 'Report Title', type: 'text', placeholder: 'Weekly Summary - July 2026' },
      { name: 'data', label: 'Data (JSON)', type: 'text', placeholder: '{"activities":["Built APIs","Deployed to Vercel"],"achievements":["5 APIs launched"]}' },
    ],
  },
}

// STEP 5: Add result renderers for each new demo type
// Add these cases to your existing result rendering logic:

// For chatbot:
// {result.response && <p className="text-gray-300">{result.response}</p>}

// For lead:
// {result.id && <p>Lead created: {result.name} ({result.email})</p>}
// {result.subject && <div><h4>{result.subject}</h4><p>{result.body}</p></div>}

// For document:
// {result.summary && <p>{result.summary}</p>}
// {result.key_points && result.key_points.map((p, i) => <span key={i} className="tag">{p}</span>)}
// {result.document_type && <span className="badge">{result.document_type}</span>}

// For appointment:
// {result.confirmation_message && <p>{result.confirmation_message}</p>}
// {result.status && <span className="badge">{result.status}</span>}

// For report:
// {result.content && <div dangerouslySetInnerHTML={{ __html: result.content }} />}
