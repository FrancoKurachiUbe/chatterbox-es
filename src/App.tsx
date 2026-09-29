import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { ScriptEditor } from './components/ScriptEditor';
import { VoiceSettings } from './components/VoiceSettings';
import { ProductionPanel } from './components/ProductionPanel';
import {
  ProcessingMode,
  ScriptSection,
  StudioSettings,
} from './types';
import {
  DEFAULT_SCRIPT_SAMPLE,
  SUPPORTED_LANGUAGES,
  PRESET_VOICES,
} from './constants/languages';
import { buildProjectStructure } from './utils/scriptParser';
import {
  apiService,
  BackendStatus,
  GenerationProgress,
  VoiceOption,
} from './services/api';
import {
  synthesizePartAudio,
  concatenateAudioBlobs,
} from './utils/audioEngine';
import { AlertTriangle, CheckCircle, Info, Terminal, Cpu } from 'lucide-react';

export const App: React.FC = () => {
  const [processingMode, setProcessingMode] = useState<ProcessingMode>('scene');
  const [scriptText, setScriptText] = useState<string>(DEFAULT_SCRIPT_SAMPLE);
  const [settings, setSettings] = useState<StudioSettings>({
    language: 'es',
    voiceName: PRESET_VOICES[0].id,
    refAudioUrl: SUPPORTED_LANGUAGES['es'].audioPromptUrl,
    refAudioName: 'es_prompt.flac',
    exaggeration: 0.35,
    cfgWeight: 0.5,
    temperature: 0.55,
    seed: 737219296,
  });

  const [sections, setSections] = useState<ScriptSection[]>([]);
  const [parseError, setParseError] = useState<string | null>(null);
  const [isGeneratingAll, setIsGeneratingAll] = useState(false);
  const [latestAudioUrl, setLatestAudioUrl] = useState<string | undefined>();
  const [latestAudioTitle, setLatestAudioTitle] = useState<string | undefined>();
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);

  // Estado del backend Python
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

  const isGeneratingRef = useRef(false);

  const showNotification = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification((curr) => (curr?.message === message ? null : curr));
    }, 5000);
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

  // 2. Cargar proyecto desde el backend Python si existe
  const loadProjectFromBackend = useCallback(async (mode: ProcessingMode) => {
    try {
      const res = await apiService.getProject(mode);
      if (res && res.project) {
        if (res.project.last_script && res.project.last_script.trim()) {
          setScriptText(res.project.last_script);
        }
        if (res.project.processing_mode) {
          setProcessingMode(res.project.processing_mode);
        }
        if (res.project.settings) {
          setSettings((prev) => ({
            ...prev,
            language: res.project.settings.language || prev.language,
            refAudioUrl: res.project.settings.audio_prompt_path || prev.refAudioUrl,
            exaggeration: res.project.settings.exaggeration ?? prev.exaggeration,
            temperature: res.project.settings.temperature ?? prev.temperature,
            cfgWeight: res.project.settings.cfg_weight ?? prev.cfgWeight,
            seed: res.project.settings.seed ?? prev.seed,
          }));
        }
      }

      // Si el backend devuelve panel con archivos ya generados
      if (res && Array.isArray(res.panel) && res.panel.length > 0) {
        setSections(
          res.panel.map((sec: any) => ({
            number: sec.number,
            title: sec.title || '',
            text: '',
            normalizedText: '',
            joinedAudioUrl: sec.final_audio_url || undefined,
            joinedFilename: sec.final_filename || undefined,
            parts: (sec.parts || []).map((p: any) => ({
              number: p.number,
              text: p.text,
              filename: p.filename,
              audioUrl: p.audio_url || undefined,
              status: p.exists ? 'ready' : 'pending',
            })),
          }))
        );
      }
    } catch (err) {
      console.warn('No se pudo sincronizar proyecto inicial con backend:', err);
    }
  }, []);

  // Inicialización
  useEffect(() => {
    let mounted = true;

    async function init() {
      const status = await checkBackendStatus();
      if (!mounted) return;

      if (status && status.status === 'online') {
        // Cargar voces del backend
        const vData = await apiService.getVoices();
        if (mounted && vData.voices && vData.voices.length > 0) {
          setBackendVoices(vData.voices);
        }
        // Cargar proyecto
        await loadProjectFromBackend(processingMode);
      }
    }

    init();

    // Intervalo de comprobación de backend cada 4s
    const statusInterval = setInterval(() => {
      checkBackendStatus();
    }, 4000);

    return () => {
      mounted = false;
      clearInterval(statusInterval);
    };
  }, [checkBackendStatus, loadProjectFromBackend, processingMode]);

  // Polling de progreso de generación cuando está activo
  useEffect(() => {
    let interval: any = null;

    if (backendStatus.status === 'online') {
      interval = setInterval(async () => {
        try {
          const prog = await apiService.getProgress();
          setGenerationProgress(prog);

          if (isGeneratingRef.current && !prog.is_generating) {
            // Terminó la generación en segundo plano
            isGeneratingRef.current = false;
            setIsGeneratingAll(false);
            showNotification(prog.message || 'Generación completada en backend', 'success');

            // Recargar datos actualizados del proyecto
            await loadProjectFromBackend(processingMode);

            if (prog.last_generated) {
              setLatestAudioUrl(apiService.getAudioUrl(prog.last_generated));
              setLatestAudioTitle(prog.last_generated);
            }
          }
        } catch {
          // Ignorar fallos transitorios
        }
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [backendStatus.status, loadProjectFromBackend, processingMode, showNotification]);

  // Sincronizar estructura de guion si no hay secciones cargadas desde backend
  useEffect(() => {
    try {
      if (!scriptText.trim()) {
        setSections([]);
        setParseError(null);
        return;
      }

      const parsed = buildProjectStructure(scriptText, processingMode, settings.language);

      setSections((prevSections) => {
        // Mapear audios existentes para conservarlos si el texto coincide
        const audioMap = new Map<string, { audioUrl?: string; filename?: string; status: 'ready' | 'pending' }>();

        prevSections.forEach((sec) => {
          sec.parts.forEach((p) => {
            if (p.audioUrl) {
              audioMap.set(p.text, {
                audioUrl: p.audioUrl,
                filename: p.filename,
                status: 'ready',
              });
            }
          });
        });

        return parsed.map((sec) => ({
          ...sec,
          parts: sec.parts.map((p) => {
            const existing = audioMap.get(p.text);
            if (existing) {
              return {
                ...p,
                audioUrl: existing.audioUrl,
                filename: existing.filename,
                status: existing.status,
              };
            }
            return p;
          }),
        }));
      });

      setParseError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setParseError(msg);
    }
  }, [scriptText, processingMode, settings.language]);

  // Cargar ejemplo
  const handleLoadSample = () => {
    setProcessingMode('scene');
    setScriptText(DEFAULT_SCRIPT_SAMPLE);
    showNotification('Guion de ejemplo cargado', 'info');
  };

  // Cambio de idioma
  const handleLanguageChange = (langCode: string) => {
    const lang = SUPPORTED_LANGUAGES[langCode];
    if (!lang) return;

    setSettings((prev) => ({
      ...prev,
      language: langCode,
      refAudioUrl: lang.audioPromptUrl,
      refAudioName: `${lang.code}_prompt.flac`,
    }));
  };

  // Generación completa
  const handleGenerateAll = async () => {
    if (sections.length === 0 || isGeneratingAll) return;

    // 1. SI EL BACKEND PYTHON ESTÁ ACTIVO -> LLAMAR A LA API DE PYTHON
    if (backendStatus.status === 'online') {
      try {
        setIsGeneratingAll(true);
        isGeneratingRef.current = true;

        showNotification('Iniciando síntesis en backend Python con Chatterbox...', 'info');

        await apiService.startGeneration({
          text: scriptText,
          processing_mode: processingMode,
          language: settings.language,
          voice_name: settings.voiceName,
          ref_audio_path: settings.refAudioUrl,
          exaggeration: settings.exaggeration,
          temperature: settings.temperature,
          cfg_weight: settings.cfgWeight,
          seed: settings.seed,
        });

        // La interfaz se actualizará a través del polling de /api/progress
      } catch (err: unknown) {
        setIsGeneratingAll(false);
        isGeneratingRef.current = false;
        const msg = err instanceof Error ? err.message : String(err);
        showNotification(`Error en backend: ${msg}`, 'error');
      }
      return;
    }

    // 2. FALLBACK SI PYTHON NO ESTÁ INICIADO LOCALMENTE
    showNotification(
      '⚠️ Backend Python no detectado. Para usar Chatterbox TTS, ejecuta: python multilingual_app.py',
      'info'
    );
    setIsGeneratingAll(true);

    try {
      const updated = JSON.parse(JSON.stringify(sections));
      for (let sIdx = 0; sIdx < updated.length; sIdx++) {
        const sec = updated[sIdx];
        for (let pIdx = 0; pIdx < sec.parts.length; pIdx++) {
          const part = sec.parts[pIdx];
          if (part.status === 'ready' && part.audioUrl) continue;

          setSections((curr) => {
            const next = [...curr];
            if (next[sIdx]?.parts[pIdx]) {
              next[sIdx].parts[pIdx].status = 'generating';
            }
            return next;
          });

          const { blob, url, duration } = await synthesizePartAudio(part.text, {
            text: part.text,
            lang: settings.language,
            voiceName: settings.voiceName,
            rate: settings.cfgWeight,
            pitch: settings.exaggeration,
            seed: settings.seed + sIdx * 100 + pIdx,
          });

          part.audioUrl = url;
          part.audioBlob = blob;
          part.duration = duration;
          part.status = 'ready';

          setLatestAudioUrl(url);
          setLatestAudioTitle(`${processingMode === 'scene' ? 'Escena' : 'Párrafo'} ${sec.number} · Parte ${part.number}`);

          setSections((curr) => {
            const next = [...curr];
            if (next[sIdx]?.parts[pIdx]) {
              next[sIdx].parts[pIdx] = { ...part };
            }
            return next;
          });
        }
      }
      showNotification('Generación completada en modo vista previa', 'success');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error: ${msg}`, 'error');
    } finally {
      setIsGeneratingAll(false);
    }
  };

  // Regeneración individual
  const handleRegeneratePart = async (sectionNumber: number, partNumber: number) => {
    const secIdx = sections.findIndex((s) => s.number === sectionNumber);
    if (secIdx === -1) return;
    const partIdx = sections[secIdx].parts.findIndex((p) => p.number === partNumber);
    if (partIdx === -1) return;

    const part = sections[secIdx].parts[partIdx];

    setSections((curr) => {
      const next = [...curr];
      next[secIdx].parts[partIdx].status = 'generating';
      return next;
    });

    // Si el backend Python está activo
    if (backendStatus.status === 'online') {
      try {
        const res = await apiService.regeneratePart({
          processing_mode: processingMode,
          section_number: sectionNumber,
          part_number: partNumber,
          language: settings.language,
          audio_prompt_path: settings.refAudioUrl,
          exaggeration: settings.exaggeration,
          temperature: settings.temperature,
          cfg_weight: settings.cfgWeight,
          seed: settings.seed,
        });

        setSections((curr) => {
          const next = [...curr];
          next[secIdx].parts[partIdx] = {
            ...part,
            audioUrl: res.audio_url,
            filename: res.filename,
            status: 'ready',
          };
          return next;
        });

        setLatestAudioUrl(res.audio_url);
        setLatestAudioTitle(res.filename);
        showNotification(`Parte ${partNumber} regenerada por Chatterbox`, 'success');
        return;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        showNotification(`Error al regenerar en Python: ${msg}`, 'error');
        setSections((curr) => {
          const next = [...curr];
          next[secIdx].parts[partIdx].status = 'error';
          return next;
        });
        return;
      }
    }

    // Fallback cliente
    try {
      const { blob, url, duration } = await synthesizePartAudio(part.text, {
        text: part.text,
        lang: settings.language,
        voiceName: settings.voiceName,
        rate: settings.cfgWeight,
        pitch: settings.exaggeration,
        seed: Math.floor(Math.random() * 1000000000),
      });

      setSections((curr) => {
        const next = [...curr];
        next[secIdx].parts[partIdx] = {
          ...part,
          audioUrl: url,
          audioBlob: blob,
          duration,
          status: 'ready',
        };
        return next;
      });

      setLatestAudioUrl(url);
      setLatestAudioTitle(`Parte ${partNumber} (Sección ${sectionNumber})`);
      showNotification(`Parte ${partNumber} regenerada`, 'success');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error: ${msg}`, 'error');
    }
  };

  // Regeneración múltiple
  const handleBatchRegenerate = async (selectedKeys: string[]) => {
    if (selectedKeys.length === 0) return;

    if (backendStatus.status === 'online') {
      try {
        const items = selectedKeys.map((k) => {
          const [s, p] = k.split('|');
          return [parseInt(s, 10), parseInt(p, 10)];
        });

        isGeneratingRef.current = true;
        setIsGeneratingAll(true);

        showNotification(`Iniciando regeneración de ${items.length} partes en backend...`, 'info');
        await apiService.regenerateBatch({
          selected_items: items,
          processing_mode: processingMode,
          language: settings.language,
          audio_prompt_path: settings.refAudioUrl,
          exaggeration: settings.exaggeration,
          temperature: settings.temperature,
          cfg_weight: settings.cfgWeight,
          seed: settings.seed,
        });
        return;
      } catch (err: unknown) {
        setIsGeneratingAll(false);
        isGeneratingRef.current = false;
        const msg = err instanceof Error ? err.message : String(err);
        showNotification(`Error: ${msg}`, 'error');
        return;
      }
    }

    // Fallback cliente
    let count = 0;
    for (const key of selectedKeys) {
      const [secStr, partStr] = key.split('|');
      await handleRegeneratePart(parseInt(secStr, 10), parseInt(partStr, 10));
      count++;
    }
    showNotification(`Regeneración finalizada: ${count} parte(s).`, 'success');
  };

  // Unir sección
  const handleJoinSection = async (sectionNumber: number) => {
    const secIdx = sections.findIndex((s) => s.number === sectionNumber);
    if (secIdx === -1) return;

    setSections((curr) => {
      const next = [...curr];
      next[secIdx].isJoining = true;
      return next;
    });

    if (backendStatus.status === 'online') {
      try {
        const res = await apiService.joinSection({
          processing_mode: processingMode,
          section_number: sectionNumber,
        });

        setSections((curr) => {
          const next = [...curr];
          next[secIdx].joinedAudioUrl = res.audio_url;
          next[secIdx].joinedFilename = res.filename;
          next[secIdx].isJoining = false;
          return next;
        });

        setLatestAudioUrl(res.audio_url);
        setLatestAudioTitle(res.filename);
        showNotification(`WAV ensamblado por Python: ${res.filename}`, 'success');
        return;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        showNotification(`Error al unir en Python: ${msg}`, 'error');
        setSections((curr) => {
          const next = [...curr];
          next[secIdx].isJoining = false;
          return next;
        });
        return;
      }
    }

    // Fallback cliente
    try {
      const blobs: Blob[] = [];
      for (const part of sections[secIdx].parts) {
        if (!part.audioBlob) {
          showNotification(`Falta el audio de la Parte ${part.number}.`, 'error');
          setSections((curr) => {
            const next = [...curr];
            next[secIdx].isJoining = false;
            return next;
          });
          return;
        }
        blobs.push(part.audioBlob);
      }

      const { blob, url } = await concatenateAudioBlobs(blobs);

      setSections((curr) => {
        const next = [...curr];
        next[secIdx].joinedAudioUrl = url;
        next[secIdx].joinedAudioBlob = blob;
        next[secIdx].isJoining = false;
        return next;
      });

      setLatestAudioUrl(url);
      setLatestAudioTitle(`Sección ${sectionNumber} (Audio Final Unido)`);
      showNotification(`Audio final unido para sección ${sectionNumber}`, 'success');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showNotification(`Error al unir: ${msg}`, 'error');
      setSections((curr) => {
        const next = [...curr];
        next[secIdx].isJoining = false;
        return next;
      });
    }
  };

  return (
    <div className="min-h-screen bg-[#090c10] text-[#e7eaf0] flex flex-col selection:bg-cyan-500/30 selection:text-white">
      <Header
        backendStatus={backendStatus}
        onRefreshStatus={checkBackendStatus}
      />

      {/* Backend offline alert / help banner */}
      {backendStatus.status === 'offline' && (
        <div className="bg-[#121822] border-b border-[#202938] px-4 py-2.5 text-xs text-[#94a3b8]">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
              <span>
                <strong>Modo Vista Previa:</strong> El backend Python no responde en <code>http://localhost:8000</code>.
              </span>
            </div>
            <div className="flex items-center gap-2 text-cyan-400 font-mono text-[11px] bg-[#0c1017] px-2.5 py-1 rounded border border-[#1e2736]">
              <Terminal className="h-3 w-3" />
              <span>python multilingual_app.py</span>
            </div>
          </div>
        </div>
      )}

      {/* Notification Toast */}
      {notification && (
        <div className="fixed top-5 right-5 z-50 max-w-md animate-in slide-in-from-top-2">
          <div
            className={`flex items-center gap-2.5 rounded-xl border px-4 py-3 text-sm shadow-2xl backdrop-blur-md ${
              notification.type === 'success'
                ? 'border-emerald-500/40 bg-emerald-950/95 text-emerald-200'
                : notification.type === 'error'
                ? 'border-rose-500/40 bg-rose-950/95 text-rose-200'
                : 'border-cyan-500/40 bg-[#0d141e]/95 text-cyan-200'
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

      {/* Main Workspace Layout */}
      <main className="flex-1 max-w-[1550px] w-full mx-auto px-4 sm:px-6 py-6">
        {parseError && (
          <div className="mb-6 rounded-xl border border-rose-500/40 bg-rose-950/30 p-4 text-sm text-rose-200 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
            <div>
              <div className="font-bold text-rose-300">Error en el formato del guion</div>
              <div className="text-xs text-rose-200/90 mt-0.5 font-mono">{parseError}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-11 gap-6">
          {/* Left Column: Script & Voice Setup (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            <ScriptEditor
              processingMode={processingMode}
              onModeChange={setProcessingMode}
              scriptText={scriptText}
              onScriptChange={setScriptText}
              onLoadSample={handleLoadSample}
            />

            <VoiceSettings
              settings={settings}
              voiceOptions={backendVoices}
              onSettingsChange={setSettings}
              onLanguageChange={handleLanguageChange}
            />
          </div>

          {/* Right Column: Audio Production & Review (6 cols) */}
          <div className="lg:col-span-6">
            <ProductionPanel
              sections={sections}
              processingMode={processingMode}
              settings={settings}
              isGeneratingAll={isGeneratingAll}
              progressInfo={generationProgress}
              isBackendOnline={backendStatus.status === 'online'}
              onGenerateAll={handleGenerateAll}
              onRegeneratePart={handleRegeneratePart}
              onBatchRegenerate={handleBatchRegenerate}
              onJoinSection={handleJoinSection}
              latestAudioUrl={latestAudioUrl}
              latestAudioTitle={latestAudioTitle}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1a202c] bg-[#070a0e] py-4 text-center text-xs text-[#7f8996]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Crónicas Mundiales &bull; Chatterbox Multilingual Narration Studio</span>
          <div className="flex items-center gap-3 font-mono text-[11px]">
            <span>FastAPI: /api</span>
            <span>&bull;</span>
            <span>Gradio: /gradio</span>
            <span>&bull;</span>
            <span className="text-cyan-400">{backendStatus.device.toUpperCase()}</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
