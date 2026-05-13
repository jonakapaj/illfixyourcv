import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, FileText, Sparkles, Radar as RadarIcon, 
  Download, CheckCircle2, ChevronRight, Settings, 
  AlertCircle, Layout, Cpu, Database, Code, Globe
} from 'lucide-react';
import axios from 'axios';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer
} from 'recharts';

const API_BASE = "http://localhost:8000";

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
      setError(err.response?.data?.detail || "An error occurred during analysis.");
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
      setError("Failed to generate PDF.");
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
    { id: 'corporate', label: 'Corporate Classic', desc: 'Navy header, gold accent bar — for banking & enterprise.', color: 'from-[#1a1035] to-[#0e0920]', badge: 'Formal', badgeColor: 'bg-amber-500/20 text-amber-400' },
    { id: 'tech', label: 'Tech Modern', desc: 'Teal/blue gradient header — for startups & tech companies.', color: 'from-[#0f1f35] to-[#071020]', badge: 'Modern', badgeColor: 'bg-blue-500/20 text-blue-400' },
    { id: 'minimal', label: 'Minimal Slate', desc: 'Dark slate sidebar — for product & creative-tech roles.', color: 'from-[#1a0f2e] to-[#100a20]', badge: 'Creative', badgeColor: 'bg-pink-500/20 text-pink-400' },
  ];

  return (
    <div className="flex h-screen bg-[#09070f] text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-80 border-r border-violet-900/30 bg-[#110d1f] p-6 flex flex-col overflow-y-auto">
        <div className="mb-8">
          <div className="flex items-center gap-2 text-violet-400 mb-2">
            <Sparkles size={20} />
            <h1 className="text-xl font-bold tracking-tight">Career Sentinel</h1>
          </div>
          <p className="text-xs text-violet-300/50 uppercase tracking-widest font-semibold">AI CV Optimizer Pro</p>
        </div>

        <div className="space-y-6 flex-1">
          <section>
            <div className="flex items-center gap-3 mb-3">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-violet-600 text-[10px] font-bold">1</span>
              <label className="text-sm font-semibold text-violet-100">Job Description</label>
            </div>
            <textarea 
              className="w-full bg-violet-900/10 border border-violet-900/30 rounded-xl p-3 text-sm h-40 focus:outline-none focus:border-violet-500 transition-colors"
              placeholder="Paste the job description here..."
              value={jobDesc}
              onChange={(e) => setJobDesc(e.target.value)}
            />
          </section>

          <section>
            <div className="flex items-center gap-3 mb-3">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-violet-600 text-[10px] font-bold">2</span>
              <label className="text-sm font-semibold text-violet-100">Upload CV (PDF)</label>
            </div>
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-violet-900/30 rounded-xl cursor-pointer bg-violet-900/5 hover:bg-violet-900/10 transition-colors">
              <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center px-2">
                <Upload className="w-8 h-8 mb-2 text-violet-400" />
                <p className="text-xs text-violet-300">{file ? file.name : "Click to upload PDF"}</p>
              </div>
              <input type="file" className="hidden" accept=".pdf" onChange={handleFileUpload} />
            </label>
          </section>

          <section>
            <div className="flex items-center gap-3 mb-3">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-violet-600 text-[10px] font-bold">3</span>
              <label className="text-sm font-semibold text-violet-100">Extra Instructions</label>
            </div>
            <textarea 
              className="w-full bg-violet-900/10 border border-violet-900/30 rounded-xl p-3 text-sm h-20 focus:outline-none focus:border-violet-500 transition-colors"
              placeholder="e.g. Emphasise leadership..."
              value={extraInstructions}
              onChange={(e) => setExtraInstructions(e.target.value)}
            />
          </section>
        </div>

        <button 
          onClick={runAnalysis}
          disabled={!file || !jobDesc || loading}
          className="mt-8 w-full bg-gradient-to-r from-violet-600 to-purple-500 py-3 rounded-xl font-bold text-sm shadow-lg shadow-violet-900/20 hover:translate-y-[-2px] active:scale-95 disabled:opacity-50 disabled:translate-y-0 transition-all flex items-center justify-center gap-2"
        >
          {loading ? (
            <motion.div 
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
            >
              <Cpu size={18} />
            </motion.div>
          ) : <Sparkles size={18} />}
          {loading ? "Analyzing..." : "Run Analysis"}
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-8 relative">
        <header className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <span className="px-3 py-1 bg-violet-500/10 border border-violet-500/20 rounded-full text-[10px] font-bold text-violet-400 tracking-wider flex items-center gap-2 uppercase">
              <Cpu size={12} /> Multi-Agent Engine
            </span>
          </div>
          <h2 className="text-5xl font-extrabold bg-gradient-to-r from-white via-violet-300 to-pink-400 bg-clip-text text-transparent mb-2">
            AI Career Sentinel
          </h2>
          <p className="text-violet-300/50">Multi-agent CV optimisation powered by local AI.</p>
        </header>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400">
            <AlertCircle size={20} />
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        {!results ? (
          <div className="flex flex-col items-center justify-center h-[60vh] text-center">
            <div className="w-20 h-20 rounded-3xl bg-violet-900/10 border border-violet-900/30 flex items-center justify-center mb-6">
              <FileText className="text-violet-500" size={40} />
            </div>
            <h3 className="text-2xl font-bold mb-2">Start your optimisation</h3>
            <p className="text-violet-300/50 max-w-md">Upload your CV and paste a job description in the sidebar to get AI-powered insights and professional rewrites.</p>
          </div>
        ) : (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Left Column: Radar & Scores */}
              <div className="glass rounded-3xl p-8">
                <div className="card-title flex items-center gap-2 mb-6">
                  <RadarIcon size={16} /> Skill Alignment Radar
                </div>
                <div className="h-64 mb-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                      <PolarGrid stroke="#2e1065" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#a78bfa', fontSize: 10 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar
                        name="Skills"
                        dataKey="A"
                        stroke="#8b5cf6"
                        fill="#8b5cf6"
                        fillOpacity={0.3}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(results.scores).map(([key, value]) => (
                    <div key={key} className="px-3 py-1.5 bg-violet-500/10 border border-violet-500/20 rounded-full text-xs font-semibold text-violet-200">
                      {key} <span className="text-violet-400 ml-1">{value}/100</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Column: Audit & Rewrite */}
              <div className="glass rounded-3xl p-8 flex flex-col h-[500px]">
                <div className="flex items-center justify-between mb-6">
                  <div className="card-title mb-0">AI Optimised Content</div>
                  <div className="flex gap-1 bg-violet-900/20 p-1 rounded-lg">
                    <button 
                      onClick={() => setActiveTab('rewrite')}
                      className={`px-4 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${activeTab === 'rewrite' ? 'bg-violet-600 text-white shadow-lg' : 'text-violet-400 hover:text-violet-200'}`}
                    >
                      💡 Edits
                    </button>
                    <button 
                      onClick={() => setActiveTab('audit')}
                      className={`px-4 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${activeTab === 'audit' ? 'bg-violet-600 text-white shadow-lg' : 'text-violet-400 hover:text-violet-200'}`}
                    >
                      🚩 Audit
                    </button>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeTab}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      className="text-sm text-violet-100/80 leading-relaxed whitespace-pre-wrap"
                    >
                      {activeTab === 'rewrite' ? results.rewrite : results.audit}
                    </motion.div>
                  </AnimatePresence>
                </div>
              </div>
            </div>

            {/* Template Selector */}
            <div>
              <div className="w-full h-px bg-gradient-to-r from-transparent via-violet-900/40 to-transparent my-10" />
              <div className="card-title mb-2">Choose your CV template</div>
              <p className="text-sm text-violet-300/50 mb-8">Pick a style then click Generate. The AI-optimised content will be applied to your chosen layout.</p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {templates.map((tpl) => (
                  <motion.div 
                    key={tpl.id}
                    whileHover={{ y: -5 }}
                    onClick={() => setSelectedTemplate(tpl.id)}
                    className={`relative p-6 rounded-3xl cursor-pointer border-2 transition-all overflow-hidden bg-gradient-to-br ${tpl.color} ${selectedTemplate === tpl.id ? 'border-violet-500 ring-1 ring-violet-500 shadow-2xl shadow-violet-500/20' : 'border-white/5 opacity-70 hover:opacity-100'}`}
                  >
                    <div className="absolute top-4 right-4">
                      {selectedTemplate === tpl.id && <CheckCircle2 className="text-violet-400" size={20} />}
                    </div>
                    <span className={`inline-block px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider mb-4 ${tpl.badgeColor}`}>
                      {tpl.badge}
                    </span>
                    <h4 className="text-lg font-bold mb-2">{tpl.label}</h4>
                    <p className="text-xs text-violet-300/60 leading-relaxed mb-4">{tpl.desc}</p>
                    <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className={`h-full ${tpl.id === 'corporate' ? 'w-1/2 bg-amber-500/40' : tpl.id === 'tech' ? 'w-2/3 bg-blue-500/40' : 'w-1/3 bg-pink-500/40'}`} />
                    </div>
                  </motion.div>
                ))}
              </div>

              <div className="mt-10 flex justify-center">
                <button 
                  onClick={downloadPDF}
                  className="px-10 py-4 bg-gradient-to-r from-violet-600 to-indigo-500 rounded-2xl font-bold text-lg shadow-2xl shadow-violet-900/30 hover:scale-105 active:scale-95 transition-all flex items-center gap-3"
                >
                  <Download size={24} />
                  Generate CV — {templates.find(t => t.id === selectedTemplate)?.label}
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
