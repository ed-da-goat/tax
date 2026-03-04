#!/usr/bin/env python3
"""
Agent Architecture Diagram — Version 11.
Landscape page, vertical tree (top to bottom), zoomed in, big text.
72 DPI so what you see in Preview is roughly 1:1 pixel.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np


def node(ax, x, y, label, color, r=0.4, fs=18):
    for i in range(3):
        ax.add_patch(plt.Circle((x, y), r+0.05*(3-i), fc=color, ec='none', alpha=0.04, zorder=3))
    ax.add_patch(plt.Circle((x, y), r, fc=color, ec='white', lw=3, zorder=10))
    ax.add_patch(plt.Circle((x, y-r*0.1), r*0.6, fc='white', ec='none', alpha=0.1, zorder=11))
    ax.text(x, y, label, ha='center', va='center', fontsize=fs, fontweight='bold',
            color='white', zorder=12, path_effects=[pe.withStroke(linewidth=1.5, foreground=color)])


def branch(ax, x1, y1, x2, y2, color='#ccc', lw=2.5):
    t = np.linspace(0, 1, 50)
    my = (y1+y2)/2
    xs = [x1, x1, x2, x2]
    ys = [y1, my+(y1-y2)*0.12, my-(y1-y2)*0.12, y2]
    bx = (1-t)**3*xs[0]+3*(1-t)**2*t*xs[1]+3*(1-t)*t**2*xs[2]+t**3*xs[3]
    by = (1-t)**3*ys[0]+3*(1-t)**2*t*ys[1]+3*(1-t)*t**2*ys[2]+t**3*ys[3]
    ax.plot(bx, by, color=color, lw=lw, zorder=1, solid_capstyle='round', alpha=0.5)


def twig(ax, x1, y1, x2, y2, color='#ccc', lw=1.5):
    ax.plot([x1, x2], [y1, y2], color=color, lw=lw, zorder=2, alpha=0.4, solid_capstyle='round')


def label_block(ax, x, y, items, color, fs=14, align='left'):
    """Compact text list next to an agent."""
    ha = 'left' if align == 'left' else 'right'
    for i, item in enumerate(items):
        iy = y - i * 0.38
        # small dot + text
        dx = 0.12 if align == 'left' else -0.12
        ax.add_patch(plt.Circle((x + (0 if align == 'left' else -0.05), iy), 0.06,
                                fc=color, ec='none', zorder=6, alpha=0.7))
        ax.text(x + dx + 0.05, iy, item, ha=ha, va='center', fontsize=fs,
                color='#333', zorder=6)


def main():
    fig, ax = plt.subplots(figsize=(28, 16))
    ax.set_xlim(0, 28)
    ax.set_ylim(0, 16)
    ax.axis('off')
    fig.patch.set_facecolor('#fcfcfc')
    ax.set_facecolor('#fcfcfc')

    # ── TITLE ──
    ax.text(14, 15.5, 'Georgia CPA — Agent Architecture', ha='center',
            fontsize=36, fontweight='bold', color='#2c3e50')
    ax.text(14, 15.0, '49 agents  •  shared-file coordination  •  no direct agent talk',
            ha='center', fontsize=18, color='#aaa')

    # ═════════════════════════════
    # ROW 0: CEO
    # ═════════════════════════════
    cx, cy = 14, 13.5
    node(ax, cx, cy, 'CEO', '#e74c3c', r=0.55, fs=22)

    # Shared files to the right of CEO
    ax.text(17.5, 14.0, 'Shared State', fontsize=14, fontweight='bold', color='#aaa')
    for i, f in enumerate(['CLAUDE.md', 'AGENT_LOG.md', 'OPEN_ISSUES.md', 'WORK_QUEUE.md', 'ARCHITECTURE.md']):
        ax.add_patch(plt.Circle((17.2, 13.6-i*0.38), 0.06, fc='#bdc3c7', ec='none', zorder=6))
        ax.text(17.4, 13.6-i*0.38, f, fontsize=13, va='center', color='#777', family='monospace')
    twig(ax, cx+0.55, cy, 17.0, 13.4, '#e74c3c', lw=2)

    # ═════════════════════════════
    # ROW 1: Three team hubs
    # ═════════════════════════════
    # Research
    rx, ry = 5, 11
    branch(ax, cx, cy-0.55, rx, ry+0.45, '#1abc9c', lw=3.5)
    node(ax, rx, ry, 'Research', '#1abc9c', r=0.5, fs=16)
    ax.text(rx, ry-0.7, 'Team (4)', ha='center', fontsize=13, color='#1abc9c', fontweight='bold')

    # Migration
    mx, my = 14, 11
    branch(ax, cx, cy-0.55, mx, my+0.45, '#f39c12', lw=3.5)
    node(ax, mx, my, 'Migration', '#f39c12', r=0.5, fs=15)
    ax.text(mx, my-0.7, 'Team (2)', ha='center', fontsize=13, color='#f39c12', fontweight='bold')

    # Builders
    bx, by = 23, 11
    branch(ax, cx, cy-0.55, bx, by+0.45, '#3498db', lw=3.5)
    node(ax, bx, by, 'Builders', '#3498db', r=0.5, fs=15)
    ax.text(bx, by-0.7, '43 agents', ha='center', fontsize=13, color='#3498db', fontweight='bold')

    # ═════════════════════════════
    # ROW 2: Individual agents
    # ═════════════════════════════

    # -- Research agents --
    ra = [
        (2, 8, '00', 'Research', '#16a085',
         ['SETUP.md', '001_schema.sql', 'MIGRATION_SPEC.md', 'Folder structure']),
        (5, 8, '03', 'Review', '#1abc9c',
         ['QA report', 'Issue flags']),
        (8, 8, '04', 'GA Tax', '#0e6655',
         ['Withholding tables', 'SUTA rates', 'Federal rates', 'Form specs']),
    ]
    for ax2, ay, lbl, nm, clr, items in ra:
        branch(ax, rx, ry-0.5, ax2, ay+0.42, '#1abc9c', lw=2.5)
        node(ax, ax2, ay, lbl, clr, r=0.42, fs=18)
        ax.text(ax2, ay-0.6, nm, ha='center', fontsize=13, color=clr, fontweight='bold')
        # Items below agent
        for i, item in enumerate(items):
            iy = ay - 1.0 - i*0.36
            ax.add_patch(plt.Circle((ax2-0.8, iy), 0.05, fc=clr, ec='none', zorder=6, alpha=0.7))
            ax.text(ax2-0.65, iy, item, fontsize=12, va='center', color='#444')
            twig(ax, ax2, ay-0.42, ax2-0.6, iy, clr)

    # -- Migration agents --
    ma = [
        (12, 8, '05', 'QB Fmt', '#d4ac0d',
         ['Export formats', 'Column mappings', 'Sample CSVs']),
        (16, 8, '01', 'Migrate', '#e67e22',
         ['M1 CSV Parser', 'M2 Client Splitter', 'M3 CoA Mapper',
          'M4 Txn Import', 'M5 Invoice Import', 'M6 Payroll Import', 'M7 Audit Rpt']),
    ]
    for ax2, ay, lbl, nm, clr, items in ma:
        branch(ax, mx, my-0.5, ax2, ay+0.42, '#f39c12', lw=2.5)
        node(ax, ax2, ay, lbl, clr, r=0.42, fs=18)
        ax.text(ax2, ay-0.6, nm, ha='center', fontsize=13, color=clr, fontweight='bold')
        for i, item in enumerate(items):
            iy = ay - 1.0 - i*0.36
            ax.add_patch(plt.Circle((ax2-0.8, iy), 0.05, fc=clr, ec='none', zorder=6, alpha=0.7))
            ax.text(ax2-0.65, iy, item, fontsize=12, va='center', color='#444')
            twig(ax, ax2, ay-0.42, ax2-0.6, iy, clr)

    # -- Builder phase agents --
    phases = [
        (19.5, 8, 'P1', 'Foundation', '#27ae60',
         ['F1 Schema', 'F2 CoA', 'F3 GL', 'F4 Clients', 'F5 Auth']),
        (22, 8, 'P2', 'Transactions', '#c0392b',
         ['T1 AP', 'T2 AR', 'T3 Bank Rec', 'T4 Approvals']),
        (24.5, 8, 'P3', 'Documents', '#8e44ad',
         ['D1 Upload', 'D2 Viewer', 'D3 Search']),
        (27, 8, 'P4', 'Payroll', '#e91e63',
         ['P1 Employees', 'P2 GA W/H', 'P3 SUTA', 'P4 Federal', 'P5 Stubs', 'P6 Gate']),
    ]
    for px, py, plbl, pnm, pclr, pitems in phases:
        branch(ax, bx, by-0.5, px, py+0.42, '#3498db', lw=2.5)
        node(ax, px, py, plbl, pclr, r=0.38, fs=16)
        ax.text(px, py-0.55, pnm, ha='center', fontsize=11, color=pclr, fontweight='bold')
        for i, item in enumerate(pitems):
            iy = py - 0.95 - i*0.34
            ax.add_patch(plt.Circle((px-0.6, iy), 0.04, fc=pclr, ec='none', zorder=6, alpha=0.7))
            ax.text(px-0.45, iy, item, fontsize=11, va='center', color='#444')
            twig(ax, px, py-0.38, px-0.45, iy, pclr)

    # Phases 5-7 in a second row below
    phases2 = [
        (19.5, 3.5, 'P5', 'Tax Forms', '#2980b9',
         ['X1 G-7', 'X2 F-500', 'X3 F-600', 'X4 ST-3', 'X5 Sch C',
          'X6 1120-S', 'X7 1120', 'X8 1065', 'X9 Checklist']),
        (23, 3.5, 'P6', 'Reporting', '#e67e22',
         ['R1 P&L', 'R2 Bal Sheet', 'R3 Cash Flow', 'R4 PDF', 'R5 Dashboard']),
        (26, 3.5, 'P7', 'Operations', '#6c3483',
         ['O1 Audit', 'O2 Backup', 'O3 Restore', 'O4 Health']),
    ]
    for px, py, plbl, pnm, pclr, pitems in phases2:
        branch(ax, bx, by-0.5, px, py+0.42, '#3498db', lw=2)
        node(ax, px, py, plbl, pclr, r=0.38, fs=16)
        ax.text(px, py-0.55, pnm, ha='center', fontsize=11, color=pclr, fontweight='bold')
        for i, item in enumerate(pitems):
            iy = py - 0.95 - i*0.34
            ax.add_patch(plt.Circle((px-0.6, iy), 0.04, fc=pclr, ec='none', zorder=6, alpha=0.7))
            ax.text(px-0.45, iy, item, fontsize=11, va='center', color='#444')
            twig(ax, px, py-0.38, px-0.45, iy, pclr)

    # ═════════════════════════════
    # LEGEND (bottom left)
    # ═════════════════════════════
    ax.text(0.5, 1.8, 'LEGEND', fontsize=16, fontweight='bold', color='#555')
    for i, (clr, lbl) in enumerate([
        ('#e74c3c', 'CEO Orchestrator'),
        ('#1abc9c', 'Research Team (4)'),
        ('#f39c12', 'Migration Team (2)'),
        ('#3498db', 'Builder Agents (43)'),
    ]):
        ly = 1.2 - i*0.45
        ax.add_patch(plt.Circle((0.7, ly), 0.15, fc=clr, ec='white', lw=2, zorder=10))
        ax.text(1.0, ly, lbl, va='center', fontsize=14, color='#444')

    plt.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=0.01)
    out = '/Users/edwardahrens/tax/docs/diagrams/agent_architecture.png'
    plt.savefig(out, dpi=72, bbox_inches='tight', facecolor='#fcfcfc', edgecolor='none')
    print(f'Saved to: {out}')
    plt.close()


if __name__ == '__main__':
    main()
