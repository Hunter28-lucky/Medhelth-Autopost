import React, { useState, useEffect } from 'react';
import { 
  Activity, Layers, Sliders, FileText, PlayCircle, Settings as SettingsIcon, 
  Globe, Clock, Download, RefreshCw, AlertCircle, ExternalLink, Sparkles,
  Shield, Lock, LogOut, Eye, EyeOff, CheckCircle2
} from 'lucide-react';

import { getDeveloperToken, setDeveloperToken, removeDeveloperToken } from './apiClient';
import TopicManager from './components/TopicManager';
import ContentRulesEditor from './components/ContentRulesEditor';
import DraftReviewQueue from './components/DraftReviewQueue';
import RunControlsAndLogs from './components/RunControlsAndLogs';
import SystemSettings from './components/SystemSettings';

export default function App() {
  const [activeTab, setActiveTab] = useState('topics');
  
  // Developer Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [passwordInput, setPasswordInput] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [developerName, setDeveloperName] = useState('Krish Goswami');

  // Data states
  const [topics, setTopics] = useState([]);
  const [contentRules, setContentRules] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [runLogs, setRunLogs] = useState([]);
  const [settings, setSettings] = useState(null);
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check developer session on startup
  useEffect(() => {
    const checkAuth = async () => {
      const token = getDeveloperToken();
      if (!token) {
        setIsAuthenticated(false);
        setIsCheckingAuth(false);
        return;
      }
      try {
        const res = await fetch('/api/auth/verify');
        if (res.ok) {
          const data = await res.json();
          setIsAuthenticated(true);
          setDeveloperName(data.developer_name || 'Krish Goswami');
          fetchAllData();
        } else {
          removeDeveloperToken();
          setIsAuthenticated(false);
        }
      } catch (err) {
        removeDeveloperToken();
        setIsAuthenticated(false);
      } finally {
        setIsCheckingAuth(false);
      }
    };

    checkAuth();

    // Listen for auth-required events from apiClient
    const handleAuthRequired = () => {
      setIsAuthenticated(false);
      removeDeveloperToken();
    };
    window.addEventListener('pulse_auth_required', handleAuthRequired);
    return () => window.removeEventListener('pulse_auth_required', handleAuthRequired);
  }, []);

  const fetchAllData = async () => {
    try {
      const [tRes, rRes, dRes, lRes, sRes, scRes] = await Promise.all([
        fetch('/api/topics').then(r => r.json()),
        fetch('/api/content-rules').then(r => r.json()),
        fetch('/api/drafts').then(r => r.json()),
        fetch('/api/runs/history').then(r => r.json()),
        fetch('/api/settings').then(r => r.json()),
        fetch('/api/scheduler/status').then(r => r.json())
      ]);

      setTopics(Array.isArray(tRes) ? tRes : []);
      setContentRules(rRes);
      setDrafts(Array.isArray(dRes) ? dRes : []);
      setRunLogs(Array.isArray(lRes) ? lRes : []);
      setSettings(sRes);
      setSchedulerStatus(scRes);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchAllData();
    const interval = setInterval(fetchAllData, 10000); // Poll every 10s for live run updates
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleDeveloperLogin = async (e) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setAuthError('');

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: passwordInput })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Invalid developer credentials');
      }

      setDeveloperToken(data.token);
      setDeveloperName(data.developer_name || 'Krish Goswami');
      setIsAuthenticated(true);
      setPasswordInput('');
      fetchAllData();
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => {
    removeDeveloperToken();
    setIsAuthenticated(false);
  };

  const handleTriggerRun = async (topicId = null) => {
    const res = await fetch('/api/runs/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic_id: topicId, force_fresh_search: true })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to trigger run');
    }
    setActiveTab('runs');
    setTimeout(fetchAllData, 1200);
  };

  const handleSaveContentRules = async (updatedRules) => {
    const res = await fetch('/api/content-rules', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedRules)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update rules');
    setContentRules(data);
  };

  const handleSaveSettings = async (updatedSettings) => {
    const res = await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedSettings)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update settings');
    setSettings(data);
  };

  const handleToggleScheduler = async (enable) => {
    const res = await fetch(`/api/scheduler/toggle?enable=${enable}`, { method: 'POST' });
    const data = await res.json();
    setSchedulerStatus(data);
  };

  const pendingDraftsCount = drafts.filter(d => d.status === 'PENDING_REVIEW').length;

  // --- DEVELOPER ACCESS LOCK SCREEN ---
  if (!isAuthenticated && !isCheckingAuth) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        background: 'radial-gradient(circle at 50% 20%, rgba(15, 23, 42, 0.95), #020617)'
      }}>
        <div className="glass-card" style={{
          maxWidth: '480px',
          width: '100%',
          padding: '36px',
          borderRadius: '16px',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7), 0 0 30px rgba(0, 240, 255, 0.15)',
          border: '1px solid rgba(0, 240, 255, 0.3)'
        }}>
          {/* Header Icon */}
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <div style={{
              width: '56px',
              height: '56px',
              margin: '0 auto 16px auto',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, #00f0ff 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(0, 240, 255, 0.4)'
            }}>
              <Shield size={28} color="#041019" />
            </div>
            <h2 style={{ fontSize: '1.4rem', color: '#fff', fontWeight: '700', marginBottom: '6px' }}>
              PulsePublish Portal
            </h2>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(99, 102, 241, 0.15)', padding: '4px 10px', borderRadius: '20px', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
              <Lock size={12} style={{ color: '#818cf8' }} />
              <span style={{ fontSize: '0.75rem', color: '#c7d2fe', fontWeight: '500' }}>
                Restricted Developer Access: Krish Goswami
              </span>
            </div>
          </div>

          <form onSubmit={handleDeveloperLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {authError && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                padding: '10px 14px',
                borderRadius: '8px',
                color: '#fca5a5',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertCircle size={16} />
                {authError}
              </div>
            )}

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Developer Key</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Default: krish@dev2026</span>
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  placeholder="Enter developer password"
                  value={passwordInput}
                  onChange={e => setPasswordInput(e.target.value)}
                  autoFocus
                  required
                  style={{ paddingRight: '40px' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '10px', justifyContent: 'center', fontWeight: '600' }}
              disabled={isLoggingIn}
            >
              {isLoggingIn ? 'Authenticating...' : 'Unlock Developer Session'}
            </button>
          </form>

          <div style={{ marginTop: '24px', textAlign: 'center', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: 0 }}>
              Protected by HMAC-SHA256 Cryptographic Sessions &bull; WordPress Draft Enforcement &bull; Stealth Sync
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation Bar */}
      <header style={{ 
        background: 'rgba(7, 9, 14, 0.85)', 
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--border-subtle)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        padding: '0 24px'
      }}>
        <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '70px' }}>
          
          {/* Brand Logo & Name */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ 
              width: '40px', 
              height: '40px', 
              borderRadius: '10px', 
              background: 'linear-gradient(135deg, #00f0ff 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(0, 240, 255, 0.4)'
            }}>
              <Activity size={22} color="#041019" />
            </div>
            <div>
              <h1 style={{ fontSize: '1.15rem', color: '#fff', fontWeight: '700', lineHeight: 1.2 }}>
                PulsePublish <span style={{ color: '#00f0ff', fontSize: '0.8rem', fontWeight: '500' }}>AI News Engine</span>
              </h1>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Medical & AI Research &bull; WordPress Auto-Publisher</span>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav style={{ display: 'flex', gap: '4px', background: 'var(--bg-surface-elevated)', padding: '5px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <button 
              className={`btn btn-ghost ${activeTab === 'topics' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('topics')}
              style={{ fontSize: '0.85rem', padding: '6px 14px' }}
            >
              <Layers size={16} /> Topics ({topics.length})
            </button>

            <button 
              className={`btn btn-ghost ${activeTab === 'rules' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('rules')}
              style={{ fontSize: '0.85rem', padding: '6px 14px' }}
            >
              <Sliders size={16} /> Content Rules & Style Cloner
            </button>

            <button 
              className={`btn btn-ghost ${activeTab === 'drafts' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('drafts')}
              style={{ fontSize: '0.85rem', padding: '6px 14px', position: 'relative' }}
            >
              <FileText size={16} /> Review Queue
              {pendingDraftsCount > 0 && (
                <span className="badge badge-amber" style={{ padding: '1px 6px', fontSize: '0.7rem', marginLeft: '4px' }}>
                  {pendingDraftsCount}
                </span>
              )}
            </button>

            <button 
              className={`btn btn-ghost ${activeTab === 'runs' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('runs')}
              style={{ fontSize: '0.85rem', padding: '6px 14px' }}
            >
              <PlayCircle size={16} /> Run & Logs
            </button>

            <button 
              className={`btn btn-ghost ${activeTab === 'settings' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('settings')}
              style={{ fontSize: '0.85rem', padding: '6px 14px' }}
            >
              <SettingsIcon size={16} /> Settings
            </button>
          </nav>

          {/* Status Indicators, Developer Badge & Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span 
              className="badge" 
              style={{ 
                background: settings?.wordpress_api_key_configured ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                color: settings?.wordpress_api_key_configured ? '#34d399' : '#fbbf24',
                border: settings?.wordpress_api_key_configured ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)'
              }}
              title={settings?.wordpress_api_key_configured ? 'WordPress credentials configured' : 'WordPress API key not set yet'}
            >
              <Globe size={12} /> {settings?.wordpress_api_key_configured ? 'WP Connected' : 'WP Setup Needed'}
            </span>

            {/* Developer Status Badge */}
            <div 
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: 'rgba(99, 102, 241, 0.15)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                padding: '4px 10px',
                borderRadius: '8px',
                fontSize: '0.78rem',
                color: '#c7d2fe'
              }}
              title="Authenticated Developer Session"
            >
              <Shield size={13} style={{ color: '#818cf8' }} />
              <span>{developerName}</span>
              <button
                onClick={handleLogout}
                title="Log out developer session"
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center',
                  marginLeft: '4px'
                }}
              >
                <LogOut size={12} />
              </button>
            </div>

            <button 
              className="btn btn-primary"
              style={{ padding: '7px 14px', fontSize: '0.8rem' }}
              onClick={() => handleTriggerRun(null)}
            >
              <Sparkles size={15} /> Run Pipeline
            </button>
          </div>
        </div>
      </header>

      {/* Main Content View */}
      <main style={{ flex: 1, maxWidth: '1440px', width: '100%', margin: '0 auto', padding: '32px 24px' }}>
        {activeTab === 'topics' && (
          <TopicManager 
            topics={topics} 
            onRefresh={fetchAllData} 
            onTriggerRun={handleTriggerRun} 
          />
        )}

        {activeTab === 'rules' && (
          <ContentRulesEditor 
            rules={contentRules} 
            onSaveRules={handleSaveContentRules} 
          />
        )}

        {activeTab === 'drafts' && (
          <DraftReviewQueue 
            drafts={drafts} 
            onRefresh={fetchAllData} 
          />
        )}

        {activeTab === 'runs' && (
          <RunControlsAndLogs 
            topics={topics}
            runLogs={runLogs}
            schedulerStatus={schedulerStatus}
            onTriggerRun={handleTriggerRun}
            onRefresh={fetchAllData}
            onToggleScheduler={handleToggleScheduler}
          />
        )}

        {activeTab === 'settings' && (
          <SystemSettings 
            settings={settings}
            onSaveSettings={handleSaveSettings}
          />
        )}
      </main>

      {/* Footer */}
      <footer style={{ 
        borderTop: '1px solid var(--border-subtle)', 
        padding: '16px 24px', 
        fontSize: '0.8rem', 
        color: 'var(--text-muted)',
        background: 'rgba(7, 9, 14, 0.9)'
      }}>
        <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            AI Medical/AI News Publisher &bull; Deduplication Engine &bull; Forced Draft Status &bull; Developed by Krish Goswami
          </div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <a 
              href="/api/docs" 
              target="_blank" 
              rel="noopener noreferrer" 
              style={{ color: '#38bdf8', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              FastAPI Interactive API Docs <ExternalLink size={12} />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
