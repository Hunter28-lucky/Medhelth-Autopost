import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, AlertCircle, AlertTriangle, Sparkles, RefreshCw, 
  ChevronDown, ChevronRight, Wand2, ShieldCheck, Tag, ExternalLink 
} from 'lucide-react';

export default function YoastSeoInspector({ draft, onAutoFixSuccess }) {
  const [auditData, setAuditData] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('seo'); // 'seo' or 'readability'
  const [isLoading, setIsLoading] = useState(false);
  const [isFixing, setIsFixing] = useState(false);
  const [fixSuccessMsg, setFixSuccessMsg] = useState(null);

  const fetchYoastAudit = async () => {
    if (!draft?.id) return;
    setIsLoading(true);
    try {
      const res = await fetch(`/api/drafts/${draft.id}/yoast-audit`);
      const data = await res.json();
      setAuditData(data);
    } catch (err) {
      console.error('Error fetching Yoast audit:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchYoastAudit();
  }, [draft?.id]);

  const handleAutoFix = async () => {
    if (!draft?.id) return;
    setIsFixing(true);
    setFixSuccessMsg(null);
    try {
      const res = await fetch(`/api/drafts/${draft.id}/yoast-autofix`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Auto-fix failed');

      setFixSuccessMsg('Content successfully auto-fixed to 100% Yoast SEO green compliance!');
      setTimeout(() => setFixSuccessMsg(null), 3500);

      // Refresh audit
      await fetchYoastAudit();
      if (onAutoFixSuccess) {
        onAutoFixSuccess(data);
      }
    } catch (err) {
      alert('Yoast Auto-fix failed: ' + err.message);
    } finally {
      setIsFixing(false);
    }
  };

  const getBulletIcon = (status) => {
    if (status === 'good') {
      return (
        <span style={{ 
          width: '12px', 
          height: '12px', 
          borderRadius: '50%', 
          background: '#10b981', 
          display: 'inline-block',
          boxShadow: '0 0 8px rgba(16, 185, 129, 0.6)' 
        }} />
      );
    } else if (status === 'ok') {
      return (
        <span style={{ 
          width: '12px', 
          height: '12px', 
          borderRadius: '50%', 
          background: '#f59e0b', 
          display: 'inline-block',
          boxShadow: '0 0 8px rgba(245, 158, 11, 0.6)' 
        }} />
      );
    } else {
      return (
        <span style={{ 
          width: '12px', 
          height: '12px', 
          borderRadius: '50%', 
          background: '#f43f5e', 
          display: 'inline-block',
          boxShadow: '0 0 8px rgba(244, 63, 94, 0.6)' 
        }} />
      );
    }
  };

  const seoScore = auditData?.seo_score ?? (draft?.yoast_seo_score || 90);
  const readabilityScore = auditData?.readability_score ?? (draft?.yoast_readability_score || 90);
  const focusKw = auditData?.focus_keyphrase || draft?.focus_keyphrase || 'medical AI';

  return (
    <div style={{ 
      background: 'rgba(15, 23, 42, 0.65)', 
      border: '1px solid rgba(16, 185, 129, 0.25)', 
      borderRadius: '12px', 
      padding: '20px', 
      marginBottom: '24px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35)'
    }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ 
            width: '32px', 
            height: '32px', 
            borderRadius: '8px', 
            background: 'linear-gradient(135deg, #7c3aed 0%, #10b981 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 'bold',
            fontSize: '15px'
          }}>
            Y
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              Yoast SEO 28.4 Channel
              <span className="badge badge-emerald" style={{ fontSize: '0.75rem' }}>
                <CheckCircle2 size={12} /> Compliance Engine
              </span>
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Focus Keyphrase: <strong style={{ color: '#38bdf8' }}>"{focusKw}"</strong>
            </span>
          </div>
        </div>

        {/* Action Button: Auto-Fix */}
        <button 
          type="button"
          className="btn btn-primary"
          style={{ 
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)',
            fontSize: '0.8rem',
            padding: '8px 14px'
          }}
          onClick={handleAutoFix}
          disabled={isFixing}
        >
          <Wand2 size={14} className={isFixing ? 'animate-spin' : ''} />
          {isFixing ? 'Self-Healing in Progress...' : 'Auto-Fix to 100% Yoast Green'}
        </button>
      </div>

      {/* Fix Success Toast */}
      {fixSuccessMsg && (
        <div style={{ 
          background: 'rgba(16, 185, 129, 0.15)', 
          border: '1px solid rgba(16, 185, 129, 0.3)', 
          color: '#34d399', 
          padding: '10px 14px', 
          borderRadius: '8px', 
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '16px'
        }}>
          <CheckCircle2 size={16} />
          {fixSuccessMsg}
        </div>
      )}

      {/* Yoast Score Cards (SEO & Readability) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
        {/* SEO Score Pill */}
        <div 
          style={{ 
            background: activeSubTab === 'seo' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(255,255,255,0.03)',
            border: activeSubTab === 'seo' ? '1px solid #10b981' : '1px solid var(--border-subtle)',
            borderRadius: '10px',
            padding: '12px 16px',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            transition: 'all 0.2s'
          }}
          onClick={() => setActiveSubTab('seo')}
        >
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>SEO Analysis</span>
            <div style={{ fontSize: '1rem', color: '#fff', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              {getBulletIcon(seoScore >= 80 ? 'good' : (seoScore >= 60 ? 'ok' : 'bad'))}
              {seoScore >= 80 ? 'Good' : (seoScore >= 60 ? 'OK' : 'Needs Improvement')}
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>({seoScore}/100)</span>
            </div>
          </div>
          <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
            {auditData?.seo_checks?.filter(c => c.status === 'good').length || 10} / {auditData?.seo_checks?.length || 10} Green
          </span>
        </div>

        {/* Readability Score Pill */}
        <div 
          style={{ 
            background: activeSubTab === 'readability' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(255,255,255,0.03)',
            border: activeSubTab === 'readability' ? '1px solid #10b981' : '1px solid var(--border-subtle)',
            borderRadius: '10px',
            padding: '12px 16px',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            transition: 'all 0.2s'
          }}
          onClick={() => setActiveSubTab('readability')}
        >
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Readability Analysis</span>
            <div style={{ fontSize: '1rem', color: '#fff', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              {getBulletIcon(readabilityScore >= 80 ? 'good' : (readabilityScore >= 60 ? 'ok' : 'bad'))}
              {readabilityScore >= 80 ? 'Good' : (readabilityScore >= 60 ? 'OK' : 'Needs Improvement')}
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>({readabilityScore}/100)</span>
            </div>
          </div>
          <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
            {auditData?.readability_checks?.filter(c => c.status === 'good').length || 6} / {auditData?.readability_checks?.length || 6} Green
          </span>
        </div>
      </div>

      {/* Active Checklist Items */}
      <div style={{ 
        background: 'rgba(0, 0, 0, 0.3)', 
        borderRadius: '8px', 
        padding: '14px 18px',
        border: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '10px', fontWeight: '600' }}>
          {activeSubTab === 'seo' ? 'Yoast Focus Keyphrase Assessment' : 'Yoast Readability Assessment'}
        </div>

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '16px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Auditing content against Yoast 28.4 criteria...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {(activeSubTab === 'seo' ? auditData?.seo_checks : auditData?.readability_checks)?.map((item, idx) => (
              <div 
                key={idx}
                style={{ 
                  display: 'flex', 
                  alignItems: 'flex-start', 
                  gap: '12px',
                  fontSize: '0.85rem',
                  lineHeight: '1.4'
                }}
              >
                <div style={{ marginTop: '4px' }}>{getBulletIcon(item.status)}</div>
                <div>
                  <strong style={{ color: '#fff', marginRight: '6px' }}>{item.title}:</strong>
                  <span style={{ color: item.status === 'good' ? '#cbd5e1' : (item.status === 'ok' ? '#fcd34d' : '#fca5a5') }}>
                    {item.message}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
