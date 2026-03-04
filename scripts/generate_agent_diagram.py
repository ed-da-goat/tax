#!/usr/bin/env python3
"""
Generate the Agent Architecture Diagram for the Georgia CPA Accounting System.
Produces a PNG image showing all agents, their roles, and how they interact.

Usage:
    python3 scripts/generate_agent_diagram.py
    # or with the temp venv:
    /tmp/diagram_venv/bin/python3 scripts/generate_agent_diagram.py
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np


def draw_agent_box(ax, x, y, w, h, title, subtitle, color, text_color='white', fontsize=9):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                         facecolor=color, edgecolor='#333333', linewidth=1.5,
                         alpha=0.95)
    ax.add_patch(box)
    ax.text(x + w/2, y + h - 0.03, title, ha='center', va='top',
            fontsize=fontsize, fontweight='bold', color=text_color)
    ax.text(x + w/2, y + h - 0.07, subtitle, ha='center', va='top',
            fontsize=6, color=text_color, alpha=0.85, style='italic')


def draw_phase_box(ax, x, y, w, h, title, modules, color, text_color='white'):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01",
                         facecolor=color, edgecolor='#555', linewidth=1,
                         alpha=0.85)
    ax.add_patch(box)
    ax.text(x + w/2, y + h - 0.015, title, ha='center', va='top',
            fontsize=7, fontweight='bold', color=text_color)
    ax.text(x + w/2, y + h/2 - 0.01, modules, ha='center', va='center',
            fontsize=5.5, color=text_color, alpha=0.9, family='monospace')


def draw_arrow(ax, x1, y1, x2, y2, color='#666', style='->', lw=1.0):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                               connectionstyle='arc3,rad=0.1'))


def draw_file_box(ax, x, y, w, h, name, color='#f0f0f0'):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.005",
                         facecolor=color, edgecolor='#999', linewidth=0.8)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, name, ha='center', va='center',
            fontsize=5, family='monospace', color='#333')


def main():
    fig, ax = plt.subplots(1, 1, figsize=(20, 14))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_facecolor('#fafafa')
    fig.patch.set_facecolor('#fafafa')

    # Title
    ax.text(0.5, 0.97, 'GEORGIA CPA ACCOUNTING SYSTEM — AGENT ARCHITECTURE',
            ha='center', va='top', fontsize=16, fontweight='bold', color='#1a1a2e')
    ax.text(0.5, 0.945, 'How agents coordinate to build the system',
            ha='center', va='top', fontsize=10, color='#666')

    # ═══════════════════════════════════════
    # ORCHESTRATION LAYER (top)
    # ═══════════════════════════════════════
    # Background
    layer_bg = FancyBboxPatch((0.02, 0.82), 0.96, 0.1, boxstyle="round,pad=0.01",
                              facecolor='#fff3e0', edgecolor='#ff6b35', linewidth=2, alpha=0.3)
    ax.add_patch(layer_bg)
    ax.text(0.04, 0.91, 'ORCHESTRATION', fontsize=7, fontweight='bold',
            color='#ff6b35', alpha=0.7, rotation=90, va='center')

    draw_agent_box(ax, 0.35, 0.83, 0.30, 0.08,
                   'CEO ORCHESTRATOR',
                   'Reads all files • Assigns tasks • Detects conflicts • Status dashboard',
                   '#ff6b35')

    # ═══════════════════════════════════════
    # COORDINATION FILES (middle band)
    # ═══════════════════════════════════════
    coord_bg = FancyBboxPatch((0.02, 0.74), 0.96, 0.07, boxstyle="round,pad=0.01",
                              facecolor='#e8e8e8', edgecolor='#999', linewidth=1, alpha=0.4)
    ax.add_patch(coord_bg)
    ax.text(0.04, 0.775, 'SHARED STATE', fontsize=7, fontweight='bold',
            color='#666', alpha=0.7, rotation=90, va='center')

    files = ['CLAUDE.md', 'AGENT_LOG.md', 'OPEN_ISSUES.md', 'WORK_QUEUE.md', 'ARCHITECTURE.md']
    for i, f in enumerate(files):
        draw_file_box(ax, 0.12 + i * 0.16, 0.755, 0.13, 0.025, f, '#e0e0e0')

    # ═══════════════════════════════════════
    # RESEARCH LAYER
    # ═══════════════════════════════════════
    research_bg = FancyBboxPatch((0.02, 0.60), 0.96, 0.13, boxstyle="round,pad=0.01",
                                 facecolor='#e0f7fa', edgecolor='#4ecdc4', linewidth=2, alpha=0.3)
    ax.add_patch(research_bg)
    ax.text(0.04, 0.665, 'RESEARCH\n(Run Once)', fontsize=6, fontweight='bold',
            color='#4ecdc4', alpha=0.7, rotation=90, va='center', ha='center')

    draw_agent_box(ax, 0.07, 0.615, 0.20, 0.08,
                   'RESEARCH AGENT (00)',
                   'Schema • Setup • Migration Spec • Work Queue',
                   '#4ecdc4', fontsize=8)

    draw_agent_box(ax, 0.29, 0.615, 0.17, 0.08,
                   'REVIEW AGENT (03)',
                   'QA on Research output',
                   '#26a69a')

    draw_agent_box(ax, 0.48, 0.615, 0.22, 0.08,
                   'GA TAX RESEARCH (04)',
                   'DOR tables • SUTA • Federal rates • Forms',
                   '#00897b')

    draw_agent_box(ax, 0.72, 0.615, 0.22, 0.08,
                   'QB FORMAT RESEARCH (05)',
                   'CSV formats • Column mapping • Sample data',
                   '#00796b')

    # ═══════════════════════════════════════
    # MIGRATION LAYER
    # ═══════════════════════════════════════
    migration_bg = FancyBboxPatch((0.02, 0.50), 0.96, 0.09, boxstyle="round,pad=0.01",
                                  facecolor='#fffde7', edgecolor='#f9a825', linewidth=2, alpha=0.3)
    ax.add_patch(migration_bg)
    ax.text(0.04, 0.545, 'MIGRATION\n(Run Once)', fontsize=6, fontweight='bold',
            color='#f9a825', alpha=0.7, rotation=90, va='center', ha='center')

    draw_agent_box(ax, 0.30, 0.51, 0.40, 0.07,
                   'MIGRATION AGENT (01)',
                   'Validate CSVs → Dry Run → Confirm → Import (single transaction) → Verify',
                   '#f9a825', text_color='#1a1a2e', fontsize=9)

    # ═══════════════════════════════════════
    # BUILD LAYER (phases)
    # ═══════════════════════════════════════
    build_bg = FancyBboxPatch((0.02, 0.03), 0.96, 0.46, boxstyle="round,pad=0.01",
                              facecolor='#f5f5f5', edgecolor='#666', linewidth=2, alpha=0.3)
    ax.add_patch(build_bg)
    ax.text(0.04, 0.26, 'BUILD LAYER\n(Per Module)', fontsize=7, fontweight='bold',
            color='#666', alpha=0.7, rotation=90, va='center', ha='center')

    # Phase boxes - Row 1
    draw_phase_box(ax, 0.07, 0.36, 0.20, 0.11,
                   'PHASE 1: Foundation',
                   'F1: DB Schema\nF2: Chart of Accts\nF3: General Ledger\nF4: Client Mgmt\nF5: Auth/JWT',
                   '#43a047')

    draw_phase_box(ax, 0.29, 0.36, 0.17, 0.11,
                   'PHASE 2: Transactions',
                   'T1: AP\nT2: AR/Invoicing\nT3: Bank Rec\nT4: Approval Flow',
                   '#e53935')

    draw_phase_box(ax, 0.48, 0.36, 0.14, 0.11,
                   'PHASE 3: Documents',
                   'D1: Upload\nD2: Viewer\nD3: Search',
                   '#8e24aa')

    draw_phase_box(ax, 0.64, 0.36, 0.30, 0.11,
                   'PHASE 4: Payroll (GA-specific)',
                   'P1: Employees  P2: GA Withholding  P3: GA SUTA\nP4: Federal Tax  P5: Pay Stubs  P6: Payroll Gate',
                   '#d81b60')

    # Phase boxes - Row 2
    draw_phase_box(ax, 0.07, 0.18, 0.40, 0.11,
                   'PHASE 5: Tax Form Exports',
                   'X1: G-7    X2: Form 500   X3: Form 600   X4: ST-3\nX5: Sched C   X6: 1120-S   X7: 1120   X8: 1065   X9: Checklist',
                   '#1565c0')

    draw_phase_box(ax, 0.49, 0.18, 0.22, 0.11,
                   'PHASE 6: Reporting',
                   'R1: P&L\nR2: Balance Sheet\nR3: Cash Flow\nR4: PDF Export\nR5: Dashboard',
                   '#ef6c00', text_color='white')

    draw_phase_box(ax, 0.73, 0.18, 0.21, 0.11,
                   'PHASE 7: Operations',
                   'O1: Audit Viewer\nO2: Backup\nO3: Restore\nO4: Health Check',
                   '#6a1b9a')

    # ═══════════════════════════════════════
    # ARROWS: CEO → Coordination Files
    # ═══════════════════════════════════════
    ax.annotate('', xy=(0.50, 0.78), xytext=(0.50, 0.83),
                arrowprops=dict(arrowstyle='<->', color='#ff6b35', lw=2))

    # Research Agent → Coordination Files
    ax.annotate('', xy=(0.17, 0.74), xytext=(0.17, 0.695),
                arrowprops=dict(arrowstyle='->', color='#4ecdc4', lw=1.5))

    # Review Agent → OPEN_ISSUES
    ax.annotate('', xy=(0.44, 0.755), xytext=(0.375, 0.695),
                arrowprops=dict(arrowstyle='->', color='#26a69a', lw=1,
                               connectionstyle='arc3,rad=0.2', linestyle='dashed'))

    # Research → Review (dotted)
    ax.annotate('', xy=(0.29, 0.655), xytext=(0.27, 0.655),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1,
                               linestyle='dotted'))

    # GA Tax Research → Payroll phases
    ax.annotate('', xy=(0.75, 0.47), xytext=(0.59, 0.615),
                arrowprops=dict(arrowstyle='->', color='#00897b', lw=1.5,
                               connectionstyle='arc3,rad=-0.2'))

    # QB Research → Migration
    ax.annotate('', xy=(0.70, 0.575), xytext=(0.83, 0.615),
                arrowprops=dict(arrowstyle='->', color='#00796b', lw=1.5,
                               connectionstyle='arc3,rad=0.3'))

    # CEO → Build Layer
    ax.annotate('', xy=(0.50, 0.47), xytext=(0.65, 0.83),
                arrowprops=dict(arrowstyle='->', color='#ff6b35', lw=1.5,
                               connectionstyle='arc3,rad=0.3', linestyle='dashed'))
    ax.text(0.62, 0.64, 'assigns\ntasks', fontsize=6, color='#ff6b35',
            ha='center', style='italic', alpha=0.8)

    # Phase flow arrows
    # Phase 1 → Phase 2
    ax.annotate('', xy=(0.29, 0.42), xytext=(0.27, 0.42),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.5))
    # Phase 1 → Phase 3
    ax.annotate('', xy=(0.48, 0.44), xytext=(0.27, 0.46),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1,
                               connectionstyle='arc3,rad=-0.2'))
    # Phase 2 → Phase 5
    ax.annotate('', xy=(0.27, 0.29), xytext=(0.375, 0.36),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1,
                               connectionstyle='arc3,rad=0.2'))
    # Phase 4 → Phase 5
    ax.annotate('', xy=(0.35, 0.29), xytext=(0.64, 0.36),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1,
                               connectionstyle='arc3,rad=0.3'))
    # Phase 5 → Phase 6
    ax.annotate('', xy=(0.49, 0.24), xytext=(0.47, 0.24),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1))
    # Phase 1 → Phase 7
    ax.annotate('', xy=(0.73, 0.24), xytext=(0.27, 0.40),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1,
                               connectionstyle='arc3,rad=-0.3'))

    # ═══════════════════════════════════════
    # LEGEND
    # ═══════════════════════════════════════
    legend_y = 0.06
    ax.text(0.08, legend_y + 0.06, 'LEGEND', fontsize=8, fontweight='bold', color='#333')

    legend_items = [
        ('#ff6b35', 'Orchestrator'),
        ('#4ecdc4', 'Research (run once)'),
        ('#f9a825', 'Migration (run once)'),
        ('#43a047', 'Builder (per module)'),
    ]
    for i, (color, label) in enumerate(legend_items):
        box = FancyBboxPatch((0.08 + i * 0.12, legend_y), 0.02, 0.015,
                             boxstyle="round,pad=0.002", facecolor=color,
                             edgecolor='#333', linewidth=0.5)
        ax.add_patch(box)
        ax.text(0.105 + i * 0.12, legend_y + 0.007, label,
                fontsize=6, va='center', color='#333')

    # Arrow legend
    ax.text(0.58, legend_y + 0.007, '── data flow    - - - task assignment    ··· QA review',
            fontsize=6, color='#666', va='center', family='monospace')

    # Stats box
    stats_bg = FancyBboxPatch((0.73, legend_y - 0.02), 0.22, 0.08,
                              boxstyle="round,pad=0.01", facecolor='white',
                              edgecolor='#ccc', linewidth=1)
    ax.add_patch(stats_bg)
    ax.text(0.84, legend_y + 0.045, '6 Agent Types • 34 Modules • 7 Phases',
            ha='center', fontsize=7, fontweight='bold', color='#333')
    ax.text(0.84, legend_y + 0.015, 'Coordination via shared markdown files\nNo direct agent-to-agent communication',
            ha='center', fontsize=5.5, color='#666')

    plt.tight_layout(pad=0.5)
    output_path = '/Users/edwardahrens/tax/docs/diagrams/agent_architecture.png'
    plt.savefig(output_path, dpi=200, bbox_inches='tight',
                facecolor='#fafafa', edgecolor='none')
    print(f'Diagram saved to: {output_path}')
    plt.close()


if __name__ == '__main__':
    main()
