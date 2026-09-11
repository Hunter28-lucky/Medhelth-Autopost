import React, { useState, useEffect } from 'react';
import { 
  Play, Clock, Calendar, RefreshCw, 
  Terminal, ChevronRight, ChevronDown, Zap 
} from 'lucide-react';

export default function RunControlsAndLogs({ 
  topics, 
  runLogs, 
  schedulerStatus, 
  onTriggerRun, 
  onRefresh, 
  onToggleScheduler 
}) {
  const [selectedTopicId, setSelectedTopicId] = useState('');
  const [isTriggering, setIsTriggering] = useState(false);
  const [expandedRunId, setExpandedRunId] = useState(null);

  const handleRunTopic = async (topicId = null) => {
    setIsTriggering(true);
    try {
      await onTriggerRun(topicId ? parseInt(topicId) : null);
      setTimeout(onRefresh, 1500);
    } catch (err) {
      alert('Failed to trigger run: ' + err.message);
    } finally {
      setIsTriggering(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLETED':
        return <span className="badge badge-emerald">Completed</span>;
      case 'RUNNING':
        return <span className="badge badge-cyan"><RefreshCw size={10} className="animate-spin" /> In Progress</span>;
      case 'FAILED':
        return <span className="badge badge-rose">Failed</span>;
      case 'DUPLICATE_STOPPED':
        return <span className="badge badge-amber">Duplicate Halted</span>;
      default:
        return <span className="badge badge-indigo">{status}</span>;
    }
  };

  const getStepLevelColor = (level) => {
    switch (level) {
      case 'warning': return '#f59e0b';
      case 'error': return '#f43f5e';
      default: return '#38bdf8';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div>
        <h2 style={{ fontSize: '1.5rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
          Execution Controls & Audit Trail <span className="badge badge-indigo">Pipeline Engine</span>
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Trigger immediate runs, configure recurring cron schedules, and inspect detailed execution traces.
        </p>
      </div>

      {/* Control Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
        {/* Manual Trigger Panel */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1.15rem', color: '#fff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={18} style={{ color: '#00f0ff' }} /> On-Demand Trigger
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '16px' }}>
            Fetch fresh news, verify deduplication, and draft articles immediately.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <button 
              className="btn btn-primary"
              style={{ width: '100%', padding: '12px' }}
              onClick={() => handleRunTopic(null)}
              disabled={isTriggering}
            >
              <Play size={16} /> Run All Active Topics ({topics.filter(t => t.is_active).length})
            </button>

            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
              <select 
                className="form-select"
                value={selectedTopicId}
                onChange={e => setSelectedTopicId(e.target.value)}
                style={{ flex: 1 }}
              >
                <option value="">-- Choose specific topic --</option>
                {topics.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.name} (Weight: {t.weight})
                  </option>
                ))}
              </select>

              <button 
                className="btn btn-secondary"
                onClick={() => selectedTopicId && handleRunTopic(selectedTopicId)}
                disabled={!selectedTopicId || isTriggering}
              >
                Run Topic
              </button>
            </div>
          </div>
        </div>

        {/* Scheduler Panel */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ fontSize: '1.15rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={18} style={{ color: '#10b981' }} /> Automated Background Scheduler
            </h3>

            <label className="toggle-switch">
              <input 
                type="checkbox" 
                checked={schedulerStatus?.is_running || false}
                onChange={e => onToggleScheduler(e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>

          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '16px' }}>
            Selects active topics using weighted random priority (topics with higher weight run more often).
          </p>

          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Scheduler State:</span>
              <strong style={{ color: schedulerStatus?.is_running ? '#34d399' : '#94a3b8' }}>
                {schedulerStatus?.is_running ? 'Active (Running in background)' : 'Paused'}
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Interval:</span>
              <strong style={{ color: '#fff' }}>Every {schedulerStatus?.interval_hours || 6} hours</strong>
            </div>

            {schedulerStatus?.next_run_time && (
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Next Run:</span>
                <strong style={{ color: '#38bdf8' }}>{new Date(schedulerStatus.next_run_time).toLocaleTimeString()}</strong>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Execution History Table */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.2rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={18} style={{ color: '#a5b4fc' }} /> Recent Execution History
          </h3>
          <button className="btn btn-ghost" onClick={onRefresh} title="Refresh Logs">
            <RefreshCw size={15} /> Refresh
          </button>
        </div>

        {runLogs.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '20px' }}>
            No run history available yet. Click "Run All Active Topics" to initiate the pipeline.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {runLogs.map(log => {
              const isExpanded = expandedRunId === log.run_id;
              return (
                <div 
                  key={log.id} 
                  style={{ 
                    background: 'rgba(255,255,255,0.02)', 
                    border: '1px solid var(--border-subtle)', 
                    borderRadius: '8px', 
                    overflow: 'hidden' 
                  }}
                >
                  <div 
                    style={{ 
                      padding: '12px 16px', 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      cursor: 'pointer',
                      flexWrap: 'wrap',
                      gap: '10px'
                    }}
                    onClick={() => setExpandedRunId(isExpanded ? null : log.run_id)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      <div>
                        <strong style={{ color: '#fff', fontSize: '0.95rem' }}>{log.topic_name}</strong>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '8px' }}>
                          ID: {log.run_id.substring(0, 8)} &bull; {new Date(log.started_at).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                      <span className="badge badge-indigo" style={{ fontSize: '0.7rem' }}>{log.trigger_type}</span>
                      {getStatusBadge(log.status)}
                    </div>
                  </div>

                  {/* Step by Step Trace Drawer */}
                  {isExpanded && (
                    <div style={{ 
                      background: 'rgba(0,0,0,0.4)', 
                      padding: '16px 20px', 
                      borderTop: '1px solid var(--border-subtle)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.8rem'
                    }}>
                      <div style={{ marginBottom: '10px', color: 'var(--text-secondary)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                        Pipeline Execution Steps ({log.step_logs?.length || 0})
                      </div>

                      {log.step_logs?.map((step, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '12px', marginBottom: '6px', lineHeight: 1.4 }}>
                          <span style={{ color: 'var(--text-muted)', minWidth: '70px' }}>
                            {new Date(step.timestamp).toLocaleTimeString().split(' ')[0]}
                          </span>
                          <span style={{ color: getStepLevelColor(step.level), fontWeight: '600', minWidth: '130px' }}>
                            [{step.step}]
                          </span>
                          <span style={{ color: '#e2e8f0' }}>{step.message}</span>
                        </div>
                      ))}

                      {log.error_message && (
                        <div style={{ color: '#fb7185', marginTop: '10px', background: 'rgba(244,63,94,0.1)', padding: '8px 12px', borderRadius: '4px' }}>
                          <strong>Error:</strong> {log.error_message}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
