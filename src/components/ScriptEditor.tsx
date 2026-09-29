import React from 'react';
import { ProcessingMode } from '../types';
import { FileText, Clapperboard, HelpCircle, RotateCcw } from 'lucide-react';
import { DEFAULT_SCRIPT_SAMPLE } from '../constants/languages';

interface ScriptEditorProps {
  processingMode: ProcessingMode;
  onModeChange: (mode: ProcessingMode) => void;
  scriptText: string;
  onScriptChange: (text: string) => void;
  onLoadSample: () => void;
}

export const ScriptEditor: React.FC<ScriptEditorProps> = ({
  processingMode,
  onModeChange,
  scriptText,
  onScriptChange,
  onLoadSample,
}) => {
  const lineCount = scriptText ? scriptText.split('\n').length : 0;
  const charCount = scriptText ? scriptText.length : 0;

  return (
    <div className="space-y-4">
      {/* Processing Mode selector */}
      <div>
        <div className="text-xs font-bold uppercase tracking-wider text-[#d8dde5] mb-2 flex items-center gap-2">
          <span>🎬 MODO DE PROCESAMIENTO</span>
        </div>
        <div className="rounded-xl border border-[#252a31] bg-[#12161b] p-3.5">
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => onModeChange('paragraph')}
              className={`flex items-center gap-2.5 rounded-lg border px-3.5 py-2.5 text-left text-sm font-medium transition-all ${
                processingMode === 'paragraph'
                  ? 'border-cyan-500 bg-cyan-950/30 text-cyan-200 shadow-sm'
                  : 'border-[#292f37] bg-[#0f1216] text-[#8d96a3] hover:border-[#3a434f] hover:text-[#d8dde5]'
              }`}
            >
              <FileText className="h-4 w-4 shrink-0 text-cyan-400" />
              <div>
                <div className="font-semibold text-white">Por párrafos</div>
                <div className="text-[11px] text-[#7f8996]">Usa líneas en blanco</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => onModeChange('scene')}
              className={`flex items-center gap-2.5 rounded-lg border px-3.5 py-2.5 text-left text-sm font-medium transition-all ${
                processingMode === 'scene'
                  ? 'border-cyan-500 bg-cyan-950/30 text-cyan-200 shadow-sm'
                  : 'border-[#292f37] bg-[#0f1216] text-[#8d96a3] hover:border-[#3a434f] hover:text-[#d8dde5]'
              }`}
            >
              <Clapperboard className="h-4 w-4 shrink-0 text-amber-400" />
              <div>
                <div className="font-semibold text-white">Por escenas</div>
                <div className="text-[11px] text-[#7f8996]">Usa ESCENA 1 — Título</div>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Script Box */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs font-bold uppercase tracking-wider text-[#d8dde5]">
            📝 GUION
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onLoadSample}
              className="inline-flex items-center gap-1 rounded bg-[#1c222b] hover:bg-[#252d3a] border border-[#2d3542] px-2 py-0.5 text-[11px] text-[#8d96a3] hover:text-white transition-colors"
            >
              <RotateCcw className="h-3 w-3" /> Cargar ejemplo
            </button>
            <span className="text-[11px] font-mono text-[#7f8996]">
              {charCount} caracteres &bull; {lineCount} líneas
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-[#252a31] bg-[#12161b] p-4 space-y-3">
          <textarea
            value={scriptText}
            onChange={(e) => onScriptChange(e.target.value)}
            rows={14}
            placeholder={
              processingMode === 'scene'
                ? "ESCENA 1 — Título de la escena\nEscribe aquí el relato narrativo...\n\nESCENA 2 — La continuación\nSiguiente fragmento de la historia..."
                : "Pega aquí el guion.\nSepara cada párrafo con una línea en blanco."
            }
            className="w-full rounded-lg border border-[#292f37] bg-[#0f1216] p-3 text-sm text-[#e7eaf0] placeholder-[#4f5865] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono leading-relaxed"
          />

          <div className="rounded-lg bg-[#0f1216] border border-[#20262f] p-3 text-xs text-[#8d96a3] space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-[#b5bcc7]">
              <HelpCircle className="h-3.5 w-3.5 text-cyan-400" />
              <span>Instrucciones de formato:</span>
            </div>
            {processingMode === 'paragraph' ? (
              <p>
                <strong>Por párrafos:</strong> Separa cada párrafo con una o más líneas en blanco. Cada párrafo se procesará y segmentará en partes de hasta 250 caracteres respetando los signos de puntuación.
              </p>
            ) : (
              <p>
                <strong>Por escenas:</strong> Usa el formato <code>ESCENA 1 — Título</code>. El título organiza el proyecto en la mesa de producción y los números se normalizan automáticamente a texto fonético.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
