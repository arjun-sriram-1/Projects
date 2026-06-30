"""Shared styling for the Streamlit dashboard."""

from __future__ import annotations

import streamlit as st


CSS = """
<style>
:root {
  --canvas: #05070F;
  --sidebar: #0B0F19;
  --surface: #111827;
  --surface-raised: #151F32;
  --surface-soft: #0F1422;
  --surface-hover: #1F2937;
  --border: #1E293B;
  --border-fine: #111726;
  --terminal-accent: #38BDF8;
  --terminal-danger-accent: #FF3B6B;
  --text: #FFFFFF;
  --text-secondary: #C1C7D0;
  --text-muted: #8994A5;
  --code-text: #E2E8F0;
  --positive: #00E096;
  --info: #3B82F6;
  --warning: #F59E0B;
  --danger: #EF4444;
  --positive-soft: rgba(0, 224, 150, .10);
  --info-soft: rgba(59, 130, 246, .14);
  --warning-soft: rgba(245, 158, 11, .13);
  --danger-soft: rgba(239, 68, 68, .13);
}

/* App canvas and density */
html, body, [class*="css"] {
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  color: var(--text-secondary);
}
.stApp {
  background: var(--canvas);
}
[data-testid="stAppViewContainer"] {
  background: #090D16;
}
.block-container {
  padding-top: 1rem !important;
  padding-bottom: 1.25rem !important;
  padding-left: 1.35rem !important;
  padding-right: 1.35rem !important;
  max-width: 98% !important;
}
[data-testid="stHeader"] {
  background: rgba(5, 7, 15, .88);
  border-bottom: 1px solid var(--border-fine);
}
footer { visibility: hidden; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: #101827;
  border-right: 1px solid #2A3547;
}
[data-testid="stSidebar"] > div:first-child {
  padding-top: 1.25rem;
  padding-left: .75rem;
  padding-right: .75rem;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p:first-child {
  color: var(--text) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: var(--text-muted) !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius: 6px;
  padding: .65rem .7rem;
  margin-bottom: .35rem;
  min-height: 44px;
  border-left: 3px solid transparent;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
  background: var(--surface-hover);
}
[data-testid="stSidebar"] [role="radiogroup"] label span {
  color: var(--text-secondary) !important;
  font-weight: 740;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: #1F2937;
  border-left-color: var(--terminal-accent);
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) span {
  color: var(--text) !important;
}
[data-testid="stSidebar"] hr {
  border-color: var(--border);
}

/* Typography */
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6 {
  color: var(--text);
  letter-spacing: 0;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"] {
  color: var(--text-secondary);
}
[data-testid="stMarkdownContainer"] code,
pre, code {
  color: var(--code-text) !important;
  background: #0A0E18 !important;
  border: 1px solid var(--border-fine);
  border-radius: 6px;
}

/* Header and context */
.terminal-header-strip {
  display: grid;
  grid-template-columns: minmax(210px, .95fr) minmax(260px, 1.4fr) repeat(4, minmax(145px, auto)) minmax(92px, auto);
  gap: .9rem;
  align-items: center;
  background: #111827;
  border: 1px solid #2A3547;
  border-radius: 8px;
  padding: .9rem 1rem;
  margin-bottom: 1rem;
}
.terminal-brand {
  color: var(--terminal-accent);
  font-size: 1.14rem;
  font-weight: 850;
  white-space: nowrap;
}
.terminal-brand-mark {
  color: var(--terminal-accent);
  font-weight: 900;
  margin-right: .4rem;
}
.terminal-counterparty-select,
.terminal-meta-pill {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: .35rem;
  background: #1F2937;
  border: 1px solid #374151;
  border-radius: 7px;
  padding: .62rem .8rem;
  color: var(--text);
  font-weight: 760;
  overflow-wrap: anywhere;
}
.terminal-counterparty-select {
  position: relative;
  padding-right: 2rem;
}
.terminal-counterparty-select::after {
  content: "v";
  position: absolute;
  right: .78rem;
  color: var(--text-muted);
  font-size: 1rem;
}
.terminal-meta-pill {
  background: #111827;
}
.terminal-meta-pill span {
  color: var(--text-muted);
  font-weight: 520;
}
.terminal-meta-pill strong {
  color: var(--text);
  font-weight: 800;
}
.terminal-page-kicker {
  color: var(--text);
  font-size: 1.48rem;
  font-weight: 820;
  margin: .35rem 0 .14rem 0;
}
.terminal-page-question {
  color: var(--text-muted);
  font-size: .82rem;
  letter-spacing: .08em;
  text-transform: uppercase;
  margin-bottom: 1rem;
}
.terminal-copilot-rail {
  position: sticky;
  top: 1rem;
  min-height: calc(100vh - 8.5rem);
  background: #111827;
  border: 1px solid #2A3547;
  border-radius: 8px;
  padding: 1rem;
}
.terminal-copilot-title {
  color: var(--terminal-danger-accent);
  font-weight: 850;
  font-size: 1.08rem;
  margin-bottom: 1rem;
}
.terminal-copilot-message {
  background: #1F2937;
  border-left: 3px solid var(--terminal-accent);
  border-radius: 7px;
  color: var(--text);
  line-height: 1.5;
  padding: .9rem 1rem;
  font-size: .95rem;
}
.terminal-copilot-message strong {
  color: var(--text);
}
.terminal-copilot-context {
  display: grid;
  gap: .26rem;
  margin-top: .85rem;
  background: #0A0E18;
  border: 1px solid #374151;
  border-radius: 7px;
  padding: .72rem .78rem;
}
.terminal-copilot-context span {
  color: var(--text-muted);
  font-size: .72rem;
  font-weight: 820;
  text-transform: uppercase;
}
.terminal-copilot-context strong {
  color: var(--text);
  font-size: .92rem;
  line-height: 1.28;
}
.terminal-copilot-context em {
  color: var(--text-muted);
  font-style: normal;
  font-size: .8rem;
  line-height: 1.35;
}
.terminal-copilot-presets {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .5rem;
  margin-top: 1rem;
}
.terminal-copilot-presets div {
  color: var(--text-secondary);
  background: #1F2937;
  border: 1px solid #374151;
  border-radius: 6px;
  padding: .58rem .65rem;
  font-size: .84rem;
  overflow-wrap: anywhere;
}
.terminal-copilot-foot {
  margin-top: 1rem;
  border-top: 1px solid #2A3547;
  color: var(--text-muted);
  font-size: .84rem;
  line-height: 1.4;
  padding-top: .8rem;
}
.terminal-copilot-foot strong {
  color: var(--text);
}
.terminal-kpi-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  gap: .75rem;
  margin: .75rem 0 1rem 0;
}
.terminal-kpi-card {
  min-height: 112px;
  background: #111827;
  border: 1px solid #374151;
  border-radius: 7px;
  padding: .95rem 1rem;
  border-left: 3px solid transparent;
}
.terminal-kpi-ok { border-left-color: var(--positive); }
.terminal-kpi-info { border-left-color: var(--terminal-accent); }
.terminal-kpi-watch { border-left-color: var(--warning); }
.terminal-kpi-risk { border-left-color: var(--danger); }
.terminal-kpi-neutral { border-left-color: #374151; }
.terminal-kpi-label {
  color: #AEB8C8;
  font-size: .76rem;
  font-weight: 780;
  text-transform: uppercase;
  line-height: 1.35;
}
.terminal-kpi-value {
  color: var(--text);
  font-size: 1.55rem;
  font-weight: 850;
  line-height: 1.12;
  margin-top: .58rem;
  overflow-wrap: anywhere;
}
.terminal-kpi-helper {
  color: var(--text-muted);
  font-size: .78rem;
  line-height: 1.35;
  margin-top: .35rem;
}
.terminal-panel,
.terminal-decision-card,
.terminal-evidence-panel {
  background: #111827;
  border: 1px solid #374151;
  border-radius: 7px;
  padding: 1rem;
}
.terminal-panel-title,
.terminal-decision-label {
  color: #AEB8C8;
  font-size: .78rem;
  font-weight: 820;
  text-transform: uppercase;
  letter-spacing: .03em;
  border-bottom: 1px solid #374151;
  padding-bottom: .55rem;
  margin-bottom: .75rem;
}
.terminal-panel-subtitle {
  color: var(--text-muted);
  font-size: .84rem;
  line-height: 1.35;
  margin: -.35rem 0 .75rem 0;
}
.terminal-panel-body {
  color: var(--text-secondary);
}
.terminal-risk-row {
  display: grid;
  grid-template-columns: minmax(120px, 1fr) minmax(82px, 120px) 42px;
  gap: .65rem;
  align-items: center;
  padding: .48rem 0;
  border-top: 1px solid var(--border-fine);
}
.terminal-risk-row:first-child {
  border-top: 0;
}
.terminal-risk-row span {
  color: var(--text);
  font-size: .9rem;
  line-height: 1.35;
}
.terminal-risk-row strong {
  color: var(--text-secondary);
  font-size: .8rem;
  text-align: right;
}
.terminal-risk-meter {
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: #263244;
}
.terminal-risk-fill {
  height: 100%;
}
.terminal-risk-ok { background: var(--positive); }
.terminal-risk-info { background: var(--terminal-accent); }
.terminal-risk-watch { background: var(--warning); }
.terminal-risk-risk { background: var(--danger); }
.terminal-risk-neutral { background: var(--text-muted); }
.terminal-table-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid #263244;
  border-radius: 7px;
}
.terminal-compact-table {
  width: 100%;
  border-collapse: collapse;
  background: #0A0E18;
  color: var(--text-secondary);
  font-size: .84rem;
}
.terminal-compact-table th {
  background: #151F32;
  color: #AEB8C8;
  text-align: left;
  padding: .62rem .68rem;
  font-size: .74rem;
  font-weight: 820;
  text-transform: uppercase;
  border-bottom: 1px solid #374151;
  white-space: nowrap;
}
.terminal-compact-table td {
  padding: .62rem .68rem;
  border-bottom: 1px solid var(--border-fine);
  color: var(--text-secondary);
  vertical-align: top;
}
.terminal-compact-table tr:last-child td {
  border-bottom: 0;
}
.terminal-decision-card {
  border-left: 4px solid #374151;
}
.terminal-decision-ok { border-left-color: var(--positive); }
.terminal-decision-info { border-left-color: var(--terminal-accent); }
.terminal-decision-watch { border-left-color: var(--warning); }
.terminal-decision-risk { border-left-color: var(--danger); }
.terminal-decision-neutral { border-left-color: #374151; }
.terminal-decision-title {
  color: var(--text);
  font-size: 1.38rem;
  font-weight: 860;
  line-height: 1.18;
  margin-bottom: .8rem;
}
.terminal-decision-row,
.terminal-evidence-row {
  display: grid;
  grid-template-columns: minmax(110px, .85fr) minmax(90px, 1fr);
  gap: .75rem;
  align-items: baseline;
  border-top: 1px solid var(--border-fine);
  padding: .58rem 0;
}
.terminal-decision-row span,
.terminal-evidence-row span {
  color: var(--text-muted);
  font-size: .86rem;
}
.terminal-decision-row strong,
.terminal-evidence-row strong {
  color: var(--text);
  font-weight: 780;
  text-align: right;
  overflow-wrap: anywhere;
}
.terminal-decision-rationale {
  color: var(--text-secondary);
  line-height: 1.48;
  margin-top: .8rem;
  padding-top: .75rem;
  border-top: 1px solid var(--border-fine);
}
.terminal-evidence-row {
  grid-template-columns: minmax(100px, .75fr) minmax(110px, .95fr) minmax(120px, 1fr);
}
.terminal-evidence-row em {
  color: var(--text-muted);
  font-style: normal;
  font-size: .8rem;
  text-align: right;
}
.terminal-status-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 5px;
  padding: .25rem .5rem;
  font-size: .74rem;
  font-weight: 820;
  border: 1px solid transparent;
}
.terminal-status-ok { color: var(--positive); background: var(--positive-soft); border-color: rgba(0, 224, 150, .32); }
.terminal-status-info { color: var(--terminal-accent); background: var(--info-soft); border-color: rgba(56, 189, 248, .35); }
.terminal-status-watch { color: var(--warning); background: var(--warning-soft); border-color: rgba(245, 158, 11, .35); }
.terminal-status-risk { color: #FCA5A5; background: var(--danger-soft); border-color: rgba(239, 68, 68, .35); }
.terminal-status-neutral { color: var(--text-secondary); background: #0A0E18; border-color: #374151; }
.terminal-action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: .6rem;
}
.terminal-action-card {
  background: #0A0E18;
  border: 1px solid #374151;
  border-radius: 7px;
  padding: .72rem .78rem;
}
.terminal-action-card strong {
  display: block;
  color: var(--text);
  font-size: .9rem;
}
.terminal-action-card span {
  display: block;
  color: var(--text-muted);
  font-size: .8rem;
  line-height: 1.35;
  margin-top: .2rem;
}
.terminal-ingest-context {
  display: flex;
  justify-content: space-between;
  gap: .75rem;
  align-items: center;
  background: #0A0E18;
  border: 1px solid #374151;
  border-radius: 7px;
  padding: .7rem .85rem;
  margin-bottom: .8rem;
}
.terminal-ingest-context span {
  color: var(--text-muted);
  font-size: .76rem;
  font-weight: 820;
  text-transform: uppercase;
}
.terminal-ingest-context strong {
  color: var(--text);
  font-weight: 800;
  text-align: right;
  overflow-wrap: anywhere;
}
.terminal-ingest-note {
  display: grid;
  grid-template-columns: minmax(120px, .28fr) minmax(0, 1fr);
  gap: .75rem;
  align-items: start;
  border: 1px solid rgba(56, 189, 248, .28);
  background: rgba(59, 130, 246, .10);
  border-radius: 7px;
  padding: .75rem .85rem;
  margin-bottom: .85rem;
}
.terminal-ingest-note strong {
  color: var(--text);
}
.terminal-ingest-note span {
  color: var(--text-secondary);
  line-height: 1.4;
  font-size: .88rem;
}
.context-note {
  color: var(--text-muted);
  font-size: .9rem;
}
.section-header {
  margin: 1.1rem 0 .6rem 0;
}
.section-title {
  color: var(--text);
  font-size: 1.08rem;
  font-weight: 760;
}
.section-subtitle {
  color: var(--text-muted);
  font-size: .9rem;
  margin-top: .12rem;
}
.compact-bullet-list {
  margin-top: .55rem;
  padding-left: 1.1rem;
}
.compact-bullet-list li {
  color: var(--text-secondary);
  margin-bottom: .32rem;
}
.decision-panel-ok { border-color: rgba(0, 224, 150, .45); }
.decision-panel-watch { border-color: rgba(245, 158, 11, .48); }
.decision-panel-risk { border-color: rgba(239, 68, 68, .48); }
.decision-panel-info { border-color: rgba(59, 130, 246, .45); }
.decision-panel-neutral { border-color: var(--border); }
.main-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 1rem;
}
.main-title {
  color: var(--text);
  font-size: 1.55rem;
  font-weight: 780;
  margin: 0;
}
.main-subtitle {
  color: var(--text-muted);
  margin-top: .2rem;
  font-size: .92rem;
}
.context-bar {
  background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(11, 15, 25, .98));
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-secondary);
  padding: .85rem 1rem;
  margin-bottom: 1rem;
}
.context-bar strong {
  color: var(--text);
}

/* Cards and panels */
.panel, .kpi-card, .data-summary-card, .decision-panel, .chat-shell, .chat-user, .chat-assistant {
  background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(12, 16, 31, .98));
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: none;
}
.kpi-card {
  min-height: 112px;
  padding: .95rem 1rem;
  margin-bottom: .75rem;
}
.kpi-label {
  color: var(--text-muted);
  font-size: .72rem;
  font-weight: 760;
  letter-spacing: .05em;
  text-transform: uppercase;
}
.kpi-value {
  color: var(--text);
  margin-top: .3rem;
  font-size: 1.38rem;
  font-weight: 800;
  line-height: 1.16;
  overflow-wrap: anywhere;
}
.kpi-help {
  color: var(--text-muted);
  font-size: .78rem;
  line-height: 1.35;
  margin-top: .38rem;
}
.data-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: .75rem;
  margin-top: .75rem;
}
.data-summary-card, .decision-panel, .chat-shell, .chat-user, .chat-assistant {
  padding: .95rem 1rem;
}
.data-summary-title {
  color: var(--text);
  font-weight: 740;
  margin-bottom: .35rem;
}
.data-summary-copy {
  color: var(--text-secondary);
  font-size: .9rem;
  line-height: 1.45;
}
.decision-panel ul {
  margin-top: .5rem;
  padding-left: 1.1rem;
}
.decision-panel li {
  color: var(--text-secondary);
  margin-bottom: .35rem;
}

/* Status badges */
.status-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: .18rem .58rem;
  font-size: .76rem;
  font-weight: 760;
  border: 1px solid transparent;
  white-space: nowrap;
}
.status-ok { color: var(--positive); background: var(--positive-soft); border-color: rgba(0, 224, 150, .34); }
.status-info { color: #93C5FD; background: var(--info-soft); border-color: rgba(59, 130, 246, .38); }
.status-watch { color: var(--warning); background: var(--warning-soft); border-color: rgba(245, 158, 11, .38); }
.status-risk { color: #FCA5A5; background: var(--danger-soft); border-color: rgba(239, 68, 68, .38); }
.status-neutral { color: var(--text-secondary); background: var(--surface-soft); border-color: var(--border); }

/* Executive overview */
.executive-split {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, .95fr);
  gap: .9rem;
  align-items: start;
  margin-top: .25rem;
}
.executive-panel {
  background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(12, 16, 31, .98));
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1rem;
}
.executive-panel-title {
  color: var(--text);
  font-size: 1rem;
  font-weight: 760;
  margin-bottom: .65rem;
}
.alert-card {
  border: 1px solid var(--border);
  border-left: 3px solid var(--info);
  background: #0A0E18;
  border-radius: 6px;
  padding: .75rem .85rem;
  margin-bottom: .55rem;
}
.alert-card-risk { border-left-color: var(--danger); }
.alert-card-watch { border-left-color: var(--warning); }
.alert-card-ok { border-left-color: var(--positive); }
.alert-title {
  color: var(--text);
  font-weight: 720;
  margin-bottom: .2rem;
}
.alert-meta {
  color: var(--text-muted);
  font-size: .8rem;
  line-height: 1.35;
}
.posture-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .55rem;
  margin-top: .7rem;
}
.posture-item {
  background: #0A0E18;
  border: 1px solid var(--border-fine);
  border-radius: 6px;
  padding: .65rem .7rem;
}
.posture-label {
  color: var(--text-muted);
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .04em;
  font-weight: 740;
}
.posture-value {
  color: var(--text);
  font-size: .98rem;
  font-weight: 720;
  margin-top: .18rem;
}
.next-action-strip {
  margin-top: .8rem;
  padding: .7rem .8rem;
  border-radius: 6px;
  border: 1px solid rgba(245, 158, 11, .35);
  background: var(--warning-soft);
  color: var(--text-secondary);
  font-size: .9rem;
}
@media (max-width: 980px) {
  .executive-split { grid-template-columns: 1fr; }
  .posture-grid { grid-template-columns: 1fr; }
}
/* Phase UI-4: counterparty and credit decision */
.workflow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: .75rem;
  margin: .75rem 0 1rem 0;
}
.workflow-card {
  background: #0A0E18;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .8rem .85rem;
}
.workflow-card-ok { border-left: 3px solid var(--positive); }
.workflow-card-neutral { border-left: 3px solid var(--text-muted); }
.workflow-title {
  color: var(--text);
  font-weight: 740;
  margin-top: .45rem;
}
.workflow-copy {
  color: var(--text-muted);
  font-size: .82rem;
  line-height: 1.35;
  margin-top: .18rem;
}
.workspace-split, .decision-split {
  display: grid;
  grid-template-columns: minmax(0, .95fr) minmax(340px, 1.05fr);
  gap: .9rem;
  align-items: start;
  margin-top: .5rem;
}
.authorization-panel {
  background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(12, 16, 31, .98));
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1rem;
}
.authorization-panel-ok { border-left: 4px solid var(--positive); }
.authorization-panel-watch { border-left: 4px solid var(--warning); }
.authorization-panel-risk { border-left: 4px solid var(--danger); }
.authorization-panel-neutral { border-left: 4px solid var(--text-muted); }
.authorization-status {
  color: var(--text);
  font-size: 1.3rem;
  font-weight: 800;
  margin: .55rem 0 .35rem 0;
}
.authorization-limit {
  color: var(--positive);
  font-size: 1.65rem;
  font-weight: 820;
  line-height: 1.12;
}
.authorization-subgrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .55rem;
  margin-top: .8rem;
}
.security-badge {
  display: inline-flex;
  border: 1px solid rgba(245, 158, 11, .45);
  background: var(--warning-soft);
  color: var(--warning);
  border-radius: 6px;
  padding: .35rem .55rem;
  font-size: .82rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .03em;
  margin-top: .5rem;
}
.action-list {
  display: grid;
  gap: .55rem;
  margin-top: .65rem;
}
.action-item {
  background: #0A0E18;
  border: 1px solid var(--border-fine);
  border-radius: 6px;
  padding: .65rem .75rem;
}
.action-title {
  color: var(--text);
  font-weight: 720;
}
.action-copy {
  color: var(--text-muted);
  font-size: .84rem;
  line-height: 1.35;
  margin-top: .15rem;
}
@media (max-width: 980px) {
  .workspace-split, .decision-split { grid-template-columns: 1fr; }
  .authorization-subgrid { grid-template-columns: 1fr; }
}
/* Phase UI-5: financial extraction and model pages */
.audit-panel, .ledger-panel, .model-comparison {
  background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(10, 14, 24, .98));
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: .8rem;
}
.audit-eyebrow, .model-comparison-title, .ratio-group-title {
  color: var(--text-muted);
  font-size: .72rem;
  font-weight: 780;
  letter-spacing: .06em;
  text-transform: uppercase;
}
.audit-title {
  color: var(--text);
  font-size: 1.24rem;
  font-weight: 820;
  margin-top: .24rem;
}
.audit-status {
  margin: .65rem 0;
}
.audit-row, .ledger-row, .ratio-item, .model-detail-item, .loss-item {
  display: flex;
  justify-content: space-between;
  gap: .75rem;
  align-items: baseline;
  border-top: 1px solid var(--border-fine);
  padding: .58rem 0;
}
.audit-row span, .ledger-label, .ratio-item span, .model-detail-item span, .loss-item span {
  color: var(--text-muted);
  font-size: .86rem;
}
.audit-row strong, .ledger-value, .ratio-item strong, .model-detail-item strong, .loss-item strong {
  color: var(--text);
  font-weight: 780;
  text-align: right;
  overflow-wrap: anywhere;
}
.audit-note {
  color: var(--text-muted);
  font-size: .82rem;
  line-height: 1.4;
  margin-top: .7rem;
}
.ledger-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 .9rem;
}
.ratio-grid, .model-node-grid, .model-detail-grid, .loss-panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: .75rem;
  margin: .75rem 0 1rem 0;
}
.ratio-group, .model-node, .model-detail-item, .loss-item {
  background: #0A0E18;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .8rem .85rem;
}
.ratio-item, .model-detail-item, .loss-item {
  margin-top: .4rem;
  border-top-color: var(--border-fine);
}
.model-node-label {
  color: var(--text-muted);
  font-size: .74rem;
  font-weight: 760;
  letter-spacing: .05em;
  text-transform: uppercase;
}
.model-node-value {
  color: var(--text);
  font-size: 1.35rem;
  font-weight: 840;
  margin-top: .28rem;
}
.model-node-help {
  color: var(--text-muted);
  font-size: .8rem;
  line-height: 1.35;
  margin-top: .2rem;
}
.model-divergence {
  color: var(--text-secondary);
  border-top: 1px solid var(--border-fine);
  margin-top: .8rem;
  padding-top: .72rem;
}
.warning-callout, .success-callout {
  border-radius: 6px;
  padding: .82rem .95rem;
  margin: .75rem 0;
  border: 1px solid rgba(245, 158, 11, .38);
  background: var(--warning-soft);
  color: var(--text-secondary);
}
.success-callout {
  border-color: rgba(0, 224, 150, .35);
  background: var(--positive-soft);
}
.warning-callout strong, .success-callout strong {
  color: var(--text);
}
.warning-callout p, .success-callout p {
  color: var(--text-secondary);
  margin: .22rem 0 0 0;
  font-size: .88rem;
  line-height: 1.4;
}
@media (max-width: 900px) {
  .ledger-panel { grid-template-columns: 1fr; }
}
/* Phase UI-6: market intelligence and tail-risk pages */
.market-factor-grid, .scenario-shock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: .75rem;
  margin: .75rem 0 1rem 0;
}
.market-factor-item, .scenario-shock-item, .scenario-detail-panel {
  background: #0A0E18;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .8rem .85rem;
}
.market-factor-item, .scenario-shock-item, .scenario-detail-row {
  display: flex;
  justify-content: space-between;
  gap: .75rem;
  align-items: baseline;
  border-top: 1px solid var(--border-fine);
  padding: .56rem 0;
}
.market-factor-item:first-child, .scenario-shock-item:first-child, .scenario-detail-row:first-child {
  border-top: 0;
}
.market-factor-item span, .scenario-shock-item span, .scenario-detail-row span {
  color: var(--text-muted);
  font-size: .86rem;
}
.market-factor-item strong, .scenario-shock-item strong, .scenario-detail-row strong {
  color: var(--text);
  font-weight: 780;
  text-align: right;
  overflow-wrap: anywhere;
}
.scenario-detail-panel {
  margin: .9rem 0;
}
.scenario-shock-grid {
  margin-bottom: 0;
}
.simulation-control-strip {
  background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(10, 14, 24, .98));
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .85rem;
  margin-bottom: .85rem;
}
/* Phase UI-7: monitoring and validation */
.monitoring-alert-grid, .validation-check-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: .75rem;
  margin: .75rem 0 1rem 0;
}
.validation-check-item {
  display: flex;
  justify-content: space-between;
  gap: .75rem;
  align-items: center;
  background: #0A0E18;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .72rem .85rem;
}
.validation-check-item span {
  color: var(--text-secondary);
  font-size: .88rem;
  overflow-wrap: anywhere;
}
/* Phase UI-8/9: copilot and reporting */
.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: .75rem;
  margin: .75rem 0 .35rem 0;
}
.suggestion-card, .export-result-panel, .memo-output-panel {
  background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(10, 14, 24, .98));
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .9rem .95rem;
}
.suggestion-title, .export-result-title {
  color: var(--text);
  font-weight: 760;
  line-height: 1.3;
}
.suggestion-copy {
  color: var(--text-muted);
  font-size: .82rem;
  line-height: 1.35;
  margin-top: .25rem;
}
.export-result-panel {
  margin: .8rem 0;
}
.export-file-row {
  display: flex;
  justify-content: space-between;
  gap: .75rem;
  align-items: baseline;
  border-top: 1px solid var(--border-fine);
  padding: .58rem 0;
}
.export-file-row:first-of-type {
  margin-top: .5rem;
}
.export-file-row span {
  color: var(--text-muted);
  font-size: .84rem;
}
.export-file-row strong {
  color: var(--text-secondary);
  font-weight: 680;
  text-align: right;
  overflow-wrap: anywhere;
}
.memo-output-panel {
  margin-top: .8rem;
}
.memo-output-panel p, .memo-output-panel li {
  color: var(--text-secondary);
}
/* Inputs */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
  background: #0A0E18 !important;
  color: var(--text) !important;
  border-color: var(--border) !important;
  border-radius: 6px !important;
}
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus,
[data-baseweb="select"] > div:focus-within {
  border-color: var(--info) !important;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, .45) !important;
}
[data-baseweb="popover"] div,
[data-baseweb="menu"] {
  background: var(--surface) !important;
  color: var(--text-secondary) !important;
  border-color: var(--border) !important;
}
.stSlider [data-baseweb="slider"] div {
  color: var(--text-secondary);
}
.stFileUploader section {
  background: #0A0E18;
  border: 1px dashed var(--border);
  border-radius: 6px;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
button[kind="primary"] {
  background: linear-gradient(180deg, #1D4ED8, #1E40AF) !important;
  border: 1px solid rgba(59, 130, 246, .55) !important;
  border-radius: 6px !important;
  color: #FFFFFF !important;
  font-weight: 700 !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
  background: linear-gradient(180deg, #2563EB, #1D4ED8) !important;
  border-color: rgba(147, 197, 253, .72) !important;
  color: #FFFFFF !important;
}
.stButton > button:disabled,
.stDownloadButton > button:disabled {
  background: #111827 !important;
  border-color: var(--border) !important;
  color: var(--text-muted) !important;
}

/* Tabs and expanders */
.stTabs [data-baseweb="tab-list"] {
  gap: .25rem;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
  color: var(--text-muted);
  border-radius: 6px 6px 0 0;
}
.stTabs [aria-selected="true"] {
  color: var(--text) !important;
  background: var(--surface-raised);
}
.streamlit-expanderHeader,
[data-testid="stExpander"] summary {
  background: var(--surface-soft) !important;
  color: var(--text) !important;
  border-radius: 6px !important;
}
[data-testid="stExpander"] {
  border-color: var(--border) !important;
}

/* Tables and dataframes */
.stDataFrame,
[data-testid="stDataFrame"] {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
}
[data-testid="stTable"] table,
[data-testid="stDataFrame"] table {
  background: var(--surface);
  color: var(--text-secondary);
}
[data-testid="stTable"] th,
[data-testid="stDataFrame"] th {
  background: var(--surface-raised) !important;
  color: var(--text-muted) !important;
  font-size: .78rem;
  font-weight: 750;
  text-transform: uppercase;
}
[data-testid="stTable"] td,
[data-testid="stDataFrame"] td {
  color: var(--text-secondary) !important;
  border-color: var(--border-fine) !important;
}

/* Alerts */
[data-testid="stAlert"] {
  border-radius: 6px;
  border: 1px solid var(--border);
  color: var(--text-secondary);
}
[data-testid="stAlert"] div {
  color: inherit;
}

/* Charts and iframes */
.js-plotly-plot,
[data-testid="stVegaLiteChart"],
[data-testid="stPlotlyChart"] {
  background: var(--surface) !important;
  border-radius: 6px;
}
iframe {
  background: var(--surface) !important;
}

/* Chat */
.chat-user { background: var(--info-soft); }
.chat-assistant { background: var(--surface); }
[data-testid="stChatMessage"] {
  background: transparent;
}

/* Scrollbars */
*::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
*::-webkit-scrollbar-track {
  background: #080C16;
}
*::-webkit-scrollbar-thumb {
  background: #263244;
  border-radius: 999px;
}
*::-webkit-scrollbar-thumb:hover {
  background: #334155;
}

@media (max-width: 1024px) {
  .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
  .kpi-card { min-height: 104px; }
  .terminal-header-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .terminal-brand {
    grid-column: 1 / -1;
  }
  .terminal-copilot-rail {
    position: static;
    min-height: auto;
  }
}
@media (max-width: 768px) {
  .main-header { flex-direction: column; }
  .main-title { font-size: 1.25rem; }
  .main-subtitle { font-size: .86rem; }
  .context-bar { font-size: .9rem; }
  .kpi-card { padding: .75rem; min-height: 96px; }
  .kpi-value { font-size: 1.1rem; }
  .status-badge { white-space: normal; }
  .terminal-header-strip {
    grid-template-columns: 1fr;
  }
  .terminal-page-kicker {
    font-size: 1.22rem;
  }
  .terminal-copilot-presets {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 430px) {
  .block-container { padding-left: .65rem !important; padding-right: .65rem !important; }
  .main-title { font-size: 1.1rem; }
  .kpi-label, .kpi-help { font-size: .72rem; }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)







