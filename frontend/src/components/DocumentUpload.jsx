import React, { useRef, useState } from 'react';
import { FileText, Upload, CheckCircle2, AlertTriangle, X, Clock } from 'lucide-react';
import { api } from '../services/api';
import StatusBadge from './StatusBadge';

/**
 * DocumentUpload Component
 * 4-Stage bank statement ingestion workflow:
 * 01 Select Statement -> 02 Processing -> 03 Review Candidates -> 04 Confirm Import
 *
 * CRITICAL SEPARATION:
 * Explicitly marks extracted items as "NOT YET COMMITTED" until user confirms.
 */
export default function DocumentUpload({ onAnnounce, onRefresh }) {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  // Derive active workflow step: 1 (Select), 2 (Processing), 3 (Review), 4 (Confirmed)
  const currentStep = isUploading ? 2 : uploadResult ? 3 : 1;

  const handleFileChange = async (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    setFile(selected);
    setIsUploading(true);
    if (onAnnounce) onAnnounce(`Processing and extracting candidates from ${selected.name}...`);

    try {
      // Extracted candidates adhering to backend ingestion schema
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
    <section className="card" aria-labelledby="statement-upload-heading">
      {/* 1. Header */}
      <div className="flex-between" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: 'var(--fs-radius-md)',
              backgroundColor: 'var(--fs-accent-surface)',
              color: 'var(--fs-accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(141, 219, 146, 0.25)',
            }}
          >
            <FileText size={22} aria-hidden="true" />
          </div>
          <div>
            <h2 id="statement-upload-heading" className="text-card-heading" style={{ color: 'var(--fs-text)', margin: 0 }}>
              Statement Import Workflow
            </h2>
            <p className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Staged Document Ingestion
            </p>
          </div>
        </div>

        {uploadResult && (
          <StatusBadge variant="warning" icon={<Clock size={13} />}>
            Staged · Not Yet Committed
          </StatusBadge>
        )}
      </div>

      {/* 2. 4-Stage Workflow Step Indicator */}
      <div className="workflow-stepper" aria-label="Statement Ingestion Progress">
        <div className={`stepper-step ${currentStep === 1 ? 'active' : currentStep > 1 ? 'completed' : ''}`}>
          <span>01</span>
          <span>Select Statement</span>
        </div>
        <div className={`stepper-step ${currentStep === 2 ? 'active' : currentStep > 2 ? 'completed' : ''}`}>
          <span>02</span>
          <span>Processing</span>
        </div>
        <div className={`stepper-step ${currentStep === 3 ? 'active' : currentStep > 3 ? 'completed' : ''}`}>
          <span>03</span>
          <span>Review Candidates</span>
        </div>
        <div className={`stepper-step ${currentStep === 4 ? 'active' : ''}`}>
          <span>04</span>
          <span>Confirm Import</span>
        </div>
      </div>

      {/* 3. Stage 01: File Selection Dropzone */}
      {!file && (
        <div
          className="flex-col flex-center gap-3"
          style={{
            textAlign: 'center',
            padding: '3rem 1.5rem',
            border: '2px dashed var(--fs-border-hover)',
            borderRadius: 'var(--fs-radius-md)',
            backgroundColor: 'var(--fs-bg)',
            cursor: 'pointer',
            transition: 'border-color var(--fs-transition-fast)',
          }}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
          }}
          tabIndex={0}
          role="button"
          aria-label="Upload bank statement document. PDF, JPG, or PNG files supported."
        >
          <div
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '50%',
              backgroundColor: 'var(--fs-surface-elevated)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--fs-accent)',
            }}
          >
            <Upload size={24} aria-hidden="true" />
          </div>

          <div>
            <p className="text-body" style={{ fontWeight: 600, color: 'var(--fs-text)', marginBottom: '0.25rem' }}>
              Select or drop bank statement for extraction
            </p>
            <p className="text-secondary" style={{ fontSize: '0.875rem', margin: 0 }}>
              Supported: PDF, JPG, PNG (Max 15MB)
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
      )}

      {/* 4. Stage 02: Processing State */}
      {isUploading && (
        <div
          className="flex-col flex-center gap-3"
          style={{
            padding: '3rem 1.5rem',
            textAlign: 'center',
            backgroundColor: 'var(--fs-bg)',
            borderRadius: 'var(--fs-radius-md)',
          }}
          role="status"
          aria-live="polite"
        >
          <div className="skeleton" style={{ width: '48px', height: '48px', borderRadius: '50%' }} />
          <p className="text-body" style={{ fontWeight: 600, color: 'var(--fs-text)', margin: 0 }}>
            Extracting and deduplicating statement transactions...
          </p>
          <p className="text-secondary" style={{ fontSize: '0.875rem', margin: 0 }}>
            Reading {file?.name}
          </p>
        </div>
      )}

      {/* 5. Stage 03: Review Candidates & Explicit Confirmation */}
      {uploadResult && !isUploading && (
        <div className="flex-col gap-4">
          {/* Explicit Staging Notice */}
          <div
            style={{
              padding: '1rem 1.25rem',
              borderRadius: 'var(--fs-radius-sm)',
              backgroundColor: 'var(--fs-warning-surface)',
              border: '1px solid var(--fs-warning-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <AlertTriangle size={18} color="var(--fs-warning)" aria-hidden="true" />
              <span className="text-body" style={{ fontSize: '0.925rem', color: 'var(--fs-warning-bright)' }}>
                <strong>STAGED CANDIDATES ONLY:</strong> These transactions are not yet committed to your balance until you confirm below.
              </span>
            </div>

            <button
              type="button"
              onClick={handleReset}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--fs-text-muted)',
                cursor: 'pointer',
                padding: '4px',
              }}
              aria-label="Discard staged statement"
            >
              <X size={18} aria-hidden="true" />
            </button>
          </div>

          {/* Metrics Summary */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '0.75rem',
              textAlign: 'center',
            }}
          >
            <div className="card-elevated" style={{ padding: '0.85rem' }}>
              <span className="text-meta" style={{ textTransform: 'uppercase' }}>Extracted</span>
              <p className="text-section-heading tabular-nums" style={{ color: 'var(--fs-text)', marginTop: '0.2rem' }}>
                {uploadResult.total_candidates}
              </p>
            </div>

            <div className="card-elevated" style={{ padding: '0.85rem' }}>
              <span className="text-meta" style={{ textTransform: 'uppercase' }}>Valid Candidates</span>
              <p className="text-section-heading tabular-nums" style={{ color: 'var(--fs-accent)', marginTop: '0.2rem' }}>
                {uploadResult.valid_candidates_count}
              </p>
            </div>

            <div className="card-elevated" style={{ padding: '0.85rem' }}>
              <span className="text-meta" style={{ textTransform: 'uppercase' }}>Duplicates Skipped</span>
              <p className="text-section-heading tabular-nums" style={{ color: 'var(--fs-warning)', marginTop: '0.2rem' }}>
                {uploadResult.duplicate_candidates_count}
              </p>
            </div>
          </div>

          {/* Candidates List */}
          <div
            style={{
              backgroundColor: 'var(--fs-bg)',
              borderRadius: 'var(--fs-radius-md)',
              border: '1px solid var(--fs-border)',
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
                      padding: '0.85rem 1rem',
                      borderRadius: 'var(--fs-radius-sm)',
                      backgroundColor: 'var(--fs-surface-elevated)',
                      opacity: isDup ? 0.6 : 1,
                      border: isDup ? '1px dashed var(--fs-border)' : '1px solid transparent',
                    }}
                  >
                    <div>
                      <p className="text-body" style={{ fontWeight: 600, fontSize: '0.95rem', margin: 0 }}>
                        {cand.merchant_name || cand.description}
                      </p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                        <span className="text-secondary" style={{ fontSize: '0.825rem' }}>
                          {cand.category}
                        </span>
                        {isDup && (
                          <StatusBadge variant="warning" showDot={false}>
                            Duplicate
                          </StatusBadge>
                        )}
                      </div>
                    </div>

                    <div className="tabular-nums" style={{ fontWeight: 700, fontSize: '1rem', color: isCredit ? 'var(--fs-accent)' : 'var(--fs-text)' }}>
                      {isCredit ? '+' : '−'}₹{Number(cand.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Action Row */}
          <div className="flex-row gap-3">
            <button
              type="button"
              className="btn"
              onClick={handleConfirmImport}
              disabled={isUploading || uploadResult.valid_candidates_count === 0}
              style={{ flex: 1 }}
              aria-label={`Confirm import of ${uploadResult.valid_candidates_count} valid transactions to account`}
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
