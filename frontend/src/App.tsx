import React, { useState } from 'react';
import './index.css';

// We will extract these to separate files in the next steps
const Sidebar = () => (
  <aside className="sidebar">
    <div style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid var(--border-color)' }}>
      <div style={{ width: '32px', height: '32px', background: '#d97706', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px' }}>🐰</div>
      <div>
        <div className="font-bold text-sm">PancakeSwap</div>
        <div className="text-xs text-green">Prediction Bot</div>
      </div>
    </div>
    
    <nav style={{ padding: '16px 8px', flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {['Dashboard', 'Auto Trading', 'Manual Trading', 'Strategies', 'AI Predictor', 'Market Analysis', 'Performance', 'Transactions', 'Logs', 'Settings'].map((item, i) => (
        <div key={item} style={{ 
          padding: '10px 16px', 
          borderRadius: '6px', 
          cursor: 'pointer',
          background: i === 0 ? 'var(--bg-panel-hover)' : 'transparent',
          borderLeft: i === 0 ? '3px solid var(--accent-green)' : '3px solid transparent',
          color: i === 0 ? 'var(--text-main)' : 'var(--text-muted)'
        }} className="text-sm font-semibold hover:bg-[var(--bg-panel-hover)]">
          {item}
        </div>
      ))}
    </nav>

    <div style={{ padding: '16px', borderTop: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div className="flex justify-between items-center text-xs">
        <span className="text-muted">Bot Status:</span>
        <span className="text-green font-bold">RUNNING</span>
      </div>
      <div className="flex justify-between items-center text-xs text-muted mb-2">
        <span>Uptime</span>
        <span>02:45:17</span>
      </div>
      <button className="btn btn-red w-full" style={{ padding: '8px', width: '100%' }}>Stop Bot</button>
    </div>
  </aside>
);

const TopStats = () => (
  <div style={{ display: 'flex', gap: '16px', padding: '16px', borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--bg-panel)' }}>
    <div className="flex-1 flex gap-4">
      <div>
        <div className="text-xs text-muted mb-1 text-uppercase">Balance (BNB)</div>
        <div className="text-lg font-bold">2.5834 BNB</div>
        <div className="text-xs text-muted">$1,632.45</div>
      </div>
      <div style={{ width: '1px', background: 'var(--border-color)', margin: '0 8px' }}></div>
      <div>
        <div className="text-xs text-muted mb-1">Winnings (24h)</div>
        <div className="text-lg font-bold">0.3546 BNB</div>
        <div className="text-xs text-muted">$223.77</div>
      </div>
      <div style={{ width: '1px', background: 'var(--border-color)', margin: '0 8px' }}></div>
      <div>
        <div className="text-xs text-muted mb-1">Win Rate</div>
        <div className="text-lg font-bold text-main">76.42%</div>
      </div>
      <div style={{ width: '1px', background: 'var(--border-color)', margin: '0 8px' }}></div>
      <div>
        <div className="text-xs text-muted mb-1">Profit (24h)</div>
        <div className="text-lg font-bold text-green">+0.3546 BNB</div>
        <div className="text-xs text-green">+15.87%</div>
      </div>
      <div style={{ width: '1px', background: 'var(--border-color)', margin: '0 8px' }}></div>
      <div>
        <div className="text-xs text-muted mb-1">Total Profit</div>
        <div className="text-lg font-bold">1.1032 BNB</div>
        <div className="text-xs text-muted">$695.01</div>
      </div>
    </div>
    
    <div className="flex gap-4 items-center">
      <div className="flex-col gap-1">
        <div className="text-xs text-muted">BOT MODE</div>
        <div className="text-sm text-green flex items-center gap-1"><span>🤖</span> Fully Automated</div>
      </div>
      <div style={{ width: '1px', height: '100%', background: 'var(--border-color)' }}></div>
      <div className="flex-col gap-1">
        <div className="text-xs text-muted">CONNECTION</div>
        <div className="text-sm flex items-center gap-2"><div style={{width:'8px',height:'8px',borderRadius:'50%',background:'var(--accent-green)'}}></div> BSC Network</div>
        <div className="text-xs text-muted text-right">128 ms</div>
      </div>
    </div>
  </div>
);

function App() {
  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-content">
        <TopStats />
        
        {/* Main Grid Placeholder */}
        <div style={{ flex: 1, padding: '16px', display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '16px', overflowY: 'auto' }}>
          
          {/* Left Column */}
          <div className="flex-col gap-4">
            <div className="panel" style={{ flex: 1.5 }}>
              <div className="panel-header">Live Prediction Chart <span className="text-muted" style={{textTransform: 'none', fontWeight: 'normal'}}>Round ID: 3456789</span></div>
              <div className="text-2xl font-bold text-main mb-2">00:12 <span className="text-xs text-muted font-normal ml-2">Time Left</span></div>
              <div className="flex-1 border border-[var(--border-color)] rounded mb-3 relative flex items-center justify-center overflow-hidden" style={{ background: '#0d1117' }}>
                 <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
                   <path d="M0,80 L10,70 L20,85 L30,60 L40,65 L50,40 L60,50 L70,30 L80,35 L90,20 L100,25" stroke="var(--accent-blue)" strokeWidth="1.5" fill="none" />
                   <circle cx="100" cy="25" r="3" fill="var(--accent-blue)" />
                 </svg>
              </div>
              <div className="flex gap-3">
                <button className="btn btn-green flex-1 flex-col items-center py-2" style={{ border: 'none' }}>
                  <div className="font-bold text-sm">Predict UP ↑</div>
                  <div className="text-xs opacity-90 mt-1" style={{ color: '#000' }}>1.28x | Payout 1.90x</div>
                </button>
                <button className="btn btn-red flex-1 flex-col items-center py-2" style={{ border: 'none' }}>
                  <div className="font-bold text-sm text-white">Predict DOWN ↓</div>
                  <div className="text-xs opacity-90 mt-1 text-white">1.28x | Payout 1.90x</div>
                </button>
              </div>
            </div>
            
            <div className="panel" style={{ flex: 1 }}>
              <div className="panel-header mb-2">Automated Settings</div>
              <div className="flex-col gap-1 mt-1">
                <div className="flex justify-between items-center py-2">
                  <span className="text-main font-semibold text-xs">Auto Trading</span>
                  <div className="toggle-switch on"></div>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-main font-semibold text-xs">Auto Prediction</span>
                  <div className="toggle-switch on"></div>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-main font-semibold text-xs">Risk Management</span>
                  <div className="toggle-switch on"></div>
                </div>
                
                <div className="flex justify-between items-center py-2 mt-2">
                  <span className="text-muted font-semibold text-xs">Martingale</span>
                  <span className="text-main px-2 py-1 rounded text-xs" style={{ background: '#0d1117', border: '1px solid var(--border-color)' }}>Level: 3 ▾</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-muted font-semibold text-xs">Take Profit</span>
                  <span className="text-main px-2 py-1 rounded text-xs" style={{ background: '#0d1117', border: '1px solid var(--border-color)' }}>0.0500 BNB</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-muted font-semibold text-xs">Stop Loss</span>
                  <span className="text-main px-2 py-1 rounded text-xs" style={{ background: '#0d1117', border: '1px solid var(--border-color)' }}>0.0300 BNB</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-muted font-semibold text-xs">Max Bet Amount</span>
                  <span className="text-main px-2 py-1 rounded text-xs" style={{ background: '#0d1117', border: '1px solid var(--border-color)' }}>0.1000 BNB</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-muted font-semibold text-xs">Win Chance (%)</span>
                  <span className="text-main px-2 py-1 rounded text-xs" style={{ background: '#0d1117', border: '1px solid var(--border-color)' }}>65.00%+ ▾</span>
                </div>
              </div>
            </div>
          </div>

          {/* Middle Column */}
          <div className="flex-col gap-4">
            <div className="panel" style={{ flex: 1 }}>
              <div className="panel-header">AI Prediction</div>
              <div className="flex gap-4 items-center mb-4 mt-2">
                <div style={{ width: '80px', height: '80px', borderRadius: '50%', border: '2px solid var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '32px', boxShadow: '0 0 15px rgba(59,130,246,0.3)' }}>
                  🧠
                </div>
                <div className="flex-col gap-1">
                  <div className="text-muted text-xs">Prediction</div>
                  <div className="text-2xl font-bold text-green flex items-center gap-2">UP ↑</div>
                  <div className="text-muted text-xs mt-1">Confidence</div>
                  <div className="text-xl font-bold text-main">78.56%</div>
                </div>
              </div>
              <div className="text-xs text-muted mb-1">AI Model</div>
              <div className="text-sm font-semibold mb-4">NeuralNet v2.3</div>
              
              <div className="text-xs text-muted mb-1">Analysis</div>
              <div className="text-sm font-semibold mb-2">Bullish Momentum</div>
              <div className="flex items-center gap-2">
                <div style={{ flex: 1, height: '4px', background: '#0d1117', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '78%', height: '100%', background: 'var(--accent-green)' }}></div>
                </div>
                <div className="text-xs font-bold">78%</div>
              </div>
            </div>

            <div className="panel" style={{ flex: 1 }}>
              <div className="panel-header">Performance (24H)</div>
              <div className="flex-1 relative flex items-end mb-2 mt-2" style={{ minHeight: '120px' }}>
                 <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
                   <path d="M0,90 L10,85 L20,88 L30,75 L40,80 L50,60 L60,55 L70,45 L80,50 L90,20 L100,10" stroke="var(--accent-green)" strokeWidth="1.5" fill="none" />
                 </svg>
                 <div className="absolute bottom-0 left-0 right-0 border-t border-[var(--border-color)]"></div>
                 <div className="absolute left-0 top-0 bottom-0 border-l border-[var(--border-color)]"></div>
              </div>
              
              <div className="grid grid-cols-3 gap-2 mt-2 pt-2 border-t border-[var(--border-color)] flex justify-between">
                <div>
                  <div className="text-xs text-muted">Profit</div>
                  <div className="text-sm font-bold text-green">+0.3546 BNB</div>
                </div>
                <div>
                  <div className="text-xs text-muted">ROI</div>
                  <div className="text-sm font-bold text-green">+15.87%</div>
                </div>
                <div>
                  <div className="text-xs text-muted">Wagers</div>
                  <div className="text-sm font-bold">2.2334 BNB</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="flex-col gap-4">
            <div className="panel" style={{ flex: 1 }}>
              <div className="panel-header">Recent Trades</div>
              <div className="flex-col gap-2 mt-2">
                {[
                  { dir: 'UP', icon: '↑', color: 'green', mult: '1.23x', status: 'WIN', prof: '+0.0201 BNB' },
                  { dir: 'UP', icon: '↑', color: 'green', mult: '1.45x', status: 'WIN', prof: '+0.0243 BNB' },
                  { dir: 'DOWN', icon: '↓', color: 'red', mult: '0.85x', status: 'WIN', prof: '+0.0187 BNB' },
                  { dir: 'UP', icon: '↑', color: 'green', mult: '1.67x', status: 'WIN', prof: '+0.0302 BNB' },
                  { dir: 'UP', icon: '↑', color: 'green', mult: '1.31x', status: 'LOSE', prof: '-0.0200 BNB', statusColor: 'red' },
                  { dir: 'DOWN', icon: '↓', color: 'red', mult: '0.92x', status: 'WIN', prof: '+0.0184 BNB' },
                  { dir: 'UP', icon: '↑', color: 'green', mult: '1.56x', status: 'WIN', prof: '+0.0278 BNB' },
                  { dir: 'UP', icon: '↑', color: 'green', mult: '1.19x', status: 'WIN', prof: '+0.0190 BNB' }
                ].map((t, i) => (
                  <div key={i} className="flex justify-between items-center text-xs py-1.5 border-b border-[var(--border-color)] last:border-0">
                    <span className={`text-${t.color} font-bold w-12 flex items-center gap-1`}>{t.icon} {t.dir}</span>
                    <span className="text-muted w-12 text-center">{t.mult}</span>
                    <span className={`text-${t.statusColor || 'green'} font-bold w-12 text-center`}>{t.status}</span>
                    <span className={`text-${t.statusColor || 'green'} font-bold text-right flex-1`}>{t.prof}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="panel" style={{ flex: 1 }}>
              <div className="panel-header">Bot Logs</div>
              <div className="flex-1 bg-[#0d1117] border border-[var(--border-color)] rounded p-3 overflow-y-auto font-mono text-[10px] text-muted flex-col gap-1 mt-2">
                <div className="flex gap-2"><span className="opacity-50">12:14:18</span><span>Prediction: UP (Confidence: 78.56%)</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:14:10</span><span className="text-green">Round 3456788 - WIN - 1.23x</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:13:58</span><span>New round started: 3456789</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:13:45</span><span>Prediction: UP (Confidence: 81.12%)</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:13:37</span><span className="text-green">Round 3456787 - WIN - 1.45x</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:13:25</span><span>New round started: 3456788</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:13:12</span><span>Prediction: DOWN (Confidence: 65.23%)</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:13:04</span><span className="text-green">Round 3456786 - WIN - 0.85x</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:12:38</span><span>New round started: 3456787</span></div>
                <div className="flex gap-2"><span className="opacity-50">12:12:25</span><span>Bot started successfully</span></div>
              </div>
              <div className="mt-3 text-center">
                <button className="btn w-full py-1.5 text-xs font-semibold">Clear Logs</button>
              </div>
            </div>
          </div>

        </div>
        
        {/* Footer */}
        <div style={{ padding: '8px 16px', background: 'var(--bg-panel)', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
          <div className="flex items-center gap-2">
            <span>🐰 PancakeSwap Prediction Bot</span>
            <span>|</span>
            <span>Automated. Intelligent. Profitable.</span>
          </div>
          <div className="flex gap-4">
            <span className="text-green flex items-center gap-1">✓ Secure</span>
            <span className="text-green flex items-center gap-1">✓ Reliable</span>
            <span className="text-green flex items-center gap-1">✓ Profitable</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
