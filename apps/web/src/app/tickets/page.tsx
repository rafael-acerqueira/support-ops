'use client';

import {
  AlertCircle,
  BookOpen,
  CheckCircle,
  Clock,
  Eye,
  MessageSquare,
  RefreshCw,
  Search,
  Ticket,
  X,
} from 'lucide-react';
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
type SuggestedResponseStatus = 'draft' | 'approved' | 'rejected';
type ProductArea = 'billing' | 'security' | 'support' | 'api' | 'product' | 'legal';
type FilterValue = 'all' | string;

type SuggestedResponse = {
  id: string;
  ticket_id: string;
  content: string;
  status: SuggestedResponseStatus;
  sources: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
};

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

const suggestedResponseStatusLabels: Record<SuggestedResponseStatus, string> = {
  draft: 'Draft',
  approved: 'Approved',
  rejected: 'Rejected',
};

const statusIcons = {
  open: Clock,
  triaged: CheckCircle,
  waiting_on_customer: Clock,
  waiting_on_support: Clock,
  resolved: CheckCircle,
  closed: CheckCircle,
};

const statusOptions = Object.entries(statusLabels) as Array<[TicketStatus, string]>;
const priorityOptions = Object.entries(priorityLabels) as Array<[TicketPriority, string]>;

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
  const [statusFilter, setStatusFilter] = useState<FilterValue>('all');
  const [priorityFilter, setPriorityFilter] = useState<FilterValue>('all');
  const [categoryFilter, setCategoryFilter] = useState<FilterValue>('all');
  const [planFilter, setPlanFilter] = useState<FilterValue>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [suggestedResponses, setSuggestedResponses] = useState<SuggestedResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);

  const categoryOptions = useMemo(
    () => Array.from(new Set(tickets.map((ticket) => ticket.product_area))).sort(),
    [tickets]
  );
  const planOptions = useMemo(
    () => Array.from(new Set(tickets.map((ticket) => ticket.customer_tier))).sort(),
    [tickets]
  );

  const filteredTickets = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return tickets.filter((ticket) => {
      const matchesStatus = statusFilter === 'all' || ticket.status === statusFilter;
      const matchesPriority = priorityFilter === 'all' || ticket.priority === priorityFilter;
      const matchesCategory = categoryFilter === 'all' || ticket.product_area === categoryFilter;
      const matchesPlan = planFilter === 'all' || ticket.customer_tier === planFilter;
      const matchesSearch =
        !query ||
        [ticket.external_id, ticket.customer_name, ticket.subject, ticket.description]
          .join(' ')
          .toLowerCase()
          .includes(query);

      return matchesStatus && matchesPriority && matchesCategory && matchesPlan && matchesSearch;
    });
  }, [categoryFilter, planFilter, priorityFilter, searchQuery, statusFilter, tickets]);

  const openCount = useMemo(
    () => filteredTickets.filter((ticket) => ticket.status === 'open').length,
    [filteredTickets]
  );
  const triagedCount = useMemo(
    () => filteredTickets.filter((ticket) => ticket.status === 'triaged').length,
    [filteredTickets]
  );
  const urgentOrHighCount = useMemo(
    () => filteredTickets.filter((ticket) => ['urgent', 'high'].includes(ticket.priority)).length,
    [filteredTickets]
  );
  const selectedTicket = useMemo(
    () => tickets.find((ticket) => ticket.id === selectedTicketId) ?? null,
    [selectedTicketId, tickets]
  );
  const SelectedStatusIcon = selectedTicket ? statusIcons[selectedTicket.status] : null;
  const latestSuggestedResponse = suggestedResponses[0] ?? null;

  const loadTickets = useCallback(async () => {
    setError(null);

    try {
      const response = await fetch('/api/tickets', { cache: 'no-store' });
      if (!response.ok) throw new Error('Unable to load tickets.');

      const nextTickets = (await response.json()) as SupportTicket[];
      setTickets(nextTickets);
      setSelectedTicketId((currentTicketId) =>
        currentTicketId && nextTickets.some((ticket) => ticket.id === currentTicketId)
          ? currentTicketId
          : null
      );
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unexpected error while loading.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  useEffect(() => {
    if (!selectedTicketId) {
      setSuggestedResponses([]);
      setSuggestionError(null);
      return;
    }

    let shouldIgnore = false;

    async function loadSuggestedResponses() {
      setIsLoadingSuggestions(true);
      setSuggestionError(null);

      try {
        const response = await fetch(`/api/tickets/${selectedTicketId}/suggested-responses`, {
          cache: 'no-store',
        });
        if (!response.ok) throw new Error('Unable to load suggested responses.');

        const nextSuggestions = (await response.json()) as SuggestedResponse[];
        if (!shouldIgnore) setSuggestedResponses(nextSuggestions);
      } catch (loadError) {
        if (!shouldIgnore) {
          setSuggestedResponses([]);
          setSuggestionError(
            loadError instanceof Error ? loadError.message : 'Unexpected error while loading.'
          );
        }
      } finally {
        if (!shouldIgnore) setIsLoadingSuggestions(false);
      }
    }

    void loadSuggestedResponses();

    return () => {
      shouldIgnore = true;
    };
  }, [selectedTicketId]);

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
            <strong>{filteredTickets.length}</strong>
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
                <p>
                  {isLoading
                    ? 'Loading records'
                    : `${filteredTickets.length} of ${tickets.length} records`}
                </p>
              </div>
              <span className="environment">development</span>
            </div>

            {error && (
              <div className="notice error" role="status">
                <AlertCircle size={16} aria-hidden="true" />
                {error}
              </div>
            )}

            <div className="ticket-controls" aria-label="Ticket filters">
              <label className="field compact-field">
                <span>Status</span>
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                >
                  <option value="all">All</option>
                  {statusOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field compact-field">
                <span>Priority</span>
                <select
                  value={priorityFilter}
                  onChange={(event) => setPriorityFilter(event.target.value)}
                >
                  <option value="all">All</option>
                  {priorityOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field compact-field">
                <span>Category</span>
                <select
                  value={categoryFilter}
                  onChange={(event) => setCategoryFilter(event.target.value)}
                >
                  <option value="all">All</option>
                  {categoryOptions.map((category) => (
                    <option key={category} value={category}>
                      {humanize(category)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field compact-field">
                <span>Plan</span>
                <select value={planFilter} onChange={(event) => setPlanFilter(event.target.value)}>
                  <option value="all">All</option>
                  {planOptions.map((plan) => (
                    <option key={plan} value={plan}>
                      {humanize(plan)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="search-field">
              <Search size={18} aria-hidden="true" />
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search by customer, subject, ticket id, or content"
              />
            </label>

            <div className="table-wrap">
              <table className="tickets-table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Customer</th>
                    <th>Plan</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTickets.map((ticket) => {
                    const StatusIcon = statusIcons[ticket.status];

                    return (
                      <tr
                        key={ticket.id}
                        className={
                          selectedTicketId === ticket.id ? 'document-row selected' : 'document-row'
                        }
                        tabIndex={0}
                        onClick={() => setSelectedTicketId(ticket.id)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            setSelectedTicketId(ticket.id);
                          }
                        }}
                      >
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
                        <td>
                          <div className="actions">
                            <button
                              className="icon-button small"
                              type="button"
                              title="View details"
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedTicketId(ticket.id);
                              }}
                            >
                              <Eye size={16} aria-hidden="true" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}

                  {!isLoading && filteredTickets.length === 0 && (
                    <tr>
                      <td colSpan={8}>
                        <div className="empty-state">
                          <Ticket size={24} aria-hidden="true" />
                          <strong>
                            {tickets.length === 0
                              ? 'No tickets registered'
                              : 'No tickets match the current filters'}
                          </strong>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="detail-panel ticket-detail-panel" aria-labelledby="ticket-detail-title">
            {selectedTicket && SelectedStatusIcon ? (
              <>
                <div className="detail-header">
                  <div className="detail-title-group">
                    <span className="icon-frame">
                      <Ticket size={20} aria-hidden="true" />
                    </span>
                    <div>
                      <p className="eyebrow">Ticket detail</p>
                      <h2 id="ticket-detail-title">{selectedTicket.subject}</h2>
                    </div>
                  </div>
                  <button
                    className="icon-button small"
                    type="button"
                    title="Close details"
                    onClick={() => setSelectedTicketId(null)}
                  >
                    <X size={16} aria-hidden="true" />
                  </button>
                </div>

                <div className="detail-actions">
                  <button className="primary-button compact" type="button" disabled>
                    <MessageSquare size={16} aria-hidden="true" />
                    Suggest response
                  </button>
                </div>

                <dl className="detail-grid">
                  <div>
                    <dt>Ticket</dt>
                    <dd className="mono-value">{selectedTicket.external_id}</dd>
                  </div>
                  <div>
                    <dt>Customer</dt>
                    <dd>{selectedTicket.customer_name}</dd>
                  </div>
                  <div>
                    <dt>Plan</dt>
                    <dd>{humanize(selectedTicket.customer_tier)}</dd>
                  </div>
                  <div>
                    <dt>Category</dt>
                    <dd>{humanize(selectedTicket.product_area)}</dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>
                      <span className={`status-badge ${selectedTicket.status}`}>
                        <SelectedStatusIcon size={14} aria-hidden="true" />
                        {statusLabels[selectedTicket.status]}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt>Priority</dt>
                    <dd>
                      <span className={`priority-badge ${selectedTicket.priority}`}>
                        {priorityLabels[selectedTicket.priority]}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt>Created</dt>
                    <dd>{formatDate(selectedTicket.created_at)}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatDate(selectedTicket.updated_at)}</dd>
                  </div>
                </dl>

                <section className="detail-section">
                  <h3>Customer message</h3>
                  <p className="ticket-description">{selectedTicket.description}</p>
                </section>

                <section className="detail-section">
                  <div className="section-title-row">
                    <h3>Suggested response</h3>
                    <MessageSquare size={16} aria-hidden="true" />
                  </div>

                  {suggestionError && (
                    <div className="notice error inline-notice" role="status">
                      <AlertCircle size={16} aria-hidden="true" />
                      {suggestionError}
                    </div>
                  )}

                  {isLoadingSuggestions && !suggestionError && (
                    <div className="placeholder-item">Loading suggested responses...</div>
                  )}

                  {!isLoadingSuggestions && !suggestionError && latestSuggestedResponse && (
                    <article className="suggested-response-card">
                      <div className="suggested-response-meta">
                        <span
                          className={`suggested-response-status ${latestSuggestedResponse.status}`}
                        >
                          {suggestedResponseStatusLabels[latestSuggestedResponse.status]}
                        </span>
                        <span>{formatDate(latestSuggestedResponse.created_at)}</span>
                      </div>
                      <p>{latestSuggestedResponse.content}</p>
                    </article>
                  )}

                  {!isLoadingSuggestions && !suggestionError && !latestSuggestedResponse && (
                    <div className="placeholder-item">
                      No suggested responses generated for this ticket yet.
                    </div>
                  )}
                </section>

                <section className="detail-section">
                  <div className="section-title-row">
                    <h3>Sources</h3>
                    <BookOpen size={16} aria-hidden="true" />
                  </div>
                  <div className="placeholder-item">
                    {latestSuggestedResponse
                      ? `${latestSuggestedResponse.sources.length} sources linked to the latest suggestion.`
                      : 'Sources will be shown after a suggested response retrieves document chunks.'}
                  </div>
                </section>

                <section className="detail-section">
                  <h3>Review</h3>
                  <div className="placeholder-item">
                    Approval and rejection controls will be enabled after a draft response exists.
                  </div>
                </section>
              </>
            ) : (
              <div className="detail-empty">
                <Ticket size={28} aria-hidden="true" />
                <h2 id="ticket-detail-title">Ticket detail</h2>
                <p>Select a ticket to inspect customer context and prepare response review.</p>
              </div>
            )}
          </aside>
        </section>
      </section>
    </main>
  );
}
