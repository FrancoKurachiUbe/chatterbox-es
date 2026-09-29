import React, { useState } from 'react';
import { StudioSettings } from '../types';
import { SUPPORTED_LANGUAGES, PRESET_VOICES } from '../constants/languages';
import { VoiceOption } from '../services/api';
import { Sliders, Volume2, Globe, ChevronDown, ChevronUp, Upload, Play, Square } from 'lucide-react';
import { speakText, stopSpeaking } from '../utils/audioEngine';

interface VoiceSettingsProps {
  settings: StudioSettings;
  voiceOptions?: VoiceOption[];
  onSettingsChange: (settings: StudioSettings) => void;
  onLanguageChange: (langCode: string) => void;
}

export const VoiceSettings: React.FC<VoiceSettingsProps> = ({
  settings,
  voiceOptions = [],
  onSettingsChange,
  onLanguageChange,
}) => {
  const [accordionOpen, setAccordionOpen] = useState(false);
  const [isPlayingSample, setIsPlayingSample] = useState(false);
  const selectedLang = SUPPORTED_LANGUAGES[settings.language] || SUPPORTED_LANGUAGES['es'];

  // Combinar voces del backend (voices/) con presets
  const availableVoices = voiceOptions.length > 0
    ? voiceOptions.map((v) => ({ id: v.name, name: v.name, path: v.path }))
    : PRESET_VOICES.map((v) => ({ id: v.id, name: v.name, path: '' }));

  const handleLangSelect = (code: string) => {
    onLanguageChange(code);
  };

  const handleVoiceSelect = (voiceId: string) => {
    const found = availableVoices.find((v) => v.id === voiceId);
    onSettingsChange({
      ...settings,
      voiceName: voiceId,
      refAudioUrl: found?.path || settings.refAudioUrl,
    });
  };

  const handleTestVoice = () => {
    if (isPlayingSample) {
      stopSpeaking();
      setIsPlayingSample(false);
      return;
    }

    setIsPlayingSample(true);
    speakText(selectedLang.defaultText, {
      lang: selectedLang.code,
      rate: settings.cfgWeight,
      pitch: settings.exaggeration,
      voiceName: settings.voiceName,
      onEnd: () => setIsPlayingSample(false),
      onError: () => setIsPlayingSample(false),
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      onSettingsChange({
        ...settings,
        refAudioUrl: url,
        refAudioName: file.name,
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="text-xs font-bold uppercase tracking-wider text-[#d8dde5]">
        🎙️ VOZ Y MODELO CHATTERBOX
      </div>

      <div className="rounded-xl border border-[#252a31] bg-[#12161b] p-4 space-y-4">
        {/* Language selector */}
        <div>
          <label className="block text-xs font-medium text-[#b5bcc7] mb-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5 text-cyan-400" /> Idioma ({Object.keys(SUPPORTED_LANGUAGES).length} soportados)
            </span>
            <span className="text-[11px] text-[#7f8996] font-mono">{selectedLang.code.toUpperCase()}</span>
          </label>
          <select
            value={settings.language}
            onChange={(e) => handleLangSelect(e.target.value)}
            className="w-full rounded-lg border border-[#292f37] bg-[#0f1216] px-3 py-2 text-sm text-[#e7eaf0] focus:border-cyan-500 focus:outline-none"
          >
            {Object.values(SUPPORTED_LANGUAGES).map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} — {lang.nativeName} ({lang.code})
              </option>
            ))}
          </select>
        </div>

        {/* Voice selector */}
        <div>
          <label className="block text-xs font-medium text-[#b5bcc7] mb-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Volume2 className="h-3.5 w-3.5 text-emerald-400" /> Voz de referencia (voices/)
            </span>
            <span className="text-[11px] text-cyan-400 font-mono">Brian Warm Clonacion Voz</span>
          </label>
          <select
            value={settings.voiceName}
            onChange={(e) => handleVoiceSelect(e.target.value)}
            className="w-full rounded-lg border border-[#292f37] bg-[#0f1216] px-3 py-2 text-sm text-[#e7eaf0] focus:border-cyan-500 focus:outline-none"
          >
            {availableVoices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </div>

        {/* Audio prompt reference */}
        <div className="rounded-lg border border-[#252a31] bg-[#0f1216] p-3 space-y-2">
          <div className="flex items-center justify-between text-xs text-[#8d96a3]">
            <span>Muestra de audio de referencia</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleTestVoice}
                className="inline-flex items-center gap-1 rounded bg-cyan-950/60 border border-cyan-800/60 px-2 py-0.5 text-[11px] text-cyan-300 hover:bg-cyan-900/60 transition-colors"
              >
                {isPlayingSample ? (
                  <>
                    <Square className="h-3 w-3 fill-cyan-300" /> Detener
                  </>
                ) : (
                  <>
                    <Play className="h-3 w-3 fill-cyan-300" /> Probar voz
                  </>
                )}
              </button>
            </div>
          </div>

          {settings.refAudioUrl ? (
            <div className="space-y-1">
              <audio
                controls
                src={settings.refAudioUrl}
                className="w-full h-8 rounded opacity-90"
              />
              {settings.refAudioName && (
                <div className="text-[10px] text-[#7f8996] truncate">
                  Archivo: {settings.refAudioName}
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-[#7f8996] italic">
              Usando muestra por defecto para {selectedLang.name}.
            </div>
          )}

          <div className="flex items-center gap-2 pt-1">
            <label className="flex-1 cursor-pointer flex items-center justify-center gap-1.5 rounded border border-[#2d3542] bg-[#161b22] px-2.5 py-1.5 text-xs text-[#b5bcc7] hover:bg-[#202732] hover:text-white transition-colors">
              <Upload className="h-3.5 w-3.5 text-cyan-400" />
              <span>Subir WAV personalizado</span>
              <input
                type="file"
                accept="audio/*"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
            <button
              type="button"
              onClick={() => {
                onSettingsChange({
                  ...settings,
                  refAudioUrl: selectedLang.audioPromptUrl,
                  refAudioName: `${selectedLang.code}_prompt.flac`,
                });
              }}
              className="rounded border border-[#2d3542] bg-[#161b22] px-2.5 py-1.5 text-xs text-[#8d96a3] hover:text-white hover:bg-[#202732] transition-colors"
              title="Restaurar audio de muestra de Google Cloud"
            >
              Demo Cloud
            </button>
          </div>
        </div>

        {/* Settings Accordion */}
        <div className="rounded-lg border border-[#252a31] bg-[#0f1216] overflow-hidden">
          <button
            type="button"
            onClick={() => setAccordionOpen(!accordionOpen)}
            className="w-full flex items-center justify-between px-3.5 py-2.5 text-left text-xs font-semibold text-[#b5bcc7] hover:bg-[#151a21] transition-colors"
          >
            <span className="flex items-center gap-2">
              <Sliders className="h-3.5 w-3.5 text-amber-400" />
              <span>⚙️ Configuración avanzada de narración</span>
            </span>
            {accordionOpen ? (
              <ChevronUp className="h-4 w-4 text-[#7f8996]" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[#7f8996]" />
            )}
          </button>

          {accordionOpen && (
            <div className="p-3.5 border-t border-[#252a31] space-y-3.5 bg-[#0b0e13]">
              {/* Exaggeration */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-[#8d96a3]">Exaggeration (Inflexión):</span>
                  <span className="font-mono text-cyan-400 font-semibold">{settings.exaggeration.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.25"
                  max="2.0"
                  step="0.05"
                  value={settings.exaggeration}
                  onChange={(e) =>
                    onSettingsChange({
                      ...settings,
                      exaggeration: parseFloat(e.target.value),
                    })
                  }
                  className="w-full accent-cyan-500 cursor-pointer"
                />
              </div>

              {/* CFG / Pace */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-[#8d96a3]">CFG Weight / Pace (Ritmo):</span>
                  <span className="font-mono text-cyan-400 font-semibold">{settings.cfgWeight.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.20"
                  max="1.0"
                  step="0.05"
                  value={settings.cfgWeight}
                  onChange={(e) =>
                    onSettingsChange({
                      ...settings,
                      cfgWeight: parseFloat(e.target.value),
                    })
                  }
                  className="w-full accent-cyan-500 cursor-pointer"
                />
              </div>

              {/* Temperature */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-[#8d96a3]">Temperature (Variación):</span>
                  <span className="font-mono text-cyan-400 font-semibold">{settings.temperature.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="5.0"
                  step="0.05"
                  value={settings.temperature}
                  onChange={(e) =>
                    onSettingsChange({
                      ...settings,
                      temperature: parseFloat(e.target.value),
                    })
                  }
                  className="w-full accent-cyan-500 cursor-pointer"
                />
              </div>

              {/* Fixed Seed */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-[#8d96a3]">Seed fija (Reproducibilidad):</span>
                  <button
                    type="button"
                    onClick={() =>
                      onSettingsChange({
                        ...settings,
                        seed: Math.floor(Math.random() * 1000000000),
                      })
                    }
                    className="text-[10px] text-cyan-400 hover:underline"
                  >
                    Aleatorio
                  </button>
                </div>
                <input
                  type="number"
                  value={settings.seed}
                  onChange={(e) =>
                    onSettingsChange({
                      ...settings,
                      seed: parseInt(e.target.value, 10) || 0,
                    })
                  }
                  className="w-full rounded border border-[#292f37] bg-[#0f1216] px-2.5 py-1.5 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
