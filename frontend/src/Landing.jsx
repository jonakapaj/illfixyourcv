import React, { useEffect, useState, useRef } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart,
} from 'recharts';
import { Zap, ShieldCheck, Users, Globe, BarChart2 } from 'lucide-react';

const generateInitialData = () => {
  const now = Date.now();
  return Array.from({ length: 24 }).map((_, i) => ({
    time: new Date(now - (23 - i) * 1000).toLocaleTimeString().replace(/:\d+ /, ' '),
    value: Math.round(60 + Math.random() * 20),
  }));
};

export default function Landing() {
  const [data, setData] = useState(generateInitialData);
  const timerRef = useRef(null);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setData((d) => {
        const next = d.slice(1);
        next.push({ time: new Date().toLocaleTimeString().replace(/:\d+ /, ' '), value: Math.round(60 + Math.random() * 30) });
        return next;
      });
    }, 1500);
    return () => clearInterval(timerRef.current);
  }, []);

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-[#031018] via-[#02121a] to-[#01060a] text-white">
      <header className="max-w-7xl mx-auto px-6 py-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-sky-400 flex items-center justify-center text-black font-black">S</div>
          <div>
            <div className="font-black text-lg">Spectra</div>
            <div className="text-xs opacity-60">Analytics & Insights</div>
          </div>
        </div>
        <nav className="flex items-center gap-4">
          <a className="text-sm opacity-80 hover:opacity-100">Product</a>
          <a className="text-sm opacity-80 hover:opacity-100">Pricing</a>
          <a className="text-sm opacity-80 hover:opacity-100">Docs</a>
          <button className="ml-4 px-4 py-2 rounded-lg bg-emerald-500 text-black font-bold">Get started</button>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
          <div>
            <h1 className="text-5xl font-extrabold leading-tight mb-4">Real-time SaaS analytics for modern teams</h1>
            <p className="text-lg opacity-80 mb-6">Monitor live metrics, uncover trends, and make decisions faster — all from a clean, privacy-first dashboard with beautiful glassmorphic components.</p>

            <div className="flex gap-4 mb-8">
              <button className="px-6 py-3 rounded-lg bg-emerald-500 text-black font-bold">Start free trial</button>
              <button className="px-6 py-3 rounded-lg border border-white/10 text-white opacity-90">Request demo</button>
            </div>

            <div className="flex gap-4 flex-wrap">
              <div className="glass rounded-xl p-4 w-40">
                <div className="text-xs uppercase opacity-70">Active users</div>
                <div className="text-2xl font-black mt-2">12.4k</div>
                <div className="text-[11px] opacity-60 mt-1">+4.2% vs yesterday</div>
              </div>
              <div className="glass rounded-xl p-4 w-40">
                <div className="text-xs uppercase opacity-70">Conversion</div>
                <div className="text-2xl font-black mt-2">3.8%</div>
                <div className="text-[11px] opacity-60 mt-1">Stable</div>
              </div>
              <div className="glass rounded-xl p-4 w-40">
                <div className="text-xs uppercase opacity-70">Availability</div>
                <div className="text-2xl font-black mt-2">99.99%</div>
                <div className="text-[11px] opacity-60 mt-1">SLA-backed</div>
              </div>
            </div>
          </div>

          <div className="glass rounded-3xl p-6 border border-white/5 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-bold">Live traffic</div>
              <div className="text-xs opacity-60">Updated every 1.5s</div>
            </div>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity={0.6} />
                      <stop offset="100%" stopColor="#10b981" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" axisLine={false} tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }} />
                  <YAxis axisLine={false} tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#051016', border: '1px solid rgba(255,255,255,0.04)' }} />
                  <Area type="monotone" dataKey="value" stroke="#10b981" fill="url(#grad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        <section className="mt-16">
          <h3 className="text-2xl font-bold mb-6">Key features</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-3"><Zap className="text-emerald-400" /> <div className="font-bold">Real-time alerts</div></div>
              <div className="text-sm opacity-70">Custom thresholds and intelligent anomaly detection keep you informed.</div>
            </div>
            <div className="glass rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-3"><BarChart2 className="text-emerald-400" /> <div className="font-bold">Advanced analytics</div></div>
              <div className="text-sm opacity-70">Slice data across segments with high-performance queries and visualizations.</div>
            </div>
            <div className="glass rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-3"><ShieldCheck className="text-emerald-400" /> <div className="font-bold">Enterprise security</div></div>
              <div className="text-sm opacity-70">SOC2 controls, SSO, and fine-grained access controls for teams.</div>
            </div>
          </div>
        </section>

        <section className="mt-16">
          <h3 className="text-2xl font-bold mb-6">Pricing</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass rounded-2xl p-6 text-center">
              <div className="text-xs uppercase opacity-70">Starter</div>
              <div className="text-3xl font-black mt-2">Free</div>
              <div className="text-sm opacity-70 mt-2">For personal projects and exploration</div>
              <ul className="mt-4 text-sm space-y-2 opacity-80 text-left">
                <li>• 5k monthly events</li>
                <li>• Standard charts</li>
                <li>• Community support</li>
              </ul>
              <button className="mt-6 px-6 py-2 rounded-lg bg-emerald-500 text-black font-bold">Create account</button>
            </div>
            <div className="glass rounded-2xl p-6 text-center border-2 border-emerald-500">
              <div className="text-xs uppercase opacity-70">Pro</div>
              <div className="text-3xl font-black mt-2">$49/mo</div>
              <div className="text-sm opacity-70 mt-2">Best for small teams</div>
              <ul className="mt-4 text-sm space-y-2 opacity-80 text-left">
                <li>• 250k monthly events</li>
                <li>• Real-time alerts</li>
                <li>• Priority support</li>
              </ul>
              <button className="mt-6 px-6 py-2 rounded-lg bg-emerald-500 text-black font-bold">Start trial</button>
            </div>
            <div className="glass rounded-2xl p-6 text-center">
              <div className="text-xs uppercase opacity-70">Enterprise</div>
              <div className="text-3xl font-black mt-2">Custom</div>
              <div className="text-sm opacity-70 mt-2">High-scale and SLA backed</div>
              <ul className="mt-4 text-sm space-y-2 opacity-80 text-left">
                <li>• Unlimited events</li>
                <li>• SSO and SAML</li>
                <li>• Dedicated onboarding</li>
              </ul>
              <button className="mt-6 px-6 py-2 rounded-lg border border-white/10">Contact sales</button>
            </div>
          </div>
        </section>

        <section className="mt-16">
          <h3 className="text-2xl font-bold mb-6">Trusted by</h3>
          <div className="flex items-center gap-6 flex-wrap">
            <div className="glass rounded-lg p-4 px-6 opacity-90">Acme Corp</div>
            <div className="glass rounded-lg p-4 px-6 opacity-90">Nova Labs</div>
            <div className="glass rounded-lg p-4 px-6 opacity-90">Orbit Inc</div>
            <div className="glass rounded-lg p-4 px-6 opacity-90">Cloudway</div>
          </div>
        </section>
      </main>
    </div>
  );
}
