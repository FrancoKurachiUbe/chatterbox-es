export type ProcessingMode = 'paragraph' | 'scene';

export interface ScriptPart {
  number: number;
  text: string;
  filename?: string;
  audioUrl?: string;
  audioBlob?: Blob;
  duration?: number;
  status: 'pending' | 'generating' | 'ready' | 'error';
  errorMessage?: string;
}

export interface ScriptSection {
  number: number;
  title: string;
  text: string;
  normalizedText: string;
  parts: ScriptPart[];
  joinedAudioUrl?: string;
  joinedAudioBlob?: Blob;
  joinedFilename?: string;
  isJoining?: boolean;
}

export interface StudioSettings {
  language: string;
  voiceName: string;
  refAudioUrl?: string;
  refAudioName?: string;
  exaggeration: number; // 0.25 - 2.0
  cfgWeight: number; // 0.2 - 1.0 (Pace)
  temperature: number; // 0.05 - 5.0
  seed: number;
}

export interface NarrationProject {
  lastScript: string;
  processingMode: ProcessingMode;
  settings: StudioSettings;
  sections: ScriptSection[];
  createdAt: number;
  updatedAt: number;
}
