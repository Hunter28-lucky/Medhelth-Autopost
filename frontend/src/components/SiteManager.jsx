import React, { useState } from 'react';
import { 
  Globe, Plus, CheckCircle2, AlertCircle, RefreshCw, 
  ExternalLink, Layers, FileText, Send, Sparkles, 
  Settings2, Trash2, Key, Check, Shield, Clock, HelpCircle
} from 'lucide-react';
import { authFetch } from '../apiClient';

export default function SiteManager({ 
  sites, 
  selectedSiteId, 
  onSelectSite, 
  onRefresh, 
  onTriggerRun 
}) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSite, setEditingSite] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [testingSiteId, setTestingSiteId] = useState(null);
  const [seedingPresetSiteId, setSeedingPresetSiteId] = useState(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState('');

  // New Site Form state
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    wp_url: '',
    wp_api_key: '',
    description: '',
    auto_push_to_wp: false,
    is_scheduler_enabled: false,
    preset: 'none'
  });

  const [modalTesting, setModalTesting] = useState(false);
  const [modalTestResult, setModalTestResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const showNotification = (msg) => {
    setActionSuccessMsg(msg);
    setTimeout(() => setActionSuccessMsg(''), 3500);
  };

  const handleTestConnection = async (siteId) => {
    setTestingSiteId(siteId);
    try {
      const res = await authFetch(`/api/sites/${siteId}/test-wordpress`, { method: 'POST' });
      const data = await res.json();
      setTestResults(prev => ({ ...prev, [siteId]: data }));
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [siteId]: { connected: false, message: 'Network error contacting backend: ' + err.message }
      }));
    } finally {
      setTestingSiteId(null);
    }
  };

  const handleTestModalConnection = async () => {
    if (!formData.wp_url || !formData.wp_api_key) {
      alert('Please enter both the WordPress URL and API Key first.');
      return;
    }
    setModalTesting(true);
    setModalTestResult(null);
    try {
      const res = await authFetch('/api/settings/test-wordpress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wordpress_url: formData.wp_url,
          wordpress_api_key: formData.wp_api_key
        })
      });
      const data = await res.json();
      setModalTestResult(data);
    } catch (err) {
      setModalTestResult({ connected: false, message: err.message });
    } finally {
      setModalTesting(false);
    }
  };

  const handleCreateSite = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        name: formData.name.trim(),
        slug: formData.slug.trim() || undefined,
        wp_url: formData.wp_url.trim(),
        wp_api_key: formData.wp_api_key.trim(),
        description: formData.description.trim() || undefined,
        auto_push_to_wp: formData.auto_push_to_wp,
        is_scheduler_enabled: formData.is_scheduler_enabled,
        schedule_interval_hours: 6
      };

      const res = await authFetch('/api/sites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const newSite = await res.json();
      if (!res.ok) throw new Error(newSite.detail || 'Failed to create website');

      // Seed preset topics if requested
      if (formData.preset && formData.preset !== 'none') {
        await authFetch(`/api/sites/${newSite.id}/seed-presets?preset_type=${formData.preset}`, {
          method: 'POST'
        });
      }

      setShowAddModal(false);
      setFormData({
        name: '', slug: '', wp_url: '', wp_api_key: '',
        description: '', auto_push_to_wp: false,
        is_scheduler_enabled: false, preset: 'none'
      });
      setModalTestResult(null);
      showNotification(`Successfully connected website: ${newSite.name}!`);
      onRefresh();
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateSite = async (e) => {
    e.preventDefault();
    if (!editingSite) return;
    setIsSubmitting(true);
    try {
      const payload = {
        name: editingSite.name,
        wp_url: editingSite.wp_url,
        description: editingSite.description,
        auto_push_to_wp: editingSite.auto_push_to_wp,
        is_scheduler_enabled: editingSite.is_scheduler_enabled,
        schedule_interval_hours: editingSite.schedule_interval_hours
      };
      if (editingSite.new_wp_api_key) {
        payload.wp_api_key = editingSite.new_wp_api_key;
      }

      const res = await authFetch(`/api/sites/${editingSite.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update website');

      setEditingSite(null);
      showNotification(`Website updated successfully: ${data.name}`);
      onRefresh();
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteSite = async (site) => {
    if (site.id === 1) {
      alert('The Primary Site (MedHealth Times) cannot be deleted.');
      return;
    }
    const confirm = window.confirm(`Are you sure you want to remove "${site.name}" and all its assigned topics and drafts?`);
    if (!confirm) return;

    try {
      const res = await authFetch(`/api/sites/${site.id}`, { method: 'DELETE' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to delete website');
      }
      showNotification(`Removed website: ${site.name}`);
      if (selectedSiteId === site.id) {
        onSelectSite(1);
      }
      onRefresh();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  const handleSeedPresets = async (siteId, presetType) => {
    setSeedingPresetSiteId(siteId);
    try {
      const res = await authFetch(`/api/sites/${siteId}/seed-presets?preset_type=${presetType}`, {
        method: 'POST'
      });
      const data = await res.json();
      showNotification(`Seeded ${data.created_topics_count} starter topics for ${data.site_name}!`);
      onRefresh();
    } catch (err) {
      alert('Failed to seed preset topics: ' + err.message);
    } finally {
      setSeedingPresetSiteId(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.6rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '12px', fontWeight: '700' }}>
            Multi-Site Publishing Hub
            <span className="badge badge-cyan" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
              Multi-Tenant Isolation
            </span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
            Control posting across multiple distinct websites. Each website has isolated categories, tone guidelines, review queues, and WordPress stealth connectors.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            className="btn btn-secondary" 
            onClick={onRefresh}
            title="Refresh sites list and status"
          >
            <RefreshCw size={15} /> Refresh
          </button>
          <button 
            className="btn btn-primary" 
            onClick={() => setShowAddModal(true)}
            style={{ padding: '8px 18px' }}
          >
            <Plus size={16} /> Connect New Website
          </button>
        </div>
      </div>

      {/* Success Notification Alert */}
      {actionSuccessMsg && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.4)',
          color: '#34d399',
          padding: '12px 18px',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '0.9rem'
        }}>
          <CheckCircle2 size={18} />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {/* System-Grade Safety & Additive-Only Assurance Banner */}
      <div style={{
        background: 'rgba(16, 185, 129, 0.08)',
        border: '1px solid rgba(16, 185, 129, 0.25)',
        borderRadius: '10px',
        padding: '14px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: '14px'
      }}>
        <Shield size={24} style={{ color: '#10b981', flexShrink: 0 }} />
        <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.5' }}>
          <strong style={{ color: '#34d399' }}>System-Grade Safety Protocol (Additive-Only Guarantee):</strong>
          {' '}All connected WordPress sites are protected with strict zero-mutation guardrails. PulsePublish only creates isolated draft posts (<code>{"post_status => 'draft'"}</code>). It has <strong>no delete or edit permissions</strong> over your existing posts, manually written articles, pages, or WordPress database records. Your website remains completely safe and untouched.
        </div>
      </div>

      {/* Plugin Download Notice Banner */}
      <div className="glass-card" style={{ padding: '16px 20px', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.25)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Shield size={22} style={{ color: '#818cf8', flexShrink: 0 }} />
          <div>
            <h4 style={{ color: '#fff', fontSize: '0.92rem', fontWeight: '600' }}>
              Stealth Connector Plugin (v2.8.4 by Krish Goswami)
            </h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: 0 }}>
              Install this plugin on any WordPress site you connect. It establishes the secure REST endpoint and bypasses host firewalls.
            </p>
          </div>
        </div>
        <a 
          href="/api/download-plugin" 
          className="btn btn-secondary"
          style={{ fontSize: '0.82rem', padding: '6px 14px', textDecoration: 'none' }}
        >
          Download Plugin Zip
        </a>
      </div>

      {/* Websites Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: '22px' }}>
        {sites.map(site => {
          const isSelected = selectedSiteId === site.id;
          const isPrimary = site.id === 1;
          const testResult = testResults[site.id];

          return (
            <div 
              key={site.id} 
              className="glass-card"
              style={{
                padding: '24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '18px',
                position: 'relative',
                border: isSelected ? '1px solid #00f0ff' : '1px solid var(--border-subtle)',
                boxShadow: isSelected ? '0 0 20px rgba(0, 240, 255, 0.15)' : 'var(--shadow-card)'
              }}
            >
              {/* Card Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '10px',
                    background: isPrimary 
                      ? 'linear-gradient(135deg, #00f0ff 0%, #6366f1 100%)' 
                      : 'linear-gradient(135deg, #6366f1 0%, #ec4899 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#041019',
                    fontWeight: 'bold',
                    boxShadow: isPrimary ? '0 0 12px rgba(0, 240, 255, 0.3)' : '0 0 12px rgba(99, 102, 241, 0.3)'
                  }}>
                    <Globe size={22} />
                  </div>
                  <div>
                    <h3 
                      style={{ fontSize: '1.15rem', color: '#fff', fontWeight: '700', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
                      onClick={() => onSelectSite(site.id, 'topics')}
                      title={`Open ${site.name} Control Center`}
                    >
                      {site.name}
                      {isPrimary && (
                        <span className="badge badge-cyan" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                          Primary
                        </span>
                      )}
                    </h3>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      slug: {site.slug}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '6px' }}>
                  {isSelected ? (
                    <span className="badge badge-cyan" style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 8px' }}>
                      <Check size={12} /> Active Focus
                    </span>
                  ) : (
                    <button
                      className="btn btn-ghost"
                      onClick={() => onSelectSite(site.id, 'topics')}
                      style={{ fontSize: '0.78rem', padding: '4px 10px' }}
                      title="Set active site focus for the entire dashboard"
                    >
                      Focus Site
                    </button>
                  )}
                </div>
              </div>

              {/* Description */}
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0, minHeight: '38px' }}>
                {site.description || 'No niche description provided.'}
              </p>

              {/* WordPress Endpoint & Key */}
              <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Globe size={13} /> WP Target:
                  </span>
                  <a 
                    href={site.wp_url} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    style={{ color: '#38bdf8', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  >
                    {site.wp_url} <ExternalLink size={11} />
                  </a>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Key size={13} /> Stealth Key:
                  </span>
                  <span style={{ color: '#cbd5e1', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                    {site.wp_api_key_masked}
                  </span>
                </div>
              </div>

              {/* Metrics Pill Row - Interactive direct links */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                <div 
                  onClick={() => onSelectSite(site.id, 'topics')}
                  style={{ 
                    background: 'rgba(255, 255, 255, 0.03)', 
                    padding: '10px', 
                    borderRadius: '8px', 
                    border: '1px solid var(--border-subtle)', 
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'border-color 0.2s, background 0.2s'
                  }}
                  title={`Click to view and manage topics for ${site.name}`}
                >
                  <div style={{ fontSize: '1.25rem', color: '#00f0ff', fontWeight: '700' }}>
                    {site.topics_count}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', marginTop: '2px' }}>
                    <Layers size={11} /> Topics &rarr;
                  </div>
                </div>

                <div 
                  onClick={() => onSelectSite(site.id, 'drafts')}
                  style={{ 
                    background: 'rgba(255, 255, 255, 0.03)', 
                    padding: '10px', 
                    borderRadius: '8px', 
                    border: '1px solid var(--border-subtle)', 
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'border-color 0.2s, background 0.2s'
                  }}
                  title={`Click to view review queue for ${site.name}`}
                >
                  <div style={{ fontSize: '1.25rem', color: site.drafts_count > 0 ? '#fbbf24' : '#fff', fontWeight: '700' }}>
                    {site.drafts_count}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', marginTop: '2px' }}>
                    <FileText size={11} /> Review &rarr;
                  </div>
                </div>

                <div 
                  onClick={() => onSelectSite(site.id, 'drafts')}
                  style={{ 
                    background: 'rgba(255, 255, 255, 0.03)', 
                    padding: '10px', 
                    borderRadius: '8px', 
                    border: '1px solid var(--border-subtle)', 
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'border-color 0.2s, background 0.2s'
                  }}
                  title={`Click to view published posts for ${site.name}`}
                >
                  <div style={{ fontSize: '1.25rem', color: '#34d399', fontWeight: '700' }}>
                    {site.published_count}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', marginTop: '2px' }}>
                    <Send size={11} /> Live WP
                  </div>
                </div>
              </div>

              {/* Main CTA: Enter Website Control Center */}
              <button
                className="btn btn-primary"
                onClick={() => onSelectSite(site.id, 'topics')}
                style={{ 
                  width: '100%', 
                  justifyContent: 'center', 
                  padding: '10px 14px', 
                  fontSize: '0.86rem',
                  fontWeight: '600'
                }}
                title={`Open dedicated control page for ${site.name}`}
              >
                <Sliders size={15} /> Enter {site.name} Control Center &rarr;
              </button>

              {/* Config Badges */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span className={`badge ${site.auto_push_to_wp ? 'badge-emerald' : 'badge-amber'}`} style={{ fontSize: '0.72rem' }}>
                  Auto-Push: {site.auto_push_to_wp ? 'Immediate Draft' : 'Review Gate'}
                </span>
                <span className={`badge ${site.is_scheduler_enabled ? 'badge-indigo' : 'badge-muted'}`} style={{ fontSize: '0.72rem' }}>
                  <Clock size={11} style={{ marginRight: '4px' }} />
                  Cron: {site.is_scheduler_enabled ? `Every ${site.schedule_interval_hours}h` : 'Disabled (Safe)'}
                </span>
              </div>

              {/* Test Result Display if ran */}
              {testResult && (
                <div style={{
                  padding: '10px 14px',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  background: testResult.connected ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
                  border: testResult.connected ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(244, 63, 94, 0.3)',
                  color: testResult.connected ? '#34d399' : '#f87171',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  {testResult.connected ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                  <span>{testResult.message}</span>
                </div>
              )}

              {/* Action Buttons Toolbar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', marginTop: 'auto', gap: '8px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleTestConnection(site.id)}
                    disabled={testingSiteId === site.id}
                    style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                    title="Ping WordPress health endpoint"
                  >
                    {testingSiteId === site.id ? <RefreshCw size={13} className="spin" /> : <Globe size={13} />}
                    Test Health
                  </button>

                  <button
                    className="btn btn-secondary"
                    onClick={() => onSelectSite(site.id, 'rules')}
                    style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                    title="Configure content directives for this website"
                  >
                    <Sliders size={13} /> Rules
                  </button>

                  <button
                    className="btn btn-ghost"
                    onClick={() => setEditingSite({ ...site, new_wp_api_key: '' })}
                    style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                    title="Edit site configuration"
                  >
                    <Settings2 size={13} /> Edit
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {site.topics_count === 0 && (
                    <select
                      onChange={(e) => {
                        if (e.target.value) handleSeedPresets(site.id, e.target.value);
                      }}
                      disabled={seedingPresetSiteId === site.id}
                      style={{
                        background: 'var(--bg-surface)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px',
                        fontSize: '0.76rem',
                        padding: '5px 8px'
                      }}
                      defaultValue=""
                    >
                      <option value="" disabled>+ Add Presets...</option>
                      <option value="tech_ai">AI & Tech (5)</option>
                      <option value="finance_crypto">Finance & Crypto (5)</option>
                      <option value="clean_energy">Clean Energy (5)</option>
                      <option value="lifestyle">Lifestyle & Longevity (5)</option>
                    </select>
                  )}

                  {!isPrimary && (
                    <button
                      className="btn btn-ghost"
                      onClick={() => handleDeleteSite(site)}
                      style={{ color: '#f87171', padding: '6px', minWidth: '32px' }}
                      title="Delete website and isolated data"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* MODAL: Connect New Website */}
      {showAddModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="glass-card" style={{ maxWidth: '580px', width: '100%', padding: '28px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.3rem', color: '#fff', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Plus size={20} color="#00f0ff" /> Connect Additional Website
              </h3>
              <button 
                onClick={() => setShowAddModal(false)}
                className="btn btn-ghost"
                style={{ padding: '4px 8px', fontSize: '1.2rem', lineHeight: 1 }}
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateSite} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Website Name *
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. TechPulse AI, GreenTech Chronicle"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  WordPress Site Base URL *
                </label>
                <input
                  type="url"
                  className="form-input"
                  placeholder="e.g. https://techpulse.ai or http://example.com/site2"
                  value={formData.wp_url}
                  onChange={e => setFormData({ ...formData, wp_url: e.target.value })}
                  required
                />
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Must have the stealth Pulse Content Sync plugin activated.
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  WordPress Stealth API Key (`X-Pulse-Sync-Key`) *
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Secret key generated in WP Admin -> Settings -> Pulse Sync"
                  value={formData.wp_api_key}
                  onChange={e => setFormData({ ...formData, wp_api_key: e.target.value })}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Niche & Focus Description
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Enterprise AI, Cloud Infrastructure, Machine Learning Breakthroughs"
                  value={formData.description}
                  onChange={e => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Starter Topics Preset (Optional)
                </label>
                <select
                  className="form-input"
                  value={formData.preset}
                  onChange={e => setFormData({ ...formData, preset: e.target.value })}
                >
                  <option value="none">None (I will configure topics manually)</option>
                  <option value="tech_ai">Artificial Intelligence & Tech (5 topics)</option>
                  <option value="finance_crypto">Finance, DeFi & Crypto (5 topics)</option>
                  <option value="clean_energy">Clean Energy & Sustainability (5 topics)</option>
                  <option value="lifestyle">Health & Longevity (5 topics)</option>
                </select>
              </div>

              {/* Safety Toggles */}
              <div style={{ background: 'var(--bg-surface)', padding: '14px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '12px', border: '1px solid var(--border-subtle)' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: '#fff', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={formData.auto_push_to_wp}
                    onChange={e => setFormData({ ...formData, auto_push_to_wp: e.target.checked })}
                  />
                  Auto-push passing drafts to WordPress as Drafts (Default: Hold in Review Gate)
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: '#fff', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={formData.is_scheduler_enabled}
                    onChange={e => setFormData({ ...formData, is_scheduler_enabled: e.target.checked })}
                  />
                  Enable background cron scheduler for this site (Default: OFF for testing)
                </label>
              </div>

              {/* Modal Test Result */}
              {modalTestResult && (
                <div style={{
                  padding: '10px',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  background: modalTestResult.connected ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
                  color: modalTestResult.connected ? '#34d399' : '#f87171',
                  border: modalTestResult.connected ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(244, 63, 94, 0.3)'
                }}>
                  {modalTestResult.message}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleTestModalConnection}
                  disabled={modalTesting}
                  style={{ fontSize: '0.82rem' }}
                >
                  {modalTesting ? 'Testing...' : 'Test Connection'}
                </button>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setShowAddModal(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Connecting...' : 'Connect Website'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Edit Website */}
      {editingSite && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="glass-card" style={{ maxWidth: '560px', width: '100%', padding: '28px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.25rem', color: '#fff', fontWeight: '700' }}>
                Edit Website: {editingSite.name}
              </h3>
              <button 
                onClick={() => setEditingSite(null)}
                className="btn btn-ghost"
                style={{ padding: '4px 8px', fontSize: '1.2rem', lineHeight: 1 }}
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleUpdateSite} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Website Name
                </label>
                <input
                  type="text"
                  className="form-input"
                  value={editingSite.name}
                  onChange={e => setEditingSite({ ...editingSite, name: e.target.value })}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  WordPress URL
                </label>
                <input
                  type="url"
                  className="form-input"
                  value={editingSite.wp_url}
                  onChange={e => setEditingSite({ ...editingSite, wp_url: e.target.value })}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Change API Key (Leave empty to keep existing)
                </label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="Enter new secret key or leave blank"
                  value={editingSite.new_wp_api_key || ''}
                  onChange={e => setEditingSite({ ...editingSite, new_wp_api_key: e.target.value })}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Niche Description
                </label>
                <input
                  type="text"
                  className="form-input"
                  value={editingSite.description || ''}
                  onChange={e => setEditingSite({ ...editingSite, description: e.target.value })}
                />
              </div>

              <div style={{ background: 'var(--bg-surface)', padding: '14px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: '#fff', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={editingSite.auto_push_to_wp}
                    onChange={e => setEditingSite({ ...editingSite, auto_push_to_wp: e.target.checked })}
                  />
                  Auto-push drafts directly to WordPress
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: '#fff', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={editingSite.is_scheduler_enabled}
                    onChange={e => setEditingSite({ ...editingSite, is_scheduler_enabled: e.target.checked })}
                  />
                  Enable background cron schedule for this site
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setEditingSite(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
