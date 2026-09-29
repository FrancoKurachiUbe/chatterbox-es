import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { VoiceManagerModal } from './components/VoiceManagerModal';
import {
  ProcessingMode,
  ScriptSection,
  StudioSettings,
} from './types';
import {
  DEFAULT_SCRIPT_SAMPLE,
  SUPPORTED_LANGUAGES,
} from './constants/languages';
import {
  apiService,
  BackendStatus,
  GenerationProgress,
  VoiceOption,
  ProjectSummary,
} from './services/api';
import {
  AlertTriangle,
  CheckCircle,
  Info,
  Terminal,
  Play,
  RotateCw,
  FastForward,
  Download,
  Share2,
  Trash2,
  Sliders,
  Scissors,
  Layers,
  StopCircle,
} from 'lucide-react';

export const App: React.FC = () => {
  const [processingMode, setProcessingMode] = useState<ProcessingMode>('scene');
  const [scriptText, setScriptText] = useState<string>(DEFAULT_SCRIPT_SAMPLE);
  const [settings, setSettings] = useState<StudioSettings>({
    language: 'es',
    voiceName: 'Brian Warm Clonacion Voz',
    refAudioUrl: '',
    refAudioName: 'Brian Warm Clonacion Voz.wav',
    exaggeration: 0.35,
    cfgWeight: 0.5,
    temperature: 0.55,
    seed: 737219296,
  });

  const [sections, setSections] = useState<any[]>([]);
  const [summary, setSummary] = useState<ProjectSummary>({
    mode: 'scene',
    mode_label: 'Escenas',
    total_sections: 0,
    total_parts: 0,
    ready_parts: 0,
    pending_parts: 0,
    errors_count: 0,
    percent: 0,
  });

  const [selectedParts, setSelectedParts] = useState<Set<string>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [masterAudioUrl, setMasterAudioUrl] = useState<string | null>(null);

  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);

  const [backendStatus, setBackendStatus] = useState<BackendStatus>({
    status: 'offline',
    device: 'desconocido',
    device_label: 'Comprobando conexión...',
    model_loaded: false,
    model_status: 'Iniciando',
    t3_model: 'v2',
    is_generating: false,
  });
  const [backendVoices, setBackendVoices] = useState<VoiceOption[]>([]);
  const [generationProgress, setGenerationProgress] = useState<GenerationProgress>({
    is_generating: false,
    current_step: 0,
    total_steps: 0,
    current_label: '',
    message: 'Inactivo',
    errors: [],
  });

  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showNotification = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification((curr) => (curr?.message === message ? null : curr));
    }, 4000);
  }, []);

  // 1. Comprobar estado del backend
  const checkBackendStatus = useCallback(async () => {
    try {
      const status = await apiService.checkStatus();
      setBackendStatus(status);
      return status;
    } catch {
      return null;
    }
  }, []);

  // 2. Cargar lista de voces
  const loadVoices = useCallback(async () => {
    try {
      const res = await apiService.getVoices();
      if (res && res.voices) {
        setBackendVoices(res.voices);
      }
    } catch {}
  }, []);

  // 3. Cargar proyecto desde el backend
  const loadProjectData = useCallback(async (mode: ProcessingMode) => {
    try {
      const res = await apiService.getProject(mode);
      if (res) {
        if (res.project) {
          if (res.project.last_script && res.project.last_script.trim()) {
            setScriptText(res.project.last_script);
          }
          if (res.project.settings) {
            const s = res.project.settings;
            setSettings((curr) => ({
              ...curr,
              language: s.language || curr.language,
              exaggeration: s.exaggeration ?? curr.exaggeration,
              temperature: s.temperature ?? curr.temperature,
              cfgWeight: s.cfg_weight ?? curr.cfgWeight,
              seed: s.seed ?? curr.seed,
              voiceName: s.voice_name || curr.voiceName,
            }));
          }
        }
        if (res.panel) {
          setSections(res.panel);
        }
        if (res.summary) {
          setSummary(res.summary);
        }
      }
    } catch {}
  }, []);

  // Polling de progreso
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    if (isGenerating) {
      interval = setInterval(async () => {
        const prog = await apiService.getProgress();
        setGenerationProgress(prog);
        if (!prog.is_generating) {
          setIsGenerating(false);
          loadProjectData(processingMode);
          showNotification(prog.message || 'Producción finalizada', 'success');
        }
      }, 1200);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isGenerating, processingMode, loadProjectData, showNotification]);

  // Inicialización
  useEffect(() => {
    checkBackendStatus();
    loadVoices();
    loadProjectData(processingMode);
  }, [checkBackendStatus, loadVoices, loadProjectData, processingMode]);

  // Autosave con debounce
  const triggerAutosave = useCallback(
    (textToSave: string, modeToSave: ProcessingMode, settingsToSave: StudioSettings) => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = setTimeout(async () => {
        if (!textToSave.trim()) return;
        try {
          await apiService.saveProject({
            text: textToSave,
            processing_mode: modeToSave,
            language: settingsToSave.language,
            voice_name: settingsToSave.voiceName,
            exaggeration: settingsToSave.exaggeration,
            temperature: settingsToSave.temperature,
            cfg_weight: settingsToSave.cfgWeight,
            seed: settingsToSave.seed,
          });
        } catch {}
      }, 900);
    },
    []
  );

  const handleScriptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setScriptText(val);
    triggerAutosave(val, processingMode, settings);
  };

  const handleModeChange = (mode: ProcessingMode) => {
    setProcessingMode(mode);
    loadProjectData(mode);
    triggerAutosave(scriptText, mode, settings);
  };

  const handleSettingChange = (field: keyof StudioSettings, val: any) => {
    const updated = { ...settings, [field]: val };
    setSettings(updated);
    triggerAutosave(scriptText, processingMode, updated);
  };

  // Optimizar en bloques de 250 chars
  const handleAutoSplit = () => {
    const rawText = scriptText.trim();
    if (!rawText) return;

    const paragraphs = rawText.split(/\n\s*\n/);
    const chunks: string[] = [];
    let counter = 1;

    for (const p of paragraphs) {
      const cleanP = p.replace(/^ESCENA\s+\d+[:\s—-]*/i, '').trim();
      if (!cleanP) continue;

      if (cleanP.length <= 250) {
        if (processingMode === 'scene') chunks.push(`ESCENA ${counter} — Escena ${counter}\n${cleanP}`);
        else chunks.push(cleanP);
        counter++;
      } else {
        const sentences = cleanP.match(/[^.!?;\n]+(?:[.!?;\n]+|$)/g) || [cleanP];
        let currentChunk = '';
        for (let s of sentences) {
          s = s.trim();
          if (!s) continue;
          if ((currentChunk + ' ' + s).trim().length <= 250) {
            currentChunk = (currentChunk + ' ' + s).trim();
          } else {
            if (currentChunk) {
              if (processingMode === 'scene') chunks.push(`ESCENA ${counter} — Parte ${counter}\n${currentChunk}`);
              else chunks.push(currentChunk);
              counter++;
            }
            currentChunk = s;
          }
        }
        if (currentChunk) {
          if (processingMode === 'scene') chunks.push(`ESCENA ${counter} — Parte ${counter}\n${currentChunk}`);
          else chunks.push(currentChunk);
          counter++;
        }
      }
    }

    const nextScript = chunks.join('\n\n');
    setScriptText(nextScript);
    triggerAutosave(nextScript, processingMode, settings);
    showNotification('Guion optimizado en bloques de ~250 caracteres', 'info');
  };

  // Iniciar Producción
  const handleGenerateAll = async () => {
    if (!scriptText.trim()) {
      showNotification('Introduce un guion antes de generar', 'error');
      return;
    }

    setIsGenerating(true);
    try {
      await apiService.startGeneration({
        text: scriptText,
        processing_mode: processingMode,
        language: settings.language,
        voice_name: settings.voiceName,
        exaggeration: settings.exaggeration,
        temperature: settings.temperature,
        cfg_weight: settings.cfgWeight,
        seed: settings.seed,
      });
      showNotification('Producción de audio iniciada en background', 'info');
    } catch (err: unknown) {
      setIsGenerating(false);
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error: ${msg}`, 'error');
    }
  };

  // Cancelar Producción
  const handleCancelGeneration = async () => {
    try {
      await apiService.cancelGeneration();
      showNotification('Petición de cancelación enviada', 'info');
    } catch {}
  };

  // Regenerar individual
  const handleRegeneratePart = async (secNum: number, partNum: number) => {
    showNotification(`Regenerando parte ${partNum}...`, 'info');
    try {
      await apiService.regeneratePart({
        processing_mode: processingMode,
        section_number: secNum,
        part_number: partNum,
        language: settings.language,
        exaggeration: settings.exaggeration,
        temperature: settings.temperature,
        cfg_weight: settings.cfgWeight,
        seed: settings.seed,
      });
      showNotification(`Parte ${partNum} regenerada con éxito`, 'success');
      loadProjectData(processingMode);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error: ${msg}`, 'error');
    }
  };

  // Regenerar desde aquí
  const handleRegenerateFromHere = async (secNum: number, partNum: number) => {
    if (!confirm(`¿Regenerar desde la sección ${secNum}, parte ${partNum} en adelante?`)) return;
    setIsGenerating(true);
    try {
      await apiService.regenerateFromHere({
        processing_mode: processingMode,
        section_number: secNum,
        part_number: partNum,
        language: settings.language,
        exaggeration: settings.exaggeration,
        temperature: settings.temperature,
        cfg_weight: settings.cfgWeight,
        seed: settings.seed,
      });
      showNotification('Regeneración secuencial iniciada', 'info');
    } catch (err: unknown) {
      setIsGenerating(false);
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error: ${msg}`, 'error');
    }
  };

  // Regenerar seleccionadas
  const handleRegenerateSelected = async () => {
    if (selectedParts.size === 0) return;
    const items = Array.from(selectedParts).map((k) => {
      const [s, p] = k.split('-');
      return [parseInt(s, 10), parseInt(p, 10)];
    });

    setIsGenerating(true);
    try {
      await apiService.regenerateBatch({
        selected_items: items,
        processing_mode: processingMode,
        language: settings.language,
        exaggeration: settings.exaggeration,
        temperature: settings.temperature,
        cfg_weight: settings.cfgWeight,
        seed: settings.seed,
      });
      setSelectedParts(new Set());
      showNotification(`Regenerando ${items.length} partes seleccionadas`, 'info');
    } catch (err: unknown) {
      setIsGenerating(false);
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error: ${msg}`, 'error');
    }
  };

  // Unir sección
  const handleJoinSection = async (secNum: number) => {
    showNotification(`Concatenando partes de la sección ${secNum}...`, 'info');
    try {
      const res = await apiService.joinSection({
        processing_mode: processingMode,
        section_number: secNum,
      });
      showNotification(`Sección unida: ${res.filename}`, 'success');
      loadProjectData(processingMode);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error: ${msg}`, 'error');
    }
  };

  // Unir todo
  const handleJoinAll = async () => {
    showNotification('Concatenando todas las partes en Master WAV...', 'info');
    try {
      const res = await apiService.joinAll({
        processing_mode: processingMode,
        section_number: 1,
      });
      setMasterAudioUrl(`${res.audio_url}?t=${Date.now()}`);
      showNotification('¡Audio Master completo creado!', 'success');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error al unir todo: ${msg}`, 'error');
    }
  };

  // Marcas de tiempo YouTube
  const handleCopyYouTube = () => {
    if (!sections || sections.length === 0) {
      showNotification('Genera o analiza un guion primero', 'info');
      return;
    }
    let output = '00:00 Introducción\n';
    let totalSecs = 0;
    sections.forEach((s, idx) => {
      if (idx === 0) return;
      totalSecs += 32;
      const m = Math.floor(totalSecs / 60).toString().padStart(2, '0');
      const sec = (totalSecs % 60).toString().padStart(2, '0');
      output += `${m}:${sec} ${s.title || (processingMode === 'scene' ? 'Escena ' : 'Párrafo ') + s.number}\n`;
    });
    navigator.clipboard.writeText(output);
    showNotification('Marcas de tiempo copiadas al portapapeles', 'success');
  };

  const toggleSelectPart = (secNum: number, partNum: number) => {
    const key = `${secNum}-${partNum}`;
    setSelectedParts((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Cálculos de estadísticas del texto
  const wordsCount = scriptText.trim() ? scriptText.trim().split(/\s+/).length : 0;
  const charsCount = scriptText.length;

  return (
    <div className="min-h-screen bg-[#080a0f] text-[#f8fafc] flex flex-col font-sans selection:bg-cyan-500/30 selection:text-white">
      {/* Header */}
      <Header
        backendStatus={backendStatus}
        onRefreshStatus={checkBackendStatus}
        onOpenVoiceManager={() => setIsVoiceModalOpen(true)}
      />

      {/* Toast Notification */}
      {notification && (
        <div className="fixed top-5 right-5 z-50 max-w-md animate-in slide-in-from-top-2">
          <div
            className={`flex items-center gap-2.5 rounded-xl border px-4 py-3 text-sm shadow-2xl backdrop-blur-md ${
              notification.type === 'success'
                ? 'border-emerald-500/40 bg-[#0c1815] text-emerald-200'
                : notification.type === 'error'
                ? 'border-rose-500/40 bg-[#1d0d12] text-rose-200'
                : 'border-cyan-500/40 bg-[#0a1520] text-cyan-200'
            }`}
          >
            {notification.type === 'success' ? (
              <CheckCircle className="h-4 w-4 shrink-0 text-emerald-400" />
            ) : notification.type === 'error' ? (
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
            ) : (
              <Info className="h-4 w-4 shrink-0 text-cyan-400" />
            )}
            <span>{notification.message}</span>
          </div>
        </div>
      )}

      {/* Main Studio Container */}
      <main className="flex-1 max-w-[1400px] w-full mx-auto p-4 sm:p-6 space-y-4">
        {/* 1. EDITOR FULL-WIDTH */}
        <div className="rounded-xl border border-[#1b2333] bg-[#121722] p-4 sm:p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <span className="text-cyan-400">📝</span> 1. Editor de Guion Full-Width
            </span>
            <button
              type="button"
              onClick={handleAutoSplit}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-3 py-1.5 text-xs font-semibold text-white transition-all"
            >
              <Scissors className="h-3.5 w-3.5 text-cyan-400" />
              <span>Optimizar en Bloques (~250 chars)</span>
            </button>
          </div>

          <textarea
            value={scriptText}
            onChange={handleScriptChange}
            placeholder="Escribe o pega aquí tu guion..."
            rows={7}
            className="w-full rounded-lg border border-[#1b2333] bg-[#090c12] p-3 text-sm text-[#f8fafc] leading-relaxed outline-none focus:border-cyan-500 transition-all font-sans"
          />

          <div className="flex flex-wrap items-center justify-between text-xs text-[#64748b] font-mono">
            <div className="flex items-center gap-4">
              <span>{charsCount} caracteres</span>
              <span>&bull;</span>
              <span>{wordsCount} palabras</span>
              <span>&bull;</span>
              <span>
                {summary.total_sections} {processingMode === 'scene' ? 'escenas' : 'párrafos'}
              </span>
            </div>
            <span className="text-emerald-400 font-sans font-medium">💾 Autosave activo</span>
          </div>
        </div>

        {/* 2. MODO, IDIOMA, VOZ Y PARÁMETROS */}
        <div className="rounded-xl border border-[#1b2333] bg-[#121722] p-4 sm:p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <span className="text-cyan-400">⚙️</span> 2. Modo de Trabajo, Voz y Parámetros
            </span>
            <button
              type="button"
              onClick={() => {
                setSettings({
                  language: 'es',
                  voiceName: 'Brian Warm Clonacion Voz',
                  refAudioUrl: '',
                  refAudioName: 'Brian Warm Clonacion Voz.wav',
                  exaggeration: 0.35,
                  cfgWeight: 0.5,
                  temperature: 0.55,
                  seed: 737219296,
                });
                showNotification('Valores predeterminados restaurados', 'info');
              }}
              className="text-xs text-[#94a3b8] hover:text-white underline cursor-pointer"
            >
              Restaurar Parámetros Recomendados
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            {/* Modo de Trabajo */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#94a3b8]">
                Modo de Trabajo
              </label>
              <div className="flex rounded-lg border border-[#1b2333] bg-[#090c12] p-1 gap-1">
                <button
                  type="button"
                  onClick={() => handleModeChange('paragraph')}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${
                    processingMode === 'paragraph' ? 'bg-[#182233] text-white' : 'text-[#64748b] hover:text-white'
                  }`}
                >
                  📄 Párrafos
                </button>
                <button
                  type="button"
                  onClick={() => handleModeChange('scene')}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${
                    processingMode === 'scene'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-[#64748b] hover:text-white'
                  }`}
                >
                  🎬 Escenas
                </button>
              </div>
            </div>

            {/* Idioma */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#94a3b8]">
                Idioma
              </label>
              <select
                value={settings.language}
                onChange={(e) => handleSettingChange('language', e.target.value)}
                className="w-full rounded-lg border border-[#1b2333] bg-[#090c12] px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
              >
                <option value="es">Español (es)</option>
                <option value="en">Inglés (en)</option>
                <option value="fr">Francés (fr)</option>
                <option value="de">Alemán (de)</option>
                <option value="it">Italiano (it)</option>
                <option value="pt">Portugués (pt)</option>
              </select>
            </div>

            {/* Voz */}
            <div className="space-y-1.5 md:col-span-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold uppercase tracking-wider text-[#94a3b8]">
                  Voz de Referencia (WAV)
                </label>
                <button
                  type="button"
                  onClick={() => setIsVoiceModalOpen(true)}
                  className="text-[11px] text-cyan-400 hover:underline"
                >
                  + Administrar voces
                </button>
              </div>
              <div className="flex gap-2">
                <select
                  value={settings.voiceName}
                  onChange={(e) => handleSettingChange('voiceName', e.target.value)}
                  className="flex-1 rounded-lg border border-[#1b2333] bg-[#090c12] px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
                >
                  {backendVoices.map((v) => (
                    <option key={v.name} value={v.name}>
                      {v.name} {v.is_default ? '(Principal)' : ''}
                    </option>
                  ))}
                  {backendVoices.length === 0 && (
                    <option value="Brian Warm Clonacion Voz">Brian Warm Clonacion Voz (Predeterminada)</option>
                  )}
                </select>
                <button
                  type="button"
                  onClick={() => {
                    const audio = new Audio(`/api/voices/${encodeURIComponent(settings.voiceName)}.wav/preview?t=${Date.now()}`);
                    audio.play().catch(() => showNotification('No se pudo reproducir la muestra de voz', 'info'));
                  }}
                  className="rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-3 py-2 text-xs text-white"
                  title="Reproducir voz"
                >
                  <Play className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Sliders de Parámetros */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2 border-t border-[#1b2333]">
            {/* Exaggeration */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-[#94a3b8]">
                <span>Énfasis / Exaggeration</span>
                <span className="font-mono text-cyan-400">{settings.exaggeration.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.01"
                value={settings.exaggeration}
                onChange={(e) => handleSettingChange('exaggeration', parseFloat(e.target.value))}
                className="w-full accent-cyan-400 h-1 bg-[#1b2333] rounded"
              />
            </div>

            {/* Temperature */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-[#94a3b8]">
                <span>Temperatura</span>
                <span className="font-mono text-cyan-400">{settings.temperature.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.01"
                value={settings.temperature}
                onChange={(e) => handleSettingChange('temperature', parseFloat(e.target.value))}
                className="w-full accent-cyan-400 h-1 bg-[#1b2333] rounded"
              />
            </div>

            {/* CFG Weight */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-[#94a3b8]">
                <span>CFG Weight</span>
                <span className="font-mono text-cyan-400">{settings.cfgWeight.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={settings.cfgWeight}
                onChange={(e) => handleSettingChange('cfgWeight', parseFloat(e.target.value))}
                className="w-full accent-cyan-400 h-1 bg-[#1b2333] rounded"
              />
            </div>

            {/* Seed Fijo */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-[#94a3b8]">
                <span>Seed (Fijo)</span>
                <button
                  type="button"
                  onClick={() => handleSettingChange('seed', Math.floor(Math.random() * 1000000000))}
                  className="text-[10px] text-cyan-400 hover:underline"
                >
                  🎲 Aleatorio
                </button>
              </div>
              <input
                type="number"
                value={settings.seed}
                onChange={(e) => handleSettingChange('seed', parseInt(e.target.value, 10) || 0)}
                className="w-full rounded-lg border border-[#1b2333] bg-[#090c12] px-2 py-1 text-xs text-white font-mono outline-none focus:border-cyan-500"
              />
            </div>
          </div>
        </div>

        {/* 3. ACCIÓN PRINCIPAL: GENERAR AUDIO */}
        <div className="flex gap-3">
          <button
            type="button"
            disabled={isGenerating}
            onClick={handleGenerateAll}
            className="flex-1 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-slate-950 font-extrabold text-sm sm:text-base py-3.5 shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
          >
            <Play className="h-5 w-5 fill-current" />
            <span>{isGenerating ? 'GENERANDO AUDIO EN BACKGROUND...' : '🎙️ GENERAR AUDIO'}</span>
          </button>

          {isGenerating && (
            <button
              type="button"
              onClick={handleCancelGeneration}
              className="rounded-xl border border-rose-500/40 bg-rose-950/40 hover:bg-rose-900/40 text-rose-300 font-bold text-xs sm:text-sm px-5 py-3.5 transition-all flex items-center gap-2 cursor-pointer"
            >
              <StopCircle className="h-4 w-4" />
              <span>Cancelar</span>
            </button>
          )}
        </div>

        {/* 4. RESUMEN DE MÉTRICAS */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          <div className="rounded-lg border border-[#1b2333] bg-[#0e121a] p-3 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
              {processingMode === 'scene' ? 'Escenas' : 'Párrafos'}
            </span>
            <div className="text-xl font-extrabold text-white font-mono">{summary.total_sections}</div>
          </div>
          <div className="rounded-lg border border-[#1b2333] bg-[#0e121a] p-3 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
              Partes Totales
            </span>
            <div className="text-xl font-extrabold text-white font-mono">{summary.total_parts}</div>
          </div>
          <div className="rounded-lg border border-[#1b2333] bg-[#0e121a] p-3 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
              Generadas
            </span>
            <div className="text-xl font-extrabold text-emerald-400 font-mono">{summary.ready_parts}</div>
          </div>
          <div className="rounded-lg border border-[#1b2333] bg-[#0e121a] p-3 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
              Pendientes
            </span>
            <div className="text-xl font-extrabold text-amber-400 font-mono">{summary.pending_parts}</div>
          </div>
          <div className="rounded-lg border border-[#1b2333] bg-[#0e121a] p-3 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
              Errores
            </span>
            <div className="text-xl font-extrabold text-rose-400 font-mono">{summary.errors_count}</div>
          </div>
          <div className="rounded-lg border border-[#1b2333] bg-[#0e121a] p-3 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
              Progreso
            </span>
            <div className="text-xl font-extrabold text-cyan-400 font-mono">{summary.percent}%</div>
          </div>
        </div>

        {/* Barra de progreso de generación */}
        {isGenerating && (
          <div className="rounded-lg border border-[#1b2333] bg-[#090c12] p-3 space-y-2">
            <div className="flex justify-between text-xs font-semibold">
              <span>{generationProgress.message || `Generando: ${generationProgress.current_label}`}</span>
              <span className="font-mono text-cyan-400">
                {generationProgress.total_steps > 0
                  ? Math.round((generationProgress.current_step / generationProgress.total_steps) * 100)
                  : 5}
                %
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-[#1b2333] overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-300"
                style={{
                  width: `${
                    generationProgress.total_steps > 0
                      ? Math.round((generationProgress.current_step / generationProgress.total_steps) * 100)
                      : 5
                  }%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Master Audio Banner */}
        {masterAudioUrl && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 rounded-xl border border-cyan-500/40 bg-gradient-to-r from-cyan-950/40 to-emerald-950/20 p-4 shadow-xl">
            <div>
              <div className="text-sm font-bold text-cyan-300">🏆 AUDIO COMPLETO UNIDO (MASTER WAV)</div>
              <div className="text-xs text-[#94a3b8]">Narración completa lista para YouTube</div>
            </div>
            <audio controls src={masterAudioUrl} className="flex-1 max-w-md h-8 outline-none" />
            <a
              href={masterAudioUrl}
              download="Master_Chatterbox_Prime.wav"
              className="rounded-lg bg-cyan-600 hover:bg-cyan-500 px-4 py-2 text-xs font-bold text-white transition-all whitespace-nowrap"
            >
              ⬇️ Descargar WAV
            </a>
          </div>
        )}

        {/* 5. PANEL DE PRODUCCIÓN */}
        <div className="rounded-xl border border-[#1b2333] bg-[#121722] p-4 sm:p-5 shadow-xl space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1b2333] pb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <span className="text-cyan-400">📑</span> Línea de Producción y Control de Audio
            </span>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={selectedParts.size === 0 || isGenerating}
                onClick={handleRegenerateSelected}
                className="rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-3 py-1.5 text-xs font-semibold text-white transition-all disabled:opacity-40"
              >
                🔄 Regenerar seleccionadas ({selectedParts.size})
              </button>
              <button
                type="button"
                onClick={handleJoinAll}
                className="rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-3 py-1.5 text-xs font-semibold text-cyan-300 transition-all"
              >
                🔗 Unir Todo (Master WAV)
              </button>
              <button
                type="button"
                onClick={handleCopyYouTube}
                className="rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-3 py-1.5 text-xs font-semibold text-[#94a3b8] hover:text-white transition-all"
              >
                📋 Marcas YouTube
              </button>
              <button
                type="button"
                onClick={() => loadProjectData(processingMode)}
                className="rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-2.5 py-1.5 text-xs text-[#94a3b8] hover:text-white"
              >
                <RotateCw className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Listado de secciones */}
          <div className="space-y-4">
            {sections.length === 0 ? (
              <div className="text-center py-12 text-sm text-[#64748b]">
                Pega tu guion arriba y pulsa <b>"GENERAR AUDIO"</b> para iniciar la producción.
              </div>
            ) : (
              sections.map((sec) => {
                const secLabel = processingMode === 'scene' ? 'Escena' : 'Párrafo';
                return (
                  <div key={sec.number} className="rounded-xl border border-[#1b2333] bg-[#0c1017] overflow-hidden">
                    {/* Header de sección */}
                    <div className="flex items-center justify-between bg-[#101622] px-4 py-3 border-b border-[#182233]">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">
                          {processingMode === 'scene' ? '🎬' : '📄'} {sec.title || `${secLabel} ${sec.number}`}
                        </span>
                        <span className="text-xs text-[#64748b]">({sec.parts.length} partes)</span>
                      </div>

                      <div className="flex items-center gap-2">
                        {sec.has_joined && (
                          <div className="flex items-center gap-2">
                            <audio controls src={`${sec.joined_audio_url}?t=${Date.now()}`} className="h-7 w-40" />
                            <a
                              href={sec.joined_audio_url}
                              download={sec.joined_filename}
                              className="rounded bg-[#141c28] hover:bg-[#1b2536] px-2 py-1 text-xs text-cyan-300 border border-[#1b2333]"
                            >
                              ⬇️ WAV
                            </a>
                          </div>
                        )}
                        <button
                          type="button"
                          onClick={() => handleJoinSection(sec.number)}
                          className="rounded-lg border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-3 py-1.5 text-xs font-semibold text-white"
                        >
                          🔗 Unir {secLabel}
                        </button>
                      </div>
                    </div>

                    {/* Partes de la sección */}
                    <div className="p-3 space-y-2">
                      {sec.parts.map((p: any) => {
                        const isChecked = selectedParts.has(`${sec.number}-${p.number}`);
                        return (
                          <div
                            key={p.number}
                            className={`flex flex-col md:flex-row items-start md:items-center justify-between gap-3 rounded-lg border border-[#182233] bg-[#0f141f] p-3 transition-all ${
                              p.has_audio ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-[#1b2333]'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => toggleSelectPart(sec.number, p.number)}
                                className="cursor-pointer"
                              />
                              <div>
                                <div className="text-xs font-bold text-white flex items-center gap-2">
                                  <span>
                                    {secLabel} {sec.number} &bull; Parte {p.number}
                                  </span>
                                  <span
                                    className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                                      p.has_audio
                                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                        : 'bg-[#182233] text-[#64748b]'
                                    }`}
                                  >
                                    {p.has_audio ? 'Listo' : 'Pendiente'}
                                  </span>
                                  <span className="text-[10px] text-[#64748b] font-mono">
                                    {(p.text || '').length} chars
                                  </span>
                                </div>
                                <div
                                  className="text-xs text-[#94a3b8] mt-1 line-clamp-2 max-w-xl"
                                  title={p.text}
                                >
                                  {p.text}
                                </div>
                              </div>
                            </div>

                            {/* Player & Actions */}
                            <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                              {p.has_audio ? (
                                <audio controls src={`${p.audio_url}?t=${Date.now()}`} className="h-7 w-48" />
                              ) : (
                                <span className="text-[11px] text-[#64748b]">Sin audio aún</span>
                              )}

                              <button
                                type="button"
                                onClick={() => handleRegeneratePart(sec.number, p.number)}
                                className="rounded border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-2.5 py-1 text-xs font-semibold text-white whitespace-nowrap"
                              >
                                {p.has_audio ? '🔄 Regenerar' : '🎙️ Generar'}
                              </button>

                              <button
                                type="button"
                                onClick={() => handleRegenerateFromHere(sec.number, p.number)}
                                title="Regenerar desde esta parte hacia adelante"
                                className="rounded border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] px-2 py-1 text-xs text-[#94a3b8] hover:text-white"
                              >
                                <FastForward className="h-3.5 w-3.5" />
                              </button>

                              {p.has_audio && (
                                <a
                                  href={p.audio_url}
                                  download={p.filename}
                                  className="rounded border border-[#1b2333] bg-[#141c28] hover:bg-[#1b2536] p-1 text-[#94a3b8] hover:text-white"
                                  title="Descargar parte WAV"
                                >
                                  <Download className="h-3.5 w-3.5" />
                                </a>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </main>

      {/* Voice Manager Modal */}
      <VoiceManagerModal
        isOpen={isVoiceModalOpen}
        voices={backendVoices}
        onClose={() => setIsVoiceModalOpen(false)}
        onVoicesUpdated={() => {
          loadVoices();
          loadProjectData(processingMode);
        }}
      />
    </div>
  );
};
