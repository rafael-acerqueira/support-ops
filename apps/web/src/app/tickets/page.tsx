'use client';

import { AlertCircle, CheckCircle, Clock, RefreshCw, Ticket } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';

type TicketStatus =
  | 'open'
  | 'triaged'
  | 'waiting_on_customer'
  | 'waiting_on_support'
  | 'resolved'
  | 'closed';
type TicketPriority = 'low' | 'normal' | 'high' | 'urgent';
type ProductArea = 'billing' | 'security' | 'support' | 'api' | 'product' | 'legal';

type SupportTicket = {
  id: string;
  external_id: string;
  customer_name: string;
  customer_tier: string;
  subject: string;
  description: string;
  product_area: ProductArea;
  status: TicketStatus;
  priority: TicketPriority;
  created_at: string;
  updated_at: string;
};

const statusLabels: Record<TicketStatus, string> = {
  open: 'Open',
  triaged: 'Triaged',
  waiting_on_customer: 'Waiting on customer',
  waiting_on_support: 'Waiting on support',
  resolved: 'Resolved',
  closed: 'Closed',
};

const priorityLabels: Record<TicketPriority, string> = {
  low: 'Low',
  normal: 'Normal',
  high: 'High',
  urgent: 'Urgent',
};

const statusIcons = {
  open: Clock,
  triaged: CheckCircle,
  waiting_on_customer: Clock,
  waiting_on_support: Clock,
  resolved: CheckCircle,
  closed: CheckCircle,
};

function formatDate(value: string | null) {
  if (!value) return '-';

  return new Intl.DateTimeFormat('en-US', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function humanize(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const openCount = useMemo(
    () => tickets.filter((ticket) => ticket.status === 'open').length,
    [tickets]
  );
  const triagedCount = useMemo(
    () => tickets.filter((ticket) => ticket.status === 'triaged').length,
    [tickets]
  );
  const urgentOrHighCount = useMemo(
    () => tickets.filter((ticket) => ['urgent', 'high'].includes(ticket.priority)).length,
    [tickets]
  );

  const loadTickets = useCallback(async () => {
    setError(null);

    try {
      const response = await fetch('/api/tickets', { cache: 'no-store' });
      if (!response.ok) throw new Error('Unable to load tickets.');
      setTickets((await response.json()) as SupportTicket[]);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unexpected error while loading.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  return (
    <main className="shell">
      <section className="workspace" aria-labelledby="page-title">
        <header className="header documents-header">
          <div>
            <p className="eyebrow">SupportOps</p>
            <h1 id="page-title">Tickets</h1>
            <p className="summary">
              Support requests waiting for triage, review, and AI-assisted response drafting.
            </p>
          </div>

          <div className="header-actions">
            <Link className="secondary-button compact" href="/">
              Knowledge Base
            </Link>
            <button
              className="icon-button"
              type="button"
              onClick={() => void loadTickets()}
              title="Refresh tickets"
            >
              <RefreshCw size={18} aria-hidden="true" />
            </button>
          </div>
        </header>

        <section className="metrics" aria-label="Tickets summary">
          <div className="metric">
            <span>Total</span>
            <strong>{tickets.length}</strong>
          </div>
          <div className="metric">
            <span>Open</span>
            <strong>{openCount}</strong>
          </div>
          <div className="metric">
            <span>Triaged</span>
            <strong>{triagedCount}</strong>
          </div>
          <div className="metric">
            <span>High priority</span>
            <strong>{urgentOrHighCount}</strong>
          </div>
        </section>

        <section className="tickets-layout">
          <section className="documents-panel" aria-labelledby="tickets-title">
            <div className="panel-heading">
              <div>
                <h2 id="tickets-title">Ticket queue</h2>
                <p>{isLoading ? 'Loading records' : `${tickets.length} records`}</p>
              </div>
              <span className="environment">development</span>
            </div>

            {error && (
              <div className="notice error" role="status">
                <AlertCircle size={16} aria-hidden="true" />
                {error}
              </div>
            )}

            <div className="table-wrap">
              <table className="tickets-table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Customer</th>
                    <th>Tier</th>
                    <th>Area</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => {
                    const StatusIcon = statusIcons[ticket.status];

                    return (
                      <tr key={ticket.id}>
                        <td>
                          <div className="ticket-subject">
                            <Ticket size={18} aria-hidden="true" />
                            <div>
                              <strong>{ticket.subject}</strong>
                              <span>{ticket.external_id}</span>
                            </div>
                          </div>
                        </td>
                        <td>{ticket.customer_name}</td>
                        <td>{humanize(ticket.customer_tier)}</td>
                        <td>{humanize(ticket.product_area)}</td>
                        <td>
                          <span className={`status-badge ${ticket.status}`}>
                            <StatusIcon size={14} aria-hidden="true" />
                            {statusLabels[ticket.status]}
                          </span>
                        </td>
                        <td>
                          <span className={`priority-badge ${ticket.priority}`}>
                            {priorityLabels[ticket.priority]}
                          </span>
                        </td>
                        <td>{formatDate(ticket.updated_at)}</td>
                      </tr>
                    );
                  })}

                  {!isLoading && tickets.length === 0 && (
                    <tr>
                      <td colSpan={7}>
                        <div className="empty-state">
                          <Ticket size={24} aria-hidden="true" />
                          <strong>No tickets registered</strong>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}
