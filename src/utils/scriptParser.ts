import { ProcessingMode, ScriptSection } from '../types';
import { normalizeNumbersForTTS } from './spanishNumbers';
import { splitTextForTTS } from './textSplitter';

export interface RawSection {
  number: number;
  title: string;
  text: string;
}

export function parseParagraphsFromScript(textInput: string): RawSection[] {
  const normalizedInput = textInput.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();

  if (!normalizedInput) {
    throw new Error('El guion está vacío.');
  }

  const paragraphs = normalizedInput.split(/\n\s*\n/);
  const result: RawSection[] = [];
  let number = 1;

  for (const paragraph of paragraphs) {
    const text = paragraph.trim();
    if (!text) continue;

    result.push({
      number,
      title: '',
      text,
    });
    number++;
  }

  if (result.length === 0) {
    throw new Error('No se encontraron párrafos.');
  }

  return result;
}

export function parseScenesFromScript(textInput: string): RawSection[] {
  const normalizedInput = textInput.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();

  if (!normalizedInput) {
    throw new Error('El guion está vacío.');
  }

  const lines = normalizedInput.split('\n');
  const scenePattern = /^\s*ESCENA\s+(\d+)(?:\s*[—–:-]\s*(.*))?\s*$/i;

  const scenes: RawSection[] = [];
  let currentScene: { number: number; title: string; lines: string[] } | null = null;
  const contentBeforeFirstScene: string[] = [];

  for (const line of lines) {
    const match = line.match(scenePattern);

    if (match) {
      if (currentScene !== null) {
        scenes.push({
          number: currentScene.number,
          title: currentScene.title,
          text: currentScene.lines.join('\n').trim(),
        });
      }

      const sceneNumber = parseInt(match[1], 10);
      const sceneTitle = (match[2] || '').trim();

      currentScene = {
        number: sceneNumber,
        title: sceneTitle,
        lines: [],
      };
    } else {
      if (currentScene !== null) {
        currentScene.lines.push(line);
      } else if (line.trim()) {
        contentBeforeFirstScene.push(line.trim());
      }
    }
  }

  if (currentScene !== null) {
    scenes.push({
      number: currentScene.number,
      title: currentScene.title,
      text: currentScene.lines.join('\n').trim(),
    });
  }

  if (contentBeforeFirstScene.length > 0) {
    throw new Error(
      "Hay texto antes de la primera ESCENA. El guion debe comenzar con 'ESCENA 1 — Título'."
    );
  }

  if (scenes.length === 0) {
    throw new Error("No se encontraron escenas. Usá el formato 'ESCENA 1 — Título'.");
  }

  for (const scene of scenes) {
    if (!scene.text) {
      throw new Error(`La ESCENA ${scene.number} no tiene texto.`);
    }
  }

  return scenes;
}

export function buildProjectStructure(
  textInput: string,
  processingMode: ProcessingMode,
  languageId: string
): ScriptSection[] {
  const rawSections =
    processingMode === 'scene'
      ? parseScenesFromScript(textInput)
      : parseParagraphsFromScript(textInput);

  return rawSections.map((section) => {
    const normalizedText = normalizeNumbersForTTS(section.text, languageId);
    const chunks = splitTextForTTS(normalizedText);

    return {
      number: section.number,
      title: section.title,
      text: section.text,
      normalizedText,
      parts: chunks.map((chunk, index) => ({
        number: index + 1,
        text: chunk,
        status: 'pending',
      })),
    };
  });
}
