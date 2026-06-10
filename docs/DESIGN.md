# Design System - SupportOps

## Visual Direction

**Style**: Dark-first, tech-forward, premium  
**Inspiration**: Linear.app meets Anthropic Claude  
**Audience**: Tech-savvy support professionals + admins

## Color Palette

### Primary Colors

- **Roxo (Primary)**: `#7C3AED` — Tech, premium, IA
- **Cyan (Secondary)**: `#0EA5E9` — Trust, clarity, info
- **Laranja (Accent)**: `#F97316` — Citations, important highlights

### Status Colors

- **Success**: `#10B981` — Processed, indexed, approved
- **Warning**: `#FBBF24` — Processing, in review, caution
- **Error**: `#DC2626` — Error, failed, low confidence
- **Info**: `#3B82F6` — Information, neutral

### Neutrals (Dark Mode)

- **Background Dark**: `#0F172A` — Main background
- **Background Card**: `#1E293B` — Card/panel background
- **Background Hover**: `#334155` — Hover state
- **Text Primary**: `#F1F5F9` — Main text (light)
- **Text Secondary**: `#CBD5E1` — Secondary text (muted)
- **Border**: `#475569` — Subtle borders

### Neutrals (Light Mode - optional)

- **Background Light**: `#FFFFFF` — Main background
- **Background Card**: `#F1F5F9` — Card background
- **Background Hover**: `#E2E8F0` — Hover state
- **Text Primary**: `#0F172A` — Main text (dark)
- **Text Secondary**: `#64748B` — Secondary text
- **Border**: `#E2E8F0` — Borders

## Typography

### Font Family

- **Primary**: Inter (Google Fonts)
  - Standard size, professional, excellent hinting
- **Monospace**: JetBrains Mono (for code, IDs, timestamps)
  - For: Ticket IDs (TCK-1001), timestamps, code blocks

### Font Scale

```
Heading 1: 32px, weight 700, line-height 1.2
Heading 2: 24px, weight 700, line-height 1.3
Heading 3: 20px, weight 600, line-height 1.4
Heading 4: 16px, weight 600, line-height 1.5

Body Large: 16px, weight 400, line-height 1.6
Body Normal: 14px, weight 400, line-height 1.5
Body Small: 12px, weight 400, line-height 1.4

Button: 14px, weight 600, line-height 1.5
Label: 12px, weight 500, line-height 1.4
Caption: 11px, weight 400, line-height 1.4
```

## Component Styles

### Buttons

**Primary Button**

- Background: `#7C3AED` (roxo)
- Text: `#FFFFFF`
- Hover: `#6D28D9` (darker roxo)
- Padding: 12px 24px
- Border-radius: 8px
- Font: Body Normal, weight 600

**Secondary Button**

- Border: 2px `#7C3AED`
- Text: `#7C3AED`
- Background: transparent
- Hover: `#0F172A` background at 5%

**Danger Button**

- Background: `#DC2626`
- Text: `#FFFFFF`
- Hover: `#991B1B`

**Ghost Button**

- Background: transparent
- Text: `#CBD5E1`
- Border: 1px `#475569`
- Hover: `#334155` background at 10%

### Cards/Panels

```
Background: #1E293B
Border: 1px solid #475569 (subtle)
Padding: 20px
Border-radius: 12px
Box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3)

Hover: Slight shadow increase
Active: Border color changes to #7C3AED
```

### Input Fields

```
Background: #0F172A
Border: 1px solid #475569
Text: #F1F5F9
Placeholder: #64748B
Focus: Border color → #7C3AED
Padding: 12px 16px
Border-radius: 8px
Font: Body Normal
```

### Tables

```
Header Background: #0F172A
Row Background: #1E293B
Row Hover: #334155 background
Border: 1px solid #475569

Text: #F1F5F9 (normal), #CBD5E1 (secondary)
Padding: 12px 16px
```

### Status Badges

```
Indexado (Success)
- Background: #10B981 with 20% opacity
- Border: 1px #10B981
- Text: #10B981
- Icon: ✓
- Padding: 6px 12px
- Border-radius: 16px (pill)

Processando (Warning)
- Background: #FBBF24 with 20% opacity
- Border: 1px #FBBF24
- Text: #FBBF24
- Icon: Spinner animation
- Animation: 200ms rotation

Erro (Error)
- Background: #DC2626 with 20% opacity
- Border: 1px #DC2626
- Text: #DC2626
- Icon: ⚠

Em Revisão (Info)
- Background: #3B82F6 with 20% opacity
- Border: 1px #3B82F6
- Text: #3B82F6
- Icon: 👁
```

### Citations/Sources

```
Container:
- Background: #334155 (highlighted area)
- Border-left: 4px #F97316 (laranja accent)
- Padding: 12px 16px
- Border-radius: 0 8px 8px 0

Title: "Fonte utilizada"
- Font: Body Small, weight 600
- Color: #F97316

Content:
- Font: Body Small
- Color: #CBD5E1
- Quote: #F1F5F9
- Score: #0EA5E9 (cyan accent)
```

## Icons

- **Library**: Lucide React
- **Size Grid**: 16px, 20px, 24px, 32px
- **Color**: Inherit from text color, or roxo/cyan/laranja for accent
- **Stroke Width**: 2px

Common icons:

- Upload: `Upload`
- Documents: `FileText`, `FileJson`, `Pdf`
- Tickets: `Ticket`, `MessageSquare`
- Status: `CheckCircle`, `Clock`, `AlertCircle`, `XCircle`
- Actions: `ChevronDown`, `MoreHorizontal`, `Edit`, `Trash`
- Search: `Search`
- Filter: `Filter`
- Menu: `Menu`, `X`
- User: `User`, `LogOut`

## Layout Grid

- **Base unit**: 4px
- **Spacing scale**: 4, 8, 12, 16, 20, 24, 32, 40, 48px
- **Container width**: 1280px max
- **Sidebar width**: 240px
- **Gutter**: 24px

## Dark Mode Strategy

✅ **Dark mode is DEFAULT and primary**

Tailwind configuration:

```typescript
module.exports = {
  darkMode: 'class', // Toggle via .dark class
  theme: {
    extend: {
      colors: {
        primary: '#7C3AED',
        secondary: '#0EA5E9',
        accent: '#F97316',
      },
    },
  },
};
```

Usage in components:

```jsx
<div className="bg-white dark:bg-slate-900">
  <p className="text-gray-900 dark:text-white">Content</p>
</div>
```

## Animations

### Duration

- Micro interactions: 100ms
- UI transitions: 200ms
- Modals: 300ms
- Page transitions: 400ms

### Easing

- Default: `cubic-bezier(0.4, 0, 0.2, 1)` (ease-in-out)
- Enter: `cubic-bezier(0.34, 1.56, 0.64, 1)` (ease-out)
- Exit: `cubic-bezier(0.3, 0, 0.8, 0.15)` (ease-in)

### Examples

**Button Hover**

```css
transition: all 200ms ease-in-out;
transform: scale(1.02);
box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
```

**Loading Spinner**

```css
animation: spin 1s linear infinite;
```

**Toast Notification**

```css
animation: slideUp 300ms ease-out;
```

## Responsive Design

Breakpoints (Tailwind default):

```
Mobile:  < 640px
Tablet:  640px - 1024px
Desktop: > 1024px
```

Strategy:

- **Mobile-first** (but dashboard optimized for desktop)
- Sidebar collapse on tablet
- Single-column layout on mobile
- Touch-friendly (44px min tap target)

## Accessibility

- **Color contrast**: WCAG AA minimum (4.5:1 for text)
- **Focus states**: Always visible (border or outline)
- **Keyboard navigation**: Tab, Shift+Tab, Enter, Escape
- **ARIA labels**: For interactive elements
- **Semantic HTML**: `<button>`, `<label>`, etc.
- **Reduced motion**: Respect `prefers-reduced-motion`

## File Organization

```
components/
├── ui/                  # Shadcn/ui base components
├── documents/           # Document-specific components
│   ├── DocumentUploadForm.tsx
│   ├── DocumentList.tsx
│   ├── DocumentVersionHistory.tsx
│   └── ...
├── tickets/             # Ticket components
│   ├── TicketList.tsx
│   ├── TicketDetail.tsx
│   ├── TicketMetadataCard.tsx
│   └── ...
├── ai/                  # IA response components
│   ├── AIAnalysisPanel.tsx
│   ├── SuggestedResponseEditor.tsx
│   ├── SourcesPanel.tsx
│   ├── ConfidenceBadge.tsx
│   └── GuardrailsChecklist.tsx
├── review/              # Review/approval components
│   ├── HumanReviewForm.tsx
│   ├── ApprovalActions.tsx
│   └── RejectionReasonSelector.tsx
├── evaluations/         # Dashboard components
│   ├── EvaluationSummaryCards.tsx
│   ├── RagExperimentTable.tsx
│   ├── KnowledgeGapList.tsx
│   └── RejectionReasonsChart.tsx
└── shared/              # Reusable
    ├── Layout.tsx
    ├── Header.tsx
    ├── Sidebar.tsx
    └── ...
```

## Figma File (Optional)

For a production project, create a Figma file with:

1. Color styles
2. Typography styles
3. Component library
4. Layouts
5. Icons
6. Interactions

Share as design system source of truth.

## Migration from Prototype

If migrating from unstyled prototype:

1. Install Shadcn/ui: `npx shadcn-ui@latest init`
2. Configure Tailwind with colors above
3. Add next-themes for dark mode toggle
4. Replace generic divs with Shadcn components
5. Apply color/typography tokens
6. Test dark mode thoroughly
