import React, { useState } from 'react';
import { 
  FileText, CheckCircle, ExternalLink, RefreshCw, XCircle, 
  Eye, AlertTriangle, Sparkles, X, Send, Trash2, Globe
} from 'lucide-react';
import YoastSeoInspector from './YoastSeoInspector';

export default function DraftReviewQueue({ drafts, onSelectSite, onRefresh }) {
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [regeneratePrompt, setRegeneratePrompt] = useState('');
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [showRegenBox, setShowRegenBox] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [confirmDeleteModal, setConfirmDeleteModal] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const filteredDrafts = drafts.filter(d => {
    if (statusFilter === 'ALL') return true;
    return d.status === statusFilter;
  });

  const toggleSelect = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    const visibleIds = filteredDrafts.map(d => d.id);
    const allSelected = visibleIds.length > 0 && visibleIds.every(id => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds(prev => prev.filter(id => !visibleIds.includes(id)));
    } else {
      setSelectedIds(prev => Array.from(new Set([...prev, ...visibleIds])));
    }
  };

  const handleDeleteSingle = (postId, title) => {
    setDeleteError(null);
    setConfirmDeleteModal({
      type: 'single',
      ids: [postId],
      title: title || `Draft #${postId}`
    });
  };

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) return;
    setDeleteError(null);
    setConfirmDeleteModal({
      type: 'bulk',
      ids: selectedIds,
      title: `${selectedIds.length} selected draft(s)`
    });
  };

  const handleDeleteAllFiltered = () => {
    const visibleIds = filteredDrafts.map(d => d.id);
    if (visibleIds.length === 0) return;
    const filterName = statusFilter === 'ALL' ? 'all' : statusFilter.toLowerCase().replace('_', ' ');
    setDeleteError(null);
    setConfirmDeleteModal({
      type: 'all_filtered',
      ids: visibleIds,
      title: `all ${visibleIds.length} ${filterName} draft(s)`
    });
  };

  const executeDelete = async () => {
    if (!confirmDeleteModal) return;
    setIsActionLoading(true);
    setDeleteError(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 20000);

    try {
      const payload = confirmDeleteModal.type === 'all_filtered'
        ? { delete_all: true, status: statusFilter }
        : { post_ids: confirmDeleteModal.ids };

      const res = await fetch('/api/drafts/bulk-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.message || `Server error (${res.status})`);
      }

      if (confirmDeleteModal.ids) {
        setSelectedIds(prev => prev.filter(id => !confirmDeleteModal.ids.includes(id)));
      } else {
        setSelectedIds([]);
      }

      if (selectedDraft && confirmDeleteModal.ids?.includes(selectedDraft.id)) {
        setSelectedDraft(null);
      } else if (confirmDeleteModal.type === 'all_filtered') {
        setSelectedDraft(null);
      }

      setConfirmDeleteModal(null);
      setIsActionLoading(false);

      if (typeof onRefresh === 'function') {
        try {
          onRefresh();
        } catch (refErr) {
          console.warn('onRefresh error:', refErr);
        }
      }
    } catch (err) {
      clearTimeout(timeoutId);
      console.error('Delete failed:', err);
      const msg = err.name === 'AbortError'
        ? 'Request timed out after 20 seconds. The server may still be deploying. Please try again.'
        : (err.message || 'Error deleting drafts.');
      setDeleteError(msg);
      setIsActionLoading(false);
    }
  };

  const handleAction = async (postId, action, feedback = null) => {
    setIsActionLoading(true);
    try {
      const res = await fetch(`/api/drafts/${postId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, feedback })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Action failed');
      }
      
      onRefresh();
      // Update selected draft view if open
      if (action === 'push_to_wp' && selectedDraft?.id === postId) {
        setSelectedDraft(prev => ({ ...prev, status: 'SENT_TO_WP', wp_post_id: data.wp_post_id, wp_edit_url: data.edit_url }));
      } else if (action === 'regenerate') {
        setSelectedDraft(null);
        setShowRegenBox(false);
      } else if (action === 'reject' || action === 'approve' || action === 'delete') {
        setSelectedDraft(null);
      }
    } catch (err) {
      alert('Error executing action: ' + err.message);
    } finally {
      setIsActionLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PENDING_REVIEW':
        return <span className="badge badge-amber">Pending Review</span>;
      case 'SENT_TO_WP':
        return <span className="badge badge-emerald">In WordPress Draft</span>;
      case 'APPROVED':
        return <span className="badge badge-cyan">Approved</span>;
      case 'DUPLICATE_FLAGGED':
        return <span className="badge badge-rose">Duplicate Flagged</span>;
      case 'REJECTED':
        return <span className="badge badge-rose">Rejected</span>;
      default:
        return <span className="badge badge-indigo">{status}</span>;
    }
  };

  const getSimilarityBadge = (score, status) => {
    const pct = (score * 100).toFixed(1);
    if (score >= 0.80) {
      return (
        <span className="badge badge-rose" title="Similarity exceeds threshold (>80%)">
          <AlertTriangle size={12} /> {pct}% Overlap
        </span>
      );
    } else if (status === 'RE_ANGLED') {
      return (
        <span className="badge badge-indigo" title="Re-angled following deduplication warning">
          <Sparkles size={12} /> Re-Angled ({pct}%)
        </span>
      );
    } else {
      return (
        <span className="badge badge-emerald" title="Unique draft content">
          <CheckCircle size={12} /> {pct}% Overlap (Unique)
        </span>
      );
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header & Filter Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            Editorial Review Gate <span className="badge badge-cyan">{drafts.length} Total Drafts</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Review fact-grounded drafts, verify similarity scores, and dispatch directly to WordPress with one click.
          </p>
        </div>

        {/* Status Filter Tabs */}
        <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-surface-elevated)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
          {[
            { id: 'ALL', label: 'All Drafts' },
            { id: 'PENDING_REVIEW', label: 'Pending Review' },
            { id: 'SENT_TO_WP', label: 'Sent to WordPress' },
            { id: 'DUPLICATE_FLAGGED', label: 'Duplicates' },
          ].map(tab => (
            <button
              key={tab.id}
              className={`btn btn-ghost ${statusFilter === tab.id ? 'btn-secondary' : ''}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
              onClick={() => setStatusFilter(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Bulk Action & Management Toolbar */}
      {filteredDrafts.length > 0 && (
        <div 
          className="glass-card" 
          style={{ 
            padding: '12px 20px', 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            flexWrap: 'wrap', 
            gap: '12px',
            background: 'rgba(15, 23, 42, 0.65)',
            border: '1px solid rgba(255, 255, 255, 0.08)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', color: '#fff', fontSize: '0.875rem', userSelect: 'none' }}>
              <input 
                type="checkbox" 
                checked={filteredDrafts.length > 0 && filteredDrafts.every(d => selectedIds.includes(d.id))}
                onChange={toggleSelectAll}
                style={{ width: '16px', height: '16px', accentColor: '#00f0ff', cursor: 'pointer' }}
              />
              <span>Select All ({filteredDrafts.length})</span>
            </label>

            {selectedIds.length > 0 && (
              <>
                <span className="badge badge-rose" style={{ padding: '4px 10px', fontSize: '0.8rem' }}>
                  {selectedIds.length} Selected
                </span>
                <button 
                  className="btn btn-danger" 
                  style={{ padding: '6px 14px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                  onClick={handleDeleteSelected}
                  disabled={isActionLoading}
                >
                  <Trash2 size={14} /> Delete Selected ({selectedIds.length})
                </button>
                <button 
                  className="btn btn-ghost" 
                  style={{ padding: '6px 10px', fontSize: '0.8rem', color: 'var(--text-muted)' }}
                  onClick={() => setSelectedIds([])}
                >
                  Deselect All
                </button>
              </>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button 
              className="btn btn-ghost" 
              style={{ 
                color: '#f43f5e', 
                padding: '6px 12px', 
                fontSize: '0.8rem', 
                display: 'flex', 
                alignItems: 'center', 
                gap: '6px',
                border: '1px solid rgba(244, 63, 94, 0.2)' 
              }}
              onClick={handleDeleteAllFiltered}
              disabled={isActionLoading}
              title="Delete all drafts currently matching this filter"
            >
              <Trash2 size={14} /> Delete All {statusFilter === 'ALL' ? 'Drafts' : statusFilter.replace('_', ' ')} ({filteredDrafts.length})
            </button>
          </div>
        </div>
      )}

      {/* Drafts List */}
      {filteredDrafts.length === 0 ? (
        <div className="glass-card" style={{ padding: '48px', textAlign: 'center' }}>
          <FileText size={48} style={{ color: 'var(--text-muted)', margin: '0 auto 16px auto', display: 'block' }} />
          <h3 style={{ color: '#fff', marginBottom: '8px' }}>No drafts in this view</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '420px', margin: '0 auto' }}>
            When the research pipeline executes, generated drafts will be queued here for editorial inspection.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredDrafts.map(draft => (
            <div 
              key={draft.id} 
              className="glass-card" 
              style={{ 
                padding: '18px 24px', 
                display: 'flex', 
                alignItems: 'center', 
                flexWrap: 'wrap', 
                gap: '16px',
                borderLeft: draft.status === 'SENT_TO_WP' ? '4px solid #10b981' : (draft.status === 'DUPLICATE_FLAGGED' ? '4px solid #f43f5e' : '4px solid #00f0ff'),
                background: selectedIds.includes(draft.id) ? 'rgba(0, 240, 255, 0.04)' : undefined
              }}
            >
              {/* Card Selection Checkbox */}
              <div style={{ display: 'flex', alignItems: 'center', paddingRight: '4px' }}>
                <input 
                  type="checkbox"
                  checked={selectedIds.includes(draft.id)}
                  onChange={() => toggleSelect(draft.id)}
                  style={{ width: '18px', height: '18px', accentColor: '#00f0ff', cursor: 'pointer' }}
                  title="Select draft for bulk actions"
                />
              </div>

              <div style={{ flex: 1, minWidth: '260px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px', flexWrap: 'wrap' }}>
                  {getStatusBadge(draft.status)}
                  {getSimilarityBadge(draft.similarity_score, draft.similarity_status)}
                  {draft.site_name && (
                    <span 
                      className="badge badge-purple" 
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', cursor: onSelectSite ? 'pointer' : 'default' }}
                      onClick={() => onSelectSite && onSelectSite(draft.site_id, 'drafts')}
                      title={`Click to focus on ${draft.site_name} drafts`}
                    >
                      <Globe size={11} /> {draft.site_name}
                    </span>
                  )}
                  <span 
                    className="badge badge-emerald" 
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '3px 8px' }}
                    title={`Yoast Score: SEO ${draft.yoast_seo_score || 90}/100, Readability ${draft.yoast_readability_score || 90}/100`}
                  >
                    <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span>
                    Yoast: {draft.yoast_seo_score >= 80 ? 'Good' : 'OK'}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {new Date(draft.created_at).toLocaleString()}
                  </span>
                </div>

                <h3 
                  style={{ fontSize: '1.1rem', color: '#fff', cursor: 'pointer', marginBottom: '4px' }}
                  onClick={() => setSelectedDraft(draft)}
                >
                  {draft.title}
                </h3>

                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineClamp: 2, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {draft.excerpt || 'No excerpt generated.'}
                </p>

                <div style={{ display: 'flex', gap: '12px', marginTop: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span><strong>Slug:</strong> /{draft.slug}</span>
                  <span>&bull;</span>
                  <span><strong>Sources Grounded:</strong> {draft.sources_used?.length || 0}</span>
                  {draft.wp_post_id && (
                    <>
                      <span>&bull;</span>
                      <span style={{ color: '#34d399' }}>WP Post #{draft.wp_post_id}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button 
                  className="btn btn-secondary" 
                  style={{ padding: '8px 14px' }}
                  onClick={() => setSelectedDraft(draft)}
                >
                  <Eye size={15} /> Preview & Inspect
                </button>

                {draft.status !== 'SENT_TO_WP' ? (
                  <button 
                    className="btn btn-primary" 
                    style={{ padding: '8px 14px' }}
                    onClick={() => handleAction(draft.id, 'push_to_wp')}
                    disabled={isActionLoading}
                  >
                    <Send size={15} /> Push to WP
                  </button>
                ) : (
                  <a 
                    href={draft.wp_edit_url || '#'} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="btn btn-secondary" 
                    style={{ padding: '8px 14px', color: '#38bdf8' }}
                  >
                    <ExternalLink size={15} /> Edit in WP
                  </a>
                )}

                {/* Normal / Single Delete Button */}
                <button 
                  className="btn btn-ghost" 
                  style={{ 
                    color: '#f43f5e', 
                    padding: '8px 12px', 
                    border: '1px solid rgba(244, 63, 94, 0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px'
                  }}
                  onClick={() => handleDeleteSingle(draft.id, draft.title)}
                  disabled={isActionLoading}
                  title="Permanently delete this draft"
                >
                  <Trash2 size={15} /> Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detailed Article Modal & Similarity Inspector */}
      {selectedDraft && (
        <div className="modal-overlay">
          <div className="modal-container" style={{ maxWidth: '880px', padding: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px', marginBottom: '20px' }}>
              <div>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  {getStatusBadge(selectedDraft.status)}
                  {getSimilarityBadge(selectedDraft.similarity_score, selectedDraft.similarity_status)}
                  {selectedDraft.site_name && (
                    <span className="badge badge-purple" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <Globe size={11} /> {selectedDraft.site_name}
                    </span>
                  )}
                </div>
                <h2 style={{ fontSize: '1.4rem', color: '#fff' }}>{selectedDraft.title}</h2>
              </div>

              <button className="btn btn-ghost" onClick={() => { setSelectedDraft(null); setShowRegenBox(false); }}>
                <X size={20} />
              </button>
            </div>

            {/* Google SERP Snippet Preview */}
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px 18px', borderRadius: '8px', marginBottom: '20px', border: '1px solid rgba(255,255,255,0.06)' }}>
              <span className="form-label" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>SEO Search Preview</span>
              <div style={{ fontSize: '0.85rem', color: '#38bdf8', marginBottom: '2px', wordBreak: 'break-all' }}>
                https://your-site.com/{selectedDraft.slug}
              </div>
              <div style={{ fontSize: '1.05rem', color: '#8ab4f8', fontWeight: '500', marginBottom: '4px' }}>
                {selectedDraft.meta_title || selectedDraft.title}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#bdc1c6' }}>
                {selectedDraft.meta_description || selectedDraft.excerpt}
              </div>
            </div>

            {/* Deduplication Analysis Card */}
            <div style={{ 
              background: selectedDraft.similarity_score >= 0.80 ? 'rgba(244, 63, 94, 0.08)' : 'rgba(16, 185, 129, 0.08)',
              border: selectedDraft.similarity_score >= 0.80 ? '1px solid rgba(244, 63, 94, 0.25)' : '1px solid rgba(16, 185, 129, 0.25)',
              padding: '14px 18px',
              borderRadius: '8px',
              marginBottom: '24px'
            }}>
              <strong style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#fff', fontSize: '0.9rem' }}>
                <Sparkles size={16} style={{ color: selectedDraft.similarity_score >= 0.80 ? '#f43f5e' : '#10b981' }} />
                Deduplication Fingerprint: {(selectedDraft.similarity_score * 100).toFixed(1)}% Max Historical Similarity
              </strong>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                {selectedDraft.similarity_score >= 0.80 
                  ? `Warning: Content exceeded the 80% threshold against historical post #${selectedDraft.similarity_matched_id}. Re-angling recommended.`
                  : `Uniqueness threshold passed (< 80%). Content is distinct and safe for publication without duplicate penalties.`}
              </p>
            </div>

            {/* Yoast SEO 28.4 Inspector & Self-Healing Auto-Fixer */}
            <YoastSeoInspector 
              draft={selectedDraft} 
              onAutoFixSuccess={(updated) => {
                setSelectedDraft(prev => ({
                  ...prev,
                  ...updated
                }));
                onRefresh();
              }}
            />

            {/* Article Content Simulation */}
            <div className="article-reader" style={{ background: 'var(--bg-surface-elevated)', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
              <div dangerouslySetInnerHTML={{ __html: selectedDraft.body_html }} />
            </div>

            {/* Referenced Grounding Sources */}
            {selectedDraft.sources_used && selectedDraft.sources_used.length > 0 && (
              <div style={{ marginBottom: '24px' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '10px' }}>
                  Grounded in Verified Research Sources ({selectedDraft.sources_used.length})
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {selectedDraft.sources_used.map((src, idx) => (
                    <a 
                      key={idx} 
                      href={src.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'space-between',
                        padding: '8px 12px', 
                        background: 'rgba(255,255,255,0.03)', 
                        borderRadius: '6px',
                        color: '#93c5fd',
                        textDecoration: 'none',
                        fontSize: '0.85rem'
                      }}
                    >
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '80%' }}>
                        <strong>{src.title || src.url}</strong> ({src.domain || 'Source'})
                      </span>
                      <ExternalLink size={14} />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Re-Angle Feedback Box */}
            {showRegenBox && (
              <div style={{ background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.3)', padding: '16px', borderRadius: '8px', marginBottom: '20px' }}>
                <label className="form-label" style={{ color: '#fff' }}>Provide Re-Angle Instructions</label>
                <textarea 
                  className="form-textarea"
                  rows="3"
                  placeholder="e.g., Focus specifically on clinical trial sample diversity, healthcare costs, and molecular mechanisms..."
                  value={regeneratePrompt}
                  onChange={e => setRegeneratePrompt(e.target.value)}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                  <button className="btn btn-ghost" onClick={() => setShowRegenBox(false)}>Cancel</button>
                  <button 
                    className="btn btn-primary"
                    onClick={() => handleAction(selectedDraft.id, 'regenerate', regeneratePrompt)}
                    disabled={isActionLoading}
                  >
                    Generate With New Angle
                  </button>
                </div>
              </div>
            )}

            {/* Modal Bottom Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '20px', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className="btn btn-danger"
                  onClick={() => handleAction(selectedDraft.id, 'reject')}
                  disabled={isActionLoading}
                >
                  <XCircle size={16} /> Reject
                </button>
                
                {!showRegenBox && (
                  <button 
                    className="btn btn-secondary" 
                    onClick={() => setShowRegenBox(true)}
                    disabled={isActionLoading}
                  >
                    <RefreshCw size={16} /> Re-Angle
                  </button>
                )}

                <button 
                  className="btn btn-ghost"
                  style={{ 
                    color: '#f43f5e', 
                    border: '1px solid rgba(244, 63, 94, 0.3)',
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '6px' 
                  }}
                  onClick={() => handleDeleteSingle(selectedDraft.id, selectedDraft.title)}
                  disabled={isActionLoading}
                  title="Permanently delete this draft"
                >
                  <Trash2 size={16} /> Delete Draft
                </button>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                {selectedDraft.status !== 'SENT_TO_WP' ? (
                  <button 
                    className="btn btn-primary" 
                    onClick={() => handleAction(selectedDraft.id, 'push_to_wp')}
                    disabled={isActionLoading}
                  >
                    <Send size={16} /> Approve & Push to WordPress (Draft)
                  </button>
                ) : (
                  <a 
                    href={selectedDraft.wp_edit_url || '#'} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="btn btn-success"
                  >
                    <ExternalLink size={16} /> Open Draft in WordPress
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {confirmDeleteModal && (
        <div className="modal-overlay" style={{ zIndex: 1200 }}>
          <div className="modal-container" style={{ maxWidth: '460px', padding: '28px', border: '1px solid rgba(244, 63, 94, 0.3)', position: 'relative' }}>
            {/* Close X button */}
            <button 
              onClick={() => { setConfirmDeleteModal(null); setDeleteError(null); setIsActionLoading(false); }}
              style={{ position: 'absolute', top: '16px', right: '16px', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
              title="Close"
            >
              <X size={18} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', color: '#f43f5e' }}>
              <div style={{ background: 'rgba(244, 63, 94, 0.15)', padding: '10px', borderRadius: '50%', display: 'flex' }}>
                <AlertTriangle size={24} />
              </div>
              <h3 style={{ color: '#fff', fontSize: '1.25rem', margin: 0 }}>Confirm Delete</h3>
            </div>
            
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '18px', lineHeight: 1.5 }}>
              Are you sure you want to permanently delete <strong>{confirmDeleteModal.title}</strong>? This will remove {confirmDeleteModal.ids?.length === 1 ? 'this draft' : (confirmDeleteModal.ids?.length ? `${confirmDeleteModal.ids.length} drafts` : 'all matching drafts')} completely from the database. This action cannot be undone.
            </p>

            {deleteError && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                padding: '10px 14px',
                borderRadius: '8px',
                marginBottom: '18px',
                color: '#fca5a5',
                fontSize: '0.85rem',
                lineHeight: 1.4
              }}>
                {deleteError}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                className="btn btn-ghost" 
                onClick={() => { setConfirmDeleteModal(null); setDeleteError(null); setIsActionLoading(false); }}
              >
                Cancel
              </button>
              <button 
                className="btn btn-danger" 
                onClick={executeDelete}
                disabled={isActionLoading}
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px' }}
              >
                <Trash2 size={16} />
                {isActionLoading ? 'Deleting...' : `Delete ${confirmDeleteModal.ids?.length > 1 ? `(${confirmDeleteModal.ids.length})` : ''}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
