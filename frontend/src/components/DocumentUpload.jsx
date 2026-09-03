import React, { useRef, useState } from 'react';
import { FileText, Upload, CheckCircle2, AlertTriangle, X, Clock } from 'lucide-react';
import { api } from '../services/api';
import StatusBadge from './StatusBadge';

/**
 * DocumentUpload Component
 * Staged bank statement candidate ingestion workflow.
 *
 * CRITICAL BOUNDARY:
 * Explicitly separates "document processed (staged)" from "transactions committed".
 * Never marks candidates as committed to the authoritative ledger until the user confirms.
 */
export default function DocumentUpload({ onAnnounce, onRefresh }) {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  const handleFileChange = async (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    setFile(selected);
    setIsUploading(true);
    if (onAnnounce) onAnnounce(`Extracting transaction candidates from ${selected.name}...`);

    try {
      // Extracted statement candidates matching the current ingestion schema
      const mockExtractedCandidates = [
        {
          amount: 450.5,
          transaction_type: 'expense',
          category: 'Bills',
          merchant_name: 'Electric Company',
          description: 'Monthly Power Bill',
          transaction_date: '2026-08-20T10:00:00Z',
          reference_id: 'STMT-1001',
        },
        {
          amount: 15000.0,
          transaction_type: 'income',
          category: 'Other',
          merchant_name: 'Tech Corp',
          description: 'Salary Bonus',
          transaction_date: '2026-08-01T08:00:00Z',
          reference_id: 'STMT-1002',
        },
      ];

      const res = await api.uploadStatement(selected.name, mockExtractedCandidates);
      setUploadResult(res);
      setIsUploading(false);

      if (onAnnounce) {
        onAnnounce(
          `Document processed. ${res.total_candidates} candidates extracted: ${res.valid_candidates_count} valid and ${res.duplicate_candidates_count} duplicates identified.`
        );
      }
    } catch (err) {
      setIsUploading(false);
      if (onAnnounce) onAnnounce(`Failed to process statement: ${err.message}`);
    }
  };

  const handleConfirmImport = async () => {
    if (!uploadResult || uploadResult.valid_candidates_count === 0) return;

    setIsUploading(true);
    if (onAnnounce) onAnnounce('Committing validated candidates to your official bank ledger...');

    try {
      const res = await api.confirmStatement(uploadResult.candidates, null, uploadResult.document_id);
      if (onAnnounce) {
        onAnnounce(`Success. ${res.confirmed_count} transactions were permanently recorded to your account.`);
      }
      if (typeof onRefresh === 'function') {
        await onRefresh();
      }

      setFile(null);
      setUploadResult(null);
    } catch (err) {
      if (onAnnounce) onAnnounce(`Failed to commit transactions: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setUploadResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <section className="card" aria-labelledby="doc-upload-heading">
      {/* 1. Header */}
      <div className="flex-between" style={{ marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--fs-radius-sm, 8px)',
              backgroundColor: 'var(--fs-accent-surface, rgba(141, 219, 146, 0.12))',
              color: 'var(--fs-accent, #8DDB92)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <FileText size={20} aria-hidden="true" />
          </div>
          <div>
            <h2 id="doc-upload-heading" className="text-card-heading" style={{ color: 'var(--fs-text, #F5F4EC)', margin: 0 }}>
              Bank Statement Ingestion
            </h2>
            <p className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Staged Document Extraction
            </p>
          </div>
        </div>

        {uploadResult && (
          <StatusBadge variant="warning" icon={<Clock size={12} />}>
            Staged · Not Yet Committed
          </StatusBadge>
        )}
      </div>

      {/* 2. Upload Dropzone / Trigger */}
      {!file ? (
        <div
          className="flex-col flex-center gap-3"
          style={{
            textAlign: 'center',
            padding: '2.5rem 1.5rem',
            border: '2px dashed var(--fs-border-hover, #2B5748)',
            borderRadius: 'var(--fs-radius-md, 14px)',
            backgroundColor: 'var(--fs-bg, #071510)',
            cursor: 'pointer',
          }}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
          }}
          tabIndex={0}
          role="button"
          aria-label="Upload bank statement file. Supported formats: PDF, JPG, or PNG."
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: 'var(--fs-surface-elevated, #132D24)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--fs-accent, #8DDB92)',
            }}
          >
            <Upload size={24} aria-hidden="true" />
          </div>

          <div>
            <p className="text-body" style={{ fontWeight: 600, color: 'var(--fs-text, #F5F4EC)', marginBottom: '0.25rem' }}>
              Upload bank statement for extraction
            </p>
            <p className="text-secondary" style={{ fontSize: '0.875rem', margin: 0 }}>
              PDF, JPG, or PNG files supported
            </p>
          </div>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.jpg,.jpeg,.png"
            style={{ display: 'none' }}
            aria-hidden="true"
          />
        </div>
      ) : isUploading ? (
        /* 3. Processing State */
        <div
          className="flex-col flex-center gap-3"
          style={{
            padding: '2.5rem 1.5rem',
            textAlign: 'center',
            backgroundColor: 'var(--fs-bg, #071510)',
            borderRadius: 'var(--fs-radius-md, 14px)',
          }}
          role="status"
          aria-live="polite"
        >
          <div className="skeleton" style={{ width: '48px', height: '48px', borderRadius: '50%' }} />
          <p className="text-body" style={{ fontWeight: 600, color: 'var(--fs-text, #F5F4EC)' }}>
            Analyzing and deduplicating statement...
          </p>
          <p className="text-secondary" style={{ fontSize: '0.875rem' }}>
            Reading {file.name}
          </p>
        </div>
      ) : (
        /* 4. Candidate Review & Explicit Confirmation View */
        <div className="flex-col gap-4">
          {/* Staging Notice Banner */}
          <div
            style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--fs-radius-sm, 8px)',
              backgroundColor: 'var(--fs-warning-surface, rgba(230, 184, 92, 0.12))',
              border: '1px solid var(--fs-warning-border, rgba(230, 184, 92, 0.35))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={18} color="var(--fs-warning, #E6B85C)" aria-hidden="true" />
              <span className="text-body" style={{ fontSize: '0.9rem', color: 'var(--fs-warning-bright, #F5CF80)' }}>
                <strong>Staged Candidates Only:</strong> Transactions will not appear in your balance until you click Confirm.
              </span>
            </div>

            <button
              type="button"
              onClick={handleReset}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--fs-text-muted, #71817A)',
                cursor: 'pointer',
                padding: '4px',
              }}
              aria-label="Discard staged statement"
            >
              <X size={18} aria-hidden="true" />
            </button>
          </div>

          {/* Extraction Summary Stats */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '0.75rem',
              textAlign: 'center',
            }}
          >
            <div className="card-elevated" style={{ padding: '0.75rem' }}>
              <span className="text-meta" style={{ textTransform: 'uppercase' }}>Total Found</span>
              <p className="text-section-heading tabular-nums" style={{ color: 'var(--fs-text, #F5F4EC)' }}>
                {uploadResult.total_candidates}
              </p>
            </div>

            <div className="card-elevated" style={{ padding: '0.75rem' }}>
              <span className="text-meta" style={{ textTransform: 'uppercase' }}>Ready to Add</span>
              <p className="text-section-heading tabular-nums" style={{ color: 'var(--fs-accent, #8DDB92)' }}>
                {uploadResult.valid_candidates_count}
              </p>
            </div>

            <div className="card-elevated" style={{ padding: '0.75rem' }}>
              <span className="text-meta" style={{ textTransform: 'uppercase' }}>Duplicates Skipped</span>
              <p className="text-section-heading tabular-nums" style={{ color: 'var(--fs-warning, #E6B85C)' }}>
                {uploadResult.duplicate_candidates_count}
              </p>
            </div>
          </div>

          {/* Staged Candidates List */}
          <div
            style={{
              backgroundColor: 'var(--fs-bg, #071510)',
              borderRadius: 'var(--fs-radius-md, 14px)',
              border: '1px solid var(--fs-border, #1B382E)',
              padding: '1rem',
            }}
          >
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }} className="flex-col gap-2">
              {uploadResult.candidates.map((cand, idx) => {
                const isDup = cand.is_duplicate;
                const isCredit = cand.transaction_type === 'income';

                return (
                  <li
                    key={cand.candidate_id || idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.75rem',
                      borderRadius: 'var(--fs-radius-sm, 8px)',
                      backgroundColor: 'var(--fs-surface-elevated, #132D24)',
                      opacity: isDup ? 0.6 : 1,
                      border: isDup ? '1px dashed var(--fs-border, #1B382E)' : '1px solid transparent',
                    }}
                  >
                    <div>
                      <p className="text-body" style={{ fontWeight: 600, fontSize: '0.95rem', margin: 0 }}>
                        {cand.merchant_name || cand.description}
                      </p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.2rem' }}>
                        <span className="text-secondary" style={{ fontSize: '0.8rem' }}>
                          {cand.category}
                        </span>
                        {isDup && (
                          <StatusBadge variant="warning" showDot={false}>
                            Duplicate
                          </StatusBadge>
                        )}
                      </div>
                    </div>

                    <div className="tabular-nums" style={{ fontWeight: 700, color: isCredit ? 'var(--fs-accent, #8DDB92)' : 'var(--fs-text, #F5F4EC)' }}>
                      {isCredit ? '+' : '−'}₹{Number(cand.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Actions */}
          <div className="flex-row gap-3">
            <button
              type="button"
              className="btn"
              onClick={handleConfirmImport}
              disabled={isUploading || uploadResult.valid_candidates_count === 0}
              style={{ flex: 1 }}
              aria-label={`Confirm and record ${uploadResult.valid_candidates_count} valid transactions to account`}
            >
              <CheckCircle2 size={18} aria-hidden="true" />
              <span>Confirm & Commit to Ledger</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleReset}
              disabled={isUploading}
            >
              Discard
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
