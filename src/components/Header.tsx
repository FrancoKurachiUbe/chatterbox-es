import React from 'react';
import { Radio, ExternalLink, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { BackendStatus } from '../services/api';

interface HeaderProps {
  backendStatus: BackendStatus;
  onRefreshStatus: () => void;
  onOpenVoiceManager?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ backendStatus, onRefreshStatus, onOpenVoiceManager }) => {
  const isOnline = backendStatus.status === 'online';

  return (
    <header className="border-b border-[#1b2333] bg-[#0e121a]/95 backdrop-blur px-6 py-4 shadow-lg sticky top-0 z-50">
      <div className="mx-auto max-w-7xl flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Logo and Titles */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-inner">
            <Radio className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-extrabold tracking-wider text-white">
                CHATTERBOX PRIME
              </h1>
              <span className="inline-flex items-center gap-1 rounded bg-cyan-950/80 border border-cyan-800/80 px-2 py-0.5 text-[10px] font-bold text-cyan-300 uppercase tracking-widest">
                AI Narration Studio
              </span>
            </div>
            <p className="text-xs text-[#8b9bb4] tracking-wide">
              Estudio profesional de producción de voz con Chatterbox Multilingual
            </p>
          </div>
        </div>

        {/* Action Controls & Gradio Link */}
        <div className="flex flex-wrap items-center gap-2.5">
          {onOpenVoiceManager && (
            <button
              type="button"
              onClick={onOpenVoiceManager}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1a2434] px-3 py-1.5 text-xs font-semibold text-white transition-all"
            >
              🎙️ Administrar Voces
            </button>
          )}

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
                <span>Backend Python Activo</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                <span>Modo Local Autónomo</span>
              </>
            )}
            <RefreshCw className="h-3 w-3 opacity-60 hover:opacity-100" />
          </button>

          {/* Gradio Fallback Link */}
          <a
            href="/gradio"
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir interfaz Gradio alternativa"
            className="inline-flex items-center gap-1 rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1a2434] px-3 py-1.5 text-xs font-medium text-[#94a3b8] hover:text-white transition-all"
          >
            <span>Gradio</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </header>
  );
};
