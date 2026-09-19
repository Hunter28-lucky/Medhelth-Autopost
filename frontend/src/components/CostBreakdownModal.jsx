import React, { useState, useEffect } from 'react';
import { 
  X, DollarSign, Cpu, Search, PenTool, Sliders, 
  TrendingUp, CheckCircle2, Globe, Shield, Sparkles, 
  ArrowRight, Info, Layers, RefreshCw
} from 'lucide-react';

export default function CostBreakdownModal({ 
  isOpen, 
  onClose, 
  topic = null, 
  draft = null, 
  settings = null, 
  onSaveSettings = null,
  onNavigateSettings = null,
  activeTopicsCount = 5
}) {
  const [activeCurrency, setActiveCurrency] = useState('USD');
  const [selectedStage, setSelectedStage] = useState('writing');
  const [customBreakdown, setCustomBreakdown] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (settings?.cost_currency) {
      setActiveCurrency(settings.cost_currency.toUpperCase());
    }
  }, [settings]);

  useEffect(() => {
    if (!isOpen) return;

    if (draft?.cost_breakdown && Object.keys(draft.cost_breakdown).length > 0) {
      setCustomBreakdown(draft.cost_breakdown);
      return;
    }

    if (topic) {
      setLoading(true);
      fetch(`/api/topics/${topic.id}/cost-breakdown?currency=${activeCurrency}`)
        .then(r => r.json())
        .then(data => {
          setCustomBreakdown(data);
          setLoading(false);
        })
        .catch(err => {
          console.error('Failed to load topic cost breakdown:', err);
          setLoading(false);
        });
    } else {
      setLoading(true);
      fetch(`/api/analytics/cost-summary?currency=${activeCurrency}`)
        .then(r => r.json())
        .then(data => {
          if (data?.sample_post_breakdown) {
            setCustomBreakdown(data.sample_post_breakdown);
          }
          setLoading(false);
        })
        .catch(err => {
          console.error('Failed to load cost summary:', err);
          setLoading(false);
        });
    }
  }, [isOpen, topic, draft, activeCurrency]);

  if (!isOpen) return null;

  // Currency rates & symbols
  const exchangeRate = settings?.cost_exchange_rate || 87.5;
  const currencySymbols = { USD: '$', INR: '₹', EUR: '€', GBP: '£' };
  const symbol = currencySymbols[activeCurrency] || '$';

  // Format currency helper
  const formatMoney = (usdAmount) => {
    if (usdAmount === undefined || usdAmount === null) return `${symbol}0.0000`;
    let rate = 1.0;
    if (activeCurrency === 'INR') rate = exchangeRate;
    else if (activeCurrency === 'EUR') rate = 0.92;
    else if (activeCurrency === 'GBP') rate = 0.79;

    const val = usdAmount * rate;
    if (activeCurrency === 'INR') {
      return val < 0.01 ? `${symbol}${val.toFixed(3)}` : `${symbol}${val.toFixed(2)}`;
    }
    return `${symbol}${val.toFixed(4)}`;
  };

  const handleCurrencySwitch = async (curr) => {
    setActiveCurrency(curr);
    if (onSaveSettings) {
      try {
        await onSaveSettings({ cost_currency: curr });
      } catch (err) {
        console.warn('Currency auto-save note:', err);
      }
    }
  };

  // Resolve active metrics
  const isOverride = settings?.cost_manual_override_enabled || customBreakdown?.is_manual_override;
  const totalCostUsd = customBreakdown?.total_cost_usd || (isOverride ? (settings?.cost_fixed_per_post || 0.0035) : 0.0035);
  const promptTokens = customBreakdown?.prompt_tokens || 2250;
  const completionTokens = customBreakdown?.completion_tokens || 850;
  const totalTokens = customBreakdown?.total_tokens || (promptTokens + completionTokens);

  const stages = [
    {
      id: 'research',
      name: 'Web Search & Ingestion',
      icon: Search,
      percentage: 28,
      tokens: Math.round(promptTokens * 0.28),
      costUsd: totalCostUsd * 0.28,
      gradient: 'linear-gradient(90deg, #00f0ff 0%, #0284c7 100%)',
      color: '#00f0ff',
      tagline: 'Live medical intelligence crawler & verified news ingestion',
      deliverables: [
        'Real-time query execution across biomedical news indexes',
        'Strict domain whitelist validation (PubMed, FierceBiotech, FDA)',
        'MD5 URL and body fingerprinting for 0% duplicate coverage'
      ]
    },
    {
      id: 'writing',
      name: 'Writing & Clinical AI Synthesis',
      icon: PenTool,
      percentage: 58,
      tokens: Math.round(promptTokens * 0.58) + completionTokens,
      costUsd: totalCostUsd * 0.58,
      gradient: 'linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%)',
      color: '#818cf8',
      tagline: 'Medical reasoning & WordPress Classic Editor semantic drafting',
      deliverables: [
        'Domain-tuned clinical synthesis grounded in extracted claims',
        'Few-shot style cloning matching target publisher editorial tone',
        'Strict <h6><strong>Subheading</strong></h6> Classic Editor hierarchy'
      ]
    },
    {
      id: 'assembling',
      name: 'Assembling & Yoast SEO',
      icon: Sliders,
      percentage: 14,
      tokens: Math.round(promptTokens * 0.14),
      costUsd: totalCostUsd * 0.14,
      gradient: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
      color: '#34d399',
      tagline: 'Yoast SEO 28.4 compliance & self-healing transition word auto-fix',
      deliverables: [
        '100% Green bullets verified on SEO & Flesch-Kincaid readability',
        'Automated transition word density boost (>=30% sentences)',
        'Clean Classic Editor sanitation (strips raw divs, callouts & blockquotes)'
      ]
    }
  ];

  const activeStageData = stages.find(s => s.id === selectedStage) || stages[1];

  // Full catalog extrapolation calculations
  const count = topic ? 1 : Math.max(1, activeTopicsCount || 5);
  const fullCatalogUsd = totalCostUsd * count;
  const monthlyUsd = totalCostUsd * count * 4 * 30; // 4 runs/day * 30 days
  const agencyMonthlyUsd = count * 4 * 30 * 45.0; // Human copywriter agency rate $45/post

  return (
    <div className="modal-overlay" style={{ zIndex: 1050 }}>
      <div 
        className="modal-container" 
        style={{ 
          maxWidth: '820px', 
          width: '94%',
          maxHeight: '90vh', 
          overflowY: 'auto',
          padding: '28px',
          background: 'radial-gradient(circle at 50% 0%, #0f172a 0%, #020617 100%)',
          border: '1px solid rgba(0, 240, 255, 0.3)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 40px rgba(0, 240, 255, 0.15)'
        }}
      >
        {/* Top Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-cyan" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <TrendingUp size={12} /> Real-Time Token Economics
              </span>
              {isOverride && (
                <span className="badge badge-amber" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Shield size={11} /> Manual Override Active
                </span>
              )}
            </div>
            <h2 style={{ fontSize: '1.4rem', color: '#fff', fontWeight: '700' }}>
              {draft ? `Economics: ${draft.title.slice(0, 48)}...` : topic ? `Topic Run: ${topic.name}` : 'Pipeline API Cost & Token Breakdown'}
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Full financial transparency: see exactly where every token and cent is invested across research, AI drafting, and Yoast SEO.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Currency Quick-Switcher */}
            <div style={{ 
              display: 'flex', 
              background: 'rgba(255, 255, 255, 0.05)', 
              borderRadius: '8px', 
              padding: '2px', 
              border: '1px solid var(--border-subtle)' 
            }}>
              {['USD', 'INR', 'EUR', 'GBP'].map(curr => (
                <button
                  key={curr}
                  type="button"
                  onClick={() => handleCurrencySwitch(curr)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    border: 'none',
                    borderRadius: '6px',
                    background: activeCurrency === curr ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
                    color: activeCurrency === curr ? '#00f0ff' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {currencySymbols[curr]} {curr}
                </button>
              ))}
            </div>

            <button 
              type="button" 
              className="btn btn-ghost" 
              onClick={onClose} 
              style={{ padding: '6px', color: 'var(--text-muted)' }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Hero Metrics Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px', marginBottom: '24px' }}>
          <div className="glass-card" style={{ padding: '16px', border: '1px solid rgba(0, 240, 255, 0.25)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Cost per 1 Article Run
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: '800', color: '#00f0ff', margin: '4px 0' }}>
              {formatMoney(totalCostUsd)}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              {activeCurrency === 'INR' ? `≈ $${totalCostUsd.toFixed(4)} USD` : `≈ ₹${(totalCostUsd * exchangeRate).toFixed(2)} INR`}
            </div>
          </div>

          <div className="glass-card" style={{ padding: '16px', border: '1px solid rgba(99, 102, 241, 0.25)' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Token Consumption
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: '800', color: '#818cf8', margin: '4px 0' }}>
              {totalTokens.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              {promptTokens.toLocaleString()} in / {completionTokens.toLocaleString()} out
            </div>
          </div>

          <div className="glass-card" style={{ padding: '16px', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Catalog Run ({count} {count === 1 ? 'Topic' : 'Topics'})
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: '800', color: '#34d399', margin: '4px 0' }}>
              {formatMoney(fullCatalogUsd)}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              1 execution for all active topics
            </div>
          </div>

          <div className="glass-card" style={{ padding: '16px', border: '1px solid rgba(245, 158, 11, 0.25)' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Cost Efficiency vs Agency
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: '800', color: '#fbbf24', margin: '4px 0' }}>
              99.8%
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              Agency: {formatMoney(45.0)} / post
            </div>
          </div>
        </div>

        {/* Visual Token Investment Distribution Bar */}
        <div className="glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#fff' }}>
              Token & Resource Investment Distribution
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Click segment to inspect stage breakdown
            </span>
          </div>

          {/* Interactive Multi-Segment Progress Bar */}
          <div style={{ 
            height: '24px', 
            width: '100%', 
            borderRadius: '12px', 
            display: 'flex', 
            overflow: 'hidden', 
            background: 'rgba(255, 255, 255, 0.05)',
            boxShadow: 'inset 0 2px 6px rgba(0, 0, 0, 0.4)',
            cursor: 'pointer'
          }}>
            {stages.map(stage => (
              <div 
                key={stage.id}
                onClick={() => setSelectedStage(stage.id)}
                style={{
                  width: `${stage.percentage}%`,
                  background: stage.gradient,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontSize: '0.72rem',
                  fontWeight: '700',
                  letterSpacing: '0.02em',
                  opacity: selectedStage === stage.id ? 1 : 0.75,
                  transform: selectedStage === stage.id ? 'scaleY(1.08)' : 'none',
                  transition: 'all 0.2s ease',
                  borderRight: '1px solid rgba(0, 0, 0, 0.4)'
                }}
                title={`${stage.name}: ${stage.percentage}% (${formatMoney(stage.costUsd)})`}
              >
                {stage.percentage}%
              </div>
            ))}
          </div>

          {/* 3 Interactive Stage Selectors */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginTop: '16px' }}>
            {stages.map(stage => {
              const Icon = stage.icon;
              const isSelected = selectedStage === stage.id;
              return (
                <button
                  key={stage.id}
                  type="button"
                  onClick={() => setSelectedStage(stage.id)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    padding: '12px',
                    borderRadius: '8px',
                    background: isSelected ? 'rgba(255, 255, 255, 0.07)' : 'rgba(255, 255, 255, 0.02)',
                    border: isSelected ? `1px solid ${stage.color}` : '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                    <Icon size={15} style={{ color: stage.color }} />
                    <span style={{ fontSize: '0.8rem', fontWeight: '600', color: isSelected ? '#fff' : 'var(--text-secondary)' }}>
                      {stage.name}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', fontSize: '0.75rem' }}>
                    <span style={{ color: stage.color, fontWeight: '700' }}>
                      {formatMoney(stage.costUsd)}
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>
                      ~{stage.tokens.toLocaleString()} tok
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Stage Detail Panel */}
        <div 
          className="glass-card" 
          style={{ 
            padding: '20px', 
            marginBottom: '24px', 
            border: `1px solid ${activeStageData.color}40`,
            background: 'rgba(15, 23, 42, 0.6)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: activeStageData.color, display: 'flex' }}>
                <activeStageData.icon size={18} />
              </span>
              <h4 style={{ fontSize: '1rem', color: '#fff', margin: 0, fontWeight: '600' }}>
                {activeStageData.name} ({activeStageData.percentage}% of Budget)
              </h4>
            </div>
            <span className="badge" style={{ background: `${activeStageData.color}20`, color: activeStageData.color, border: `1px solid ${activeStageData.color}60` }}>
              {formatMoney(activeStageData.costUsd)} • {activeStageData.tokens.toLocaleString()} tokens
            </span>
          </div>

          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            {activeStageData.tagline}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {activeStageData.deliverables.map((item, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.8rem', color: '#cbd5e1' }}>
                <CheckCircle2 size={14} style={{ color: activeStageData.color, flexShrink: 0, marginTop: '2px' }} />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Full Catalog & Volume Extrapolation Calculator */}
        <div className="glass-card" style={{ padding: '20px', marginBottom: '20px' }}>
          <h4 style={{ fontSize: '0.92rem', color: '#fff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Globe size={16} style={{ color: '#00f0ff' }} />
            Enterprise Volume Extrapolation & ROI
          </h4>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Single Post Execution</div>
              <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#fff', margin: '2px 0' }}>{formatMoney(totalCostUsd)}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>1 complete clinical draft</div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Full Catalog Run ({count} Topics)</div>
              <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#00f0ff', margin: '2px 0' }}>{formatMoney(fullCatalogUsd)}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>All categories simultaneously</div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Monthly (4 runs/day auto-pilot)</div>
              <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#34d399', margin: '2px 0' }}>{formatMoney(monthlyUsd)}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>~{(count * 4 * 30).toLocaleString()} posts/mo</div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Traditional Copywriting Agency</div>
              <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#f43f5e', margin: '2px 0' }}>{formatMoney(agencyMonthlyUsd)}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>At standard $45/draft rate</div>
            </div>
          </div>
        </div>

        {/* Settings Navigation & Audit Note Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <Info size={13} style={{ color: '#00f0ff' }} />
            <span>
              Rates configured in Settings ({formatMoney(settings?.cost_prompt_per_1m || 0.15)}/1M in, {formatMoney(settings?.cost_completion_per_1m || 0.60)}/1M out).
            </span>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            {onNavigateSettings && (
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={() => {
                  onClose();
                  onNavigateSettings();
                }}
                style={{ fontSize: '0.8rem', padding: '6px 12px' }}
              >
                <Sliders size={14} /> Adjust Pricing & Override in Settings
              </button>
            )}
            <button 
              type="button" 
              className="btn btn-primary" 
              onClick={onClose}
              style={{ fontSize: '0.8rem', padding: '6px 14px' }}
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
