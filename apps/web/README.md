# Web App - Next.js

Frontend da aplicação SupportOps.

## Stack

- **Framework**: Next.js 14 (App Router)
- **UI Library**: Shadcn/ui (Tailwind + Radix)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Forms**: React Hook Form + Zod
- **HTTP Client**: Axios + SWR
- **Dark Mode**: next-themes
- **Theme**: Roxo (#7C3AED) + Cyan (#0EA5E9) + Laranja (#F97316)

## Estrutura

```
src/
  ├── app/              # App Router pages
  │   ├── layout.tsx
  │   ├── page.tsx
  │   ├── documents/
  │   ├── tickets/
  │   └── evaluations/
  ├── components/       # React components
  │   ├── ui/           # Shadcn/ui components
  │   ├── documents/    # Document-specific
  │   ├── tickets/      # Ticket-specific
  │   └── shared/       # Shared components
  ├── hooks/            # Custom hooks
  ├── lib/              # Utilities, API clients
  ├── styles/           # Global styles
  └── types/            # TypeScript types
```

## Desenvolvimento

Estado atual: o frontend tem uma página inicial mínima para validar o scaffold local. As telas do MVP serão implementadas nas próximas etapas.

```bash
# Instalar dependências (da raiz)
pnpm install

# Rodar em desenvolvimento
npm run dev:web

# Build
npm run build --filter=web

# Linting
npm run lint --filter=web

# Type checking
npm run type-check --filter=web
```

## Variáveis de ambiente

Ver `.env.example` na raiz do projeto.

Principais:

- `NEXT_PUBLIC_API_URL`: URL da API FastAPI (ex: http://localhost:8000)
- `NEXT_PUBLIC_API_TIMEOUT`: Timeout em ms

## Telas planejadas (MVP)

- `/documents` - Upload e gestão de documentos
- `/tickets` - Lista de tickets
- `/tickets/[id]` - Detalhe e análise do ticket
- `/evaluations` - Dashboard de avaliação

## Design System

Consulte o arquivo `DESIGN.md` para paleta de cores, tipografia e componentes.
