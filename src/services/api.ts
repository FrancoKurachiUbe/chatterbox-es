/**
 * Servicio de conexión HTTP con el Backend Python de Chatterbox ES
 * Se comunica con los endpoints REST expuestos en multilingual_app.py
 */

export interface BackendStatus {
  status: 'online' | 'offline';
  device: string;
  device_label: string;
  model_loaded: boolean;
  model_status: string;
  t3_model: string;
  is_generating: boolean;
}

export interface GenerationProgress {
  is_generating: boolean;
  current_step: number;
  total_steps: number;
  current_label: string;
  message: string;
  errors: string[];
  last_generated?: string | null;
}

export interface VoiceOption {
  name: string;
  path: string;
}

export interface LanguageOption {
  code: string;
  name: string;
  default_text: string;
  audio_prompt: string;
}

export interface ApiProjectResponse {
  project: any;
  panel: any[];
  status_text: string;
  processing_mode: string;
}

class BackendApiService {
  private baseUrl: string = '';

  constructor() {
    // Si se corre directamente contra un backend en otro puerto en dev
    this.baseUrl = '';
  }

  async checkStatus(): Promise<BackendStatus> {
    try {
      const res = await fetch(`${this.baseUrl}/api/status`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      return {
        ...data,
        status: 'online',
      };
    } catch (err) {
      return {
        status: 'offline',
        device: 'desconocido',
        device_label: 'Sin conexión con Backend Python',
        model_loaded: false,
        model_status: 'Backend no iniciado',
        t3_model: 'v2',
        is_generating: false,
      };
    }
  }

  async getProgress(): Promise<GenerationProgress> {
    try {
      const res = await fetch(`${this.baseUrl}/api/progress`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return {
        is_generating: false,
        current_step: 0,
        total_steps: 0,
        current_label: '',
        message: 'Inactivo',
        errors: [],
      };
    }
  }

  async getVoices(): Promise<{ voices: VoiceOption[]; default_voice?: string }> {
    try {
      const res = await fetch(`${this.baseUrl}/api/voices`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return {
        voices: [{ name: 'Brian Warm Clonacion Voz', path: 'voices/Brian Warm Clonacion Voz.wav' }],
        default_voice: 'Brian Warm Clonacion Voz',
      };
    }
  }

  async getLanguages(): Promise<{ languages: LanguageOption[]; default_language: string }> {
    try {
      const res = await fetch(`${this.baseUrl}/api/languages`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return {
        languages: [{ code: 'es', name: 'Español', default_text: '', audio_prompt: '' }],
        default_language: 'es',
      };
    }
  }

  async getProject(mode: string = 'scene'): Promise<ApiProjectResponse | null> {
    try {
      const res = await fetch(`${this.baseUrl}/api/project?mode=${encodeURIComponent(mode)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return null;
    }
  }

  async saveProject(payload: {
    text: string;
    processing_mode: string;
    language: string;
    voice_name?: string;
    ref_audio_path?: string;
    exaggeration: number;
    temperature: number;
    cfg_weight: number;
    seed: number;
  }): Promise<{ status: string; project: any }> {
    const res = await fetch(`${this.baseUrl}/api/project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error al guardar proyecto' }));
      throw new Error(err.detail || 'Error en el servidor');
    }
    return await res.json();
  }

  async startGeneration(payload: {
    text: string;
    processing_mode: string;
    language: string;
    voice_name?: string;
    ref_audio_path?: string;
    exaggeration: number;
    temperature: number;
    cfg_weight: number;
    seed: number;
  }): Promise<{ status: string; message: string }> {
    const res = await fetch(`${this.baseUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error al iniciar generación' }));
      throw new Error(err.detail || 'Error en el servidor');
    }
    return await res.json();
  }

  async regeneratePart(payload: {
    processing_mode: string;
    section_number: number;
    part_number: number;
    language: string;
    audio_prompt_path?: string;
    exaggeration: number;
    temperature: number;
    cfg_weight: number;
    seed: number;
  }): Promise<{ status: string; filename: string; audio_url: string }> {
    const res = await fetch(`${this.baseUrl}/api/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error al regenerar parte' }));
      throw new Error(err.detail || 'Error en el servidor');
    }
    return await res.json();
  }

  async regenerateBatch(payload: {
    selected_items: number[][]; // [[sec, part], ...]
    processing_mode: string;
    language: string;
    audio_prompt_path?: string;
    exaggeration: number;
    temperature: number;
    cfg_weight: number;
    seed: number;
  }): Promise<{ status: string; message: string }> {
    const res = await fetch(`${this.baseUrl}/api/regenerate-batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error al regenerar partes' }));
      throw new Error(err.detail || 'Error en el servidor');
    }
    return await res.json();
  }

  async joinSection(payload: {
    processing_mode: string;
    section_number: number;
  }): Promise<{ status: string; filename: string; audio_url: string }> {
    const res = await fetch(`${this.baseUrl}/api/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error al unir sección' }));
      throw new Error(err.detail || 'Error en el servidor');
    }
    return await res.json();
  }

  getAudioUrl(filename: string): string {
    return `${this.baseUrl}/api/audio/${encodeURIComponent(filename)}`;
  }
}

export const apiService = new BackendApiService();
