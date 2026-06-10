import {
  CheckCircle,
  Clock,
  Database,
  FileText,
  MessageSquare,
  Server,
  Workflow,
} from 'lucide-react';

const services = [
  {
    name: 'Frontend',
    description: 'Next.js App Router',
    status: 'Rodando',
    port: '3000',
    tone: 'success',
    icon: Server,
  },
  {
    name: 'API',
    description: 'FastAPI scaffold',
    status: 'Disponivel',
    port: '8000',
    tone: 'info',
    icon: Workflow,
  },
  {
    name: 'Workers',
    description: 'Celery conectado ao Redis',
    status: 'Pronto',
    port: '6380',
    tone: 'warning',
    icon: Database,
  },
];

const modules = [
  { label: 'Documents', icon: FileText },
  { label: 'Tickets', icon: MessageSquare },
  { label: 'Evaluations', icon: CheckCircle },
];

export default function Home() {
  return (
    <main className="shell">
      <section className="workspace" aria-labelledby="page-title">
        <header className="header">
          <div>
            <p className="eyebrow">SupportOps</p>
            <h1 id="page-title">Scaffold local pronto</h1>
            <p className="summary">
              Customer support operations platform for B2B SaaS teams: triagem, conhecimento
              confiavel, rascunhos policy-aware, revisao assistida por IA e qualidade mensuravel.
            </p>
          </div>

          <div className="environment" aria-label="Ambiente local">
            <span className="environment-dot" />
            <span>development</span>
          </div>
        </header>

        <div className="grid">
          {services.map((service) => {
            const Icon = service.icon;

            return (
              <article className="service" key={service.name}>
                <div className="service-header">
                  <span className="icon-frame" aria-hidden="true">
                    <Icon size={20} />
                  </span>
                  <span className={`badge ${service.tone}`}>
                    {service.tone === 'warning' ? (
                      <Clock size={14} aria-hidden="true" />
                    ) : (
                      <CheckCircle size={14} aria-hidden="true" />
                    )}
                    {service.status}
                  </span>
                </div>

                <div>
                  <h2>{service.name}</h2>
                  <p>{service.description}</p>
                </div>

                <div className="port-row">
                  <span>localhost</span>
                  <strong>{service.port}</strong>
                </div>
              </article>
            );
          })}
        </div>

        <div className="footer-grid">
          <section className="source-panel" aria-labelledby="routes-title">
            <p className="source-title" id="routes-title">
              Modulos planejados
            </p>
            <div className="module-list">
              {modules.map((module) => {
                const Icon = module.icon;

                return (
                  <span className="module" key={module.label}>
                    <Icon size={16} aria-hidden="true" />
                    {module.label}
                  </span>
                );
              })}
            </div>
          </section>

          <section className="command-panel" aria-labelledby="command-title">
            <p className="source-title" id="command-title">
              Comando principal
            </p>
            <code>npm run dev</code>
          </section>
        </div>

        <div className="status-strip" aria-label="Status da base local">
          <span>
            <CheckCircle size={16} aria-hidden="true" />
            pgvector habilitado
          </span>
          <span>
            <CheckCircle size={16} aria-hidden="true" />
            Redis conectado
          </span>
          <span>
            <Clock size={16} aria-hidden="true" />
            Regras de negocio em breve
          </span>
        </div>
      </section>
    </main>
  );
}
