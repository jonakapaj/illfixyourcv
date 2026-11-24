import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, FileText, Download, Check, X, Copy, RotateCcw, Loader2, AlertCircle,
  Sun, Moon, Sparkles, Target, ShieldCheck, ClipboardList, PenLine, ChevronDown, FileCheck2,
} from 'lucide-react';
import axios from 'axios';

// Use relative API paths by default so the same frontend works behind Vite or the backend server.
const API_BASE = import.meta.env.VITE_API_BASE || "";

const THEME_IDS = ['light', 'dark'];

const STEPS = [
  { key: 'extracting',  label: 'Reading your CV' },
  { key: 'scoring',     label: 'Scoring against the job' },
  { key: 'auditing',    label: 'Finding the gaps' },
  { key: 'rewriting',   label: 'Rewriting your CV' },
  { key: 'structuring', label: 'Preparing the PDF' },
];

const TEMPLATES = [
  { id: 'corporate', label: 'Executive', desc: 'Classic single column for leadership and enterprise roles.' },
  { id: 'tech',      label: 'Modern',    desc: 'Two columns with a skills sidebar. Great for tech.' },
  { id: 'minimal',   label: 'Minimal',   desc: 'Clean and type-led for design and product roles.' },
];

const scoreBand = (v) =>
  v >= 85 ? { label: 'Excellent match', color: 'var(--good)' }
  : v >= 70 ? { label: 'Good match', color: 'var(--good)' }
  : v >= 50 ? { label: 'Fair match', color: 'var(--warn)' }
  : { label: 'Needs work', color: 'var(--danger)' };

// ── Pieces ───────────────────────────────────────────────────────────────────

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-9 h-9 rounded-xl flex items-center justify-center text-white shadow-md" style={{ background: 'var(--grad)' }}>
        <FileCheck2 size={18} strokeWidth={2.4} />
      </div>
      <div className="leading-tight">
        <div className="font-extrabold text-[17px] tracking-tight">Sentinel</div>
        <div className="text-[11px] muted font-medium">AI CV optimizer</div>
      </div>
    </div>
  );
}

function TemplateSketch({ id }) {
  const line = (w, strong) => (
    <div style={{ width: w, height: strong ? 5 : 4, background: strong ? 'var(--ink-2)' : 'var(--rule-strong)', borderRadius: 3, opacity: strong ? 0.7 : 1 }} />
  );
  if (id === 'tech') {
    return (
      <div className="flex gap-2.5 h-full">
        <div className="w-1/3 rounded-md p-2 space-y-1.5" style={{ background: 'var(--accent-soft)' }}>
          {line('80%', true)}{line('60%')}{line('70%')}{line('50%')}
        </div>
        <div className="flex-1 space-y-1.5 pt-2">{line('70%', true)}{line('95%')}{line('90%')}{line('60%', true)}{line('85%')}</div>
      </div>
    );
  }
  if (id === 'minimal') {
    return (
      <div className="space-y-2 pt-1">
        <div style={{ width: '50%', height: 8, background: 'var(--ink)', borderRadius: 3, opacity: 0.8 }} />
        {line('100%')}{line('88%')}<div className="pt-1" />{line('40%', true)}{line('95%')}
      </div>
    );
  }
  return (
    <div className="space-y-1.5 pt-1">
      <div className="flex justify-center">{line('45%', true)}</div>
      <div className="flex justify-center">{line('65%')}</div>
      <div className="hairline my-2" />
      {line('35%', true)}{line('95%')}{line('88%')}{line('35%', true)}
    </div>
  );
}

function EmptyState() {
  const features = [
    { icon: Target, title: 'Match score', text: 'See how your CV scores on the six things this job cares about most.' },
    { icon: ClipboardList, title: 'Gap audit', text: 'Get the three critical gaps and a step-by-step plan to close them.' },
    { icon: PenLine, title: 'Honest rewrite', text: 'A tailored rewrite that only uses experience you actually have.' },
  ];
  return (
    <div className="py-6">
      <span className="pill mb-5"><Sparkles size={13} /> Runs privately on your computer</span>
      <h1 className="text-4xl md:text-5xl xl:text-[56px] font-extrabold tracking-tight leading-[1.05] max-w-3xl">
        Land more interviews with a CV <span className="grad-text">tailored to every job</span>
      </h1>
      <p className="text-lg ink-2 mt-5 max-w-2xl">
        Paste a job description, upload your CV, and get a match score, a gap audit and a rewritten CV ready to export as PDF.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-12">
        {features.map(({ icon: Icon, title, text }) => (
          <div key={title} className="card p-6">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4" style={{ background: 'var(--accent-soft)', color: 'var(--accent-text)' }}>
              <Icon size={20} />
            </div>
            <div className="font-bold mb-1">{title}</div>
            <div className="text-sm muted leading-relaxed">{text}</div>
          </div>
        ))}
      </div>

      <div className="card p-5 mt-5 flex items-center gap-4">
        <ShieldCheck size={22} style={{ color: 'var(--good)' }} className="shrink-0" />
        <p className="text-sm ink-2">
          <span className="font-semibold" style={{ color: 'var(--ink)' }}>No made-up achievements.</span>{' '}
          Skills the job asks for that aren't in your CV are flagged as gaps, never quietly added.
        </p>
      </div>
    </div>
  );
}

function ProgressView({ jobStage, jobStatus, jobProgress, jobId, onCancel }) {
  const pct = Math.max(jobProgress || 0, 0);
  const currentIdx = STEPS.findIndex((s) => s.key === jobStage);
  return (
    <div className="max-w-xl mx-auto py-8">
      <div className="card p-8" style={{ boxShadow: 'var(--shadow-lg)' }}>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl font-extrabold tracking-tight">Optimizing your CV</h2>
          <span className="text-sm font-bold accent">{pct}%</span>
        </div>
        <p className="text-sm muted mb-6">This usually takes a few minutes with a local model.</p>
        <div className="h-2.5 rounded-full overflow-hidden mb-8" style={{ background: 'var(--track)' }}>
          <motion.div className="h-full rounded-full" style={{ background: 'var(--grad)' }} animate={{ width: `${pct}%` }} transition={{ duration: 0.5 }} />
        </div>
        <ol className="space-y-4">
          {STEPS.map((step, i) => {
            const done = i < currentIdx || jobStatus === 'completed';
            const active = i === currentIdx;
            return (
              <li key={step.key} className="flex items-center gap-3 text-sm">
                <span className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                      style={{
                        background: done ? 'var(--grad)' : active ? 'var(--accent-soft)' : 'var(--surface-2)',
                        color: done ? '#fff' : 'var(--accent-text)',
                        border: done || active ? 'none' : '1px solid var(--rule)',
                      }}>
                  {done ? <Check size={14} strokeWidth={3} /> : active ? <Loader2 size={14} className="animate-spin" /> : <span className="text-xs muted">{i + 1}</span>}
                </span>
                <span className={done || active ? 'font-semibold' : 'muted'}>{step.label}</span>
              </li>
            );
          })}
        </ol>
        {jobId && jobStatus !== 'completed' && jobStatus !== 'failed' && (
          <button onClick={onCancel} className="btn btn-secondary mt-8">
            <X size={15} /> {jobStatus === 'canceling' ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
      </div>
    </div>
  );
}

function ScoreRing({ value }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  return (
    <svg width="132" height="132" viewBox="0 0 132 132" role="img" aria-label={`Overall match ${value} out of 100`}>
      <defs>
        <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#5b4cf0" /><stop offset="55%" stopColor="#9b4dfa" /><stop offset="100%" stopColor="#ec4899" />
        </linearGradient>
      </defs>
      <circle cx="66" cy="66" r={r} fill="none" stroke="var(--track)" strokeWidth="12" />
      <motion.circle cx="66" cy="66" r={r} fill="none" stroke="url(#ringGrad)" strokeWidth="12" strokeLinecap="round"
                     strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - value / 100) }}
                     transition={{ duration: 0.9, ease: 'easeOut' }} transform="rotate(-90 66 66)" />
      <text x="66" y="64" textAnchor="middle" fontSize="34" fontWeight="800" fill="var(--ink)">{value}</text>
      <text x="66" y="86" textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--muted)">out of 100</text>
    </svg>
  );
}

function ScoreCard({ scores }) {
  const rows = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  const avg = rows.length ? Math.round(rows.reduce((s, [, v]) => s + v, 0) / rows.length) : 0;
  const band = scoreBand(avg);
  return (
    <section className="card p-7">
      <div className="flex items-center gap-6 mb-7">
        <ScoreRing value={avg} />
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider muted mb-1">Overall match</div>
          <div className="text-2xl font-extrabold tracking-tight" style={{ color: band.color }}>{band.label}</div>
          <p className="text-sm muted mt-1">Based on six requirements from the job description.</p>
        </div>
      </div>
      <div className="space-y-4" role="table" aria-label="Score per requirement">
        {rows.map(([skill, value]) => (
          <div key={skill} role="row" title={`${skill}: ${value}/100`}>
            <div className="flex items-center justify-between mb-1.5 text-sm">
              <span role="cell" className="font-medium flex items-center gap-2">
                {skill}
                {value < 50 && <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded-md" style={{ color: 'var(--danger)', background: 'color-mix(in srgb, var(--danger) 12%, transparent)' }}>Gap</span>}
              </span>
              <span role="cell" className="font-bold tabular-nums">{value}</span>
            </div>
            <div className="bar-track">
              <motion.div className="bar-fill" initial={{ width: 0 }} animate={{ width: `${value}%` }} transition={{ duration: 0.7 }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── App ──────────────────────────────────────────────────────────────────────

const App = () => {
  const [jobDesc, setJobDesc] = useState('');
  const [extraInstructions, setExtraInstructions] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [jobId, setJobId] = useState(null);
  // The job that produced the current results; /structure needs it to re-run on edits.
  const [resultJobId, setResultJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobStage, setJobStage] = useState(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [toasts, setToasts] = useState([]);
  const [editedRewrite, setEditedRewrite] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState('corporate');
  const [activeTab, setActiveTab] = useState('audit');
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    return THEME_IDS.includes(saved) ? saved : 'light';
  });
  const [showCover, setShowCover] = useState(false);
  const [coverForm, setCoverForm] = useState({
    fullName: '', targetCompany: '', targetRole: '', keyAchievement: '', tone: 'Professional', additionalNotes: '',
  });
  const [coverLetter, setCoverLetter] = useState('');
  const [coverLoading, setCoverLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  const pickTheme = (id) => { setTheme(id); localStorage.setItem('theme', id); };

  const addToast = ({ type = 'info', msg = '', timeout = 4500 } = {}) => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    setToasts((s) => [{ id, type, msg }, ...s]);
    setTimeout(() => setToasts((s) => s.filter((x) => x.id !== id)), timeout);
  };
  const removeToast = (id) => setToasts((s) => s.filter((x) => x.id !== id));

  const handleFileUpload = (e) => {
    const uploadedFile = e.target.files[0];
    if (uploadedFile && uploadedFile.type === 'application/pdf') {
      setFile(uploadedFile);
      setError(null);
    } else {
      setError('Please upload a PDF file.');
    }
  };

  const runAnalysis = async () => {
    if (!file || !jobDesc) return;
    setLoading(true);
    setError(null);
    setResults(null);
    setJobId(null);
    setResultJobId(null);
    setJobStatus('queued');
    setJobStage('queued');
    setJobProgress(0);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_description', jobDesc);
    formData.append('user_instructions', extraInstructions);

    try {
      const response = await axios.post(`${API_BASE}/analyze`, formData);
      const body = response.data;
      if (body.status === 'completed' && body.result) {
        // Cached result: no job on the server, so edits can't be re-structured.
        setResults(body.result);
        setEditedRewrite(body.result.rewrite || null);
        setJobStatus('completed');
        setLoading(false);
      } else if (body.job_id) {
        setJobId(body.job_id);
        setJobStatus(body.status || 'queued');
        pollJob(body.job_id);
      } else {
        setResults(body);
        setLoading(false);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't reach the backend. Is it running on port 8000?");
      setLoading(false);
      setJobStatus(null);
    }
  };

  const pollJob = async (id, failures = 0) => {
    try {
      const statusResp = await axios.get(`${API_BASE}/status/${id}`);
      const s = statusResp.data.status;
      setJobStatus(s);
      setJobStage(statusResp.data.stage);
      setJobProgress(statusResp.data.progress ?? 0);
      if (s === 'completed') {
        const res = await axios.get(`${API_BASE}/result/${id}`);
        setResults(res.data);
        setEditedRewrite(res.data.rewrite || null);
        setJobProgress(100);
        setLoading(false);
        setResultJobId(id);
        setJobId(null);
        return;
      }
      if (s === 'failed' || s === 'canceled') {
        if (s === 'failed') setError(statusResp.data.error || 'Analysis failed');
        setLoading(false);
        setJobId(null);
        setJobStatus(null);
        return;
      }
      setTimeout(() => pollJob(id, 0), 750);
    } catch {
      if (failures < 5) {
        setTimeout(() => pollJob(id, failures + 1), Math.min(750 * (failures + 1), 2500));
      } else {
        setError('Lost contact with the backend while checking progress.');
        setLoading(false);
        setJobId(null);
      }
    }
  };

  const cancelJob = async () => {
    if (!jobId) return;
    try {
      await axios.post(`${API_BASE}/cancel/${jobId}`);
      addToast({ type: 'info', msg: 'Cancel requested' });
      setJobStatus('canceling');
    } catch {
      addToast({ type: 'error', msg: 'Cancel failed' });
    }
  };

  const applyEdits = async () => {
    if (!editedRewrite) return;
    if (!resultJobId) {
      addToast({ type: 'error', msg: 'This result came from the cache. Re-run the review to apply edits.' });
      return;
    }
    try {
      const payload = new FormData();
      payload.append('job_id', resultJobId);
      payload.append('rewrite_text', editedRewrite);
      const resp = await axios.post(`${API_BASE}/structure`, payload);
      setResults((prev) => ({ ...prev, cv_data: resp.data.cv_data }));
      addToast({ type: 'success', msg: 'Edits applied. The PDF will use them.' });
    } catch {
      addToast({ type: 'error', msg: 'Failed to re-structure CV.' });
    }
  };

  const downloadPDF = async () => {
    if (!results) return;
    setExporting(true);
    try {
      const response = await axios.post(`${API_BASE}/generate?template_id=${selectedTemplate}`,
        results.cv_data, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `optimised_cv_${selectedTemplate}.pdf`);
      document.body.appendChild(link);
      link.click();
    } catch {
      setError('PDF export failed.');
    } finally {
      setExporting(false);
    }
  };

  const generateCoverLetter = async () => {
    if (!file || !jobDesc) {
      addToast({ type: 'error', msg: 'Upload your CV and paste the job description first.' });
      return;
    }
    if (!coverForm.fullName || !coverForm.targetCompany || !coverForm.targetRole || !coverForm.keyAchievement) {
      addToast({ type: 'error', msg: 'Fill in your name, company, role, and key achievement.' });
      return;
    }
    setCoverLoading(true);
    try {
      const payload = new FormData();
      payload.append('file', file);
      payload.append('job_description', jobDesc);
      payload.append('full_name', coverForm.fullName);
      payload.append('target_company', coverForm.targetCompany);
      payload.append('target_role', coverForm.targetRole);
      payload.append('key_achievement', coverForm.keyAchievement);
      payload.append('tone', coverForm.tone);
      payload.append('additional_notes', coverForm.additionalNotes);
      const response = await axios.post(`${API_BASE}/cover-letter`, payload);
      setCoverLetter(response.data.cover_letter || '');
      addToast({ type: 'success', msg: 'Cover letter ready.' });
    } catch (err) {
      addToast({ type: 'error', msg: err.response?.data?.detail || 'Failed to generate cover letter.' });
    } finally {
      setCoverLoading(false);
    }
  };

  const downloadCoverLetterPDF = async () => {
    if (!coverLetter) return;
    try {
      const payload = new FormData();
      payload.append('cover_letter', coverLetter);
      payload.append('full_name', coverForm.fullName);
      payload.append('email', '');
      payload.append('phone', '');
      payload.append('location', '');
      payload.append('target_company', coverForm.targetCompany);
      payload.append('target_role', coverForm.targetRole);
      const response = await axios.post(`${API_BASE}/cover-letter-pdf`, payload, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `cover_letter_${coverForm.targetCompany || 'output'}.pdf`);
      document.body.appendChild(link);
      link.click();
      addToast({ type: 'success', msg: 'Cover letter PDF downloaded.' });
    } catch {
      addToast({ type: 'error', msg: 'Failed to create cover letter PDF.' });
    }
  };

  const setCover = (k) => (e) => setCoverForm((p) => ({ ...p, [k]: e.target.value }));

  return (
    <div data-theme={theme} className="app min-h-screen">
      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 backdrop-blur-md border-b" style={{ borderColor: 'var(--rule)', background: 'color-mix(in srgb, var(--bg) 78%, transparent)' }}>
        <div className="max-w-[1400px] mx-auto px-5 md:px-8 h-16 flex items-center justify-between">
          <Logo />
          <button type="button" className="btn btn-secondary !px-3" onClick={() => pickTheme(theme === 'light' ? 'dark' : 'light')}
                  aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
          </button>
        </div>
      </header>

      <div className="max-w-[1400px] mx-auto px-5 md:px-8 py-8 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-8 items-start">
        {/* ── Application form ────────────────────────────────────────────── */}
        <aside className="card p-6 lg:sticky lg:top-24 space-y-6">
          <div>
            <h2 className="text-lg font-extrabold tracking-tight">Your application</h2>
            <p className="text-sm muted">Three quick steps.</p>
          </div>

          <section>
            <div className="flex items-center gap-2.5 mb-2"><span className="step-badge">1</span><span className="field-label !mb-0">Job description</span></div>
            <textarea className="field h-36 resize-y" placeholder="Paste the full job posting here…"
                      value={jobDesc} onChange={(e) => setJobDesc(e.target.value)} />
          </section>

          <section>
            <div className="flex items-center gap-2.5 mb-2"><span className="step-badge">2</span><span className="field-label !mb-0">Your CV</span></div>
            <label className="dropzone flex items-center gap-3 px-4 py-4" data-filled={!!file}>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                   style={{ background: file ? 'var(--grad)' : 'var(--surface)', color: file ? '#fff' : 'var(--accent-text)', border: file ? 'none' : '1px solid var(--rule)' }}>
                {file ? <Check size={18} strokeWidth={2.6} /> : <Upload size={18} />}
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold truncate">{file ? file.name : 'Upload your CV'}</div>
                <div className="text-xs muted">{file ? `${Math.round(file.size / 1024)} KB · click to replace` : 'PDF, including scanned files'}</div>
              </div>
              <input type="file" className="hidden" accept=".pdf" onChange={handleFileUpload} />
            </label>
          </section>

          <section>
            <div className="flex items-center gap-2.5 mb-2"><span className="step-badge">3</span><span className="field-label !mb-0">Anything to emphasise? <span className="muted font-normal">(optional)</span></span></div>
            <input className="field" placeholder="e.g. Keep it to one page, highlight leadership"
                   value={extraInstructions} onChange={(e) => setExtraInstructions(e.target.value)} />
          </section>

          <button onClick={runAnalysis} disabled={!file || !jobDesc || loading} className="btn btn-primary btn-lg w-full">
            {loading ? <><Loader2 size={17} className="animate-spin" /> Optimizing…</> : <><Sparkles size={17} /> Optimize my CV</>}
          </button>

          <div className="hairline" />

          <section>
            <button type="button" onClick={() => setShowCover((v) => !v)} className="w-full flex items-center justify-between" aria-expanded={showCover}>
              <span className="flex items-center gap-2.5 font-bold text-sm"><FileText size={17} className="accent" /> Cover letter</span>
              <ChevronDown size={18} className={`muted transition-transform ${showCover ? 'rotate-180' : ''}`} />
            </button>
            <AnimatePresence initial={false}>
              {showCover && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <div className="space-y-3 pt-4">
                    <input className="field" placeholder="Your full name *" value={coverForm.fullName} onChange={setCover('fullName')} />
                    <div className="grid grid-cols-2 gap-3">
                      <input className="field" placeholder="Company *" value={coverForm.targetCompany} onChange={setCover('targetCompany')} />
                      <input className="field" placeholder="Role *" value={coverForm.targetRole} onChange={setCover('targetRole')} />
                    </div>
                    <input className="field" placeholder="Your key achievement *" value={coverForm.keyAchievement} onChange={setCover('keyAchievement')} />
                    <select className="field" value={coverForm.tone} onChange={setCover('tone')}>
                      <option>Professional</option><option>Warm</option><option>Confident</option><option>Direct</option>
                    </select>
                    <textarea className="field h-20 resize-y" placeholder="Why you want this role (optional)"
                              value={coverForm.additionalNotes} onChange={setCover('additionalNotes')} />
                    <button onClick={generateCoverLetter} disabled={!file || !jobDesc || coverLoading} className="btn btn-secondary w-full">
                      {coverLoading ? <><Loader2 size={15} className="animate-spin" /> Writing…</> : <><PenLine size={15} /> Write cover letter</>}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </section>
        </aside>

        {/* ── Results ─────────────────────────────────────────────────────── */}
        <main className="min-w-0">
          {error && (
            <div className="card mb-6 px-5 py-4 flex items-center gap-3 text-sm" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>
              <AlertCircle size={18} className="shrink-0" /><span className="flex-1 font-medium">{error}</span>
              <button onClick={() => setError(null)} aria-label="Dismiss"><X size={16} /></button>
            </div>
          )}

          {(coverLoading || coverLetter) && (
            <section className="card p-7 mb-8">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-soft)', color: 'var(--accent-text)' }}><FileText size={18} /></div>
                  <div>
                    <h2 className="font-extrabold text-lg tracking-tight">Cover letter</h2>
                    {coverForm.targetCompany && <p className="text-sm muted">{coverForm.targetRole} at {coverForm.targetCompany}</p>}
                  </div>
                </div>
                {coverLetter && (
                  <div className="flex gap-2">
                    <button className="btn btn-secondary" onClick={() => navigator.clipboard.writeText(coverLetter).then(() => addToast({ type: 'success', msg: 'Copied to clipboard' }))}>
                      <Copy size={15} /> Copy
                    </button>
                    <button className="btn btn-primary" onClick={downloadCoverLetterPDF}><Download size={15} /> Download PDF</button>
                  </div>
                )}
              </div>
              {coverLoading
                ? <p className="text-sm muted flex items-center gap-2"><Loader2 size={15} className="animate-spin" /> Writing your letter…</p>
                : <div className="prose-doc max-w-3xl text-[15px]">{coverLetter}</div>}
            </section>
          )}

          {!results && loading && (
            <ProgressView jobStage={jobStage} jobStatus={jobStatus} jobProgress={jobProgress} jobId={jobId} onCancel={cancelJob} />
          )}

          {!results && !loading && !coverLetter && !coverLoading && <EmptyState />}

          {results && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
              <div className="grid grid-cols-1 2xl:grid-cols-[420px_1fr] gap-8 items-start">
                {results.scores && <ScoreCard scores={results.scores} />}

                <section className="card p-7 flex flex-col min-h-[560px]">
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
                    <div className="segmented" role="tablist">
                      <button role="tab" aria-selected={activeTab === 'audit'} onClick={() => setActiveTab('audit')}><ClipboardList size={15} /> Audit</button>
                      <button role="tab" aria-selected={activeTab === 'rewrite'} onClick={() => setActiveTab('rewrite')}><PenLine size={15} /> Rewritten CV</button>
                    </div>
                    {activeTab === 'rewrite' && <span className="text-xs muted">Edit anything, then apply to update the PDF.</span>}
                  </div>
                  {activeTab === 'audit' ? (
                    <div className="prose-doc flex-1 overflow-y-auto max-h-[640px] pr-2">{results.audit}</div>
                  ) : (
                    <div className="flex-1 flex flex-col">
                      <textarea value={editedRewrite ?? results.rewrite} onChange={(e) => setEditedRewrite(e.target.value)}
                                className="field flex-1 min-h-[440px] leading-relaxed resize-y" />
                      <div className="flex gap-2 mt-4">
                        <button onClick={applyEdits} className="btn btn-primary"><Check size={15} /> Apply edits</button>
                        <button onClick={() => { setEditedRewrite(results.rewrite); addToast({ type: 'info', msg: 'Edits reverted' }); }}
                                className="btn btn-secondary"><RotateCcw size={15} /> Revert</button>
                      </div>
                    </div>
                  )}
                </section>
              </div>

              <section className="card p-7">
                <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                  <div>
                    <h2 className="text-xl font-extrabold tracking-tight">Choose a template</h2>
                    <p className="text-sm muted">Your optimized CV, ready to send.</p>
                  </div>
                  <button onClick={downloadPDF} disabled={exporting} className="btn btn-primary btn-lg">
                    {exporting ? <Loader2 size={17} className="animate-spin" /> : <Download size={17} />} Download PDF
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  {TEMPLATES.map((tpl) => {
                    const on = selectedTemplate === tpl.id;
                    return (
                      <button key={tpl.id} type="button" onClick={() => setSelectedTemplate(tpl.id)} aria-pressed={on}
                              className="text-left rounded-2xl p-4 border-2 transition-all hover:-translate-y-0.5"
                              style={{ borderColor: on ? 'var(--accent)' : 'var(--rule)', background: on ? 'var(--accent-soft)' : 'var(--surface)' }}>
                        <div className="h-28 mb-4 p-3.5 rounded-xl" style={{ background: 'var(--surface)', border: '1px solid var(--rule)' }}>
                          <TemplateSketch id={tpl.id} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-bold">{tpl.label}</span>
                          {on && <span className="w-6 h-6 rounded-full flex items-center justify-center text-white" style={{ background: 'var(--grad)' }}><Check size={13} strokeWidth={3} /></span>}
                        </div>
                        <p className="text-xs muted mt-1 leading-relaxed">{tpl.desc}</p>
                      </button>
                    );
                  })}
                </div>
              </section>
            </motion.div>
          )}
        </main>
      </div>

      {/* ── Toasts ───────────────────────────────────────────────────────── */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2" aria-live="polite">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 10, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10 }}
                        className="card px-4 py-3 text-sm flex items-center gap-3 max-w-sm">
              <span className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                    style={{ background: t.type === 'error' ? 'color-mix(in srgb, var(--danger) 14%, transparent)' : 'var(--accent-soft)', color: t.type === 'error' ? 'var(--danger)' : 'var(--accent-text)' }}>
                {t.type === 'error' ? <AlertCircle size={15} /> : <Check size={15} strokeWidth={2.6} />}
              </span>
              <span className="flex-1 font-medium">{t.msg}</span>
              <button onClick={() => removeToast(t.id)} aria-label="Dismiss" className="muted"><X size={15} /></button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default App;
