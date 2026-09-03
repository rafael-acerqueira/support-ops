'use client';

import {
  AlertCircle,
  BookOpen,
  CheckCircle,
  Clock,
  Eye,
  FileText,
  Loader2,
  MessageSquare,
  RefreshCw,
  Search,
  Ticket,
  X,
} from 'lucide-react';
import Link from 'next/link';
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';

type TicketStatus =
  | 'open'
  | 'triaged'
  | 'waiting_on_customer'
  | 'waiting_on_support'
  | 'resolved'
  | 'closed';
type TicketPriority = 'low' | 'normal' | 'high' | 'urgent';
type SuggestedResponseStatus = 'draft' | 'approved' | 'rejected';
type RiskLevel = 'Low' | 'Medium' | 'High';
type ProductArea = 'billing' | 'security' | 'support' | 'api' | 'product' | 'legal';
type FilterValue = 'all' | string;
type SuggestionConfidenceLevel = 'low' | 'medium' | 'high';
type SuggestionConfidence = SuggestionConfidenceLevel | 'none';
type TicketReadinessTone = 'success' | 'warning' | 'neutral';

type SuggestedResponseSource = {
  document_id?: string;
  chunk_id?: string;
  chunk_index?: number;
  document_name?: string;
  document_type?: string;
  relevance_score?: number;
  excerpt?: string;
};

type SuggestedResponse = {
  id: string;
  ticket_id: string;
  content: string;
  status: SuggestedResponseStatus;
  sources: SuggestedResponseSource[];
  confidence_score: number | null;
  confidence_level: SuggestionConfidenceLevel;
  confidence_reason: string;
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

const suggestionConfidenceLabels: Record<SuggestionConfidence, string> = {
  none: 'No sources',
  low: 'Low confidence',
  medium: 'Medium confidence',
  high: 'High confidence',
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
const lowConfidenceThreshold = 0.5;
const productAreaOptions: Array<{ value: ProductArea; label: string }> = [
  { value: 'billing', label: 'Billing' },
  { value: 'security', label: 'Security' },
  { value: 'support', label: 'Support' },
  { value: 'api', label: 'API' },
  { value: 'product', label: 'Product' },
  { value: 'legal', label: 'Legal' },
];
const customerTierOptions = ['starter', 'pro', 'enterprise'];

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

function formatRelevanceScore(value?: number) {
  if (typeof value !== 'number') return 'No score';

  return `${Math.round(value * 100)}% match`;
}

function getSuggestionConfidence(suggestion: SuggestedResponse): SuggestionConfidence {
  if (suggestion.sources.length === 0 || suggestion.confidence_score === null) return 'none';

  if (suggestion.confidence_level) return suggestion.confidence_level;

  const scores = suggestion.sources
    .map((source) => source.relevance_score)
    .filter((score): score is number => typeof score === 'number');

  if (!scores.length) return 'low';

  const bestScore = Math.max(...scores);

  if (bestScore >= 0.75) return 'high';
  if (bestScore >= lowConfidenceThreshold) return 'medium';
  return 'low';
}

function getSuggestionConfidenceMessage(confidence: SuggestionConfidence) {
  if (confidence === 'none') {
    return 'No document sources were found for this suggestion. Review carefully before using it.';
  }

  if (confidence === 'low') {
    return 'The retrieved sources have low relevance. Validate the answer against internal policy before using it.';
  }

  if (confidence === 'medium') {
    return 'This suggestion has a usable source match, but should still be reviewed before approval.';
  }

  return 'This suggestion is backed by strong retrieved document sources.';
}

function formatSuggestionConfidence(suggestion: SuggestedResponse) {
  const confidence = getSuggestionConfidence(suggestion);
  const score =
    typeof suggestion.confidence_score === 'number'
      ? ` / ${formatRelevanceScore(suggestion.confidence_score)}`
      : '';

  return `${suggestionConfidenceLabels[confidence]}${score}`;
}

function isLowConfidenceSource(source: SuggestedResponseSource) {
  return (
    typeof source.relevance_score !== 'number' || source.relevance_score < lowConfidenceThreshold
  );
}

function getReviewFeedback(status: SuggestedResponseStatus, confidence: SuggestionConfidence) {
  if (status === 'approved') {
    return 'This suggested response has been approved for this ticket.';
  }

  if (status === 'rejected') {
    return 'This suggested response was rejected and should not be used as-is.';
  }

  if (confidence === 'none') {
    return 'No trusted sources are attached. Verify the policy coverage before approving this draft.';
  }

  if (confidence === 'low') {
    return 'Low-confidence draft. Validate the source match before approving this response.';
  }

  if (confidence === 'medium') {
    return 'Medium-confidence draft. Review the retrieved source before approving.';
  }

  return 'Review this draft before using it in a customer reply.';
}

function getTicketReadiness(
  ticket: SupportTicket,
  suggestion: SuggestedResponse | null,
  confidence: SuggestionConfidence | null
): {
  label: string;
  message: string;
  tone: TicketReadinessTone;
} {
  if (!suggestion) {
    return {
      label: 'Ready for response drafting',
      message:
        'Generate a suggested response to retrieve sources and prepare this ticket for review.',
      tone: shouldEscalateTicket(ticket) ? 'warning' : 'neutral',
    };
  }

  if (suggestion.status === 'approved') {
    return {
      label: 'Response approved',
      message: 'The latest suggestion has been approved by a reviewer.',
      tone: 'success',
    };
  }

  if (suggestion.status === 'rejected') {
    return {
      label: 'Response rejected',
      message: 'Generate a new suggestion or revise the response before replying to the customer.',
      tone: 'warning',
    };
  }

  if (confidence === 'none') {
    return {
      label: 'Draft needs source review',
      message: 'The latest suggestion has no retrieved sources attached.',
      tone: 'warning',
    };
  }

  if (confidence === 'low') {
    return {
      label: 'Draft has low-confidence sources',
      message: 'Review the retrieved sources carefully before approving this response.',
      tone: 'warning',
    };
  }

  return {
    label: 'Draft ready for review',
    message: 'The latest suggestion is backed by retrieved sources and awaits approval.',
    tone: 'success',
  };
}

function getTicketRisk(ticket: SupportTicket): RiskLevel {
  if (ticket.priority === 'urgent') return 'High';
  if (ticket.priority === 'high' || ticket.customer_tier === 'enterprise') return 'Medium';
  return 'Low';
}

function shouldEscalateTicket(ticket: SupportTicket) {
  return ticket.priority === 'urgent' || ticket.priority === 'high';
}

function getTicketIntent(ticket: SupportTicket) {
  return `${ticket.product_area}_support_request`;
}

function getRequiredDocuments(ticket: SupportTicket) {
  return [
    `${ticket.product_area}-playbook.md`,
    'internal-support-policy.md',
    `${ticket.customer_tier}-sla.md`,
  ];
}

export default function TicketsPage() {
  const detailPanelRef = useRef<HTMLElement | null>(null);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [statusFilter, setStatusFilter] = useState<FilterValue>('all');
  const [priorityFilter, setPriorityFilter] = useState<FilterValue>('all');
  const [categoryFilter, setCategoryFilter] = useState<FilterValue>('all');
  const [planFilter, setPlanFilter] = useState<FilterValue>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [newTicketExternalId, setNewTicketExternalId] = useState('');
  const [newTicketCustomerName, setNewTicketCustomerName] = useState('');
  const [newTicketCustomerTier, setNewTicketCustomerTier] = useState('enterprise');
  const [newTicketSubject, setNewTicketSubject] = useState('');
  const [newTicketDescription, setNewTicketDescription] = useState('');
  const [newTicketProductArea, setNewTicketProductArea] = useState<ProductArea>('support');
  const [newTicketPriority, setNewTicketPriority] = useState<TicketPriority>('normal');
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [suggestedResponses, setSuggestedResponses] = useState<SuggestedResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingTicket, setIsCreatingTicket] = useState(false);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [isGeneratingSuggestion, setIsGeneratingSuggestion] = useState(false);
  const [reviewingSuggestionId, setReviewingSuggestionId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
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
  const latestSuggestionConfidence = latestSuggestedResponse
    ? getSuggestionConfidence(latestSuggestedResponse)
    : null;
  const selectedTicketReadiness = selectedTicket
    ? getTicketReadiness(selectedTicket, latestSuggestedResponse, latestSuggestionConfidence)
    : null;
  const previousSuggestedResponses = useMemo(
    () => suggestedResponses.slice(1),
    [suggestedResponses]
  );

  const selectTicket = useCallback((ticketId: string) => {
    setSelectedTicketId(ticketId);

    window.requestAnimationFrame(() => {
      detailPanelRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  }, []);

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

  async function handleCreateTicket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setIsCreatingTicket(true);
    setError(null);
    setMessage(null);

    try {
      const response = await fetch('/api/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          external_id: newTicketExternalId,
          customer_name: newTicketCustomerName,
          customer_tier: newTicketCustomerTier,
          subject: newTicketSubject,
          description: newTicketDescription,
          product_area: newTicketProductArea,
          priority: newTicketPriority,
        }),
      });

      if (!response.ok) throw new Error('The API could not create the ticket.');

      const createdTicket = (await response.json()) as SupportTicket;
      setTickets((currentTickets) => [
        createdTicket,
        ...currentTickets.filter((ticket) => ticket.id !== createdTicket.id),
      ]);
      selectTicket(createdTicket.id);
      setNewTicketExternalId('');
      setNewTicketCustomerName('');
      setNewTicketCustomerTier('enterprise');
      setNewTicketSubject('');
      setNewTicketDescription('');
      setNewTicketProductArea('support');
      setNewTicketPriority('normal');
      setMessage('Ticket created.');
    } catch (createError) {
      setError(
        createError instanceof Error ? createError.message : 'Unexpected error while creating.'
      );
    } finally {
      setIsCreatingTicket(false);
    }
  }

  const generateSuggestedResponse = useCallback(async () => {
    if (!selectedTicketId) return;

    setIsGeneratingSuggestion(true);
    setSuggestionError(null);

    try {
      const response = await fetch(`/api/tickets/${selectedTicketId}/suggested-responses`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Unable to generate suggested response.');

      const nextSuggestion = (await response.json()) as SuggestedResponse;
      setSuggestedResponses((currentSuggestions) => [
        nextSuggestion,
        ...currentSuggestions.filter((suggestion) => suggestion.id !== nextSuggestion.id),
      ]);
    } catch (generateError) {
      setSuggestionError(
        generateError instanceof Error
          ? generateError.message
          : 'Unexpected error while generating.'
      );
    } finally {
      setIsGeneratingSuggestion(false);
    }
  }, [selectedTicketId]);

  const reviewSuggestedResponse = useCallback(
    async (suggestion: SuggestedResponse, decision: 'approve' | 'reject') => {
      if (!selectedTicketId) return;

      setReviewingSuggestionId(suggestion.id);
      setSuggestionError(null);

      try {
        const response = await fetch(
          `/api/tickets/${selectedTicketId}/suggested-responses/${suggestion.id}/${decision}`,
          { method: 'PATCH' }
        );
        if (!response.ok) throw new Error('Unable to update suggested response review.');

        const updatedSuggestion = (await response.json()) as SuggestedResponse;
        setSuggestedResponses((currentSuggestions) =>
          currentSuggestions.map((currentSuggestion) =>
            currentSuggestion.id === updatedSuggestion.id ? updatedSuggestion : currentSuggestion
          )
        );
      } catch (reviewError) {
        setSuggestionError(
          reviewError instanceof Error ? reviewError.message : 'Unexpected error while reviewing.'
        );
      } finally {
        setReviewingSuggestionId(null);
      }
    },
    [selectedTicketId]
  );

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
          <form className="ticket-create-panel" onSubmit={handleCreateTicket}>
            <div className="panel-title-row">
              <span className="icon-frame" aria-hidden="true">
                <Ticket size={20} />
              </span>
              <div>
                <h2>Create ticket</h2>
                <p>Register a support request for local triage and response drafting.</p>
              </div>
            </div>

            <label className="field">
              <span>Ticket ID</span>
              <input
                value={newTicketExternalId}
                onChange={(event) => setNewTicketExternalId(event.target.value)}
                placeholder="TCK-1004"
                required
              />
            </label>

            <label className="field">
              <span>Customer</span>
              <input
                value={newTicketCustomerName}
                onChange={(event) => setNewTicketCustomerName(event.target.value)}
                placeholder="Globex Corp"
                required
              />
            </label>

            <label className="field">
              <span>Plan</span>
              <select
                value={newTicketCustomerTier}
                onChange={(event) => setNewTicketCustomerTier(event.target.value)}
              >
                {customerTierOptions.map((tier) => (
                  <option key={tier} value={tier}>
                    {humanize(tier)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Category</span>
              <select
                value={newTicketProductArea}
                onChange={(event) => setNewTicketProductArea(event.target.value as ProductArea)}
              >
                {productAreaOptions.map((area) => (
                  <option key={area.value} value={area.value}>
                    {area.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Priority</span>
              <select
                value={newTicketPriority}
                onChange={(event) => setNewTicketPriority(event.target.value as TicketPriority)}
              >
                {priorityOptions.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field ticket-subject-field">
              <span>Subject</span>
              <input
                value={newTicketSubject}
                onChange={(event) => setNewTicketSubject(event.target.value)}
                placeholder="Duplicate invoice charge"
                required
              />
            </label>

            <label className="field ticket-description-field">
              <span>Description</span>
              <textarea
                value={newTicketDescription}
                onChange={(event) => setNewTicketDescription(event.target.value)}
                placeholder="Customer reports being charged twice for the same invoice and asks for refund guidance."
                required
              />
            </label>

            <button className="primary-button" type="submit" disabled={isCreatingTicket}>
              {isCreatingTicket ? (
                <Loader2 className="spin" size={18} aria-hidden="true" />
              ) : (
                <Ticket size={18} aria-hidden="true" />
              )}
              Create ticket
            </button>
          </form>

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

            {(message || error) && (
              <div className={`notice ${error ? 'error' : 'success'}`} role="status">
                {error ? (
                  <AlertCircle size={16} aria-hidden="true" />
                ) : (
                  <CheckCircle size={16} aria-hidden="true" />
                )}
                {error ?? message}
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
                        onClick={() => selectTicket(ticket.id)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            selectTicket(ticket.id);
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
                                selectTicket(ticket.id);
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
                          <span>
                            {tickets.length === 0
                              ? 'Create a ticket to start support triage.'
                              : 'Adjust filters or search terms to find a matching ticket.'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <aside
            className="detail-panel ticket-detail-panel"
            ref={detailPanelRef}
            aria-labelledby="ticket-detail-title"
          >
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
                  <button
                    className="primary-button compact"
                    type="button"
                    disabled={isGeneratingSuggestion || isLoadingSuggestions}
                    onClick={() => void generateSuggestedResponse()}
                  >
                    <MessageSquare size={16} aria-hidden="true" />
                    {isGeneratingSuggestion ? 'Generating...' : 'Suggest response'}
                  </button>
                </div>

                {selectedTicketReadiness && (
                  <div className={`ticket-readiness ${selectedTicketReadiness.tone}`} role="status">
                    <strong>{selectedTicketReadiness.label}</strong>
                    <span>{selectedTicketReadiness.message}</span>
                  </div>
                )}

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
                    <h3>AI analysis</h3>
                    <AlertCircle size={16} aria-hidden="true" />
                  </div>
                  <dl className="analysis-grid">
                    <div>
                      <dt>Category</dt>
                      <dd>{humanize(selectedTicket.product_area)}</dd>
                    </div>
                    <div>
                      <dt>Intent</dt>
                      <dd>{getTicketIntent(selectedTicket)}</dd>
                    </div>
                    <div>
                      <dt>Urgency</dt>
                      <dd>{priorityLabels[selectedTicket.priority]}</dd>
                    </div>
                    <div>
                      <dt>Risk</dt>
                      <dd>
                        <span
                          className={`risk-badge ${getTicketRisk(selectedTicket).toLowerCase()}`}
                        >
                          {getTicketRisk(selectedTicket)}
                        </span>
                      </dd>
                    </div>
                    <div>
                      <dt>Escalation</dt>
                      <dd>
                        {shouldEscalateTicket(selectedTicket) ? 'Recommended' : 'Not required'}
                      </dd>
                    </div>
                  </dl>
                  <div className="required-documents">
                    <span>Required documents</span>
                    <div className="mini-tag-list">
                      {getRequiredDocuments(selectedTicket).map((documentName) => (
                        <strong key={documentName}>{documentName}</strong>
                      ))}
                    </div>
                  </div>
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

                  {(isLoadingSuggestions || isGeneratingSuggestion) && !suggestionError && (
                    <div className="placeholder-item">
                      {isGeneratingSuggestion
                        ? 'Generating suggested response...'
                        : 'Loading suggested responses...'}
                    </div>
                  )}

                  {!isLoadingSuggestions &&
                    !isGeneratingSuggestion &&
                    !suggestionError &&
                    latestSuggestedResponse && (
                      <article
                        className={`suggested-response-card ${latestSuggestedResponse.status}`}
                      >
                        <div className="suggested-response-meta">
                          <div className="suggested-response-badges">
                            <span
                              className={`suggested-response-status ${latestSuggestedResponse.status}`}
                            >
                              {suggestedResponseStatusLabels[latestSuggestedResponse.status]}
                            </span>
                            <span
                              className={`suggestion-confidence-badge ${latestSuggestionConfidence ?? 'none'}`}
                            >
                              {formatSuggestionConfidence(latestSuggestedResponse)}
                            </span>
                          </div>
                          <span>{formatDate(latestSuggestedResponse.created_at)}</span>
                        </div>
                        <small className="suggestion-confidence-reason">
                          {latestSuggestedResponse.confidence_reason}
                        </small>
                        <p>{latestSuggestedResponse.content}</p>
                      </article>
                    )}

                  {!isLoadingSuggestions &&
                    !isGeneratingSuggestion &&
                    !suggestionError &&
                    latestSuggestedResponse &&
                    latestSuggestionConfidence &&
                    latestSuggestionConfidence !== 'high' && (
                      <div
                        className={`notice inline-notice confidence-notice ${latestSuggestionConfidence}`}
                        role="status"
                      >
                        <AlertCircle size={16} aria-hidden="true" />
                        {getSuggestionConfidenceMessage(latestSuggestionConfidence)}
                      </div>
                    )}

                  {!isLoadingSuggestions &&
                    !isGeneratingSuggestion &&
                    !suggestionError &&
                    !latestSuggestedResponse && (
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
                  {latestSuggestedResponse?.sources.length ? (
                    <div className="source-list">
                      {latestSuggestedResponse.sources.map((source, index) => (
                        <article
                          className={`source-item ${
                            isLowConfidenceSource(source) ? 'low-confidence' : ''
                          }`}
                          key={source.chunk_id ?? `${source.document_name}-${index}`}
                        >
                          <div className="source-item-header">
                            <div className="source-title">
                              <FileText size={15} aria-hidden="true" />
                              <div>
                                <strong>{source.document_name ?? 'Source document'}</strong>
                                <span>
                                  {source.document_type
                                    ? humanize(source.document_type)
                                    : 'Document'}
                                  {typeof source.chunk_index === 'number'
                                    ? ` / chunk ${source.chunk_index + 1}`
                                    : ''}
                                </span>
                              </div>
                            </div>
                            <span
                              className={`source-score ${
                                isLowConfidenceSource(source) ? 'low-confidence' : ''
                              }`}
                            >
                              {formatRelevanceScore(source.relevance_score)}
                            </span>
                          </div>
                          <blockquote>
                            {source.excerpt ?? 'No excerpt available for this source yet.'}
                          </blockquote>
                          {source.document_id && (
                            <small className="source-reference">
                              Document ID {source.document_id.slice(0, 8)}
                            </small>
                          )}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="placeholder-item source-empty-state low-confidence">
                      <AlertCircle size={16} aria-hidden="true" />
                      {latestSuggestedResponse
                        ? getSuggestionConfidenceMessage('none')
                        : 'Sources will appear here when the suggested response retrieves matching document chunks.'}
                    </div>
                  )}
                </section>

                <section className="detail-section">
                  <h3>Review</h3>
                  {latestSuggestedResponse ? (
                    <div className="review-panel">
                      <div
                        className={`notice inline-notice review-feedback ${latestSuggestedResponse.status} ${
                          latestSuggestedResponse.status === 'draft' &&
                          ['none', 'low'].includes(latestSuggestionConfidence ?? 'none')
                            ? 'low-confidence'
                            : ''
                        }`}
                        role="status"
                      >
                        {latestSuggestedResponse.status === 'approved' ? (
                          <CheckCircle size={16} aria-hidden="true" />
                        ) : latestSuggestedResponse.status === 'rejected' ? (
                          <X size={16} aria-hidden="true" />
                        ) : (
                          <Clock size={16} aria-hidden="true" />
                        )}
                        {getReviewFeedback(
                          latestSuggestedResponse.status,
                          latestSuggestionConfidence ?? 'none'
                        )}
                      </div>
                      <div className="review-actions">
                        <button
                          className="secondary-button compact approve-action"
                          type="button"
                          disabled={
                            reviewingSuggestionId === latestSuggestedResponse.id ||
                            latestSuggestedResponse.status === 'approved'
                          }
                          onClick={() =>
                            void reviewSuggestedResponse(latestSuggestedResponse, 'approve')
                          }
                        >
                          {reviewingSuggestionId === latestSuggestedResponse.id ? (
                            <Loader2 size={14} aria-hidden="true" />
                          ) : (
                            <CheckCircle size={14} aria-hidden="true" />
                          )}
                          {latestSuggestedResponse.status === 'approved' ? 'Approved' : 'Approve'}
                        </button>
                        <button
                          className="secondary-button compact reject-action"
                          type="button"
                          disabled={
                            reviewingSuggestionId === latestSuggestedResponse.id ||
                            latestSuggestedResponse.status === 'rejected'
                          }
                          onClick={() =>
                            void reviewSuggestedResponse(latestSuggestedResponse, 'reject')
                          }
                        >
                          {reviewingSuggestionId === latestSuggestedResponse.id ? (
                            <Loader2 size={14} aria-hidden="true" />
                          ) : (
                            <X size={14} aria-hidden="true" />
                          )}
                          {latestSuggestedResponse.status === 'rejected' ? 'Rejected' : 'Reject'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="placeholder-item">
                      Approval and rejection controls will be enabled after a draft response exists.
                    </div>
                  )}
                </section>

                <section className="detail-section">
                  <div className="section-title-row">
                    <h3>Suggestion history</h3>
                    <Clock size={16} aria-hidden="true" />
                  </div>
                  {previousSuggestedResponses.length ? (
                    <div className="suggestion-history-list">
                      {previousSuggestedResponses.map((suggestion) => (
                        <article
                          className={`suggestion-history-item ${suggestion.status}`}
                          key={suggestion.id}
                        >
                          <div className="suggestion-history-header">
                            <div className="suggested-response-badges">
                              <span className={`suggested-response-status ${suggestion.status}`}>
                                {suggestedResponseStatusLabels[suggestion.status]}
                              </span>
                              <span
                                className={`suggestion-confidence-badge ${getSuggestionConfidence(
                                  suggestion
                                )}`}
                              >
                                {formatSuggestionConfidence(suggestion)}
                              </span>
                            </div>
                            <span>{formatDate(suggestion.created_at)}</span>
                          </div>
                          <small className="suggestion-confidence-reason compact">
                            {suggestion.confidence_reason}
                          </small>
                          <p>{suggestion.content}</p>
                          {suggestion.sources.length ? (
                            <div className="history-source-list">
                              {suggestion.sources.map((source, index) => (
                                <div
                                  className={`history-source-item ${
                                    isLowConfidenceSource(source) ? 'low-confidence' : ''
                                  }`}
                                  key={source.chunk_id ?? `${source.document_name}-${index}`}
                                >
                                  <strong>{source.document_name ?? 'Source document'}</strong>
                                  <span>{formatRelevanceScore(source.relevance_score)}</span>
                                  <small>
                                    {source.excerpt ?? 'No excerpt available for this source yet.'}
                                  </small>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <small className="history-empty-sources">
                              No sources were attached to this suggestion.
                            </small>
                          )}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="placeholder-item">
                      Previous suggestions will appear here after this ticket has more than one
                      generated response.
                    </div>
                  )}
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
