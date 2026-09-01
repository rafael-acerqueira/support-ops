'use client';

import Link from 'next/link';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  Cpu,
  Eye,
  FileText,
  History,
  Loader2,
  Power,
  PowerOff,
  RefreshCw,
  Upload,
  X,
} from 'lucide-react';
import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';

type DocumentStatus = 'uploaded' | 'processing' | 'indexed' | 'failed';
type DocumentType =
  | 'internal_policy'
  | 'sla_policy'
  | 'security_policy'
  | 'incident_policy'
  | 'playbook'
  | 'faq'
  | 'technical_documentation';
type ProductArea = 'billing' | 'security' | 'support' | 'api' | 'product' | 'legal';
type DocumentReadinessTone = 'success' | 'warning' | 'error';

type KnowledgeDocument = {
  id: string;
  name: string;
  document_type: DocumentType;
  product_area: ProductArea;
  version: string;
  status: DocumentStatus;
  is_active: boolean;
  tags: string[];
  source_file_name: string;
  storage_key: string | null;
  content_type: string;
  size_bytes: number;
  chunk_count: number;
  failure_reason: string | null;
  last_processed_at: string | null;
  created_at: string;
  updated_at: string;
};

type DocumentChunk = {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  metadata: Record<string, unknown>;
  has_embedding: boolean;
  embedding_provider: string | null;
  embedding_model: string | null;
  created_at: string;
};

const documentTypes: Array<{ value: DocumentType; label: string }> = [
  { value: 'internal_policy', label: 'Internal policy' },
  { value: 'sla_policy', label: 'SLA policy' },
  { value: 'security_policy', label: 'Security policy' },
  { value: 'incident_policy', label: 'Incident policy' },
  { value: 'playbook', label: 'Playbook' },
  { value: 'faq', label: 'FAQ' },
  { value: 'technical_documentation', label: 'Technical documentation' },
];

const productAreas: Array<{ value: ProductArea; label: string }> = [
  { value: 'billing', label: 'Billing' },
  { value: 'security', label: 'Security' },
  { value: 'support', label: 'Support' },
  { value: 'api', label: 'API' },
  { value: 'product', label: 'Product' },
  { value: 'legal', label: 'Legal' },
];

const statusLabels: Record<DocumentStatus, string> = {
  uploaded: 'Uploaded',
  processing: 'Processing',
  indexed: 'Indexed',
  failed: 'Failed',
};

const statusIcons = {
  uploaded: Clock,
  processing: Loader2,
  indexed: CheckCircle,
  failed: AlertCircle,
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

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function humanize(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function getDocumentReadiness(document: KnowledgeDocument): {
  label: string;
  message: string;
  tone: DocumentReadinessTone;
} {
  if (!document.storage_key) {
    return {
      label: 'Missing file reference',
      message: 'This document cannot be reprocessed because no stored file is attached.',
      tone: 'warning',
    };
  }

  if (document.status === 'failed') {
    return {
      label: 'Processing failed',
      message: document.failure_reason ?? 'Review the source file and try reprocessing.',
      tone: 'error',
    };
  }

  if (document.status === 'indexed') {
    return {
      label: 'Ready for retrieval',
      message: `${document.chunk_count} chunks are indexed and available for ticket suggestions.`,
      tone: 'success',
    };
  }

  if (document.status === 'processing') {
    return {
      label: 'Processing in progress',
      message: 'SupportOps is extracting chunks and generating embeddings for this document.',
      tone: 'warning',
    };
  }

  return {
    label: 'Awaiting processing',
    message: 'This document has been uploaded and is waiting for processing.',
    tone: 'warning',
  };
}

export default function DocumentsPage() {
  const detailPanelRef = useRef<HTMLElement | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [documentType, setDocumentType] = useState<DocumentType>('internal_policy');
  const [productArea, setProductArea] = useState<ProductArea>('support');
  const [tags, setTags] = useState('enterprise, sla');
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [busyDocumentId, setBusyDocumentId] = useState<string | null>(null);
  const [watchedDocumentIds, setWatchedDocumentIds] = useState<string[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [selectedDocumentChunks, setSelectedDocumentChunks] = useState<DocumentChunk[]>([]);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const indexedCount = useMemo(
    () => documents.filter((document) => document.status === 'indexed').length,
    [documents]
  );
  const chunkCount = useMemo(
    () => documents.reduce((total, document) => total + document.chunk_count, 0),
    [documents]
  );
  const activeCount = useMemo(
    () => documents.filter((document) => document.is_active).length,
    [documents]
  );
  const isPolling = watchedDocumentIds.length > 0;
  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId) ?? null,
    [documents, selectedDocumentId]
  );
  const selectedEmbeddingSummary = useMemo(() => {
    const embeddedChunks = selectedDocumentChunks.filter((chunk) => chunk.has_embedding);
    const chunkWithMetadata =
      embeddedChunks.find((chunk) => chunk.embedding_provider || chunk.embedding_model) ?? null;

    return {
      embeddedCount: embeddedChunks.length,
      provider: chunkWithMetadata?.embedding_provider ?? null,
      model: chunkWithMetadata?.embedding_model ?? null,
    };
  }, [selectedDocumentChunks]);

  const watchDocument = useCallback((documentId: string) => {
    setWatchedDocumentIds((current) =>
      current.includes(documentId) ? current : [...current, documentId]
    );
  }, []);

  const loadDocumentChunks = useCallback(async (documentId: string) => {
    setIsLoadingChunks(true);

    try {
      const response = await fetch(`/api/documents/${documentId}/chunks`, { cache: 'no-store' });
      if (!response.ok) throw new Error('Unable to load document chunks.');

      const chunks = (await response.json()) as DocumentChunk[];
      setSelectedDocumentChunks(chunks);
    } catch (chunkError) {
      setSelectedDocumentChunks([]);
      setError(
        chunkError instanceof Error
          ? chunkError.message
          : 'Unexpected error while loading document chunks.'
      );
    } finally {
      setIsLoadingChunks(false);
    }
  }, []);

  const selectDocument = useCallback(
    (documentId: string) => {
      setSelectedDocumentId(documentId);
      setSelectedDocumentChunks([]);
      void loadDocumentChunks(documentId);

      window.requestAnimationFrame(() => {
        detailPanelRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      });
    },
    [loadDocumentChunks]
  );

  const loadDocuments = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setError(null);

    try {
      const response = await fetch('/api/documents', { cache: 'no-store' });
      if (!response.ok) throw new Error('Unable to load documents.');

      const nextDocuments = (await response.json()) as KnowledgeDocument[];
      setDocuments(nextDocuments);
      setSelectedDocumentId((current) => {
        if (!current || nextDocuments.some((document) => document.id === current)) return current;

        setSelectedDocumentChunks([]);
        return null;
      });
      setWatchedDocumentIds((current) =>
        current.filter((documentId) => {
          const document = nextDocuments.find((item) => item.id === documentId);
          return document ? !['indexed', 'failed'].includes(document.status) : false;
        })
      );
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unexpected error while loading.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!isPolling) return;

    const intervalId = window.setInterval(() => {
      void loadDocuments({ silent: true });
    }, 1500);

    return () => window.clearInterval(intervalId);
  }, [isPolling, loadDocuments]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file) {
      setError('Select a file to upload.');
      return;
    }

    const formData = new FormData();
    formData.append('document_type', documentType);
    formData.append('product_area', productArea);
    tags
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean)
      .forEach((tag) => formData.append('tags', tag));
    formData.append('file', file);

    setIsUploading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('The API rejected the upload.');

      const uploadedDocument = (await response.json()) as KnowledgeDocument;
      const visibleDocument =
        uploadedDocument.status === 'uploaded'
          ? { ...uploadedDocument, status: 'processing' as DocumentStatus }
          : uploadedDocument;

      setDocuments((currentDocuments) => [
        visibleDocument,
        ...currentDocuments.filter((document) => document.id !== uploadedDocument.id),
      ]);
      setSelectedDocumentId(uploadedDocument.id);
      if (!['indexed', 'failed'].includes(uploadedDocument.status))
        watchDocument(uploadedDocument.id);

      setFile(null);
      setMessage('Document uploaded. Processing queued.');
    } catch (uploadError) {
      setError(
        uploadError instanceof Error ? uploadError.message : 'Unexpected error during upload.'
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function postDocumentAction(
    documentId: string,
    action: 'activate' | 'deactivate' | 'process'
  ) {
    setBusyDocumentId(documentId);
    setError(null);
    setMessage(null);

    try {
      const response = await fetch(`/api/documents/${documentId}/${action}`, { method: 'POST' });
      if (!response.ok) throw new Error('The API could not complete the action.');

      if (action === 'process') {
        watchDocument(documentId);
        setSelectedDocumentChunks([]);
        setDocuments((current) =>
          current.map((document) =>
            document.id === documentId ? { ...document, status: 'processing' } : document
          )
        );
      }

      setMessage(
        action === 'process'
          ? 'Processing queued.'
          : action === 'deactivate'
            ? 'Document deactivated.'
            : 'Document activated.'
      );
      await loadDocuments({ silent: action === 'process' });
    } catch (actionError) {
      setError(
        actionError instanceof Error
          ? actionError.message
          : 'Unexpected error while running the action.'
      );
    } finally {
      setBusyDocumentId(null);
    }
  }

  const SelectedStatusIcon = selectedDocument ? statusIcons[selectedDocument.status] : null;
  const selectedIsBusy = selectedDocument ? busyDocumentId === selectedDocument.id : false;
  const selectedReadiness = selectedDocument ? getDocumentReadiness(selectedDocument) : null;

  return (
    <main className="shell">
      <section className="workspace" aria-labelledby="page-title">
        <header className="header documents-header">
          <div>
            <p className="eyebrow">SupportOps</p>
            <h1 id="page-title">Knowledge Base</h1>
            <p className="summary">
              Internal documents used by AI to draft trusted responses aligned with support
              policies.
            </p>
          </div>

          <div className="header-actions">
            <Link className="secondary-button compact" href="/tickets">
              Tickets
            </Link>
            <button
              className="icon-button"
              type="button"
              onClick={() => void loadDocuments()}
              title="Refresh list"
            >
              <RefreshCw size={18} aria-hidden="true" />
            </button>
          </div>
        </header>

        <section className="metrics" aria-label="Documents summary">
          <div className="metric">
            <span>Total</span>
            <strong>{documents.length}</strong>
          </div>
          <div className="metric">
            <span>Indexed</span>
            <strong>{indexedCount}</strong>
          </div>
          <div className="metric">
            <span>Active</span>
            <strong>{activeCount}</strong>
          </div>
          <div className="metric">
            <span>Chunks</span>
            <strong>{chunkCount}</strong>
          </div>
        </section>

        <section className="document-layout">
          <form className="upload-panel" onSubmit={handleUpload}>
            <div className="panel-title-row">
              <span className="icon-frame" aria-hidden="true">
                <Upload size={20} />
              </span>
              <div>
                <h2>Upload document</h2>
                <p>Policies, playbooks, FAQs, and technical documentation.</p>
              </div>
            </div>

            <label className="field">
              <span>Document type</span>
              <select
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value as DocumentType)}
              >
                {documentTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Product area</span>
              <select
                value={productArea}
                onChange={(event) => setProductArea(event.target.value as ProductArea)}
              >
                {productAreas.map((area) => (
                  <option key={area.value} value={area.value}>
                    {area.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Tags</span>
              <input
                value={tags}
                onChange={(event) => setTags(event.target.value)}
                placeholder="enterprise, refund, billing"
              />
            </label>

            <label className="file-field">
              <FileText size={18} aria-hidden="true" />
              <span>{file ? file.name : 'Select file'}</span>
              <input type="file" onChange={handleFileChange} />
            </label>

            <button className="primary-button" type="submit" disabled={isUploading}>
              {isUploading ? (
                <Loader2 className="spin" size={18} aria-hidden="true" />
              ) : (
                <Upload size={18} aria-hidden="true" />
              )}
              Upload document
            </button>
          </form>

          <section className="documents-panel" aria-labelledby="documents-title">
            <div className="panel-heading">
              <div>
                <h2 id="documents-title">Registered documents</h2>
                <p>{isLoading ? 'Loading records' : `${documents.length} records`}</p>
              </div>
              <span className="environment">{isPolling ? 'syncing' : 'development'}</span>
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

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Area</th>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Chunks</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document) => {
                    const StatusIcon = statusIcons[document.status];
                    const isBusy = busyDocumentId === document.id;

                    return (
                      <tr
                        className={[
                          'document-row',
                          selectedDocumentId === document.id ? 'selected' : '',
                          document.is_active ? '' : 'inactive',
                        ]
                          .filter(Boolean)
                          .join(' ')}
                        key={document.id}
                        onClick={() => selectDocument(document.id)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            selectDocument(document.id);
                          }
                        }}
                        tabIndex={0}
                      >
                        <td>
                          <div className="document-name">
                            <FileText size={18} aria-hidden="true" />
                            <div>
                              <strong>{document.name}</strong>
                              <span>{formatBytes(document.size_bytes)}</span>
                            </div>
                            {!document.is_active && <em>Inactive</em>}
                          </div>
                        </td>
                        <td>{humanize(document.document_type)}</td>
                        <td>{humanize(document.product_area)}</td>
                        <td>{document.version}</td>
                        <td>
                          <span className={`status-badge ${document.status}`}>
                            <StatusIcon
                              className={document.status === 'processing' ? 'spin' : undefined}
                              size={14}
                              aria-hidden="true"
                            />
                            {statusLabels[document.status]}
                          </span>
                        </td>
                        <td>{document.chunk_count}</td>
                        <td>{formatDate(document.updated_at)}</td>
                        <td>
                          <div className="actions">
                            <button
                              className="icon-button small"
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                selectDocument(document.id);
                              }}
                              title="View details"
                            >
                              <Eye size={16} aria-hidden="true" />
                            </button>
                            <button
                              className="icon-button small"
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                void postDocumentAction(document.id, 'process');
                              }}
                              disabled={isBusy || !document.storage_key}
                              title={
                                document.storage_key
                                  ? 'Reprocess'
                                  : 'Cannot reprocess without a stored file'
                              }
                            >
                              {isBusy ? (
                                <Loader2 className="spin" size={16} aria-hidden="true" />
                              ) : (
                                <RefreshCw size={16} aria-hidden="true" />
                              )}
                            </button>
                            <button
                              className="icon-button small"
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                void postDocumentAction(
                                  document.id,
                                  document.is_active ? 'deactivate' : 'activate'
                                );
                              }}
                              disabled={isBusy}
                              title={document.is_active ? 'Deactivate' : 'Activate'}
                            >
                              {document.is_active ? (
                                <PowerOff size={16} aria-hidden="true" />
                              ) : (
                                <Power size={16} aria-hidden="true" />
                              )}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}

                  {!isLoading && documents.length === 0 && (
                    <tr>
                      <td colSpan={8}>
                        <div className="empty-state">
                          <FileText size={24} aria-hidden="true" />
                          <strong>No documents registered</strong>
                          <span>Upload a policy, playbook, FAQ, or technical document.</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="detail-panel" ref={detailPanelRef} aria-labelledby="detail-title">
            {selectedDocument && SelectedStatusIcon ? (
              <>
                <div className="detail-header">
                  <div className="detail-title-group">
                    <span className="icon-frame" aria-hidden="true">
                      <FileText size={20} />
                    </span>
                    <div>
                      <p className="eyebrow">Document detail</p>
                      <h2 id="detail-title">{selectedDocument.name}</h2>
                    </div>
                  </div>
                  <button
                    className="icon-button small"
                    type="button"
                    onClick={() => {
                      setSelectedDocumentId(null);
                      setSelectedDocumentChunks([]);
                    }}
                    title="Close detail"
                  >
                    <X size={16} aria-hidden="true" />
                  </button>
                </div>

                <div className="detail-actions">
                  <button
                    className="primary-button compact"
                    type="button"
                    onClick={() => void postDocumentAction(selectedDocument.id, 'process')}
                    disabled={selectedIsBusy || !selectedDocument.storage_key}
                    title={
                      selectedDocument.storage_key
                        ? 'Reprocess document'
                        : 'Cannot reprocess without a stored file'
                    }
                  >
                    {selectedIsBusy ? (
                      <Loader2 className="spin" size={16} aria-hidden="true" />
                    ) : (
                      <RefreshCw size={16} aria-hidden="true" />
                    )}
                    Reprocess
                  </button>
                  <button
                    className="secondary-button compact"
                    type="button"
                    onClick={() =>
                      void postDocumentAction(
                        selectedDocument.id,
                        selectedDocument.is_active ? 'deactivate' : 'activate'
                      )
                    }
                    disabled={selectedIsBusy}
                  >
                    {selectedDocument.is_active ? (
                      <PowerOff size={16} aria-hidden="true" />
                    ) : (
                      <Power size={16} aria-hidden="true" />
                    )}
                    {selectedDocument.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </div>

                {selectedReadiness && (
                  <div className={`document-readiness ${selectedReadiness.tone}`} role="status">
                    <strong>{selectedReadiness.label}</strong>
                    <span>{selectedReadiness.message}</span>
                  </div>
                )}

                <dl className="detail-grid">
                  <div>
                    <dt>Status</dt>
                    <dd>
                      <span className={`status-badge ${selectedDocument.status}`}>
                        <SelectedStatusIcon
                          className={selectedDocument.status === 'processing' ? 'spin' : undefined}
                          size={14}
                          aria-hidden="true"
                        />
                        {statusLabels[selectedDocument.status]}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt>Version</dt>
                    <dd>{selectedDocument.version}</dd>
                  </div>
                  <div>
                    <dt>Type</dt>
                    <dd>{humanize(selectedDocument.document_type)}</dd>
                  </div>
                  <div>
                    <dt>Area</dt>
                    <dd>{humanize(selectedDocument.product_area)}</dd>
                  </div>
                  <div>
                    <dt>Active</dt>
                    <dd>{selectedDocument.is_active ? 'Yes' : 'No'}</dd>
                  </div>
                  <div>
                    <dt>Chunks</dt>
                    <dd>{selectedDocument.chunk_count}</dd>
                  </div>
                  <div>
                    <dt>Content type</dt>
                    <dd>{selectedDocument.content_type}</dd>
                  </div>
                  <div>
                    <dt>Size</dt>
                    <dd>{formatBytes(selectedDocument.size_bytes)}</dd>
                  </div>
                  <div>
                    <dt>Source file</dt>
                    <dd>{selectedDocument.source_file_name}</dd>
                  </div>
                  <div>
                    <dt>Storage key</dt>
                    <dd className="mono-value">{selectedDocument.storage_key ?? '-'}</dd>
                  </div>
                  <div>
                    <dt>Created</dt>
                    <dd>{formatDate(selectedDocument.created_at)}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatDate(selectedDocument.updated_at)}</dd>
                  </div>
                  <div>
                    <dt>Last processed</dt>
                    <dd>{formatDate(selectedDocument.last_processed_at)}</dd>
                  </div>
                  {selectedDocument.failure_reason && (
                    <div>
                      <dt>Failure reason</dt>
                      <dd>{selectedDocument.failure_reason}</dd>
                    </div>
                  )}
                </dl>

                <section className="detail-section" aria-labelledby="tags-title">
                  <h3 id="tags-title">Tags</h3>
                  <div className="tag-list">
                    {selectedDocument.tags.length > 0 ? (
                      selectedDocument.tags.map((tag) => <span key={tag}>{tag}</span>)
                    ) : (
                      <span>No tags</span>
                    )}
                  </div>
                </section>

                <section className="detail-section" aria-labelledby="embedding-title">
                  <div className="section-title-row">
                    <div>
                      <h3 id="embedding-title">Embedding</h3>
                      <p>
                        {isLoadingChunks
                          ? 'Loading chunk metadata.'
                          : `${selectedEmbeddingSummary.embeddedCount} of ${selectedDocumentChunks.length} chunks have vectors.`}
                      </p>
                    </div>
                    <span className="icon-frame" aria-hidden="true">
                      <Cpu size={18} />
                    </span>
                  </div>

                  <dl className="embedding-grid">
                    <div>
                      <dt>Provider</dt>
                      <dd>{selectedEmbeddingSummary.provider ?? '-'}</dd>
                    </div>
                    <div>
                      <dt>Model</dt>
                      <dd>{selectedEmbeddingSummary.model ?? '-'}</dd>
                    </div>
                  </dl>
                </section>

                <section className="detail-section" aria-labelledby="versions-title">
                  <div className="section-title-row">
                    <div>
                      <h3 id="versions-title">Versions</h3>
                      <p>
                        Version history will be available when document versioning is implemented.
                      </p>
                    </div>
                    <button className="secondary-button compact" type="button" disabled>
                      <History size={16} aria-hidden="true" />
                      View versions
                    </button>
                  </div>
                  <div className="version-row">
                    <span>{selectedDocument.version}</span>
                    <strong>Current</strong>
                  </div>
                </section>
              </>
            ) : (
              <div className="detail-empty">
                <FileText size={24} aria-hidden="true" />
                <h2 id="detail-title">Document detail</h2>
                <p>Select a document to inspect metadata, processing state, and version context.</p>
              </div>
            )}
          </aside>
        </section>
      </section>
    </main>
  );
}
