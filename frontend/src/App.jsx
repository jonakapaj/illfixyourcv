import React, { useState, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial, Float } from '@react-three/drei';
import * as random from 'maath/random/dist/maath-random.esm';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, FileText, Sparkles, Radar as RadarIcon, 
  Download, CheckCircle2, Cpu, Database, Code, 
  Terminal, ShieldCheck, Zap, Layers, MousePointer2,
  Layout, AlertCircle
} from 'lucide-react';
import axios from 'axios';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer
} from 'recharts';

// In dev mode, point to the local FastAPI server. Allow override via VITE_API_BASE.
const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? "http://localhost:8001" : "");


// --- 3D Background Component ---
function StarField(props) {
  const ref = useRef();
  const [sphere] = useState(() => random.inSphere(new Float32Array(5000), { radius: 1.5 }));
  
  useFrame((state, delta) => {
    ref.current.rotation.x -= delta / 10;
    ref.current.rotation.y -= delta / 15;
  });

  return (
    <group rotation={[0, 0, Math.PI / 4]}>
      <Points ref={ref} positions={sphere} stride={3} frustumCulled={false} {...props}>
        <PointMaterial
          transparent
          color="#10b981"
          size={0.002}
          sizeAttenuation={true}
          depthWrite={false}
        />
      </Points>
    </group>
  );
}

const Background3D = () => (
  <div className="fixed inset-0 z-0 pointer-events-none opacity-40">
    <Canvas camera={{ position: [0, 0, 1] }}>
      <StarField />
    </Canvas>
  </div>
);

const App = () => {
  const [jobDesc, setJobDesc] = useState('');
  const [extraInstructions, setExtraInstructions] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobStage, setJobStage] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [editedRewrite, setEditedRewrite] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState('corporate');
  const [activeTab, setActiveTab] = useState('rewrite');
  const [themePreset, setThemePreset] = useState('midnight');
  const [coverForm, setCoverForm] = useState({
    fullName: '',
    targetCompany: '',
    targetRole: '',
    keyAchievement: '',
    tone: 'Professional',
    additionalNotes: '',
  });
  const [coverLetter, setCoverLetter] = useState('');
  const [coverLoading, setCoverLoading] = useState(false);

  const themePresets = {
    midnight: {
      label: 'Midnight Slate',
      description: 'Cool dark mode with blue-gray accents',
      shell: 'bg-[#0f172a] text-[#e5e7eb]',
      sidebar: 'border-slate-700 bg-[#111827]/90',
      panel: 'bg-[#172033]/88 border-slate-700',
      input: 'bg-[#1e293b] border-slate-600 text-[#f8fafc] placeholder:text-slate-400',
      button: 'bg-sky-400 hover:bg-sky-300 text-slate-950',
      chip: 'border-sky-400/25 bg-sky-400/10 text-sky-200',
    },
    paper: {
      label: 'Paper White',
      description: 'White background with dark text',
      shell: 'bg-[#f8fafc] text-slate-900',
      sidebar: 'border-slate-200 bg-white/95',
      panel: 'bg-white/90 border-slate-200',
      input: 'bg-white border-slate-300 text-slate-900 placeholder:text-slate-400',
      button: 'bg-slate-900 hover:bg-slate-800 text-white',
      chip: 'border-slate-300 bg-slate-100 text-slate-700',
    },
    graphite: {
      label: 'Graphite',
      description: 'Dark gray with white text',
      shell: 'bg-[#1b1b1b] text-[#f5f5f5]',
      sidebar: 'border-zinc-700 bg-[#222222]/95',
      panel: 'bg-[#262626]/92 border-zinc-700',
      input: 'bg-[#2d2d2d] border-zinc-600 text-white placeholder:text-zinc-400',
      button: 'bg-[#f3f3f3] hover:bg-white text-[#111111]',
      chip: 'border-zinc-500 bg-zinc-700/70 text-zinc-50',
    },
  };

  const currentTheme = useMemo(() => themePresets[themePreset] ?? themePresets.midnight, [themePreset]);

  const handleFileUpload = (e) => {
    const uploadedFile = e.target.files[0];
    if (uploadedFile && uploadedFile.type === 'application/pdf') {
      setFile(uploadedFile);
      setError(null);
    } else {
      setError('Please upload a valid PDF file.');
    }
  };

  const runAnalysis = async () => {
    if (!file || !jobDesc) return;
    setLoading(true);
    setError(null);
    setJobId(null);
    setJobStatus(null);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_description', jobDesc);
    formData.append('user_instructions', extraInstructions);

    try {
      const response = await axios.post(`${API_BASE}/analyze`, formData);
      const body = response.data;
      // If backend returned cached completed result
      if (body.status === 'completed' && body.result) {
        setResults(body.result);
        setEditedRewrite(body.result.rewrite || null);
        setJobStatus('completed');
        setLoading(false);
      } else if (body.job_id) {
        setJobId(body.job_id);
        setJobStatus(body.status || 'queued');
        // start polling
        pollJob(body.job_id);
      } else {
        // Fallback if backend API differs
        setResults(body);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Connection to neural engine failed.");
    } finally {
      // keep loading until job completes; background polling will update loading
    }
  };

  const pollJob = async (id, attempts = 0) => {
    try {
      const statusResp = await axios.get(`${API_BASE}/status/${id}`);
      const s = statusResp.data.status;
      const stage = statusResp.data.stage;
      setJobStatus(s);
      setJobStage(stage);
      if (s === 'completed') {
        const res = await axios.get(`${API_BASE}/result/${id}`);
        setResults(res.data);
        setEditedRewrite(res.data.rewrite || null);
        setLoading(false);
        setJobId(null);
        setJobStatus('completed');
        return;
      }
      if (s === 'failed') {
        setError(statusResp.data.error || 'Analysis failed');
        setLoading(false);
        setJobId(null);
        return;
      }
      // Exponential backoff up to ~10s
      const delay = Math.min(1000 * Math.pow(2, attempts), 10000);
      setTimeout(() => pollJob(id, Math.min(attempts + 1, 6)), delay);
    } catch (err) {
      if (attempts < 6) {
        const delay = Math.min(1000 * Math.pow(2, attempts), 10000);
        setTimeout(() => pollJob(id, attempts + 1), delay);
      } else {
        setError('Unable to get job status.');
        setLoading(false);
        setJobId(null);
      }
    }
  };

  const cancelJob = async () => {
    if (!jobId) return;
    try {
      await axios.post(`${API_BASE}/cancel/${jobId}`);
      addToast({type: 'info', msg: 'Cancel requested'});
      setJobStatus('canceling');
    } catch (e) {
      addToast({type: 'error', msg: 'Cancel failed'});
    }
  };

  const applyEdits = async () => {
    if (!jobId || !editedRewrite) {
      // If no jobId (cached result), try to call /structure with a dummy job id? Use results if present
      if (results && results.cv_data) {
        try {
          const payload = new FormData();
          // use last known job id if present, otherwise require user to re-run
          if (!jobId) {
            addToast({type:'error', msg:'No job context to apply edits. Re-run analysis first.'});
            return;
          }
          payload.append('job_id', jobId);
          payload.append('rewrite_text', editedRewrite);
          const resp = await axios.post(`${API_BASE}/structure`, payload);
          setResults(prev => ({...prev, cv_data: resp.data.cv_data}));
          addToast({type:'success', msg:'Edits applied and structure updated.'});
        } catch (e) {
          addToast({type:'error', msg:'Failed to re-structure CV.'});
        }
      }
      return;
    }
    try {
      const payload = new FormData();
      payload.append('job_id', jobId);
      payload.append('rewrite_text', editedRewrite);
      const resp = await axios.post(`${API_BASE}/structure`, payload);
      setResults(prev => ({...prev, cv_data: resp.data.cv_data}));
      addToast({type: 'success', msg: 'Edits applied and structure updated.'});
    } catch (e) {
      addToast({type: 'error', msg: 'Failed to re-structure CV.'});
    }
  };

  const downloadPDF = async () => {
    if (!results) return;
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/generate?template_id=${selectedTemplate}`, 
        results.cv_data, 
        { responseType: 'blob' }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `optimised_cv_${selectedTemplate}.pdf`);
      document.body.appendChild(link);
      link.click();
    } catch (err) {
      setError("Data transmission error.");
    } finally {
      setLoading(false);
    }
  };

  const radarData = results?.scores ? Object.entries(results.scores).map(([key, value]) => ({
    subject: key,
    A: value,
    fullMark: 100,
  })) : [];

  const scoreAverage = radarData.length
    ? Math.round(radarData.reduce((sum, item) => sum + item.A, 0) / radarData.length)
    : 0;

  const scoreBand = (value) => {
    if (value >= 85) return 'Very strong match';
    if (value >= 70) return 'Good match';
    if (value >= 50) return 'Mixed match';
    return 'Needs improvement';
  };

  const scoreHint = (value) => {
    if (value >= 85) return 'This area is already close to what the job is asking for.';
    if (value >= 70) return 'Solid base, but there is still room to make it more job-specific.';
    if (value >= 50) return 'You have some evidence here, but it would benefit from clearer examples.';
    return 'This is a key gap to fix if you want a stronger application.';
  };

  const templates = [
    { id: 'corporate', label: 'Executive Slate', desc: 'Minimalist hierarchy for leadership & enterprise roles.', badge: 'Classic', color: 'from-[#0a0a0a] to-[#042f2e]', badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
    { id: 'tech', label: 'Modern Matrix', desc: 'Grid-based layout for high-growth tech & startups.', badge: 'Modern', color: 'from-[#0a0a0a] to-[#064e3b]', badgeColor: 'bg-teal-500/10 text-teal-400 border-teal-500/20' },
    { id: 'minimal', label: 'Creative Mono', desc: 'High-contrast typography for design & product roles.', badge: 'Creative', color: 'from-[#0a0a0a] to-[#022c22]', badgeColor: 'bg-emerald-400/10 text-emerald-300 border-emerald-400/20' },
  ];

  const addToast = ({ type = 'info', msg = '', timeout = 4500 } = {}) => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const t = { id, type, msg };
    setToasts((s) => [t, ...s]);
    setTimeout(() => setToasts((s) => s.filter((x) => x.id !== id)), timeout);
  };

  const removeToast = (id) => setToasts((s) => s.filter((x) => x.id !== id));

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
      addToast({ type: 'success', msg: 'Cover letter generated.' });
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
    } catch (err) {
      addToast({ type: 'error', msg: 'Failed to create cover letter PDF.' });
    }
  };

  return (
    <div className={`flex h-screen overflow-hidden relative ${currentTheme.shell}`} style={{ colorScheme: themePreset === 'paper' ? 'light' : 'dark' }}>
      <Background3D />
      
      {/* Sidebar */}
      <aside className={`w-80 backdrop-blur-xl p-8 flex flex-col z-10 relative border-r overflow-y-auto custom-scrollbar ${currentTheme.sidebar}`}>
        <div className="mb-10">
          <div className="flex items-center gap-2 text-emerald-400 mb-1">
            <Terminal size={22} className="opacity-80" />
            <h1 className="text-xl font-black tracking-tighter uppercase">Sentinel</h1>
          </div>
          <div className="h-1 w-12 bg-emerald-500 rounded-full" />
        </div>

        <section className="mb-8">
          <div className="card-title">
            <Sparkles size={14} className="opacity-60" /> UI Presets
          </div>
          <div className="grid grid-cols-3 gap-2 mt-3">
            {Object.entries(themePresets).map(([key, preset]) => (
              <button
                key={key}
                type="button"
                onClick={() => setThemePreset(key)}
                className={`w-full rounded-xl border px-2 py-2 text-left transition-all ${themePreset === key ? currentTheme.chip : 'border-transparent bg-black/10 hover:border-emerald-500/20'}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-[0.18em] leading-tight">{preset.label}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </section>

        <div className="space-y-8 flex-1">
          <section>
            <div className="card-title">
              <Database size={14} className="opacity-60" /> Target Parameters
            </div>
            <textarea 
              className={`w-full rounded-2xl p-4 text-xs h-40 focus:outline-none focus:border-emerald-500/50 transition-all font-mono ${currentTheme.input}`}
              placeholder="Paste Job Requirements..."
              value={jobDesc}
              onChange={(e) => setJobDesc(e.target.value)}
            />
          </section>

          <section>
            <div className="card-title">
              <ShieldCheck size={14} className="opacity-60" /> Source Data
            </div>
            <label className="flex flex-col items-center justify-center w-full h-32 border border-emerald-900/20 rounded-2xl cursor-pointer bg-emerald-950/5 hover:bg-emerald-900/10 transition-all group">
              <div className="flex flex-col items-center justify-center p-4 text-center">
                <Upload className="w-6 h-6 mb-2 text-emerald-700 group-hover:text-emerald-500 transition-colors" />
                <p className="text-[10px] text-emerald-900 font-bold uppercase tracking-widest">{file ? file.name : "Upload CV PDF"}</p>
              </div>
              <input type="file" className="hidden" accept=".pdf" onChange={handleFileUpload} />
            </label>
          </section>

          <section>
            <div className="card-title">
              <FileText size={14} className="opacity-60" /> Cover Letter Brief
            </div>
            <div className="space-y-3">
              <input
                className={`w-full rounded-xl px-4 py-3 text-xs border focus:outline-none ${currentTheme.input}`}
                placeholder="Your full name *"
                value={coverForm.fullName}
                onChange={(e) => setCoverForm((p) => ({ ...p, fullName: e.target.value }))}
              />
              <input
                className={`w-full rounded-xl px-4 py-3 text-xs border focus:outline-none ${currentTheme.input}`}
                placeholder="Target company *"
                value={coverForm.targetCompany}
                onChange={(e) => setCoverForm((p) => ({ ...p, targetCompany: e.target.value }))}
              />
              <input
                className={`w-full rounded-xl px-4 py-3 text-xs border focus:outline-none ${currentTheme.input}`}
                placeholder="Target role *"
                value={coverForm.targetRole}
                onChange={(e) => setCoverForm((p) => ({ ...p, targetRole: e.target.value }))}
              />
              <input
                className={`w-full rounded-xl px-4 py-3 text-xs border focus:outline-none ${currentTheme.input}`}
                placeholder="Key achievement or proof point *"
                value={coverForm.keyAchievement}
                onChange={(e) => setCoverForm((p) => ({ ...p, keyAchievement: e.target.value }))}
              />
              <select
                className={`w-full rounded-xl px-4 py-3 text-xs border focus:outline-none ${currentTheme.input}`}
                value={coverForm.tone}
                onChange={(e) => setCoverForm((p) => ({ ...p, tone: e.target.value }))}
              >
                <option>Professional</option>
                <option>Warm</option>
                <option>Confident</option>
                <option>Direct</option>
              </select>
              <textarea
                className={`w-full rounded-2xl px-4 py-3 text-xs h-24 border focus:outline-none ${currentTheme.input}`}
                placeholder="Additional notes about why you want the role or what to emphasize"
                value={coverForm.additionalNotes}
                onChange={(e) => setCoverForm((p) => ({ ...p, additionalNotes: e.target.value }))}
              />
            </div>
          </section>
        </div>

        <button 
          onClick={runAnalysis}
          disabled={!file || !jobDesc || loading}
          className={`mt-10 w-full py-4 rounded-2xl font-black text-xs uppercase tracking-widest shadow-xl hover:translate-y-[-2px] active:scale-95 disabled:opacity-30 disabled:translate-y-0 transition-all flex items-center justify-center gap-3 ${currentTheme.button}`}
        >
          {loading ? (
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
              <Cpu size={18} />
            </motion.div>
          ) : <Zap size={18} fill="currentColor" />}
          {loading ? "Processing..." : "Initialise Analysis"}
        </button>

        <button
          onClick={generateCoverLetter}
          disabled={!file || !jobDesc || coverLoading}
          className={`mt-4 mb-4 w-full py-4 rounded-2xl font-black text-xs uppercase tracking-widest border transition-all flex items-center justify-center gap-3 ${themePreset === 'paper' ? 'border-slate-300 bg-white text-slate-900 hover:bg-slate-50' : 'border-slate-500/30 bg-black/10 text-current hover:bg-black/20'} disabled:opacity-30 disabled:translate-y-0`}
        >
          {coverLoading ? (
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
              <Cpu size={18} />
            </motion.div>
          ) : <FileText size={18} />}
          {coverLoading ? 'Writing Cover Letter...' : 'Generate Cover Letter'}
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-12 z-10 relative">
        <header className="mb-14 flex justify-between items-end">
          <div>
            <div className="flex items-center gap-4 mb-4">
              <span className="px-3 py-1 bg-emerald-500/5 border border-emerald-500/10 rounded-lg text-[9px] font-bold text-emerald-600 tracking-[0.2em] uppercase flex items-center gap-2">
                <span className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse" /> System v2.0.4
              </span>
            </div>
            <h2 className={`text-6xl font-black tracking-tighter ${themePreset === 'paper' ? 'text-slate-900' : 'text-gradient'}`}>
              Neural CV Optimizer
            </h2>
          </div>
          <div className={`flex flex-col items-end gap-1 ${themePreset === 'paper' ? 'opacity-70' : 'opacity-40'}`}>
            <span className="text-[9px] font-mono">ENCODING: LATIN-1</span>
            <span className="text-[9px] font-mono">MODEL: LLAMA-3-BETA</span>
          </div>
        </header>

        {error && (
          <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="mb-8 p-4 bg-red-950/20 border border-red-500/30 rounded-2xl flex items-center gap-4 text-red-400">
            <AlertCircle size={20} />
            <p className="text-xs font-bold tracking-tight uppercase">{error}</p>
          </motion.div>
        )}

        {(coverLoading || coverLetter) && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={`mb-10 glass rounded-[2.5rem] p-8 border ${currentTheme.panel}`}>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
              <div>
                <div className="card-title mb-2">
                  <FileText size={14} className="opacity-60" /> Cover Letter
                </div>
                <p className="text-xs opacity-70">Preview the generated letter and download it as a PDF.</p>
              </div>
              {coverLetter && (
                <div className="flex gap-3">
                  <button
                    onClick={() => navigator.clipboard.writeText(coverLetter).then(() => addToast({ type: 'success', msg: 'Cover letter copied.' }))}
                    className={`px-4 py-2 rounded-lg text-xs font-bold border ${themePreset === 'paper' ? 'border-slate-300 bg-white text-slate-900' : 'border-white/10 bg-black/20 text-white'}`}
                  >
                    Copy text
                  </button>
                  <button
                    onClick={downloadCoverLetterPDF}
                    className={`px-4 py-2 rounded-lg text-xs font-bold ${currentTheme.button}`}
                  >
                    Download PDF
                  </button>
                </div>
              )}
            </div>
            {coverLoading ? (
              <div className="flex items-center gap-3 text-xs uppercase tracking-widest opacity-70">
                <Cpu size={16} className="animate-spin" /> Writing a tailored letter...
              </div>
            ) : (
              <pre className="whitespace-pre-wrap text-sm leading-relaxed font-mono opacity-90">{coverLetter}</pre>
            )}
          </motion.div>
        )}

        {!results && jobStatus && (
          <div className="flex flex-col items-center justify-center h-[50vh] text-center">
            <div className="mb-6">
              <div className="text-sm font-bold uppercase tracking-widest">Analysis status</div>
              <div className="text-xs text-emerald-300 mt-2">{jobStatus.toUpperCase()}</div>
            </div>
            <div className="w-2/3 bg-emerald-900/20 rounded-full h-4 overflow-hidden mb-4">
              <div className="h-full bg-emerald-500 transition-all" style={{ width: jobStatus === 'completed' ? '100%' : jobStatus === 'running' ? '60%' : '20%' }} />
            </div>
            <p className="text-emerald-900 text-xs font-medium max-w-xs uppercase tracking-widest leading-relaxed">This may take a few seconds — we'll update automatically.</p>
          </div>
        )}
        {!results && !jobStatus && (
          <div className="flex flex-col items-center justify-center h-[50vh] text-center">
            <motion.div animate={{ y: [0, -8, 0] }} transition={{ repeat: Infinity, duration: 3 }} className={`w-24 h-24 rounded-[2rem] border flex items-center justify-center mb-6 rotate-3 shadow-2xl ${themePreset === 'paper' ? 'bg-white border-slate-200 shadow-slate-900/5' : themePreset === 'graphite' ? 'bg-[#1b1b1b] border-zinc-800 shadow-black/20' : 'bg-emerald-500/5 border-emerald-500/10 shadow-emerald-500/5'}`}>
              <Layers className="text-emerald-900" size={40} />
            </motion.div>
            <div className="text-xs text-emerald-300 mb-4">{jobStatus ? `${jobStatus.toUpperCase()} ${jobStage ? `— ${jobStage}` : ''}` : ''}</div>
            <p className="text-emerald-900 text-xs font-medium max-w-xs uppercase tracking-widest leading-relaxed">Please configure target parameters and source PDF in the command center.</p>
            <div className="mt-4 flex gap-3">
              {jobId && jobStatus !== 'completed' && jobStatus !== 'failed' && (
                <button onClick={cancelJob} className="px-4 py-2 bg-red-600 rounded-lg text-xs font-bold text-white">Cancel</button>
              )}
            </div>
          </div>
        )}
        {results && (
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="space-y-12">
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-10">
              {/* Skill Matrix */}
              <div className={`glass rounded-[2.5rem] p-10 relative overflow-hidden border ${currentTheme.panel}`}>
                <div className="absolute top-0 right-0 p-8 opacity-5">
                  <RadarIcon size={120} />
                </div>
                <div className="card-title">
                  <RadarIcon size={14} className="opacity-60" /> Alignment Matrix
                </div>
                <div className="mb-4 rounded-2xl border border-white/5 bg-black/10 p-4">
                  <div className="flex items-end justify-between gap-4">
                    <div>
                      <div className="text-sm font-black tracking-tight">
                        Overall match: {scoreAverage}%
                      </div>
                      <div className="text-xs opacity-70 mt-1">
                        {scoreBand(scoreAverage)}. Higher scores mean the CV is closer to the job description.
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] uppercase tracking-widest opacity-60">How to read</div>
                      <div className="text-xs opacity-75 max-w-[14rem]">Longer shape = stronger alignment in that area.</div>
                    </div>
                  </div>
                </div>
                <div className="h-72 my-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                      <PolarGrid stroke="#064e3b" strokeOpacity={0.3} />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#059669', fontSize: 9, fontWeight: 700 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar
                        name="Skills"
                        dataKey="A"
                        stroke="#10b981"
                        fill="#10b981"
                        fillOpacity={0.2}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-1 gap-3">
                  {Object.entries(results.scores).map(([key, value]) => (
                    <div key={key} className="p-4 bg-emerald-950/10 border border-emerald-900/10 rounded-2xl group hover:border-emerald-500/30 transition-all">
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div>
                          <span className="text-[10px] font-bold text-emerald-800 uppercase group-hover:text-emerald-400">{key}</span>
                          <div className="text-[10px] opacity-70 mt-1">{scoreBand(value)}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-black text-emerald-400">{value}%</div>
                          <div className="text-[10px] opacity-60">{value >= 70 ? 'Strong' : value >= 50 ? 'Moderate' : 'Low'}</div>
                        </div>
                      </div>
                      <div className="h-2 rounded-full bg-black/20 overflow-hidden mb-2">
                        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${value}%` }} />
                      </div>
                      <p className="text-[10px] leading-relaxed opacity-70">{scoreHint(value)}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Terminal View */}
              <div className={`glass rounded-[2.5rem] p-10 flex flex-col h-[600px] border ${currentTheme.panel}`}>
                <div className="flex items-center justify-between mb-8">
                  <div className="card-title mb-0">System Output</div>
                  <div className={`flex gap-2 p-1.5 rounded-xl border ${themePreset === 'paper' ? 'bg-white/80 border-slate-200' : 'bg-black/40 border-emerald-900/20'}`}>
                    <button 
                      onClick={() => setActiveTab('rewrite')}
                      className={`px-6 py-2 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all ${activeTab === 'rewrite' ? 'bg-emerald-600 text-black' : 'text-emerald-900 hover:text-emerald-500'}`}
                    >
                      Revised
                    </button>
                    <button 
                      onClick={() => setActiveTab('audit')}
                      className={`px-6 py-2 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all ${activeTab === 'audit' ? 'bg-emerald-600 text-black' : 'text-emerald-900 hover:text-emerald-500'}`}
                    >
                      Audited
                    </button>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto pr-4 font-mono text-[11px] text-emerald-200/60 leading-relaxed custom-scrollbar">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeTab}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="whitespace-pre-wrap"
                    >
                      {activeTab === 'rewrite' ? (
                        <div>
                          <textarea
                            value={editedRewrite ?? results.rewrite}
                            onChange={(e) => setEditedRewrite(e.target.value)}
                            className={`w-full min-h-[300px] rounded-lg p-4 text-sm font-mono border ${currentTheme.input}`}
                          />
                          <div className="flex gap-3 mt-3">
                            <button onClick={applyEdits} className={`px-4 py-2 rounded-lg text-xs font-bold ${currentTheme.button}`}>Apply edits</button>
                            <button onClick={() => { setEditedRewrite(results.rewrite); addToast({type:'info', msg:'Edits reverted'}); }} className={`px-4 py-2 rounded-lg text-xs border ${themePreset === 'paper' ? 'border-slate-300 bg-white text-slate-900' : 'border-emerald-900/20 bg-emerald-900 text-white'}`}>Revert</button>
                          </div>
                        </div>
                      ) : (
                        results.audit
                      )}
                    </motion.div>
                  </AnimatePresence>
                </div>
              </div>
            </div>

            {/* Template Engine */}
            <div className="pt-10">
              <div className="card-title">
                <Layout size={14} className="opacity-60" /> Render Engine
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-6">
                {templates.map((tpl) => (
                  <motion.div 
                    key={tpl.id}
                    whileHover={{ y: -8, scale: 1.02 }}
                    onClick={() => setSelectedTemplate(tpl.id)}
                    className={`relative p-8 rounded-[2rem] cursor-pointer border transition-all overflow-hidden bg-gradient-to-br ${tpl.color} ${selectedTemplate === tpl.id ? 'border-emerald-500 shadow-2xl shadow-emerald-500/20' : 'border-emerald-900/10 opacity-40 hover:opacity-100 hover:border-emerald-500/30'}`}
                  >
                    <div className="absolute top-6 right-6">
                      {selectedTemplate === tpl.id && <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}><CheckCircle2 className="text-emerald-400" size={24} /></motion.div>}
                    </div>
                    <span className={`inline-block px-3 py-1 rounded-lg border text-[8px] font-black uppercase tracking-widest mb-6 ${tpl.badgeColor}`}>
                      {tpl.badge}
                    </span>
                    <h4 className="text-xl font-black mb-3 tracking-tight">{tpl.label}</h4>
                    <p className="text-[10px] text-emerald-900 font-bold leading-relaxed mb-6 uppercase">{tpl.desc}</p>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: selectedTemplate === tpl.id ? '100%' : '20%' }}
                        className={`h-full bg-emerald-500`}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>

              <div className="mt-16 flex justify-center">
                <button 
                  onClick={downloadPDF}
                  className="group relative px-12 py-5 bg-emerald-600 rounded-2xl font-black text-xs uppercase tracking-widest text-black shadow-2xl shadow-emerald-500/20 hover:scale-105 active:scale-95 transition-all overflow-hidden"
                >
                  <span className="relative z-10 flex items-center gap-3">
                    <Download size={20} />
                    Finalise & Export PDF
                  </span>
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 to-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </main>
      {/* Toasts */}
      <AnimatePresence>
        {toasts.length > 0 && (
          <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3">
            {toasts.map((t) => (
              <motion.div key={t.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} className={`p-3 rounded-lg text-white max-w-sm shadow-lg ${t.type === 'error' ? 'bg-red-700' : t.type === 'info' ? 'bg-emerald-700' : 'bg-emerald-600'}`}>
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium">{t.msg}</div>
                  <div className="flex items-center gap-2">
                    <button className="text-xs underline" onClick={() => removeToast(t.id)}>Dismiss</button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default App;
