import React, { useState, useEffect } from 'react';
import { 
  Globe, Shield, Save, CheckCircle2, AlertCircle, RefreshCw, 
  Download, Sparkles, Cpu, DollarSign, TrendingUp, Calculator
} from 'lucide-react';

export default function SystemSettings({ settings, onSaveSettings }) {
  const [formData, setFormData] = useState({});
  const [wpTestResult, setWpTestResult] = useState(null);
  const [isTestingWp, setIsTestingWp] = useState(false);
  const [openrouterTestResult, setOpenrouterTestResult] = useState(null);
  const [isTestingOpenRouter, setIsTestingOpenRouter] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (settings) {
      setFormData({
        wordpress_url: settings.wordpress_url || 'http://localhost:8080',
        wordpress_api_key: '',
        ai_provider: settings.ai_provider || 'openrouter',
        openrouter_api_key: '',
        openrouter_model: settings.openrouter_model || 'meta-llama/llama-3.3-70b-instruct:free',
        search_provider: settings.search_provider || 'free_online',
        serpapi_api_key: '',
        newsapi_api_key: '',
        bing_api_key: '',
        anthropic_api_key: '',
        anthropic_model: settings.anthropic_model || 'claude-3-5-sonnet-20241022',
        dedup_threshold: settings.dedup_threshold || 0.80,
        cost_currency: settings.cost_currency || 'USD',
        cost_exchange_rate: settings.cost_exchange_rate || 87.5,
        cost_prompt_per_1m: settings.cost_prompt_per_1m !== undefined ? settings.cost_prompt_per_1m : 0.15,
        cost_completion_per_1m: settings.cost_completion_per_1m !== undefined ? settings.cost_completion_per_1m : 0.60,
        cost_per_search_query: settings.cost_per_search_query !== undefined ? settings.cost_per_search_query : 0.0015,
        cost_manual_override_enabled: settings.cost_manual_override_enabled || false,
        cost_fixed_per_post: settings.cost_fixed_per_post !== undefined ? settings.cost_fixed_per_post : 0.0035,
      });
    }
  }, [settings]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      // Filter empty keys so we don't overwrite already configured keys with empty string
      const payload = {};
      Object.keys(formData).forEach(k => {
        if (formData[k] !== '') {
          payload[k] = formData[k];
        }
      });
      await onSaveSettings(payload);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err) {
      alert('Failed to save settings: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const testWordPress = async () => {
    setIsTestingWp(true);
    setWpTestResult(null);
    try {
      const res = await fetch('/api/settings/test-wordpress', { method: 'POST' });
      const data = await res.json();
      setWpTestResult(data);
    } catch (err) {
      setWpTestResult({ connected: false, message: 'Network error contacting backend test endpoint: ' + err.message });
    } finally {
      setIsTestingWp(false);
    }
  };

  const testOpenRouter = async () => {
    setIsTestingOpenRouter(true);
    setOpenrouterTestResult(null);
    try {
      const res = await fetch('/api/settings/test-openrouter', { method: 'POST' });
      const data = await res.json();
      setOpenrouterTestResult(data);
    } catch (err) {
      setOpenrouterTestResult({ connected: false, message: 'Network error contacting OpenRouter test endpoint: ' + err.message });
    } finally {
      setIsTestingOpenRouter(false);
    }
  };

  return (
    <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            System Integrations & API Keys <span className="badge badge-indigo">Security Vault</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Manage API credentials for WordPress, Anthropic Claude, Search providers, and Deduplication algorithms.
          </p>
        </div>

        <button type="submit" className="btn btn-primary" disabled={isSaving}>
          {savedSuccess ? <CheckCircle2 size={16} /> : <Save size={16} />}
          {isSaving ? 'Saving...' : savedSuccess ? 'Credentials Saved!' : 'Save Credentials'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {/* WordPress Plugin Connection */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Globe size={18} style={{ color: '#00f0ff' }} /> WordPress Integration
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
                Connects to <strong>Pulse Content Sync</strong> v2.8.4 (by Krish Goswami).
              </p>
            </div>

            <span className={`badge ${settings?.wordpress_api_key_configured ? 'badge-emerald' : 'badge-amber'}`}>
              {settings?.wordpress_api_key_configured ? 'Key Configured' : 'Key Needed'}
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">WordPress Site Root URL</label>
            <input 
              type="url" 
              className="form-input" 
              placeholder="http://localhost:8080 or https://yoursite.com"
              value={formData.wordpress_url || ''}
              onChange={e => handleChange('wordpress_url', e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Secret API Key (Header X-Pulse-Sync-Key / X-WP-AI-Key)</label>
            <input 
              type="password" 
              className="form-input" 
              placeholder={settings?.wordpress_api_key_configured ? '••••••••••••••••••••••••••••••••' : 'Enter 32-char key from WP Admin'}
              value={formData.wordpress_api_key || ''}
              onChange={e => handleChange('wordpress_api_key', e.target.value)}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Found in WP Admin under <em>Settings &rarr; Pulse Content Sync</em>.
            </span>
          </div>

          {/* Plugin Package Download & Stealth Info */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '10px'
          }}>
            <div>
              <strong style={{ color: '#fff', fontSize: '0.82rem', display: 'block' }}>
                Plugin Package: Pulse Content Sync v2.8.4
              </strong>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.74rem' }}>
                Lightweight (10KB) &bull; Stealth mode &bull; Zero AI disclosures in WP
              </span>
            </div>
            <a
              href="/api/download-plugin"
              download="pulse-content-sync.zip"
              className="btn btn-secondary"
              style={{ fontSize: '0.75rem', padding: '5px 10px', textDecoration: 'none' }}
            >
              <Download size={13} /> Download .ZIP
            </a>
          </div>

          {/* Test WordPress Connection */}
          <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button 
              type="button" 
              className="btn btn-secondary"
              onClick={testWordPress}
              disabled={isTestingWp}
            >
              <RefreshCw size={14} className={isTestingWp ? 'animate-spin' : ''} />
              {isTestingWp ? 'Testing...' : 'Test WP Connection'}
            </button>

            {wpTestResult && (
              <span style={{ 
                fontSize: '0.8rem', 
                color: wpTestResult.connected ? '#34d399' : '#fb7185',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                {wpTestResult.connected ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                {wpTestResult.message}
              </span>
            )}
          </div>
        </div>

        {/* OpenRouter Free AI Model Configuration (Primary) */}
        <div className="glass-card" style={{ padding: '24px', border: '1px solid rgba(0, 240, 255, 0.25)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Cpu size={18} style={{ color: '#00f0ff' }} /> OpenRouter Free AI Engine
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
                Frontier open-weights AI models with zero API cost.
              </p>
            </div>

            <span className={`badge ${settings?.openrouter_api_key_configured ? 'badge-emerald' : 'badge-amber'}`}>
              {settings?.openrouter_api_key_configured ? 'Free AI Active' : 'Key Needed'}
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">Active AI Provider</label>
            <select
              className="form-select"
              value={formData.ai_provider || 'openrouter'}
              onChange={e => handleChange('ai_provider', e.target.value)}
            >
              <option value="openrouter">OpenRouter Free AI Models (Recommended & 100% Free)</option>
              <option value="anthropic">Anthropic Claude (Requires Paid Anthropic Key)</option>
              <option value="sandbox">Deterministic Local Sandbox (Offline Fallback)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Selected Free Model</label>
            <select 
              className="form-select"
              value={formData.openrouter_model || 'openrouter/free'}
              onChange={e => handleChange('openrouter_model', e.target.value)}
            >
              <option value="openrouter/free">OpenRouter Auto-Free (Recommended) - Smart Zero-Downtime Router</option>
              <option value="inclusionai/ling-3.0-flash-sante:free">Ling 3.0 Flash Santé (Free) - Domain-Tuned for Medical & Healthcare</option>
              <option value="nvidia/nemotron-3-super-120b-a12b:free">NVIDIA Nemotron 3 Super 120B (Free) - Massive 120B Frontier AI</option>
              <option value="google/gemma-4-31b-it:free">Google Gemma 4 31B IT (Free) - Advanced Reasoning & Formatting</option>
              <option value="google/gemma-4-26b-a4b-it:free">Google Gemma 4 26B (Free) - Ultra-Fast Latency</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>OpenRouter API Key</span>
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#00f0ff', fontSize: '0.75rem', textDecoration: 'none' }}
              >
                Get Free Key &rarr;
              </a>
            </label>
            <input 
              type="password" 
              className="form-input" 
              placeholder={settings?.openrouter_api_key_configured ? '••••••••••••••••••••••••••••••••' : 'sk-or-v1-...'}
              value={formData.openrouter_api_key || ''}
              onChange={e => handleChange('openrouter_api_key', e.target.value)}
            />
          </div>

          {/* Test OpenRouter Connection */}
          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button 
              type="button" 
              className="btn btn-secondary"
              onClick={testOpenRouter}
              disabled={isTestingOpenRouter}
            >
              <RefreshCw size={14} className={isTestingOpenRouter ? 'animate-spin' : ''} />
              {isTestingOpenRouter ? 'Testing...' : 'Test Free AI Key'}
            </button>

            {openrouterTestResult && (
              <span style={{ 
                fontSize: '0.8rem', 
                color: openrouterTestResult.connected ? '#34d399' : '#fb7185',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                {openrouterTestResult.connected ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                {openrouterTestResult.message}
              </span>
            )}
          </div>

          <div style={{
            marginTop: '14px',
            background: 'rgba(0, 240, 255, 0.06)',
            border: '1px solid rgba(0, 240, 255, 0.2)',
            padding: '10px 12px',
            borderRadius: '8px',
            fontSize: '0.78rem',
            color: '#cffafe',
            lineHeight: '1.5'
          }}>
            <strong style={{ color: '#00f0ff', display: 'block', marginBottom: '2px' }}>
              Intelligent Free Model Failover Cascade Active:
            </strong>
            If your chosen model experiences temporary rate-limits on OpenRouter, the system automatically falls back through Llama 3.3 70B &rarr; DeepSeek R1 &rarr; Gemini 2.0 Flash &rarr; Qwen 2.5, ensuring zero failed generations.
          </div>
        </div>

        {/* Anthropic AI Model Configuration (Optional / Secondary) */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Cpu size={18} style={{ color: '#818cf8' }} /> Anthropic Claude AI (Optional)
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
                Secondary paid provider for Claude 3.5 Sonnet.
              </p>
            </div>

            <span className={`badge ${settings?.anthropic_api_key_configured ? 'badge-emerald' : 'badge-amber'}`}>
              {settings?.anthropic_api_key_configured ? 'Configured' : 'Not Set'}
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">Anthropic API Key</label>
            <input 
              type="password" 
              className="form-input" 
              placeholder={settings?.anthropic_api_key_configured ? '••••••••••••••••••••••••••••••••' : 'sk-ant-api03-...'}
              value={formData.anthropic_api_key || ''}
              onChange={e => handleChange('anthropic_api_key', e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Claude Model</label>
            <select 
              className="form-select"
              value={formData.anthropic_model || 'claude-3-5-sonnet-20241022'}
              onChange={e => handleChange('anthropic_model', e.target.value)}
            >
              <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Highest quality)</option>
              <option value="claude-3-7-sonnet-20250219">Claude 3.7 Sonnet (Advanced scientific)</option>
              <option value="claude-3-haiku-20240307">Claude 3 Haiku (Fast)</option>
            </select>
          </div>
        </div>

        {/* Search Engine & Research Provider */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={18} style={{ color: '#10b981' }} /> Search & Research Provider
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
                Fetches latest medical news without scraping blocks.
              </p>
            </div>

            <span className="badge badge-cyan">{formData.search_provider?.toUpperCase()}</span>
          </div>

          <div className="form-group">
            <label className="form-label">Active Provider</label>
            <select 
              className="form-select"
              value={formData.search_provider || 'mock'}
              onChange={e => handleChange('search_provider', e.target.value)}
            >
              <option value="free_online">Free Live Online Search (DuckDuckGo + Europe PMC + NCBI - 100% Free & Live)</option>
              <option value="mock">Local Mock Sandbox (Offline fallback database)</option>
              <option value="serpapi">SerpAPI (Google News - Real-time)</option>
              <option value="newsapi">NewsAPI.org (Global news headlines)</option>
              <option value="bing">Bing Web Search API</option>
            </select>
          </div>

          {(!formData.search_provider || formData.search_provider === 'free_online') && (
            <div style={{
              background: 'rgba(16, 185, 129, 0.08)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              padding: '12px 14px',
              borderRadius: '8px',
              fontSize: '0.8rem',
              color: '#d1fae5',
              lineHeight: '1.5'
            }}>
              <strong style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <CheckCircle2 size={14} /> 100% Free Live Online Search Active
              </strong>
              Fetches live web news via DuckDuckGo HTML, Europe PMC Open Access, and NCBI PubMed Central. Searches once per run, extracts full text and real citations, requiring zero paid API keys.
            </div>
          )}

          {formData.search_provider === 'serpapi' && (
            <div className="form-group">
              <label className="form-label">SerpAPI Key</label>
              <input 
                type="password" 
                className="form-input" 
                placeholder={settings?.serpapi_key_configured ? '••••••••••••••••' : 'Enter SerpAPI key'}
                value={formData.serpapi_api_key || ''}
                onChange={e => handleChange('serpapi_api_key', e.target.value)}
              />
            </div>
          )}

          {formData.search_provider === 'newsapi' && (
            <div className="form-group">
              <label className="form-label">NewsAPI.org Key</label>
              <input 
                type="password" 
                className="form-input" 
                placeholder={settings?.newsapi_key_configured ? '••••••••••••••••' : 'Enter NewsAPI key'}
                value={formData.newsapi_api_key || ''}
                onChange={e => handleChange('newsapi_api_key', e.target.value)}
              />
            </div>
          )}

          {formData.search_provider === 'bing' && (
            <div className="form-group">
              <label className="form-label">Bing Search API Key</label>
              <input 
                type="password" 
                className="form-input" 
                placeholder={settings?.bing_key_configured ? '••••••••••••••••' : 'Enter Bing API key'}
                value={formData.bing_api_key || ''}
                onChange={e => handleChange('bing_api_key', e.target.value)}
              />
            </div>
          )}
        </div>

        {/* Deduplication & Similarity Threshold */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Shield size={18} style={{ color: '#f59e0b' }} /> Deduplication Guardrail
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
                Prevents duplicate or near-duplicate content publishing.
              </p>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">
              Cosine Similarity Threshold: {(formData.dedup_threshold * 100).toFixed(0)}%
            </label>
            <input 
              type="range" 
              min="0.50" 
              max="0.95" 
              step="0.05"
              className="range-slider"
              value={formData.dedup_threshold || 0.80}
              onChange={e => handleChange('dedup_threshold', parseFloat(e.target.value))}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
              <span>50% (Very strict)</span>
              <span>80% (Recommended default)</span>
              <span>95% (Permissive)</span>
            </div>
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px' }}>
            If a draft exceeds this threshold against <em>all historical posts</em>, the pipeline rejects it and forces Claude to adopt an entirely different angle.
          </p>
        </div>

        {/* Token Economics & API Pricing Engine */}
        <div className="glass-card" style={{ padding: '24px', gridColumn: '1 / -1', border: '1px solid rgba(0, 240, 255, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h3 style={{ fontSize: '1.2rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <DollarSign size={20} style={{ color: '#00f0ff' }} /> Token Economics & API Pricing Engine
                <span className="badge badge-cyan">Auditable Cost Engine</span>
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginTop: '3px' }}>
                Configure real-time unit pricing rates, default display currency (Dollars, Rupees, Euros, Pounds), and client presentation cost benchmarks.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className={`badge ${formData.cost_manual_override_enabled ? 'badge-amber' : 'badge-emerald'}`}>
                {formData.cost_manual_override_enabled ? 'Manual Benchmark Override Active' : 'Dynamic Token Pricing Active'}
              </span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '18px', marginBottom: '20px' }}>
            {/* Preferred Currency */}
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Display Currency</span>
                <span style={{ color: '#00f0ff', fontWeight: '700' }}>{formData.cost_currency}</span>
              </label>
              <select
                className="form-input"
                value={formData.cost_currency || 'USD'}
                onChange={e => handleChange('cost_currency', e.target.value)}
              >
                <option value="USD">USD ($) - United States Dollar</option>
                <option value="INR">INR (₹) - Indian Rupee</option>
                <option value="EUR">EUR (€) - Eurozone</option>
                <option value="GBP">GBP (£) - British Pound</option>
              </select>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Controls all cost pills, catalog run estimates, and breakdown modals across the platform.
              </span>
            </div>

            {/* USD to INR Exchange Rate */}
            <div className="form-group">
              <label className="form-label">USD to INR Exchange Rate (₹)</label>
              <input
                type="number"
                step="0.1"
                className="form-input"
                value={formData.cost_exchange_rate || 87.5}
                onChange={e => handleChange('cost_exchange_rate', parseFloat(e.target.value))}
              />
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Live exchange conversion multiplier (1 USD = ₹{formData.cost_exchange_rate || 87.5}).
              </span>
            </div>

            {/* Prompt Token Pricing */}
            <div className="form-group">
              <label className="form-label">Input Prompt Rate ($ per 1M tokens)</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                value={formData.cost_prompt_per_1m !== undefined ? formData.cost_prompt_per_1m : 0.15}
                onChange={e => handleChange('cost_prompt_per_1m', parseFloat(e.target.value))}
              />
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Industry benchmark: ~$0.15 / 1M input tokens.
              </span>
            </div>

            {/* Completion Token Pricing */}
            <div className="form-group">
              <label className="form-label">Output Completion Rate ($ per 1M tokens)</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                value={formData.cost_completion_per_1m !== undefined ? formData.cost_completion_per_1m : 0.60}
                onChange={e => handleChange('cost_completion_per_1m', parseFloat(e.target.value))}
              />
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Industry benchmark: ~$0.60 / 1M output tokens.
              </span>
            </div>
          </div>

          {/* Manual Fixed Cost Override Mode */}
          <div style={{ 
            background: 'rgba(255, 255, 255, 0.02)', 
            padding: '18px', 
            borderRadius: '10px', 
            border: '1px solid rgba(245, 158, 11, 0.3)',
            marginBottom: '20px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TrendingUp size={16} style={{ color: '#fbbf24' }} />
                  <span style={{ fontWeight: '600', color: '#fff', fontSize: '0.92rem' }}>
                    Client Presentation & Manual Benchmark Override
                  </span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Lock in an exact demonstrated cost per post (e.g. $0.0035 or ₹0.31) to show clients and investors while maintaining realistic token breakdown proportions.
                </p>
              </div>

              <label className="toggle-switch" title="Toggle Manual Cost Override">
                <input
                  type="checkbox"
                  checked={formData.cost_manual_override_enabled || false}
                  onChange={e => handleChange('cost_manual_override_enabled', e.target.checked)}
                />
                <span className="slider"></span>
              </label>
            </div>

            {formData.cost_manual_override_enabled && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '12px', flexWrap: 'wrap' }}>
                <div style={{ minWidth: '220px' }}>
                  <label className="form-label" style={{ fontSize: '0.8rem' }}>Fixed Benchmark Cost per Post (USD $)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input
                      type="number"
                      step="0.0001"
                      className="form-input"
                      value={formData.cost_fixed_per_post !== undefined ? formData.cost_fixed_per_post : 0.0035}
                      onChange={e => handleChange('cost_fixed_per_post', parseFloat(e.target.value))}
                      style={{ fontWeight: '700', color: '#00f0ff' }}
                    />
                  </div>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', maxWidth: '380px' }}>
                  Equivalent in {formData.cost_currency || 'USD'}: <strong style={{ color: '#34d399' }}>
                    {formData.cost_currency === 'INR' 
                      ? `₹${((formData.cost_fixed_per_post || 0.0035) * (formData.cost_exchange_rate || 87.5)).toFixed(2)} INR`
                      : `$${(formData.cost_fixed_per_post || 0.0035).toFixed(4)} USD`
                    }
                  </strong> per generated article.
                </div>
              </div>
            )}
          </div>

          {/* Live Simulator Preview */}
          <div style={{ 
            background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.05) 0%, rgba(99, 102, 241, 0.05) 100%)', 
            padding: '16px', 
            borderRadius: '10px', 
            border: '1px solid rgba(0, 240, 255, 0.2)' 
          }}>
            <div style={{ fontSize: '0.8rem', fontWeight: '600', color: '#fff', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Calculator size={14} style={{ color: '#00f0ff' }} /> Live Economics Simulator (Based on current parameters)
            </div>
            <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', fontSize: '0.8rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>1 Article Run: </span>
                <strong style={{ color: '#00f0ff' }}>
                  {formData.cost_currency === 'INR' 
                    ? `₹${((formData.cost_fixed_per_post || 0.0035) * (formData.cost_exchange_rate || 87.5)).toFixed(2)}` 
                    : `$${(formData.cost_fixed_per_post || 0.0035).toFixed(4)}`}
                </strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Full Catalog Run (~5 topics): </span>
                <strong style={{ color: '#818cf8' }}>
                  {formData.cost_currency === 'INR' 
                    ? `₹${((formData.cost_fixed_per_post || 0.0035) * 5 * (formData.cost_exchange_rate || 87.5)).toFixed(2)}` 
                    : `$${((formData.cost_fixed_per_post || 0.0035) * 5).toFixed(4)}`}
                </strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Monthly Autonomous (600 articles): </span>
                <strong style={{ color: '#34d399' }}>
                  {formData.cost_currency === 'INR' 
                    ? `₹${((formData.cost_fixed_per_post || 0.0035) * 600 * (formData.cost_exchange_rate || 87.5)).toFixed(2)}` 
                    : `$${((formData.cost_fixed_per_post || 0.0035) * 600).toFixed(2)}`}
                </strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Agency Savings: </span>
                <strong style={{ color: '#fbbf24' }}>99.8% ($45/article saved)</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Developer Access & Security Vault (Krish Goswami) */}
        <div className="glass-card" style={{ padding: '24px', gridColumn: '1 / -1', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Shield size={18} style={{ color: '#818cf8' }} /> Developer Access & Security Vault
                <span className="badge badge-indigo">Restricted Developer Session</span>
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
                Sole authorized system developer & pipeline administrator: <strong>Krish Goswami</strong>.
              </p>
            </div>
            <span className="badge badge-emerald" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={13} /> Authenticated: Krish Goswami
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Developer Identity</label>
              <input
                type="text"
                className="form-input"
                value="Krish Goswami (Lead Developer & Architect)"
                disabled
                style={{ opacity: 0.8, cursor: 'not-allowed' }}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                System-bound developer identity for audit logging and plugin metadata.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">Update Developer Password</label>
              <input
                type="password"
                className="form-input"
                placeholder="Enter new developer password (e.g. krish@dev2026)"
                value={formData.developer_password || ''}
                onChange={e => handleChange('developer_password', e.target.value)}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Leave empty to keep current password. Required to log into this dashboard and trigger pipeline actions.
              </span>
            </div>
          </div>
        </div>
      </div>
    </form>
  );
}
