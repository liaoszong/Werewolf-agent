# Werewolf-agent UI Design Notes

Purpose: before creating a new Qt/QML page, redesigning an existing page, or adding
visual components, read this file first. Keep new work visually compatible with the
current Home page and Theater / Cockpit page.

## 设计 / 重做页面工作流程 (Design Workflow)

UI 页面走「插画驱动 → 参照图复刻」,不是直接写代码堆样式。新建和重做都是「生图选型 → 复刻实现」两段式。

### 新建 UI 页面

1. **Brainstorming**:先用 brainstorming 充分讨论这个页面要承载什么内容、信息层级、交互。先想清楚「做什么」,再谈「长什么样」。
2. **总结生图提示词(约束要少)**:把讨论结论提炼成一段 GPT 生图提示词。**刻意少加约束**——只给世界观 / 风格基调 / 必须出现的内容,把构图、配色细节、具体布局留给 GPT 自由发挥,让它充分施展创造力与设计力。
3. **GPT 生图**:把提示词交给用户,用户用 GPT 生成若干张候选图,再把图发回给我。
4. **选型 + 迭代提示词**:我从候选里**选出最好的一张**;必要时**总结各张图各自的优点**,据此**修改提示词**再发给用户,让 GPT 再生一轮。
5. **定稿**:重复第 3–4 步,直到选出满意的图。
6. **参照复刻**:以定稿图为蓝本,用现有 `Theme` / 组件把页面实现出来;边实现边截图自验,直到与参照图一致(见下「实现与自验」)。

### 重做 UI 页面

流程与新建大致相同,**只有第 1 步不同**:

1. **先问需求**:询问用户——这个页面**要保留什么**(哪些信息 / 控件 / 契约不能丢)、**是否要新增东西**;并明确**排版基本都会改**(这是重做的前提)。
2. 之后同新建:**总结生图提示词(约束少)→ GPT 生图 → 我选最优 + 总结各图优点 + 改提示词 → 再生图 → 定稿 → 参照复刻实现**。

### 实现与自验

- 复刻时优先复用既有 `Theme.warm` / `Theme.parchment` token 与现有组件(见下文 Components / Layout),少造新视觉词汇。
- QML 改动必须**构建 + 截图核对**(参照图 vs 实际渲染);god-view 圆桌盘面这类用 `.tmp/shot.sh`(`qml.exe` 跑 DesignPreviewView 截 day/night/voting 三相位),细节见 skill `verifying-qt-observer-ui`。
- 若背景插画要与 QML 落位(如座椅环、头像)对齐,**让生图提示词与 QML 用同一套归一化坐标**(都按「实际绘制矩形」的比例),两边天然吻合。

## Style Direction

- Product feel: storybook tabletop theater, not a generic SaaS dashboard.
- Core mood: warm parchment, dark wood, candlelight, hand-painted fantasy room art,
  restrained game HUD.
- Main surfaces: warm cream canvas for home / light areas, deep parchment-dark panels
  for logs and control surfaces, tactile parchment cards over illustrated scenes.
- Prefer real scene artwork or role artwork over abstract gradients or SVG decor.
- Keep UI dense enough for repeated spectating: clear hierarchy, compact controls,
  no marketing hero layout inside app screens.

## Colors

- Warm canvas / parchment: cream, sand, aged paper. Use existing `Theme.warm.*` and
  `Theme.parchment.*` tokens instead of new ad hoc colors.
- Claude-inspired warm editorial colors are allowed and preferred when they fit the
  app: cream canvas `#faf9f5`, coral `#cc785c`, active coral `#a9583e`,
  warm ink `#141413`, body ink `#3d3d3a`, muted text `#6c6a64`,
  soft muted text `#8e8b82`, hairline `#e6dfd8`, card cream `#efe9de`,
  dark surface `#181715`, elevated dark `#252320`.
- The Home page intentionally borrows from that Claude-like cream/coral/ink palette;
  keep that warmth as a project taste marker.
- Dark surfaces: near-black brown / ink, used for sidebars, event logs, and footer-like
  control areas.
- Accent: muted terracotta / coral for active actions, LIVE state, phase emphasis.
- Detail accents: antique gold hairlines, role colors only as small rings / dots /
  badges.
- Avoid cold blue-gray dashboards, neon cyberpunk colors, and large flat purple/blue
  gradients. Purple should come from illustrations or role accents, not page chrome.

## Typography

- Headings and page identity use the existing serif family (`Theme.fontFamilies.serif`)
  for storybook / board-game flavor.
- Body, labels, and controls use the existing sans family.
- Mono is only for run IDs, system labels, traces, and technical metadata.
- Do not enlarge every label. HUD cards stay compact; hero-scale type belongs only on
  true landing/home hero moments.

## Components

- `HudCard`: parchment floating card with gold border, used for phase, votes, speaker,
  status, and compact summaries.
- Dark left/event panels: deep parchment background, gold hairlines, cream cards inside.
- Buttons: rounded but restrained; active state uses terracotta fill, ghost state uses
  hairline border over the scene.
- Badges/chips: small, pill or circular, used for LIVE, votes, phase, role, evidence.
- Seat/role elements: circular portrait medallions, thin role-color ring, small seat
  number seal, parchment nameplate. Do not downgrade to plain rectangles.
- Playback / segmented controls: parchment tray style, compact, centered, with obvious
  selected segment.

## Layout

- Home page: illustrated scene first, warm editorial entry, restrained cards and CTAs.
- Theater page: left event-log rail plus full-bleed illustrated stage; HUD floats over
  the scene instead of forming heavy horizontal bars.
- Keep repeated panels aligned to a clear grid. Prefer one strong scene plus useful HUD
  overlays over many decorative cards.
- Avoid cards inside cards except for genuine repeated list items or modal/tool frames.
- New pages should reuse existing tokens/components before adding visual vocabulary.

## Qt/QML Rules

- Read `clients/qt_observer/qml/Theme.qml`, existing page QML, and this file before
  inventing new colors or component styling.
- If changing QML visuals, build the Qt target and verify with screenshots. For cockpit
  / theater work, also ensure top phase card, right info tower, and bottom playback tray
  do not overlap primary content.
- Preserve client boundaries: Qt consumes observer protocol data; no direct Python
  runtime binding and no local artifact reads unless a plan explicitly allows it.

## Do / Don't

Do:
- Reuse `Theme.warm`, `Theme.parchment`, `HudCard`, role accents, parchment texture,
  gold hairlines, circular portraits, and compact control trays.
- Make new screens feel like the same premium tabletop spectator app.
- Keep evidence/debug detail available but visually secondary.

Don't:
- Replace the look with flat SaaS cards, cool slate dashboards, generic AI gradients,
  or oversized marketing copy.
- Add one-off color literals when a `Theme` token exists.
- Use decorative blobs/orbs as backgrounds.
- Make controls look cheaper than the existing Home / Theater components.
