import React, { useState } from 'react';
import { ScriptSection, ScriptPart, ProcessingMode, StudioSettings } from '../types';
import { GenerationProgress } from '../services/api';
import {
  RotateCw,
  CheckSquare,
  Square,
  Volume2,
  Download,
  Link as LinkIcon,
  CheckCircle2,
  Clock,
  AlertCircle,
  Layers,
  Sparkles,
  Loader2
} from 'lucide-react';
import { speakText, stopSpeaking } from '../utils/audioEngine';

interface ProductionPanelProps {
  sections: ScriptSection[];
  processingMode: ProcessingMode;
  settings: StudioSettings;
  isGeneratingAll: boolean;
  progressInfo?: GenerationProgress;
  isBackendOnline?: boolean;
  onGenerateAll: () => void;
  onRegeneratePart: (sectionNumber: number, partNumber: number) => Promise<void>;
  onBatchRegenerate: (selectedKeys: string[]) => Promise<void>;
  onJoinSection: (sectionNumber: number) => Promise<void>;
  latestAudioUrl?: string;
  latestAudioTitle?: string;
}

export const ProductionPanel: React.FC<ProductionPanelProps> = ({
  sections,
  processingMode,
  settings,
  isGeneratingAll,
  progressInfo,
  isBackendOnline = false,
  onGenerateAll,
  onRegeneratePart,
  onBatchRegenerate,
  onJoinSection,
  latestAudioUrl,
  latestAudioTitle,
}) => {
  const [selectedParts, setSelectedParts] = useState<string[]>([]);
  const [activeSpeechKey, setActiveSpeechKey] = useState<string | null>(null);

  // Compute stats
  let totalParts = 0;
  let readyParts = 0;
  let missingParts = 0;

  sections.forEach((sec) => {
    sec.parts.forEach((p) => {
      totalParts++;
      if (p.status === 'ready' && p.audioUrl) {
        readyParts++;
      } else {
        missingParts++;
      }
    });
  });

  const sectionLabel = processingMode === 'scene' ? 'Escena' : 'Párrafo';

  // Toggle selection of a part: "secNum|partNum"
  const togglePartSelection = (key: string) => {
    setSelectedParts((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const handleSelectAll = () => {
    const allKeys: string[] = [];
    sections.forEach((sec) => {
      sec.parts.forEach((p) => {
        allKeys.push(`${sec.number}|${p.number}`);
      });
    });
    setSelectedParts(allKeys);
  };

  const handleClearSelection = () => {
    setSelectedParts([]);
  };

  const handleBatchRegen = async () => {
    if (selectedParts.length === 0) return;
    await onBatchRegenerate(selectedParts);
    setSelectedParts([]);
  };

  const handleSpeakVoice = (secNum: number, part: ScriptPart) => {
    const key = `${secNum}|${part.number}`;
    if (activeSpeechKey === key) {
      stopSpeaking();
      setActiveSpeechKey(null);
      return;
    }

    setActiveSpeechKey(key);
    speakText(part.text, {
      lang: settings.language,
      rate: settings.cfgWeight,
      pitch: settings.exaggeration,
      voiceName: settings.voiceName,
      onEnd: () => setActiveSpeechKey(null),
      onError: () => setActiveSpeechKey(null),
    });
  };

  const isBusy = isGeneratingAll || (progressInfo?.is_generating ?? false);

  return (
    <div className="space-y-5">
      <div className="text-xs font-bold uppercase tracking-wider text-[#d8dde5] flex items-center justify-between">
        <span className="flex items-center gap-2">
          <span>🎧 PRODUCCIÓN Y REVISIÓN</span>
          {isBackendOnline && (
            <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
              API Python Activa
            </span>
          )}
        </span>
        <span className="text-[11px] text-[#7f8996] font-mono">
          {sections.length} {sectionLabel.toLowerCase()}s &bull; {totalParts} partes
        </span>
      </div>

      {/* Main Generate Button */}
      <button
        type="button"
        disabled={isBusy || sections.length === 0}
        onClick={onGenerateAll}
        className={`w-full flex items-center justify-center gap-2 rounded-xl py-4 px-6 text-base font-bold tracking-wide transition-all shadow-lg ${
          isBusy
            ? 'bg-cyan-800 text-cyan-200 cursor-wait'
            : sections.length === 0
            ? 'bg-[#181d24] text-[#4f5865] cursor-not-allowed border border-[#252a31]'
            : 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-cyan-950/40 cursor-pointer active:scale-[0.99]'
        }`}
      >
        {isBusy ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin text-cyan-300" />
            <span>SINTETIZANDO EN BACKEND PYTHON (SECUENCIAL)...</span>
          </>
        ) : (
          <>
            <RotateCw className="h-5 w-5" />
            <span>🎙️ GENERAR NARRACIÓN COMPLETA</span>
          </>
        )}
      </button>

      {/* Real-time Progress Bar if generating */}
      {isBusy && progressInfo && (
        <div className="rounded-xl border border-cyan-500/30 bg-[#101722] p-4 space-y-2.5 animate-pulse">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-cyan-300 flex items-center gap-1.5">
              <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
              <span>{progressInfo.message || 'Procesando en segundo plano...'}</span>
            </span>
            <span className="font-mono text-cyan-400 font-bold">
              {progressInfo.total_steps > 0
                ? `${progressInfo.current_step} / ${progressInfo.total_steps} (${Math.round(
                    (progressInfo.current_step / progressInfo.total_steps) * 100
                  )}%)`
                : ''}
            </span>
          </div>
          {progressInfo.total_steps > 0 && (
            <div className="h-2 w-full rounded-full bg-[#1c2432] overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                style={{
                  width: `${Math.min(
                    100,
                    Math.round((progressInfo.current_step / progressInfo.total_steps) * 100)
                  )}%`,
                }}
              />
            </div>
          )}
          {progressInfo.errors && progressInfo.errors.length > 0 && (
            <div className="rounded bg-rose-950/40 border border-rose-800/40 p-2 text-xs text-rose-300">
              {progressInfo.errors.map((err, i) => (
                <div key={i}>⚠️ {err}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Master / Latest Audio Card */}
      <div className="rounded-xl border border-[#252a31] bg-[#12161b] p-4 space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-[#b5bcc7]">
          <span className="flex items-center gap-1.5">
            <Volume2 className="h-4 w-4 text-cyan-400" />
            <span>Último audio generado</span>
          </span>
          {latestAudioTitle && (
            <span className="text-[11px] text-cyan-300 font-mono truncate max-w-[240px]">
              {latestAudioTitle}
            </span>
          )}
        </div>

        {latestAudioUrl ? (
          <div className="space-y-2">
            <audio controls src={latestAudioUrl} className="w-full h-10 rounded" />
            <div className="flex justify-end">
              <a
                href={latestAudioUrl}
                download="cronicas_audio_generado.wav"
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#2d3542] bg-[#1a202a] px-3 py-1 text-xs text-[#b5bcc7] hover:text-white hover:bg-[#252e3c] transition-colors"
              >
                <Download className="h-3.5 w-3.5 text-cyan-400" />
                <span>Descargar WAV</span>
              </a>
            </div>
          </div>
        ) : (
          <div className="rounded-lg bg-[#0f1216] border border-[#20262f] p-3 text-xs text-[#7f8996] text-center italic">
            Ningún audio generado aún. Haz clic en &ldquo;Generar Narración Completa&rdquo; para comenzar.
          </div>
        )}
      </div>

      {/* Project Status Bar */}
      <div className="rounded-xl border border-[#252a31] bg-[#101419] p-4">
        <div className="text-xs font-semibold text-[#8d96a3] uppercase tracking-wider mb-2.5">
          Estado del Proyecto
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-[#151a20] border border-[#242b35] p-2.5 text-center">
            <div className="text-xs text-[#8d96a3]">{sectionLabel}s</div>
            <div className="text-xl font-bold text-white mt-0.5">{sections.length}</div>
          </div>
          <div className="rounded-lg bg-[#151a20] border border-[#242b35] p-2.5 text-center">
            <div className="text-xs text-emerald-400/80">Partes generadas</div>
            <div className="text-xl font-bold text-emerald-400 mt-0.5">
              {readyParts} / {totalParts}
            </div>
          </div>
          <div className="rounded-lg bg-[#151a20] border border-[#242b35] p-2.5 text-center">
            <div className="text-xs text-amber-400/80">Faltantes</div>
            <div className="text-xl font-bold text-amber-400 mt-0.5">{missingParts}</div>
          </div>
        </div>
      </div>

      {/* Global Batch Selection Toolbar */}
      <div className="rounded-xl border border-[#252a31] bg-[#101419] p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold text-[#d8dde5] flex items-center gap-1.5">
            <Layers className="h-4 w-4 text-cyan-400" />
            <span>Selección múltiple para regeneración</span>
          </div>
          <span className="text-xs text-[#7f8996] font-mono">
            {selectedParts.length} seleccionada(s)
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleSelectAll}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#292f37] bg-[#151a20] px-3 py-1.5 text-xs text-[#b5bcc7] hover:text-white hover:bg-[#1d232c] transition-colors"
          >
            <CheckSquare className="h-3.5 w-3.5 text-cyan-400" />
            <span>Seleccionar todas</span>
          </button>
          <button
            type="button"
            onClick={handleClearSelection}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#292f37] bg-[#151a20] px-3 py-1.5 text-xs text-[#8d96a3] hover:text-white hover:bg-[#1d232c] transition-colors"
          >
            <Square className="h-3.5 w-3.5 text-gray-400" />
            <span>Limpiar selección</span>
          </button>
          <button
            type="button"
            disabled={selectedParts.length === 0 || isBusy}
            onClick={handleBatchRegen}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ml-auto ${
              selectedParts.length === 0 || isBusy
                ? 'bg-[#1c222b] text-[#56606f] cursor-not-allowed border border-[#262d37]'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-sm'
            }`}
          >
            <RotateCw className="h-3.5 w-3.5" />
            <span>Regenerar seleccionadas ({selectedParts.length})</span>
          </button>
        </div>
      </div>

      {/* Sections List */}
      <div className="space-y-4">
        {sections.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[#252a31] p-8 text-center text-sm text-[#7f8996]">
            🟡 Todavía no hay secciones o párrafos cargados. Escribe tu guion a la izquierda para comenzar.
          </div>
        ) : (
          sections.map((section) => {
            const allPartsReady = section.parts.every((p) => p.status === 'ready' && p.audioUrl);

            return (
              <div
                key={section.number}
                className="rounded-xl border border-[#252a31] bg-[#101419] p-4 space-y-4"
              >
                {/* Section Header */}
                <div className="flex items-center justify-between border-b border-[#1f252e] pb-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-xs font-bold text-cyan-300">
                      {section.number}
                    </span>
                    <h3 className="text-sm font-bold text-white tracking-wide">
                      {sectionLabel} {section.number}
                      {section.title ? ` — ${section.title}` : ''}
                    </h3>
                  </div>
                  <span className="text-xs text-[#7f8996] font-mono">
                    {section.parts.length} parte(s)
                  </span>
                </div>

                {/* Section Parts */}
                <div className="space-y-3">
                  {section.parts.map((part) => {
                    const partKey = `${section.number}|${part.number}`;
                    const isSelected = selectedParts.includes(partKey);
                    const isSpeaking = activeSpeechKey === partKey;

                    return (
                      <div
                        key={part.number}
                        className={`rounded-lg border p-3 transition-colors ${
                          isSelected
                            ? 'border-cyan-500/60 bg-[#141b24]'
                            : 'border-[#242b34] bg-[#12161b]'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <label className="flex items-center gap-2 cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => togglePartSelection(partKey)}
                              className="rounded border-[#303844] bg-[#0c0e12] text-cyan-500 focus:ring-cyan-500 h-4 w-4"
                            />
                            <span className="text-xs font-bold text-cyan-300 font-mono">
                              Parte {String(part.number).padStart(2, '0')}
                            </span>
                          </label>

                          <div className="flex items-center gap-1.5">
                            {part.status === 'ready' ? (
                              <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                                <CheckCircle2 className="h-3.5 w-3.5" /> Audio listo
                              </span>
                            ) : part.status === 'generating' ? (
                              <span className="inline-flex items-center gap-1 text-[11px] text-cyan-400 font-medium animate-pulse">
                                <RotateCw className="h-3.5 w-3.5 animate-spin" /> Generando...
                              </span>
                            ) : part.status === 'error' ? (
                              <span className="inline-flex items-center gap-1 text-[11px] text-rose-400 font-medium">
                                <AlertCircle className="h-3.5 w-3.5" /> Error
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[11px] text-amber-400 font-medium">
                                <Clock className="h-3.5 w-3.5" /> Pendiente
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Text Chunk */}
                        <p className="text-xs text-[#b5bcc7] leading-relaxed mb-3 bg-[#0c0f13] border border-[#1e242c] p-2.5 rounded font-mono">
                          {part.text}
                        </p>

                        {/* Audio Player and Actions */}
                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 pt-1 border-t border-[#1d232c]">
                          {part.audioUrl ? (
                            <audio
                              controls
                              src={part.audioUrl}
                              className="h-8 flex-1 max-w-[280px] rounded opacity-90"
                            />
                          ) : (
                            <div className="text-[11px] text-[#7f8996] italic">
                              Audio aún no generado en disco
                            </div>
                          )}

                          <div className="flex items-center gap-1.5 justify-end">
                            <button
                              type="button"
                              onClick={() => handleSpeakVoice(section.number, part)}
                              title="Reproducir narración fonética en tiempo real"
                              className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-xs transition-colors ${
                                isSpeaking
                                  ? 'border-emerald-500 bg-emerald-950 text-emerald-200'
                                  : 'border-[#2d3542] bg-[#161c24] text-[#b5bcc7] hover:text-white hover:bg-[#202834]'
                              }`}
                            >
                              <Volume2 className="h-3 w-3" />
                              <span>{isSpeaking ? 'Detener' : 'Voz'}</span>
                            </button>

                            <button
                              type="button"
                              disabled={isBusy}
                              onClick={() => onRegeneratePart(section.number, part.number)}
                              title="Regenerar audio de esta parte con Chatterbox"
                              className="inline-flex items-center gap-1 rounded border border-[#2d3542] bg-[#161c24] px-2 py-1 text-xs text-[#b5bcc7] hover:text-white hover:bg-[#202834] transition-colors disabled:opacity-50"
                            >
                              <RotateCw className="h-3 w-3 text-cyan-400" />
                              <span>Regenerar</span>
                            </button>

                            {part.audioUrl && (
                              <a
                                href={part.audioUrl}
                                download={part.filename || `${sectionLabel.toLowerCase()}_${section.number}_parte_${part.number}.wav`}
                                title="Descargar WAV"
                                className="inline-flex items-center gap-1 rounded border border-[#2d3542] bg-[#161c24] px-2 py-1 text-xs text-[#8d96a3] hover:text-white hover:bg-[#202834] transition-colors"
                              >
                                <Download className="h-3 w-3 text-cyan-400" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Section Join Button and Master Output */}
                <div className="rounded-lg bg-[#14181f] border border-[#232932] p-3 space-y-2">
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
                    <button
                      type="button"
                      disabled={!allPartsReady || section.isJoining || isBusy}
                      onClick={() => onJoinSection(section.number)}
                      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-xs font-bold tracking-wide transition-all ${
                        !allPartsReady || isBusy
                          ? 'border border-[#262c36] bg-[#101318] text-[#555f6e] cursor-not-allowed'
                          : 'border border-cyan-500/40 bg-cyan-950/40 text-cyan-200 hover:bg-cyan-900/50 hover:border-cyan-400 active:scale-[0.99] cursor-pointer'
                      }`}
                    >
                      <LinkIcon className={`h-3.5 w-3.5 ${section.isJoining ? 'animate-spin' : ''}`} />
                      <span>
                        {section.isJoining
                          ? `UNIENDO ${sectionLabel.toUpperCase()}...`
                          : `🔗 UNIR ${sectionLabel.toUpperCase()} ${section.number}`}
                      </span>
                    </button>

                    {section.joinedAudioUrl && (
                      <span className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Audio final ensamblado ({section.joinedFilename || 'WAV'})
                      </span>
                    )}
                  </div>

                  {section.joinedAudioUrl && (
                    <div className="space-y-1.5 pt-2 border-t border-[#1d232c]">
                      <div className="flex items-center justify-between text-[11px] text-[#8d96a3]">
                        <span>Master ensamblado ({sectionLabel} {section.number}):</span>
                        <a
                          href={section.joinedAudioUrl}
                          download={section.joinedFilename || `${sectionLabel.toLowerCase()}_${section.number}_completa.wav`}
                          className="text-cyan-400 hover:underline flex items-center gap-1"
                        >
                          <Download className="h-3 w-3" /> Descargar WAV
                        </a>
                      </div>
                      <audio
                        controls
                        src={section.joinedAudioUrl}
                        className="w-full h-8 rounded"
                      />
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
