import React, { useState, useEffect } from 'react';
import { Save, CheckCircle2, ShieldCheck, Sparkles, BookOpen, AlertTriangle } from 'lucide-react';

export default function ContentRulesEditor({ rules, onSaveRules }) {
  const [formData, setFormData] = useState(rules || {});
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (rules) {
      setFormData(rules);
    }
  }, [rules]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await onSaveRules(formData);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err) {
      alert('Error updating content rules: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            Content & SEO Directives <span className="badge badge-indigo">Claude Prompt Configuration</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Configure tone, word count targets, structural blocks, and style guide rules that Claude strictly enforces.
          </p>
        </div>

        <button type="submit" className="btn btn-primary" disabled={isSaving}>
          {savedSuccess ? <CheckCircle2 size={16} /> : <Save size={16} />}
          {isSaving ? 'Saving...' : savedSuccess ? 'Rules Updated!' : 'Save Directives'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {/* Section 1: Tone & Audience */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1.15rem', color: '#fff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} style={{ color: '#00f0ff' }} /> Tone, Audience & Structure
          </h3>

          <div className="form-group">
            <label className="form-label">Tone & Editorial Voice</label>
            <select 
              className="form-select"
              value={formData.tone || 'Professional & Informative'}
              onChange={e => handleChange('tone', e.target.value)}
            >
              <option value="Professional & Informative">Professional & Informative (Balanced news)</option>
              <option value="Clinical & Evidence-Based">Clinical & Evidence-Based (Rigorous medical)</option>
              <option value="Conversational & Accessible">Conversational & Accessible (Patient-centric)</option>
              <option value="Investigative & Analytical">Investigative & Analytical (Deeper context)</option>
              <option value="Biotech & Healthcare Executive">Biotech & Healthcare Executive (Strategic)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Target Audience & Reading Level</label>
            <select 
              className="form-select"
              value={formData.reading_level || 'General Public (Clear, Accessible)'}
              onChange={e => handleChange('reading_level', e.target.value)}
            >
              <option value="General Public (Clear, Accessible)">General Public (Clear, accessible, 8th grade)</option>
              <option value="Healthcare Professionals & Clinicians">Healthcare Professionals & Clinicians (MD/RN level)</option>
              <option value="Medical Students & Researchers">Medical Students & Researchers (Technical depth)</option>
              <option value="Health-Tech Investors & Founders">Health-Tech Investors & Founders (Commercial focus)</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Min Words: {formData.word_count_min || 800}</label>
              <input 
                type="range" 
                min="400" 
                max="1500" 
                step="50"
                className="range-slider"
                value={formData.word_count_min || 800}
                onChange={e => handleChange('word_count_min', parseInt(e.target.value))}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Max Words: {formData.word_count_max || 1200}</label>
              <input 
                type="range" 
                min="800" 
                max="3000" 
                step="50"
                className="range-slider"
                value={formData.word_count_max || 1200}
                onChange={e => handleChange('word_count_max', parseInt(e.target.value))}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Heading Hierarchy</label>
            <input 
              type="text" 
              className="form-input" 
              value={formData.heading_structure || ''}
              onChange={e => handleChange('heading_structure', e.target.value)}
              placeholder="H1 Title, 3-4 H2 Sections, H3 Sub-points"
            />
          </div>
        </div>

        {/* Section 2: Structural Components */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1.15rem', color: '#fff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookOpen size={18} style={{ color: '#10b981' }} /> Structural Modules to Include
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
              <div>
                <strong style={{ fontSize: '0.9rem', color: '#fff', display: 'block' }}>Key Takeaways Callout Box</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Bulleted summary block at top of article</span>
              </div>
              <label className="toggle-switch">
                <input 
                  type="checkbox" 
                  checked={formData.include_takeaways ?? true}
                  onChange={e => handleChange('include_takeaways', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
              <div>
                <strong style={{ fontSize: '0.9rem', color: '#fff', display: 'block' }}>Frequently Asked Questions (FAQ)</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Schema-ready Q&A section at end of post</span>
              </div>
              <label className="toggle-switch">
                <input 
                  type="checkbox" 
                  checked={formData.include_faq ?? true}
                  onChange={e => handleChange('include_faq', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
              <div>
                <strong style={{ fontSize: '0.9rem', color: '#fff', display: 'block' }}>Medical Advice Disclaimer</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Auto-append clinical legal disclaimer box</span>
              </div>
              <label className="toggle-switch">
                <input 
                  type="checkbox" 
                  checked={formData.include_disclaimer ?? true}
                  onChange={e => handleChange('include_disclaimer', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
              <div>
                <strong style={{ fontSize: '0.9rem', color: '#fff', display: 'block' }}>Pull Quotes & Blockquotes</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Format expert opinions and researcher quotes</span>
              </div>
              <label className="toggle-switch">
                <input 
                  type="checkbox" 
                  checked={formData.include_quotes ?? true}
                  onChange={e => handleChange('include_quotes', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
              <div>
                <strong style={{ fontSize: '0.9rem', color: '#fff', display: 'block' }}>Referenced Research Citations</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Grounding sources table in WP post meta box</span>
              </div>
              <label className="toggle-switch">
                <input 
                  type="checkbox" 
                  checked={formData.include_sources ?? true}
                  onChange={e => handleChange('include_sources', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>

        {/* Style Reference & Layout Cloner (Paragraph & Post Architecture) */}
        <div className="glass-card" style={{ padding: '24px', gridColumn: '1 / -1', border: '1px solid rgba(0, 240, 255, 0.25)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.2rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Sparkles size={20} style={{ color: '#00f0ff' }} /> Style Reference & Layout Cloner
                <span className="badge badge-cyan" style={{ fontSize: '0.72rem' }}>Style Cloner by Krish Goswami</span>
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px' }}>
                Provide an example paragraph or complete post. The AI will inspect its exact sentence cadence, header typography, body font, and footer structure, and clone the exact aesthetic across all generated articles.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-primary"
                style={{ fontSize: '0.78rem', padding: '6px 12px', background: 'linear-gradient(135deg, #06b6d4, #3b82f6)' }}
                onClick={() => {
                  const exampleText = `Luffu Link Launch New LTE Health Band From Fitbit Founders.

Luffu Link A New Approach to Family Health Care
The Luffu Link is an LTE health and safety wearable designed to help families stay connected while supporting everyday well-being. Created by the founders of Fitbit, this innovative band focuses on family care rather than traditional fitness tracking. It combines health sensing, emergency communication, and location awareness in a simple wearable that can work without a smartphone nearby.

The device aims to give caregivers greater peace of mind while allowing loved ones to maintain their independence. Instead of requiring users to constantly check an app or manage complicated technology, it provides essential information through a straightforward system. Users can also record details about medications, symptoms, meals, and moods through voice commands.

These updates can help families understand changes in daily routines and recognize patterns that may require attention. The approach focuses on useful information rather than overwhelming users with complicated health dashboards. As a result, the wearable is designed to function more like a supportive guardian than a surveillance device.

Luffu Link Features and Connectivity
The Luffu Link includes built-in LTE connectivity, allowing wearers to send help requests directly from their wrist. This capability can be especially useful when someone is away from their smartphone. With connected safety features, users can quickly communicate with trusted contacts when they need assistance.

GPS location tracking adds another layer of protection. When an emergency occurs, the device can help communicate the user's location to designated contacts. It can also transmit voice messages alongside important information, including heart rate, activity levels, and battery status.

The wearable continuously monitors several aspects of daily activity. Sleep, movement, breathing patterns, and heart rate can provide useful information about changes in a person's routine. Rather than simply collecting large amounts of data, the system aims to identify meaningful developments that families can understand and act upon.

The screenless design also plays an important role in the overall experience. Without a traditional display demanding constant attention, users can remain focused on their surroundings. This design may make the wearable more comfortable for older adults and people who prefer less screen-based technology.

Another advantage is the integrated connectivity approach. Users do not need to manage a separate carrier plan for the LTE service. This can make the technology easier to adopt for families looking for a convenient health and safety solution.

Luffu Link and the Future of Family Care
The Luffu Link reflects a broader movement toward technology that supports caregivers and their families. Many households currently depend on multiple health apps, communication tools, emergency devices, and monitoring systems. Managing these separate solutions can create additional work for caregivers who already have demanding responsibilities.

This wearable attempts to bring several important functions together. Health monitoring, emergency communication, location tracking, and voice logging can operate as part of one connected system. This integrated approach may help reduce the mental burden associated with coordinating care.

The founders' experience with Fitbit also provides a foundation for developing technology around everyday health and wellness. However, this product takes a different direction by focusing on family connection and safety. Its goal is not simply to measure fitness performance but to provide information that can help families understand how their loved ones are doing.

The platform can also encourage better communication between caregivers and family members. Instead of relying only on occasional conversations or manual updates, families can receive useful insights into changing routines. This may help them respond earlier when something appears unusual.

The company intends to continue developing human-focused solutions for family care. With its combination of connectivity, health sensing, and safety capabilities, the wearable represents a thoughtful direction for modern caregiving technology. Luffu Link ultimately demonstrates how wearable devices can move beyond fitness tracking and become practical tools for supporting families, encouraging independence, and creating stronger connections between loved ones.`;
                  handleChange('style_reference_sample', exampleText);
                  handleChange('style_reference_font', 'system-ui, -apple-system, sans-serif');
                  handleChange('style_reference_header', 'H1 with 3 Clean H2 Sections');
                  handleChange('style_reference_footer', 'Concluding Vision & Caregiver Impact');
                  handleChange('word_count_min', 550);
                  handleChange('word_count_max', 750);
                  handleChange('heading_structure', 'H1 Title, 3 Clean H2 Sections (Pure Semantic HTML)');
                  handleChange('include_takeaways', false);
                  handleChange('include_faq', false);
                  handleChange('include_disclaimer', false);
                }}
              >
                Load Example Post (MedlineReview Luffu Link)
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                onClick={() => {
                  handleChange('style_reference_sample', 'Recent Phase III multi-center trials demonstrated a 42% reduction in diagnostic latency when integrating deep learning convolutional networks with high-resolution cardiac MRI scans. Researchers observed marked improvements in myocardial infarction boundary detection without increasing false positive referral rates across diverse patient cohorts.');
                  handleChange('style_reference_font', 'Inter, -apple-system, sans-serif');
                  handleChange('style_reference_header', 'H1 with Category Eyebrow & Subtitle');
                  handleChange('style_reference_footer', 'Takeaways + Medical Citations + Clinical Disclaimer');
                }}
              >
                Load Clinical Sample
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                onClick={() => {
                  handleChange('style_reference_sample', 'The medical AI sector expanded rapidly this quarter following accelerated FDA approvals for foundation models in diagnostic pathology. Healthcare systems integrating multimodal clinical AI report 28% reductions in diagnostic turnaround times while maintaining physician review integrity.');
                  handleChange('style_reference_font', 'Merriweather, Georgia, serif');
                  handleChange('style_reference_header', 'Bold Editorial Header with Key Finding Lead');
                  handleChange('style_reference_footer', 'Summary Card + References Grid + Disclosures');
                }}
              >
                Load Editorial Sample
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                style={{ fontSize: '0.78rem', padding: '6px 10px' }}
                onClick={() => {
                  handleChange('style_reference_sample', '');
                }}
              >
                Clear
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Example Paragraph / Post Structure Template</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                {formData.style_reference_sample ? `${formData.style_reference_sample.length} characters` : 'No sample provided'}
              </span>
            </label>
            <textarea
              className="form-textarea"
              rows="4"
              value={formData.style_reference_sample || ''}
              onChange={e => handleChange('style_reference_sample', e.target.value)}
              placeholder="Paste an example paragraph, post layout, or phrasing style here (e.g., how the header begins, how evidence is cited, how sentences are structured, and how the conclusion is phrased)..."
              style={{ fontFamily: formData.style_reference_font || 'inherit', fontSize: '0.9rem' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Font & Typography Family</label>
              <select
                className="form-select"
                value={formData.style_reference_font || 'Inter, -apple-system, sans-serif'}
                onChange={e => handleChange('style_reference_font', e.target.value)}
              >
                <option value="Inter, -apple-system, sans-serif">Inter, -apple-system (Modern Clean Sans)</option>
                <option value="Merriweather, Georgia, serif">Merriweather, Georgia (Academic Editorial Serif)</option>
                <option value="Roboto, sans-serif">Roboto, Arial (Clinical & Technical)</option>
                <option value="'Outfit', sans-serif">Outfit (Vibrant Modern Tech)</option>
                <option value="'Playfair Display', serif">Playfair Display (Prestigious Journal)</option>
                <option value="system-ui, -apple-system, sans-serif">System Native (Apple SF Pro / Segoe UI)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Cloned Header Architecture</label>
              <select
                className="form-select"
                value={formData.style_reference_header || 'H1 with Category Eyebrow & Subtitle'}
                onChange={e => handleChange('style_reference_header', e.target.value)}
              >
                <option value="H1 with Category Eyebrow & Subtitle">H1 with Category Eyebrow & Subtitle</option>
                <option value="Bold Editorial Header with Key Finding Lead">Bold Editorial Header with Key Finding Lead</option>
                <option value="Academic Clinical Header with Date & Trial Phase">Academic Clinical Header with Date & Trial Phase</option>
                <option value="Question-Driven Explainer Header">Question-Driven Explainer Header</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Cloned Footer & Conclusion Structure</label>
              <select
                className="form-select"
                value={formData.style_reference_footer || 'Takeaways + Medical Citations + Clinical Disclaimer'}
                onChange={e => handleChange('style_reference_footer', e.target.value)}
              >
                <option value="Takeaways + Medical Citations + Clinical Disclaimer">Takeaways + Medical Citations + Clinical Disclaimer</option>
                <option value="Summary Card + References Grid + Disclosures">Summary Card + References Grid + Disclosures</option>
                <option value="Key Clinical Implications + Source Citations + Disclaimer">Key Clinical Implications + Source Citations + Disclaimer</option>
                <option value="Compact Source Footnotes + Editorial Sign-off">Compact Source Footnotes + Editorial Sign-off</option>
              </select>
            </div>
          </div>

          {/* Real-Time Cloned Preview */}
          <div style={{
            marginTop: '16px',
            padding: '16px 20px',
            borderRadius: '10px',
            background: 'rgba(15, 23, 42, 0.65)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            fontFamily: formData.style_reference_font || 'inherit'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#00f0ff', fontWeight: '600' }}>
                LIVE CLONED STYLE PREVIEW
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Font: {formData.style_reference_font || 'Inter'}
              </span>
            </div>

            <div style={{ borderLeft: '3px solid #00f0ff', paddingLeft: '14px', margin: '8px 0 12px 0' }}>
              <span style={{ fontSize: '0.75rem', color: '#6366f1', textTransform: 'uppercase', fontWeight: '600', display: 'block' }}>
                CLINICAL INNOVATION &bull; {formData.style_reference_header || 'H1 with Category Eyebrow & Subtitle'}
              </span>
              <h4 style={{ color: '#fff', fontSize: '1.1rem', margin: '4px 0 6px 0', fontWeight: '700' }}>
                Sample Cloned Headline: Multi-Center Trial Demonstrates Diagnostic Efficacy
              </h4>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: '1.6', margin: 0 }}>
                {formData.style_reference_sample || 'Your example paragraph will appear here. The generator will clone its exact phrasing rhythm, terminology density, and formatting.'}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: '#94a3b8', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '8px' }}>
              <span style={{ color: '#10b981' }}>✓ Footer Layout:</span> {formData.style_reference_footer || 'Takeaways + Medical Citations + Clinical Disclaimer'}
            </div>
          </div>
        </div>

        {/* Section 3: Style Guide & Disclaimers */}
        <div className="glass-card" style={{ padding: '24px', gridColumn: '1 / -1' }}>
          <h3 style={{ fontSize: '1.15rem', color: '#fff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} style={{ color: '#a5b4fc' }} /> Editorial Integrity & Legal Disclaimers
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div className="form-group">
              <label className="form-label">Custom Style Guide Directives</label>
              <textarea 
                className="form-textarea"
                rows="4"
                value={formData.style_guide_text || ''}
                onChange={e => handleChange('style_guide_text', e.target.value)}
                placeholder="Direct instructions the AI must follow on every run..."
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                E.g. Avoid sensational phrases like 'miracle cure'; specify trial phases; acknowledge limitations.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">Mandatory Medical Disclaimer Text</label>
              <textarea 
                className="form-textarea"
                rows="4"
                value={formData.disclaimer_text || ''}
                onChange={e => handleChange('disclaimer_text', e.target.value)}
                placeholder="Legal disclaimer to append to generated medical content..."
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Appended automatically in HTML and stored in WordPress custom meta.
              </span>
            </div>
          </div>

          {/* Yoast SEO 28.4 100% Green Compliance Guarantee */}
          <div style={{ 
            marginTop: '16px', 
            padding: '16px', 
            borderRadius: '10px', 
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <strong style={{ color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} style={{ color: '#10b981' }} />
                Yoast SEO 28.4 Channel: Enforce 100% Green Lights (Self-Healing Auto-Fix)
              </strong>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '4px' }}>
                {formData.enforce_yoast_green !== false
                  ? 'Active: Every generated draft is audited against Yoast Focus Keyphrase & Readability metrics. Any orange or red bullets are automatically fixed before queuing.' 
                  : 'Disabled: Drafts will be saved without the automatic self-healing Yoast optimization loop.'}
              </p>
            </div>

            <label className="toggle-switch">
              <input 
                type="checkbox" 
                checked={formData.enforce_yoast_green !== false}
                onChange={e => handleChange('enforce_yoast_green', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>

          {/* Publishing Policy / Review Gate */}
          <div style={{ 
            marginTop: '16px', 
            padding: '16px', 
            borderRadius: '10px', 
            background: 'rgba(99, 102, 241, 0.08)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <strong style={{ color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={16} style={{ color: '#f59e0b' }} />
                Publishing Flow Policy: Review Gate vs Auto-Push
              </strong>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '4px' }}>
                {formData.auto_push_to_wp 
                  ? 'Auto-Push Active: Verified drafts will immediately be dispatched to WordPress as draft posts.' 
                  : 'Dashboard Review Gate Active (Recommended): Drafts stay in this dashboard until you click "Approve & Push".'}
              </p>
            </div>

            <label className="toggle-switch">
              <input 
                type="checkbox" 
                checked={formData.auto_push_to_wp || false}
                onChange={e => handleChange('auto_push_to_wp', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>
    </form>
  );
}
