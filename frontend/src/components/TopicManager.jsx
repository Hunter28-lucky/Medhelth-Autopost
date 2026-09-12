import React, { useState } from 'react';
import { 
  Plus, Upload, Play, Edit3, Trash2, Globe, ShieldAlert, CheckCircle2, 
  Search, X, AlertCircle 
} from 'lucide-react';

export default function TopicManager({ topics, selectedSiteId, sites = [], onRefresh, onTriggerRun }) {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isBulkOpen, setIsBulkOpen] = useState(false);
  const [editingTopic, setEditingTopic] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');

  // Add / Edit form state
  const [formData, setFormData] = useState({
    name: '',
    keywords: '',
    weight: 5,
    is_active: true,
    domain_whitelist: '',
    domain_blocklist: '',
    lookback_days: 7,
    site_id: selectedSiteId ? parseInt(selectedSiteId, 10) : (sites[0]?.id || 1)
  });

  // Bulk import state
  const [bulkText, setBulkText] = useState('');
  const [bulkSiteId, setBulkSiteId] = useState(selectedSiteId ? parseInt(selectedSiteId, 10) : (sites[0]?.id || 1));
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkMessage, setBulkMessage] = useState(null);

  const openAddModal = () => {
    setEditingTopic(null);
    setFormData({
      name: '',
      keywords: '',
      weight: 5,
      is_active: true,
      domain_whitelist: '',
      domain_blocklist: '',
      lookback_days: 7,
      site_id: selectedSiteId ? parseInt(selectedSiteId, 10) : (sites[0]?.id || 1)
    });
    setIsAddOpen(true);
  };

  const openEditModal = (topic) => {
    setEditingTopic(topic);
    setFormData({
      name: topic.name,
      keywords: (topic.keywords || []).join(', '),
      weight: topic.weight,
      is_active: topic.is_active,
      domain_whitelist: (topic.domain_whitelist || []).join(', '),
      domain_blocklist: (topic.domain_blocklist || []).join(', '),
      lookback_days: topic.lookback_days || 7,
      site_id: topic.site_id || (selectedSiteId ? parseInt(selectedSiteId, 10) : (sites[0]?.id || 1))
    });
    setIsAddOpen(true);
  };

  const handleSaveTopic = async (e) => {
    e.preventDefault();
    const targetSiteId = formData.site_id ? parseInt(formData.site_id, 10) : (selectedSiteId ? parseInt(selectedSiteId, 10) : (sites[0]?.id || 1));
    const payload = {
      name: formData.name.trim(),
      keywords: formData.keywords.split(',').map(k => k.trim()).filter(Boolean),
      weight: parseInt(formData.weight, 10),
      is_active: formData.is_active,
      domain_whitelist: formData.domain_whitelist.split(',').map(d => d.trim()).filter(Boolean),
      domain_blocklist: formData.domain_blocklist.split(',').map(d => d.trim()).filter(Boolean),
      lookback_days: parseInt(formData.lookback_days, 10),
      site_id: targetSiteId
    };

    try {
      if (editingTopic) {
        await fetch(`/api/topics/${editingTopic.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetch('/api/topics', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      setIsAddOpen(false);
      onRefresh();
    } catch (err) {
      alert('Failed to save topic: ' + err.message);
    }
  };

  const handleDelete = async (topicId) => {
    if (!window.confirm('Delete this topic category? Generated historical posts will remain intact.')) return;
    try {
      await fetch(`/api/topics/${topicId}`, { method: 'DELETE' });
      onRefresh();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  const handleToggleActive = async (topic, currentStatus) => {
    try {
      await fetch(`/api/topics/${topic.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentStatus })
      });
      onRefresh();
    } catch (err) {
      alert('Toggle failed: ' + err.message);
    }
  };

  const handleBulkImport = async () => {
    if (!bulkText.trim()) return;
    setBulkLoading(true);
    setBulkMessage(null);
    const targetSiteId = bulkSiteId ? parseInt(bulkSiteId, 10) : (selectedSiteId ? parseInt(selectedSiteId, 10) : (sites[0]?.id || 1));
    try {
      const res = await fetch('/api/topics/bulk-import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: bulkText, site_id: targetSiteId })
      });
      const data = await res.json();
      setBulkMessage({ type: 'success', text: `Imported / updated ${data.length} topic categories!` });
      setTimeout(() => {
        setIsBulkOpen(false);
        setBulkText('');
        setBulkMessage(null);
        onRefresh();
      }, 1200);
    } catch (err) {
      setBulkMessage({ type: 'error', text: 'Bulk import failed: ' + err.message });
    } finally {
      setBulkLoading(false);
    }
  };

  const filteredTopics = topics.filter(t => 
    t.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
    (t.keywords || []).some(k => k.toLowerCase().includes(searchFilter.toLowerCase()))
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            Topic Categories <span className="badge badge-cyan">{topics.length} Configured</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Manage medical/AI research subjects, prioritized weighting, and search keywords.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ position: 'relative', width: '220px' }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '12px', color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              className="form-input" 
              placeholder="Search topics..."
              style={{ paddingLeft: '32px' }}
              value={searchFilter}
              onChange={e => setSearchFilter(e.target.value)}
            />
          </div>

          <button className="btn btn-secondary" onClick={() => setIsBulkOpen(true)}>
            <Upload size={16} /> Bulk Paste
          </button>
          
          <button className="btn btn-primary" onClick={openAddModal}>
            <Plus size={16} /> Add Topic
          </button>
        </div>
      </div>

      {/* Topics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' }}>
        {filteredTopics.map(topic => (
          <div key={topic.id} className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <h3 style={{ fontSize: '1.15rem', color: '#fff', marginBottom: '4px' }}>{topic.name}</h3>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <span className="badge badge-indigo">Weight: {topic.weight}/10</span>
                    <span className="badge badge-cyan">{topic.lookback_days}d Window</span>
                    {topic.site_name && (
                      <span className="badge badge-purple" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Globe size={11} /> {topic.site_name}
                      </span>
                    )}
                  </div>
                </div>

                <label className="toggle-switch" title={topic.is_active ? 'Topic Active' : 'Topic Inactive'}>
                  <input 
                    type="checkbox" 
                    checked={topic.is_active} 
                    onChange={() => handleToggleActive(topic, topic.is_active)} 
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>

              {/* Keywords */}
              <div style={{ marginBottom: '14px' }}>
                <span className="form-label" style={{ fontSize: '0.7rem', marginBottom: '4px' }}>Search Keywords</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {(topic.keywords || []).map((kw, i) => (
                    <span key={i} style={{ background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', color: '#cbd5e1' }}>
                      {kw}
                    </span>
                  ))}
                  {(!topic.keywords || topic.keywords.length === 0) && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Using topic name as default search</span>
                  )}
                </div>
              </div>

              {/* Whitelist / Blocklist counts */}
              <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Globe size={14} style={{ color: '#10b981' }} />
                  {topic.domain_whitelist?.length || 0} Trusted Domains
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <ShieldAlert size={14} style={{ color: '#f43f5e' }} />
                  {topic.domain_blocklist?.length || 0} Blocked
                </span>
              </div>
            </div>

            {/* Card Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '14px' }}>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button 
                  className="btn btn-ghost" 
                  style={{ padding: '6px 10px' }} 
                  onClick={() => openEditModal(topic)}
                  title="Edit Topic"
                >
                  <Edit3 size={15} />
                </button>
                <button 
                  className="btn btn-ghost" 
                  style={{ padding: '6px 10px', color: '#f43f5e' }} 
                  onClick={() => handleDelete(topic.id)}
                  title="Delete Topic"
                >
                  <Trash2 size={15} />
                </button>
              </div>

              <button 
                className="btn btn-secondary" 
                style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                onClick={() => onTriggerRun(topic.id)}
                disabled={!topic.is_active}
              >
                <Play size={14} style={{ color: '#00f0ff' }} /> Run Now
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add / Edit Modal */}
      {isAddOpen && (
        <div className="modal-overlay">
          <div className="modal-container" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.25rem', color: '#fff' }}>
                {editingTopic ? 'Edit Topic Category' : 'Add New Topic Category'}
              </h3>
              <button className="btn btn-ghost" onClick={() => setIsAddOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveTopic}>
              {sites.length > 0 && (
                <div className="form-group">
                  <label className="form-label">Target Website</label>
                  <select 
                    className="form-input"
                    value={formData.site_id || (selectedSiteId ? parseInt(selectedSiteId, 10) : (sites[0]?.id || 1))}
                    onChange={e => setFormData({ ...formData, site_id: parseInt(e.target.value, 10) })}
                  >
                    {sites.map(s => (
                      <option key={s.id} value={s.id} style={{ background: '#1e293b', color: '#fff' }}>
                        {s.name} ({s.wp_url})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Topic Name</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="e.g., AI in Diagnostics, Cardiology Breakthroughs"
                  required
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Search Keywords / Phrases (Comma-separated)</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="medical imaging AI, CT scan deep learning, radiomics"
                  value={formData.keywords}
                  onChange={e => setFormData({ ...formData, keywords: e.target.value })}
                />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Used by the search engine to retrieve recent stories.
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="form-group">
                  <label className="form-label">Priority Weight: {formData.weight} (1-10)</label>
                  <input 
                    type="range" 
                    min="1" 
                    max="10" 
                    className="range-slider"
                    value={formData.weight}
                    onChange={e => setFormData({ ...formData, weight: e.target.value })}
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Higher weight = picked more often in automated schedule.
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label">Lookback Window: {formData.lookback_days} Days</label>
                  <input 
                    type="range" 
                    min="1" 
                    max="30" 
                    className="range-slider"
                    value={formData.lookback_days}
                    onChange={e => setFormData({ ...formData, lookback_days: e.target.value })}
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    How far back in time the search engine queries.
                  </span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Domain Whitelist (Optional, comma-separated)</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="nature.com, nejm.org, thelancet.com"
                  value={formData.domain_whitelist}
                  onChange={e => setFormData({ ...formData, domain_whitelist: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Domain Blocklist (Optional, comma-separated)</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="spam-health.com, clickbait.net"
                  value={formData.domain_blocklist}
                  onChange={e => setFormData({ ...formData, domain_blocklist: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsAddOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Topic
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk Paste Modal */}
      {isBulkOpen && (
        <div className="modal-overlay">
          <div className="modal-container" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', color: '#fff' }}>Bulk Topic Import</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Paste multiple topics with optional keywords in one go.
                </p>
              </div>
              <button className="btn btn-ghost" onClick={() => setIsBulkOpen(false)}>
                <X size={18} />
              </button>
            </div>

            {sites.length > 0 && (
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label className="form-label">Target Website for Import</label>
                <select 
                  className="form-input"
                  value={bulkSiteId || (selectedSiteId ? parseInt(selectedSiteId, 10) : (sites[0]?.id || 1))}
                  onChange={e => setBulkSiteId(parseInt(e.target.value, 10))}
                >
                  {sites.map(s => (
                    <option key={s.id} value={s.id} style={{ background: '#1e293b', color: '#fff' }}>
                      {s.name} ({s.wp_url})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Paste List (Format: Topic Name: kw1, kw2, kw3)</label>
              <textarea 
                className="form-textarea" 
                rows="8" 
                placeholder={`AI in Diagnostics: medical imaging, cancer detection, radiomics\nCardiology Breakthroughs: mRNA heart repair, transcatheter valves\nFDA Drug Approvals: oncology, novel therapeutics\nMental Health Tech: digital phenotyping, depression biomarkers`}
                value={bulkText}
                onChange={e => setBulkText(e.target.value)}
                style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}
              />
            </div>

            {bulkMessage && (
              <div style={{ 
                padding: '10px 14px', 
                borderRadius: '8px', 
                marginBottom: '16px',
                background: bulkMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                color: bulkMessage.type === 'success' ? '#34d399' : '#fb7185',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                {bulkMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                {bulkMessage.text}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setIsBulkOpen(false)}>
                Cancel
              </button>
              <button 
                type="button" 
                className="btn btn-primary" 
                onClick={handleBulkImport}
                disabled={bulkLoading || !bulkText.trim()}
              >
                {bulkLoading ? 'Importing...' : 'Parse & Import Topics'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
