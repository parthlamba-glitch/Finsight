import React, { useRef, useState } from 'react';
import { FileText, Upload, CheckCircle } from 'lucide-react';
import { api } from '../services/api';

export default function DocumentUpload({ onAnnounce, onRefresh }) {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  const handleFileChange = async (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setIsUploading(true);
      if (onAnnounce) onAnnounce(`Reading and extracting data from ${selected.name}...`);

      try {
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
            category: 'Income',
            merchant_name: 'Tech Corp',
            description: 'Salary',
            transaction_date: '2026-08-01T08:00:00Z',
            reference_id: 'STMT-1002',
          },
        ];

        const res = await api.uploadStatement(selected.name, mockExtractedCandidates);
        setUploadResult(res);
        setIsUploading(false);
        if (onAnnounce) {
          onAnnounce(
            `Document processed. Found ${res.total_candidates} transactions. ${res.duplicate_candidates_count} were skipped as duplicates.`
          );
        }
      } catch (err) {
        setIsUploading(false);
        if (onAnnounce) onAnnounce(`Failed to process document: ${err.message}`);
      }
    }
  };

  const handleConfirmImport = async () => {
    if (!uploadResult || uploadResult.valid_candidates_count === 0) return;

    setIsUploading(true);
    if (onAnnounce) onAnnounce('Confirming import...');
    try {
      const res = await api.confirmStatement(uploadResult.candidates, null, uploadResult.document_id);
      if (onAnnounce) onAnnounce(`Success! ${res.confirmed_count} transactions were saved to your account.`);
      if (typeof onRefresh === 'function') await onRefresh();

      setFile(null);
      setUploadResult(null);
    } catch (err) {
      if (onAnnounce) onAnnounce(`Failed to confirm import: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section className="card" aria-labelledby="doc-heading">
      <h2 id="doc-heading" className="flex-center gap-2" style={{ justifyContent: 'flex-start' }}>
        <FileText size={24} color="var(--color-primary)" />
        Upload Bank Statement
      </h2>

      {!file ? (
        <div
          className="flex-col gap-4"
          style={{
            alignItems: 'center',
            textAlign: 'center',
            padding: '2rem 1rem',
            border: '2px dashed var(--color-border)',
            borderRadius: '8px',
          }}
        >
          <Upload size={32} color="var(--color-text-muted)" aria-hidden="true" />

          <div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>Upload statement</h3>
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>PDF, JPG, or PNG</p>
          </div>

          <input
            type="file"
            id="file-upload"
            className="sr-only"
            accept=".pdf,.jpg,.jpeg,.png"
            ref={fileInputRef}
            onChange={handleFileChange}
          />

          <label htmlFor="file-upload" className="btn btn-secondary" style={{ cursor: 'pointer' }}>
            Choose file
          </label>
        </div>
      ) : (
        <div className="flex-col gap-4">
          <div
            className="flex-center gap-2"
            style={{
              justifyContent: 'flex-start',
              padding: '1rem',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              borderRadius: '8px',
              border: '1px solid rgba(16, 185, 129, 0.2)',
            }}
          >
            <CheckCircle size={20} color="var(--color-success)" aria-hidden="true" />
            <span style={{ fontWeight: 500, wordBreak: 'break-all' }}>{file.name}</span>
          </div>

          {isUploading ? (
            <p className="text-secondary" aria-live="polite">
              Processing...
            </p>
          ) : uploadResult ? (
            <div style={{ backgroundColor: 'var(--color-bg)', padding: '1rem', borderRadius: '8px' }}>
              <p className="text-body" style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
                Extraction Results:
              </p>
              <ul
                style={{
                  listStyle: 'none',
                  padding: 0,
                  margin: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                }}
              >
                <li className="text-secondary">• Found {uploadResult.total_candidates} transactions</li>
                <li className="text-secondary">• {uploadResult.valid_candidates_count} ready to import</li>
                {uploadResult.duplicate_candidates_count > 0 && (
                  <li className="text-secondary" style={{ color: 'var(--color-warning)' }}>
                    • Skipped {uploadResult.duplicate_candidates_count} duplicate(s)
                  </li>
                )}
              </ul>
            </div>
          ) : null}

          {uploadResult && uploadResult.valid_candidates_count > 0 && !isUploading && (
            <button type="button" className="btn" onClick={handleConfirmImport}>
              Confirm Import
            </button>
          )}

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setFile(null);
              setUploadResult(null);
            }}
            disabled={isUploading}
          >
            Cancel
          </button>
        </div>
      )}
    </section>
  );
}
