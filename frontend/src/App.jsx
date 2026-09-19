import React, { useState, useEffect } from 'react';
import { 
  Activity, Layers, Sliders, FileText, PlayCircle, Settings as SettingsIcon, 
  Globe, AlertCircle, ExternalLink, Sparkles,
  Shield, Lock, LogOut, Eye, EyeOff, ChevronDown, Plus,
  DollarSign, TrendingUp
} from 'lucide-react';

import { getDeveloperToken, setDeveloperToken, removeDeveloperToken } from './apiClient';
import SiteManager from './components/SiteManager';
import TopicManager from './components/TopicManager';
import ContentRulesEditor from './components/ContentRulesEditor';
import DraftReviewQueue from './components/DraftReviewQueue';
import RunControlsAndLogs from './components/RunControlsAndLogs';
import SystemSettings from './components/SystemSettings';
import CostBreakdownModal from './components/CostBreakdownModal';

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

  // Multi-Site State
  const [sites, setSites] = useState([]);
  const [selectedSiteId, setSelectedSiteId] = useState(1); // Default to Site 1 (MedHealth Times)
  const [showSiteMenu, setShowSiteMenu] = useState(false);

  // Data states
  const [topics, setTopics] = useState([]);
  const [contentRules, setContentRules] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [runLogs, setRunLogs] = useState([]);
  const [settings, setSettings] = useState(null);
  const [schedulerStatus, setSchedulerStatus] = useState(null);

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
        } else {
          removeDeveloperToken();
          setIsAuthenticated(false);
        }
      } catch (_err) {
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
      const [sitesRes, tRes, rRes, dRes, lRes, sRes, scRes] = await Promise.all([
        fetch('/api/sites').then(r => r.json()),
        fetch('/api/topics').then(r => r.json()),
        fetch(`/api/content-rules?site_id=${selectedSiteId || 1}`).then(r => r.json()),
        fetch('/api/drafts').then(r => r.json()),
        fetch('/api/runs/history').then(r => r.json()),
        fetch('/api/settings').then(r => r.json()),
        fetch('/api/scheduler/status').then(r => r.json())
      ]);

      setSites(Array.isArray(sitesRes) ? sitesRes : []);
      setTopics(Array.isArray(tRes) ? tRes : []);
      setContentRules(rRes);
      setDrafts(Array.isArray(dRes) ? dRes : []);
      setRunLogs(Array.isArray(lRes) ? lRes : []);
      setSettings(sRes);
      setSchedulerStatus(scRes);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    }
  };

  // Reload content rules whenever active site changes
  useEffect(() => {
    if (!isAuthenticated || !selectedSiteId) return;
    fetch(`/api/content-rules?site_id=${selectedSiteId}`)
      .then(r => r.json())
      .then(data => setContentRules(data))
      .catch(console.error);
  }, [selectedSiteId, isAuthenticated]);

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
      body: JSON.stringify({ 
        site_id: selectedSiteId, 
        topic_id: topicId, 
        force_fresh_search: true 
      })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to trigger run');
    }
    setActiveTab('runs');
    setTimeout(fetchAllData, 1200);
  };

  const handleSaveContentRules = async (updatedRules) => {
    const res = await fetch(`/api/content-rules?site_id=${selectedSiteId || 1}`, {
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

  // Filtered views according to active site selection
  const displayTopics = selectedSiteId 
    ? topics.filter(t => t.site_id === selectedSiteId)
    : topics;

  const displayDrafts = selectedSiteId
    ? drafts.filter(d => d.site_id === selectedSiteId)
    : drafts;

  const pendingDraftsCount = displayDrafts.filter(d => d.status === 'PENDING_REVIEW').length;
  const currentSite = sites.find(s => s.id === selectedSiteId) || sites[0] || { name: 'MedHealth Times', id: 1, wp_url: 'http://sh012.global.temp.domains/~ttprdsmy/medhealthtimes' };

  // Token Economics global calculations & modal state
  const costCurrency = settings?.cost_currency || 'USD';
  const costSymbols = { USD: '$', INR: '₹', EUR: '€', GBP: '£' };
  const costSymbol = costSymbols[costCurrency] || '$';
  const exchangeRate = settings?.cost_exchange_rate || 87.5;
  const isCostOverride = settings?.cost_manual_override_enabled;
  const unitCostUsd = isCostOverride ? (settings?.cost_fixed_per_post || 0.0035) : 0.0035;

  const formatCostGlobal = (usdAmount) => {
    let rate = 1.0;
    if (costCurrency === 'INR') rate = exchangeRate;
    else if (costCurrency === 'EUR') rate = 0.92;
    else if (costCurrency === 'GBP') rate = 0.79;

    const val = usdAmount * rate;
    if (costCurrency === 'INR') {
      return val < 0.01 ? `${costSymbol}${val.toFixed(3)}` : `${costSymbol}${val.toFixed(2)}`;
    }
    return `${costSymbol}${val.toFixed(4)}`;
  };

  const [costModalOpen, setCostModalOpen] = useState(false);
  const [costModalTopic, setCostModalTopic] = useState(null);
  const [costModalDraft, setCostModalDraft] = useState(null);

  const handleOpenCostModal = (topic = null, draft = null) => {
    setCostModalTopic(topic);
    setCostModalDraft(draft);
    setCostModalOpen(true);
  };

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
      <header className="app-header">
        <div className="app-header-inner">
          
          {/* Brand Logo & Name */}
          <div className="app-brand-area">
            <div style={{ 
              width: '38px', 
              height: '38px', 
              borderRadius: '10px', 
              background: 'linear-gradient(135deg, #00f0ff 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(0, 240, 255, 0.4)',
              flexShrink: 0
            }}>
              <Activity size={20} color="#041019" />
            </div>
            <div>
              <h1 className="app-brand-title">
                PulsePublish <span style={{ color: '#00f0ff', fontSize: '0.78rem', fontWeight: '500' }}>AI News Engine</span>
              </h1>
              <span className="app-brand-subtitle">Multi-Site Automation &bull; WordPress Auto-Publisher</span>
            </div>

            {/* Site Switcher Dropdown */}
            <div style={{ position: 'relative', marginLeft: '4px' }}>
              <button
                type="button"
                onClick={() => setShowSiteMenu(!showSiteMenu)}
                className="app-site-btn"
                title="Switch Target Website"
              >
                <Globe size={14} color="#00f0ff" style={{ flexShrink: 0 }} />
                <span style={{ fontWeight: '600', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {selectedSiteId ? currentSite.name : 'All Websites'}
                </span>
                <ChevronDown size={14} color="var(--text-muted)" style={{ flexShrink: 0 }} />
              </button>

              {showSiteMenu && (
                <div 
                  className="glass-card"
                  style={{
                    position: 'absolute',
                    top: '115%',
                    left: 0,
                    minWidth: '260px',
                    zIndex: 200,
                    padding: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    boxShadow: '0 12px 36px rgba(0, 0, 0, 0.7)'
                  }}
                >
                  <div style={{ padding: '6px 10px', fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Active Website Focus
                  </div>
                  {sites.map(s => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => {
                        setSelectedSiteId(s.id);
                        setShowSiteMenu(false);
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        background: selectedSiteId === s.id ? 'rgba(0, 240, 255, 0.12)' : 'transparent',
                        border: 'none',
                        color: selectedSiteId === s.id ? '#00f0ff' : '#cbd5e1',
                        cursor: 'pointer',
                        textAlign: 'left',
                        fontSize: '0.84rem'
                      }}
                    >
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {s.name}
                      </span>
                      {s.id === 1 && (
                        <span className="badge badge-cyan" style={{ fontSize: '0.65rem', padding: '1px 5px' }}>
                          Primary
                        </span>
                      )}
                    </button>
                  ))}

                  <button
                    type="button"
                    onClick={() => {
                      setSelectedSiteId(null);
                      setShowSiteMenu(false);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      background: selectedSiteId === null ? 'rgba(0, 240, 255, 0.12)' : 'transparent',
                      border: 'none',
                      color: selectedSiteId === null ? '#00f0ff' : '#94a3b8',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '0.84rem'
                    }}
                  >
                    🌐 View All Websites
                  </button>

                  <div style={{ borderTop: '1px solid var(--border-subtle)', margin: '4px 0' }} />

                  <button
                    type="button"
                    onClick={() => {
                      setShowSiteMenu(false);
                      setActiveTab('sites');
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      background: 'transparent',
                      border: 'none',
                      color: '#818cf8',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '0.84rem',
                      fontWeight: '600'
                    }}
                  >
                    <Plus size={14} /> Manage Websites...
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="app-nav-container">
            <button 
              className={`btn btn-ghost app-nav-tab ${activeTab === 'sites' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('sites')}
            >
              <Globe size={15} /> Websites ({sites.length})
            </button>

            <button 
              className={`btn btn-ghost app-nav-tab ${activeTab === 'topics' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('topics')}
            >
              <Layers size={15} /> Topics ({displayTopics.length})
            </button>

            <button 
              className={`btn btn-ghost app-nav-tab ${activeTab === 'rules' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('rules')}
            >
              <Sliders size={15} /> Content Rules
            </button>

            <button 
              className={`btn btn-ghost app-nav-tab ${activeTab === 'drafts' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('drafts')}
              style={{ position: 'relative' }}
            >
              <FileText size={15} /> Review Queue
              {pendingDraftsCount > 0 && (
                <span className="badge badge-amber" style={{ padding: '1px 5px', fontSize: '0.68rem', marginLeft: '3px' }}>
                  {pendingDraftsCount}
                </span>
              )}
            </button>

            <button 
              className={`btn btn-ghost app-nav-tab ${activeTab === 'runs' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('runs')}
            >
              <PlayCircle size={15} /> Run & Logs
            </button>

            <button 
              className={`btn btn-ghost app-nav-tab ${activeTab === 'settings' ? 'btn-secondary' : ''}`}
              onClick={() => setActiveTab('settings')}
            >
              <SettingsIcon size={15} /> Settings
            </button>
          </nav>

          {/* Status Indicators, Developer Badge & Actions */}
          <div className="app-header-actions">
            {/* Global Real-Time Run Cost Pill */}
            <button
              type="button"
              onClick={() => handleOpenCostModal(null, null)}
              className="app-cost-badge"
              title={`Estimated cost: ${formatCostGlobal(unitCostUsd)}/post. Catalog total: ${formatCostGlobal(unitCostUsd * Math.max(1, displayTopics.filter(t => t.is_active).length))} across ${displayTopics.filter(t => t.is_active).length} topics. Click for real-time Token Economics.`}
            >
              <TrendingUp size={13} style={{ color: '#00f0ff', flexShrink: 0 }} />
              <span>
                Est. Run: <strong>{formatCostGlobal(unitCostUsd)}</strong> / post
              </span>
              <span className="app-cost-catalog-text" style={{ color: 'var(--text-muted)' }}>
                &bull; {formatCostGlobal(unitCostUsd * Math.max(1, displayTopics.filter(t => t.is_active).length))} catalog
              </span>
            </button>

            <span 
              className="app-wp-status" 
              style={{ 
                background: settings?.wordpress_api_key_configured ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                color: settings?.wordpress_api_key_configured ? '#34d399' : '#fbbf24',
                border: settings?.wordpress_api_key_configured ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)'
              }}
              title={settings?.wordpress_api_key_configured ? 'WordPress credentials configured' : 'WordPress API key not set yet'}
            >
              <Globe size={12} style={{ flexShrink: 0 }} /> {settings?.wordpress_api_key_configured ? 'WP Connected' : 'WP Setup Needed'}
            </span>

            {/* Developer Status Badge */}
            <div 
              className="app-dev-badge"
              title="Authenticated Developer Session"
            >
              <Shield size={13} style={{ color: '#818cf8', flexShrink: 0 }} />
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
              className="btn btn-primary app-run-btn"
              onClick={() => handleTriggerRun(null)}
            >
              <Sparkles size={14} style={{ flexShrink: 0 }} /> Run Pipeline
            </button>
          </div>
        </div>
      </header>

      {/* Main Content View */}
      <main style={{ flex: 1, maxWidth: '1560px', width: '100%', margin: '0 auto', padding: '28px 20px' }}>
        {/* Active Context Banner: Global Dashboard vs Dedicated Website Control Center */}
        <div className="glass-card" style={{
          padding: '16px 22px',
          marginBottom: '26px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          border: currentSite ? '1px solid rgba(0, 240, 255, 0.35)' : '1px solid var(--border-subtle)',
          background: currentSite ? 'rgba(0, 240, 255, 0.04)' : 'rgba(255, 255, 255, 0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: currentSite 
                ? (currentSite.id === 1 ? 'linear-gradient(135deg, #00f0ff 0%, #6366f1 100%)' : 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)')
                : 'rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: currentSite ? '#041019' : '#cbd5e1'
            }}>
              <Globe size={20} />
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <h3 style={{ fontSize: '1.2rem', color: '#fff', margin: 0, fontWeight: '700' }}>
                  {currentSite ? `${currentSite.name} Control Center` : 'Global Multi-Site Dashboard'}
                </h3>
                {currentSite ? (
                  <>
                    <span className="badge badge-cyan" style={{ fontSize: '0.72rem' }}>
                      Isolated Site #{currentSite.id}
                    </span>
                    {currentSite.id === 1 && (
                      <span className="badge badge-indigo" style={{ fontSize: '0.68rem' }}>
                        Primary
                      </span>
                    )}
                  </>
                ) : (
                  <span className="badge badge-purple" style={{ fontSize: '0.72rem' }}>
                    All Websites ({sites.length} Active)
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px', fontSize: '0.8rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                {currentSite ? (
                  <>
                    <span>Target: <strong style={{ color: '#38bdf8' }}>{currentSite.wp_url}</strong></span>
                    <span>&bull;</span>
                    <span><strong style={{ color: '#00f0ff' }}>{displayTopics.length}</strong> Topics (Isolated)</span>
                    <span>&bull;</span>
                    <span><strong style={{ color: '#fbbf24' }}>{displayDrafts.length}</strong> Review Drafts</span>
                    <span>&bull;</span>
                    <span>Auto-Push: <strong>{currentSite.auto_push_to_wp ? 'Immediate' : 'Review Gate'}</strong></span>
                  </>
                ) : (
                  <span>Managing {sites.length} connected websites. Click any website below to enter its isolated control center.</span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {currentSite ? (
              <>
                <button
                  className="btn btn-secondary"
                  onClick={() => setSelectedSiteId(null)}
                  style={{ fontSize: '0.82rem', padding: '7px 14px' }}
                  title="Return to aggregated overview of all websites"
                >
                  <Layers size={14} /> Switch to All Websites
                </button>

                <button
                  className="btn btn-primary"
                  onClick={() => handleTriggerRun(null)}
                  style={{ fontSize: '0.82rem', padding: '7px 14px' }}
                  title={`Trigger automated article run for ${currentSite.name}`}
                >
                  <Sparkles size={14} /> Run for {currentSite.name}
                </button>
              </>
            ) : (
              <button
                className="btn btn-primary"
                onClick={() => setActiveTab('sites')}
                style={{ fontSize: '0.82rem', padding: '7px 14px' }}
              >
                <Globe size={14} /> Manage Connected Websites ({sites.length})
              </button>
            )}
          </div>
        </div>

        {activeTab === 'sites' && (
          <SiteManager 
            sites={sites} 
            selectedSiteId={selectedSiteId} 
            onSelectSite={(id, tab = 'topics') => {
              setSelectedSiteId(id);
              setActiveTab(tab);
            }} 
            onRefresh={fetchAllData} 
            onTriggerRun={handleTriggerRun} 
          />
        )}

        {activeTab === 'topics' && (
          <TopicManager 
            topics={displayTopics}
            selectedSiteId={selectedSiteId}
            sites={sites}
            settings={settings}
            onOpenCostModal={handleOpenCostModal}
            onSelectSite={(id, tab = 'topics') => {
              setSelectedSiteId(id);
              setActiveTab(tab);
            }}
            onRefresh={fetchAllData} 
            onTriggerRun={handleTriggerRun} 
          />
        )}

        {activeTab === 'rules' && (
          <ContentRulesEditor 
            rules={contentRules}
            siteName={currentSite?.name}
            onSaveRules={handleSaveContentRules} 
          />
        )}

        {activeTab === 'drafts' && (
          <DraftReviewQueue 
            drafts={displayDrafts} 
            settings={settings}
            onOpenCostModal={handleOpenCostModal}
            onSelectSite={(id, tab = 'drafts') => {
              setSelectedSiteId(id);
              setActiveTab(tab);
            }}
            onRefresh={fetchAllData} 
          />
        )}

        {activeTab === 'runs' && (
          <RunControlsAndLogs 
            topics={displayTopics}
            runLogs={selectedSiteId ? runLogs.filter(l => l.site_id === selectedSiteId) : runLogs}
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

      {/* Real-Time Token Economics & Full Pipeline Pricing Modal */}
      <CostBreakdownModal 
        isOpen={costModalOpen}
        onClose={() => setCostModalOpen(false)}
        topic={costModalTopic}
        draft={costModalDraft}
        settings={settings}
        onSaveSettings={handleSaveSettings}
        onNavigateSettings={() => setActiveTab('settings')}
        activeTopicsCount={displayTopics.filter(t => t.is_active).length}
      />

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
