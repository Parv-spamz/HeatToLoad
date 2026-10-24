---
name: taste
description: >-
  Human-crafted design taste, typography, layout, and visual standards for web applications.
  Eliminates generic AI tropes (neon gradient text, random blurry glow blobs, rainbow KPI cards,
  floating frosted-glass boxes) in favor of editorial rigor, typographic craft, bespoke palettes,
  and dense, publication-grade data visualization inspired by Financial Times, Bloomberg, Linear, and Stripe.
---

# Design Taste & Frontend Craftsmanship Standards

This skill governs the aesthetic and structural design of frontend applications, data visualizations, and dashboards.
Its goal is to eradicate "AI-generated slop" and produce interfaces that feel bespoke, authoritative, and crafted by a senior product designer and data journalist.

---

## 1. What Makes an Interface Look "AI-Generated" (Anti-Patterns to Eliminate)

- **The Ambient Neon Glow**: Random circular gradient blobs blurred with `filter: blur(120px)` floating in the background. (Remove immediately).
- **The Rainbow KPI Strip**: Four adjacent metric cards colored Cyan, Amber, Emerald, and Rose for no semantic reason.
- **Cheesy Pulsing Dots**: Green or cyan glowing dots with CSS infinite pulse animations.
- **Aggressive Glassmorphism**: Overusing `backdrop-filter: blur(16px)` on floating rounded rectangles with glowing borders.
- **Gradient Headline Slop**: `background: linear-gradient(135deg, #00f2fe, #4facfe); -webkit-background-clip: text;` on every single page title.
- **Low Information Density**: Giant padding (32px+ everywhere) with tiny amounts of actual data, forcing excessive scrolling.
- **Generic Chart.js Defaults**: Default round bubble legends, thick rounded bars with default radius, cluttered unformatted tooltips.

---

## 2. Hallmarks of High Taste & Craft (What to Do Instead)

### Typography & Hierarchy
- **Editorial Contrast**: Combine an authoritative serif headline (e.g. *Newsreader*, *Playfair*, *Instrument Serif*) or precision grotesque (*Geist*, *Inter*, *Cabinet Grotesk*) with crisp, tabular monospace numerals (*JetBrains Mono*, *Geist Mono*).
- **Tabular Figures**: Always use `font-variant-numeric: tabular-nums` or monospace for data tables and KPIs so numbers line up vertically and don't jitter during updates.
- **Proportional Typographic Scale**: Clear, deliberate jump between title (28–32px), section heads (16–18px), labels (11–12px uppercase tracking 0.05em), and data values (24–36px).

### Layout & Architecture
- **Unified Structural Canvas**: Replace disconnected floating cards with an integrated grid separated by subtle 1px structural border dividers (`rgba(255,255,255,0.08)` or `#e5e7eb` on light).
- **Contextual Left-to-Right Flow**:
  - Global controls and high-level index on the left or top header.
  - Primary analytical chart at center-stage with direct line annotations.
  - Deep-dive contextual inspectors and scenario controls on the side or integrated drawer.
- **Editorial Context**: Include concise journalistic annotations, data source provenance, and dateline directly in the visual layout.

### Color & Semantic Discipline
- **Monochromatic Foundation**: Deep, rich charcoal canvas (e.g., `#090b10`, `#111318`, `#161922`) with high-contrast neutral text (`#f8fafc`, `#94a3b8`, `#475569`).
- **Singular Semantic Color Axis**: For temperature sensitivity, use a calibrated thermal gradient (e.g., deep steel blue for baseload cooling `#38bdf8`, transitioning through warm gold `#eab308` to focused vermilion `#ef4444` solely for extreme heatwaves). Never use random green/purple/pink simultaneously unless categorizing distinct regions.

### Data Visualization Craft
- **Direct Labeling over Clunky Legends**: Label lines and key threshold bands directly on the chart canvas (e.g., "28°C Thermal Inflection Point") rather than relying on floating pill legends.
- **Reference Baselines & Context Bands**: Show historical normal ranges, IQR bands, or holdout partitions with subtle hatched or shaded fills.
- **Clean Crosshairs & Tooltips**: Snappy, custom tooltip formatters showing exact date, delta, and percentage context.

### Tactile Controls
- **Segmented Button Groups**: Flush, minimal segmented pills with crisp active states (`background: rgba(255,255,255,0.1)`).
- **Precision Sliders**: Minimal track with clean thumb indicator, numeric tick marks, and immediate mathematical feedback.
