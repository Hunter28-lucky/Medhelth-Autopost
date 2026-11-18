import React, { useState, useEffect } from 'react';
import { 
  Globe, Shield, CheckCircle2, AlertCircle, RefreshCw, 
  X, Layers, Server, Cpu, Download, ExternalLink, Check, Sparkles, Eye
} from 'lucide-react';
import { authFetch } from '../apiClient';

export default function SiteInspectorModal({ site, isOpen, onClose, onRefresh }) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('categories'); // 'categories', 'environment', 'plugins'
  const [syncingCategories, setSyncingCategories] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);

  const fetchInspection = async () => {
    if (!site?.id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`/api/sites/${site.id}/inspect`);
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || 'Failed to inspect website');
      }
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && site?.id) {
      fetchInspection();
      setSyncMessage(null);
    }
  }, [isOpen, site?.id]);

  const handleSyncCategories = async () => {
    if (!site?.id) return;
    setSyncingCategories(true);
    setSyncMessage(null);
    try {
      const res = await authFetch(`/api/sites/${site.id}/sync-categories`, { method: 'POST' });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || 'Failed to sync categories');
      }
      setSyncMessage({
        type: 'success',
        text: json.message || `Successfully synced ${json.newly_imported_topics} categories into topics!`
      });
      if (onRefresh) onRefresh();
    } catch (err) {
      setSyncMessage({ type: 'error', text: err.message });
    } finally {
      setSyncingCategories(false);
    }
  };

  if (!isOpen || !site) return null;

  const siteInfo = data?.site_info || {};
  const seoInfo = data?.seo_info || {};
  const taxonomy = data?.taxonomy || {};
  const postStats = data?.post_stats || {};
  const activePlugins = data?.active_plugins || [];
  const warnings = data?.warnings || [];
  const categories = taxonomy.categories || [];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.78)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-card" style={{
        maxWidth: '820px',
        width: '100%',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: '16px',
        border: '1px solid rgba(0, 240, 255, 0.4)',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(0, 240, 255, 0.15)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(255, 255, 255, 0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #00f0ff 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#041019',
              boxShadow: '0 0 16px rgba(0, 240, 255, 0.35)'
            }}>
              <Globe size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.25rem', color: '#fff', margin: 0, fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
                {site.name} <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', fontWeight: '400' }}>Site Intelligence</span>
              </h3>
              <a 
                href={site.wp_url} 
                target="_blank" 
                rel="noopener noreferrer" 
                style={{ color: '#38bdf8', fontSize: '0.78rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}
              >
                {site.wp_url} <ExternalLink size={11} />
              </a>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={fetchInspection}
              disabled={loading}
              className="btn btn-secondary"
              style={{ fontSize: '0.78rem', padding: '6px 12px' }}
              title="Re-run deep site diagnostics"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              {loading ? 'Inspecting...' : 'Re-Inspect'}
            </button>
            <button 
              onClick={onClose} 
              className="btn btn-ghost"
              style={{ padding: '6px 10px', fontSize: '1.2rem', lineHeight: 1, color: '#94a3b8' }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {loading && !data && (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <RefreshCw size={28} className="animate-spin" style={{ color: '#00f0ff', margin: '0 auto 12px auto' }} />
              <p style={{ fontSize: '0.92rem', color: '#fff' }}>Connecting to {site.name} REST endpoint...</p>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Auditing WordPress environment, active categories, Yoast SEO, and installed plugins
              </span>
            </div>
          )}

          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              padding: '14px 18px',
              borderRadius: '10px',
              color: '#fca5a5',
              fontSize: '0.86rem',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px'
            }}>
              <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ color: '#f87171', display: 'block', marginBottom: '4px' }}>
                  Inspection Failed
                </strong>
                <span>{error}</span>
                <p style={{ marginTop: '8px', fontSize: '0.78rem', color: '#cbd5e1' }}>
                  Make sure <strong>Pulse Content Sync v2.9.0</strong> is uploaded and activated in WordPress Admin under <em>Plugins &rarr; Installed Plugins</em>, and the Secret Key matches.
                </p>
              </div>
            </div>
          )}

          {data && (
            <>
              {/* Quick Metrics 4-Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
                {/* WordPress & PHP */}
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Server size={13} style={{ color: '#00f0ff' }} /> Core Environment
                  </span>
                  <div style={{ fontSize: '1.05rem', color: '#fff', fontWeight: '700', marginTop: '4px' }}>
                    WP {siteInfo.wordpress_version || 'Detected'}
                  </div>
                  <span style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                    PHP {siteInfo.php_version || '7.4+'} &bull; {siteInfo.is_ssl ? 'SSL Active' : 'HTTP'}
                  </span>
                </div>

                {/* Yoast SEO */}
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Shield size={13} style={{ color: seoInfo.yoast_active ? '#34d399' : '#fbbf24' }} /> Yoast SEO Engine
                  </span>
                  <div style={{ fontSize: '1.05rem', color: seoInfo.yoast_active ? '#34d399' : '#fbbf24', fontWeight: '700', marginTop: '4px' }}>
                    {seoInfo.yoast_active ? `v${seoInfo.yoast_version || '28.4'}` : 'Not Detected'}
                  </div>
                  <span style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                    {seoInfo.compliance_status || 'Auto-Optimized'}
                  </span>
                </div>

                {/* Total Categories */}
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Layers size={13} style={{ color: '#818cf8' }} /> Live Categories
                  </span>
                  <div style={{ fontSize: '1.05rem', color: '#818cf8', fontWeight: '700', marginTop: '4px' }}>
                    {taxonomy.total_categories || categories.length} Categories
                  </div>
                  <span style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                    Ready for 1-click sync
                  </span>
                </div>

                {/* Published & Drafts */}
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CheckCircle2 size={13} style={{ color: '#38bdf8' }} /> WordPress Posts
                  </span>
                  <div style={{ fontSize: '1.05rem', color: '#38bdf8', fontWeight: '700', marginTop: '4px' }}>
                    {postStats.published || 0} Live
                  </div>
                  <span style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                    {postStats.drafts || 0} Drafts in WP
                  </span>
                </div>
              </div>

              {/* Warnings Banner if any */}
              {warnings.length > 0 && (
                <div style={{
                  background: 'rgba(245, 158, 11, 0.1)',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  color: '#fbbf24',
                  fontSize: '0.8rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
                }}>
                  {warnings.map((w, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <AlertCircle size={14} style={{ flexShrink: 0 }} />
                      <span>{w}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Sync Success / Error Banner */}
              {syncMessage && (
                <div style={{
                  background: syncMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  border: syncMessage.type === 'success' ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(239, 68, 68, 0.4)',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  color: syncMessage.type === 'success' ? '#34d399' : '#f87171',
                  fontSize: '0.84rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  {syncMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                  <span>{syncMessage.text}</span>
                </div>
              )}

              {/* Navigation Tabs inside modal */}
              <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
                <button
                  type="button"
                  className={`btn btn-ghost ${activeTab === 'categories' ? 'btn-secondary' : ''}`}
                  onClick={() => setActiveTab('categories')}
                  style={{ fontSize: '0.82rem', padding: '6px 14px' }}
                >
                  <Layers size={14} /> Live WordPress Categories ({categories.length})
                </button>
                <button
                  type="button"
                  className={`btn btn-ghost ${activeTab === 'environment' ? 'btn-secondary' : ''}`}
                  onClick={() => setActiveTab('environment')}
                  style={{ fontSize: '0.82rem', padding: '6px 14px' }}
                >
                  <Server size={14} /> Environment & Server
                </button>
                <button
                  type="button"
                  className={`btn btn-ghost ${activeTab === 'plugins' ? 'btn-secondary' : ''}`}
                  onClick={() => setActiveTab('plugins')}
                  style={{ fontSize: '0.82rem', padding: '6px 14px' }}
                >
                  <Cpu size={14} /> Active Plugins ({activePlugins.length})
                </button>
              </div>

              {/* TAB 1: CATEGORIES */}
              {activeTab === 'categories' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      These categories are pulled in real-time from <strong>{site.name}</strong>. Syncing them guarantees articles are automatically assigned to the right WordPress category.
                    </p>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleSyncCategories}
                      disabled={syncingCategories || categories.length === 0}
                      style={{ padding: '6px 16px', fontSize: '0.82rem' }}
                    >
                      <Sparkles size={14} />
                      {syncingCategories ? 'Syncing...' : `Sync All ${categories.length} to Topics`}
                    </button>
                  </div>

                  {categories.length > 0 ? (
                    <div style={{
                      maxHeight: '320px',
                      overflowY: 'auto',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '10px',
                      padding: '8px',
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                      gap: '8px'
                    }}>
                      {categories.map(cat => (
                        <div
                          key={cat.id}
                          style={{
                            background: 'rgba(255, 255, 255, 0.02)',
                            border: '1px solid rgba(255, 255, 255, 0.06)',
                            padding: '8px 12px',
                            borderRadius: '8px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                          }}
                        >
                          <div>
                            <strong style={{ color: '#fff', fontSize: '0.84rem', display: 'block' }}>
                              {cat.name}
                            </strong>
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                              slug: {cat.slug}
                            </span>
                          </div>
                          <span className="badge badge-cyan" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                            {cat.count} posts
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                      No categories returned from WordPress. Make sure the updated <strong>Pulse Content Sync v2.9.0</strong> plugin is uploaded and active on {site.name}.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: ENVIRONMENT */}
              {activeTab === 'environment' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', fontSize: '0.82rem' }}>
                  <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>WordPress Site Name</span>
                    <strong style={{ color: '#fff', fontSize: '0.92rem' }}>{siteInfo.name || site.name}</strong>
                  </div>

                  <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>WordPress Version</span>
                    <strong style={{ color: '#00f0ff', fontSize: '0.92rem' }}>{siteInfo.wordpress_version || 'Unknown'}</strong>
                  </div>

                  <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>PHP Runtime Version</span>
                    <strong style={{ color: '#34d399', fontSize: '0.92rem' }}>{siteInfo.php_version || 'Unknown'}</strong>
                  </div>

                  <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Web Server Software</span>
                    <strong style={{ color: '#fff', fontSize: '0.92rem' }}>{siteInfo.server_software || 'Apache/Nginx'}</strong>
                  </div>

                  <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Permalink Structure</span>
                    <strong style={{ color: '#fff', fontSize: '0.92rem' }}>{siteInfo.permalink_structure || 'Default'}</strong>
                  </div>

                  <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>PHP Memory Limit</span>
                    <strong style={{ color: '#fff', fontSize: '0.92rem' }}>{siteInfo.memory_limit || '256M'}</strong>
                  </div>

                  <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Max Upload File Size</span>
                    <strong style={{ color: '#fff', fontSize: '0.92rem' }}>{siteInfo.upload_max_filesize || '64M'}</strong>
                  </div>

                  <div style={{ background: 'var(--bg-surface)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Timezone & Locale</span>
                    <strong style={{ color: '#fff', fontSize: '0.92rem' }}>{siteInfo.timezone || 'UTC'} ({siteInfo.locale || 'en_US'})</strong>
                  </div>
                </div>
              )}

              {/* TAB 3: ACTIVE PLUGINS */}
              {activeTab === 'plugins' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    Audit of plugins currently active on <strong>{site.name}</strong>. Useful for verifying Yoast SEO and caching compatibility.
                  </p>
                  <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '8px' }}>
                    {activePlugins.length > 0 ? (
                      <table style={{ width: '100%', fontSize: '0.82rem', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                            <th style={{ padding: '8px' }}>Plugin Name</th>
                            <th style={{ padding: '8px' }}>Version</th>
                            <th style={{ padding: '8px' }}>Author</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activePlugins.map((p, idx) => (
                            <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                              <td style={{ padding: '8px', color: '#fff', fontWeight: '600' }}>
                                {p.name}
                                {p.name.includes('Yoast') && (
                                  <span className="badge badge-emerald" style={{ marginLeft: '8px', fontSize: '0.65rem' }}>
                                    SEO Active
                                  </span>
                                )}
                              </td>
                              <td style={{ padding: '8px', color: '#00f0ff', fontFamily: 'var(--font-mono)' }}>
                                {p.version}
                              </td>
                              <td style={{ padding: '8px', color: 'var(--text-muted)' }}>
                                {p.author}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                        No plugin data reported. Please upload <strong>Pulse Content Sync v2.9.0</strong> to unlock plugin auditing.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border-subtle)',
          background: 'rgba(255, 255, 255, 0.02)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <Shield size={14} style={{ color: '#00f0ff' }} />
            <span>Pulse Content Sync Connector: <strong>v{data?.plugin_version || '2.9.0'}</strong></span>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <a
              href="/api/download-plugin"
              download="pulse-content-sync.zip"
              className="btn btn-secondary"
              style={{ fontSize: '0.78rem', padding: '6px 14px', textDecoration: 'none' }}
            >
              <Download size={13} /> Download Updated v2.9.0 Plugin .ZIP
            </a>
            <button
              onClick={onClose}
              className="btn btn-primary"
              style={{ fontSize: '0.78rem', padding: '6px 16px' }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
