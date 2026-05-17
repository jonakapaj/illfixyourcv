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

// In dev mode, point to FastAPI server. In production, use relative paths.
const API_BASE = import.meta.env.DEV ? "http://localhost:8000" : "";


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
  const [selectedTemplate, setSelectedTemplate] = useState('corporate');
  const [activeTab, setActiveTab] = useState('rewrite');

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
    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_description', jobDesc);
    formData.append('user_instructions', extraInstructions);

    try {
      const response = await axios.post(`${API_BASE}/analyze`, formData);
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Connection to neural engine failed.");
    } finally {
      setLoading(false);
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

  const templates = [
    { id: 'corporate', label: 'Executive Slate', desc: 'Minimalist hierarchy for leadership & enterprise roles.', badge: 'Classic', color: 'from-[#0a0a0a] to-[#042f2e]', badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
    { id: 'tech', label: 'Modern Matrix', desc: 'Grid-based layout for high-growth tech & startups.', badge: 'Modern', color: 'from-[#0a0a0a] to-[#064e3b]', badgeColor: 'bg-teal-500/10 text-teal-400 border-teal-500/20' },
    { id: 'minimal', label: 'Creative Mono', desc: 'High-contrast typography for design & product roles.', badge: 'Creative', color: 'from-[#0a0a0a] to-[#022c22]', badgeColor: 'bg-emerald-400/10 text-emerald-300 border-emerald-400/20' },
  ];

  return (
    <div className="flex h-screen bg-[#050505] text-[#ecfdf5] overflow-hidden relative">
      <Background3D />
      
      {/* Sidebar */}
      <aside className="w-80 border-r border-emerald-950/50 bg-[#0a0a0a]/80 backdrop-blur-xl p-8 flex flex-col z-10 relative">
        <div className="mb-10">
          <div className="flex items-center gap-2 text-emerald-400 mb-1">
            <Terminal size={22} className="opacity-80" />
            <h1 className="text-xl font-black tracking-tighter uppercase">Sentinel</h1>
          </div>
          <div className="h-1 w-12 bg-emerald-500 rounded-full" />
        </div>

        <div className="space-y-8 flex-1">
          <section>
            <div className="card-title">
              <Database size={14} className="opacity-60" /> Target Parameters
            </div>
            <textarea 
              className="w-full bg-emerald-950/5 border border-emerald-900/20 rounded-2xl p-4 text-xs h-40 focus:outline-none focus:border-emerald-500/50 transition-all placeholder:text-emerald-900/40 font-mono"
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
        </div>

        <button 
          onClick={runAnalysis}
          disabled={!file || !jobDesc || loading}
          className="mt-10 w-full bg-emerald-600 hover:bg-emerald-500 py-4 rounded-2xl font-black text-xs uppercase tracking-widest shadow-xl shadow-emerald-900/20 hover:translate-y-[-2px] active:scale-95 disabled:opacity-30 disabled:translate-y-0 transition-all flex items-center justify-center gap-3 text-emerald-950"
        >
          {loading ? (
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
              <Cpu size={18} />
            </motion.div>
          ) : <Zap size={18} fill="currentColor" />}
          {loading ? "Processing..." : "Initialise Analysis"}
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
            <h2 className="text-6xl font-black tracking-tighter text-gradient">
              Neural CV Optimizer
            </h2>
          </div>
          <div className="flex flex-col items-end gap-1 opacity-40">
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

        {!results ? (
          <div className="flex flex-col items-center justify-center h-[50vh] text-center">
            <motion.div 
              animate={{ y: [0, -10, 0] }}
              transition={{ repeat: Infinity, duration: 4 }}
              className="w-24 h-24 rounded-[2rem] bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center mb-8 rotate-3 shadow-2xl shadow-emerald-500/5"
            >
              <Layers className="text-emerald-900" size={40} />
            </motion.div>
            <h3 className="text-xl font-bold mb-3 tracking-tight">System Awaiting Data Input</h3>
            <p className="text-emerald-900 text-xs font-medium max-w-xs uppercase tracking-widest leading-relaxed">Please configure target parameters and source PDF in the command center.</p>
          </div>
        ) : (
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="space-y-12">
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-10">
              {/* Skill Matrix */}
              <div className="glass rounded-[2.5rem] p-10 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-5">
                  <RadarIcon size={120} />
                </div>
                <div className="card-title">
                  <RadarIcon size={14} className="opacity-60" /> Alignment Matrix
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
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(results.scores).map(([key, value]) => (
                    <div key={key} className="p-3 bg-emerald-950/10 border border-emerald-900/10 rounded-xl flex justify-between items-center group hover:border-emerald-500/30 transition-all">
                      <span className="text-[10px] font-bold text-emerald-800 uppercase group-hover:text-emerald-400">{key}</span>
                      <span className="text-xs font-black text-emerald-400">{value}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Terminal View */}
              <div className="glass rounded-[2.5rem] p-10 flex flex-col h-[600px] border-emerald-500/5">
                <div className="flex items-center justify-between mb-8">
                  <div className="card-title mb-0">System Output</div>
                  <div className="flex gap-2 bg-black/40 p-1.5 rounded-xl border border-emerald-900/20">
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
                      {activeTab === 'rewrite' ? results.rewrite : results.audit}
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
    </div>
  );
};

export default App;
