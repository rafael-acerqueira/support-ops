'use client';

import {
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Loader2,
  Power,
  PowerOff,
  RefreshCw,
  Upload,
} from 'lucide-react';
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';

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

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [documentType, setDocumentType] = useState<DocumentType>('internal_policy');
  const [productArea, setProductArea] = useState<ProductArea>('support');
  const [tags, setTags] = useState('enterprise, sla');
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [busyDocumentId, setBusyDocumentId] = useState<string | null>(null);
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

  async function loadDocuments() {
    setError(null);

    try {
      const response = await fetch('/api/documents', { cache: 'no-store' });
      if (!response.ok) throw new Error('Unable to load documents.');
      setDocuments(await response.json());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unexpected error while loading.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
  }, []);

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

      setFile(null);
      setMessage('Document uploaded.');
      await loadDocuments();
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

      setMessage(action === 'process' ? 'Processing queued.' : 'Document updated.');
      await loadDocuments();
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

          <button
            className="icon-button"
            type="button"
            onClick={loadDocuments}
            title="Refresh list"
          >
            <RefreshCw size={18} aria-hidden="true" />
          </button>
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
                      <tr key={document.id}>
                        <td>
                          <div className="document-name">
                            <FileText size={18} aria-hidden="true" />
                            <div>
                              <strong>{document.name}</strong>
                              <span>{formatBytes(document.size_bytes)}</span>
                            </div>
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
                              onClick={() => postDocumentAction(document.id, 'process')}
                              disabled={isBusy}
                              title="Reprocess"
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
                              onClick={() =>
                                postDocumentAction(
                                  document.id,
                                  document.is_active ? 'deactivate' : 'activate'
                                )
                              }
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
