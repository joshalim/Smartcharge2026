import React, { useState, useRef } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Upload, CheckCircle2, AlertTriangle, X, FileSpreadsheet } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Import() {
  const { t } = useTranslation();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API}/transactions/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResult(response.data);
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to upload file';
      setResult({
        success: false,
        imported_count: 0,
        skipped_count: 0,
        errors: [{ row: 0, field: 'File', message: errorMessage }],
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <div>
        <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid="import-title">
          {t('import.title')}
        </h1>
        <p className="text-slate-500 dark:text-slate-400">{t('import.subtitle')}</p>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-8">
        <div
          className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
            dragActive
              ? 'border-orange-500 bg-orange-50 dark:bg-orange-950/20'
              : 'border-slate-300 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-600'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          data-testid="upload-dropzone"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileChange}
            className="hidden"
            id="file-upload"
            data-testid="file-input"
          />
          
          <div className="flex flex-col items-center gap-4">
            <div className="p-4 bg-orange-50 dark:bg-orange-950/30 rounded-full">
              <FileSpreadsheet className="w-12 h-12 text-orange-600 dark:text-orange-400" />
            </div>
            
            {file ? (
              <div className="flex items-center gap-3 px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg">
                <FileSpreadsheet className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                <span className="font-medium text-slate-900 dark:text-slate-100">{file.name}</span>
                <button
                  onClick={() => setFile(null)}
                  className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                  data-testid="remove-file-btn"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <>
                <div>
                  <p className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    {t('import.dragDrop')}
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{t('import.or')}</p>
                </div>
                <label
                  htmlFor="file-upload"
                  className="px-6 py-3 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-md cursor-pointer transition-colors"
                  data-testid="select-file-btn"
                >
                  {t('import.selectFile')}
                </label>
              </>
            )}
          </div>
        </div>

        {file && (
          <div className="mt-6 flex justify-center">
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="px-8 py-3 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              data-testid="upload-btn"
            >
              {uploading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  {t('import.uploading')}
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  {t('import.upload')}
                </>
              )}
            </button>
          </div>
        )}
      </div>

      <div className="bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
        <h3 className="text-lg font-bold mb-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
          {t('import.requiredFormat')}
        </h3>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          {t('import.requiredColumns')}
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {['TxID', 'Station', 'Connector', 'Account', 'Start Time', 'End Time', 'Meter value(kW.h)'].map((col) => (
            <div key={col} className="px-3 py-2 bg-white dark:bg-slate-800 rounded-md border border-slate-200 dark:border-slate-700">
              <code className="text-sm font-medium text-orange-600 dark:text-orange-400">{col}</code>
            </div>
          ))}
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-4">
          <strong>{t('import.note')}</strong> {t('import.noteText')}
        </p>
      </div>

      {result && (
        <div
          className={`rounded-xl border p-6 ${
            result.success
              ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800'
              : 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800'
          }`}
          data-testid="import-result"
        >
          <div className="flex items-start gap-3 mb-4">
            {result.success ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-amber-600 dark:text-amber-400 flex-shrink-0" />
            )}
            <div>
              <h3 className="text-lg font-bold mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                {result.success ? t('import.success') : t('import.withIssues')}
              </h3>
              <div className="space-y-1 text-sm">
                <p className="text-slate-700 dark:text-slate-300">
                  <strong>{result.imported_count}</strong> {t('import.imported')}
                </p>
                {result.skipped_count > 0 && (
                  <p className="text-slate-700 dark:text-slate-300">
                    <strong>{result.skipped_count}</strong> {t('import.skipped')}
                  </p>
                )}
                {result.errors && result.errors.length > 0 && (
                  <p className="text-slate-700 dark:text-slate-300">
                    <strong>{result.errors.length}</strong> {t('import.errors')}
                  </p>
                )}
              </div>
            </div>
          </div>

          {result.errors && result.errors.length > 0 && (
            <div className="mt-4 pt-4 border-t border-amber-200 dark:border-amber-800">
              <h4 className="font-semibold mb-2 text-sm">{t('import.validationErrors')}</h4>
              <div className="space-y-2 max-h-60 overflow-y-auto" data-testid="validation-errors">
                {result.errors.map((error, idx) => (
                  <div key={idx} className="text-sm p-3 bg-white dark:bg-slate-900 rounded-md border border-amber-200 dark:border-amber-800">
                    {error.row > 0 && <span className="font-semibold">Row {error.row}:</span>}{' '}
                    <span className="text-amber-700 dark:text-amber-300">
                      {error.field} - {error.message}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Import;