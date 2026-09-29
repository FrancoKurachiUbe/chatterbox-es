import React from 'react';
import { Mic, Radio, Cpu, ExternalLink, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { BackendStatus } from '../services/api';

interface HeaderProps {
  backendStatus: BackendStatus;
  onRefreshStatus: () => void;
}

export const Header: React.FC<HeaderProps> = ({ backendStatus, onRefreshStatus }) => {
  const isOnline = backendStatus.status === 'online';

  return (
    <header className="border-b border-[#222936] bg-[#0c1017] px-6 py-5 shadow-lg">
      <div className="mx-auto max-w-7xl flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Logo and Titles */}
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-inner">
            <Radio className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold tracking-wider text-white">
                CRÓNICAS MUNDIALES
              </h1>
              <span className="inline-flex items-center gap-1 rounded bg-cyan-950/80 border border-cyan-800/80 px-2 py-0.5 text-[10px] font-bold text-cyan-300 uppercase tracking-widest">
                Narration Studio
              </span>
            </div>
            <p className="text-xs text-[#8b9bb4] tracking-wide">
              Estudio de producción de narraciones con Chatterbox Multilingual TTS
            </p>
          </div>
        </div>

        {/* Badges and System Status */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Device Badge */}
          <div className="inline-flex items-center gap-1.5 rounded-lg border border-[#232b38] bg-[#141a24] px-2.5 py-1.5 text-xs text-[#cbd5e1] font-mono">
            <Cpu className="h-3.5 w-3.5 text-cyan-400" />
            <span>{isOnline ? backendStatus.device_label : 'CPU (AMD Ryzen 5600G)'}</span>
          </div>

          {/* Backend Connection Status Badge */}
          <button
            type="button"
            onClick={onRefreshStatus}
            title="Click para comprobar conexión con Python"
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all ${
              isOnline
                ? 'border-emerald-500/40 bg-emerald-950/50 text-emerald-300 hover:bg-emerald-900/40'
                : 'border-amber-500/40 bg-amber-950/50 text-amber-300 hover:bg-amber-900/40'
            }`}
          >
            {isOnline ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>Backend Python Conectado</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                <span>Python: Inicia multilingual_app.py</span>
                <RefreshCw className="h-3 w-3 ml-1" />
              </>
            )}
          </button>

          {/* Gradio Fallback link */}
          <a
            href="/gradio"
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir la interfaz Gradio original en una pestaña separada"
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#2a3444] bg-[#161d28] hover:bg-[#20293a] px-3 py-1.5 text-xs font-medium text-[#94a3b8] hover:text-white transition-colors"
          >
            <span>Gradio Fallback</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </header>
  );
};
