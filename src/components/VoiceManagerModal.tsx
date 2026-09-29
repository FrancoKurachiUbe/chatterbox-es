import React, { useState } from 'react';
import { VoiceOption, apiService } from '../services/api';
import { X, Upload, Trash2, Play, Mic, Check } from 'lucide-react';

interface VoiceManagerModalProps {
  isOpen: boolean;
  voices: VoiceOption[];
  onClose: () => void;
  onVoicesUpdated: () => void;
}

export const VoiceManagerModal: React.FC<VoiceManagerModalProps> = ({
  isOpen,
  voices,
  onClose,
  onVoicesUpdated,
}) => {
  const [voiceName, setVoiceName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      if (!voiceName.trim()) {
        const clean = e.target.files[0].name.replace(/\.[^/.]+$/, '');
        setVoiceName(clean);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Por favor selecciona un archivo WAV.');
      return;
    }
    setIsUploading(true);
    try {
      await apiService.uploadVoice(selectedFile, voiceName.trim() || undefined);
      setSelectedFile(null);
      setVoiceName('');
      onVoicesUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Error al subir voz: ${msg}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`¿Eliminar la voz "${name}" de la carpeta voices/?`)) return;
    try {
      await apiService.deleteVoice(name);
      onVoicesUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Error al eliminar: ${msg}`);
    }
  };

  const handlePlayPreview = (name: string) => {
    setPlayingVoice(name);
    const audio = new Audio(`/api/voices/${encodeURIComponent(name)}.wav/preview?t=${Date.now()}`);
    audio.onended = () => setPlayingVoice(null);
    audio.onerror = () => setPlayingVoice(null);
    audio.play().catch(() => setPlayingVoice(null));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="w-full max-w-lg rounded-2xl border border-[#1b2333] bg-[#0f141f] p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between border-b border-[#1b2333] pb-3">
          <div className="flex items-center gap-2">
            <Mic className="h-5 w-5 text-cyan-400" />
            <h2 className="text-base font-bold text-white">Administrar Voces de Referencia (WAV)</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#94a3b8] hover:bg-[#182233] hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Upload Form */}
        <div className="rounded-xl border border-[#1b2333] bg-[#090c12] p-4 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
            ➕ Agregar Nueva Voz
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Nombre de la voz (ej: Brian)"
              value={voiceName}
              onChange={(e) => setVoiceName(e.target.value)}
              className="rounded-lg border border-[#1b2333] bg-[#121722] px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
            />
            <input
              type="file"
              accept=".wav,audio/wav"
              onChange={handleFileChange}
              className="rounded-lg border border-[#1b2333] bg-[#121722] px-3 py-1.5 text-xs text-[#94a3b8] file:mr-2 file:rounded file:border-0 file:bg-cyan-500/20 file:px-2 file:py-1 file:text-xs file:font-semibold file:text-cyan-300"
            />
          </div>
          <button
            type="button"
            disabled={!selectedFile || isUploading}
            onClick={handleUpload}
            className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 py-2 text-xs font-bold text-white transition-all disabled:opacity-40"
          >
            <Upload className="h-3.5 w-3.5" />
            <span>{isUploading ? 'Guardando en voices/...' : 'Subir y Guardar en voices/'}</span>
          </button>
        </div>

        {/* Voice List */}
        <div className="space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-[#64748b]">
            Voces Registradas ({voices.length})
          </span>
          <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
            {voices.length === 0 ? (
              <p className="text-center py-6 text-xs text-[#64748b]">
                No hay archivos WAV registrados en la carpeta voices/.
              </p>
            ) : (
              voices.map((v) => (
                <div
                  key={v.name}
                  className="flex items-center justify-between rounded-lg border border-[#1b2333] bg-[#141c28] px-3.5 py-2.5"
                >
                  <div>
                    <div className="text-xs font-bold text-white flex items-center gap-1.5">
                      <span>{v.name}</span>
                      {v.is_default && (
                        <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-1.5 py-0.5 rounded">
                          Principal
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-[#64748b] font-mono">
                      {v.size_kb} KB &bull; {v.filename}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handlePlayPreview(v.name)}
                      className={`rounded-lg p-1.5 border border-[#1b2333] hover:border-cyan-500 text-xs ${
                        playingVoice === v.name ? 'bg-cyan-500 text-black' : 'bg-[#0e121a] text-white'
                      }`}
                      title="Reproducir muestra"
                    >
                      <Play className="h-3 w-3" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(v.name)}
                      className="rounded-lg p-1.5 border border-[#1b2333] hover:border-rose-500 hover:text-rose-400 bg-[#0e121a] text-[#64748b]"
                      title="Eliminar voz"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
