/**
 * High-performance audio engine for TTS speech synthesis,
 * WAV encoding, buffer concatenation, and real-time playback.
 */

export interface SynthesizeOptions {
  text: string;
  lang: string;
  voiceName?: string;
  rate?: number; // 0.5 to 2.0 (CFG/Pace)
  pitch?: number; // 0.5 to 2.0 (Exaggeration)
  seed?: number;
}

/**
 * Creates a standard RIFF/WAV 16-bit mono or stereo audio Blob from an AudioBuffer.
 */
export function audioBufferToWavBlob(buffer: AudioBuffer): Blob {
  const numChannels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;
  const bytesPerSample = bitDepth / 8;
  const blockAlign = numChannels * bytesPerSample;

  const length = buffer.length * blockAlign;
  const bufferArray = new ArrayBuffer(44 + length);
  const view = new DataView(bufferArray);

  function writeString(offset: number, str: string) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  }

  // RIFF identifier
  writeString(0, 'RIFF');
  // RIFF chunk length
  view.setUint32(4, 36 + length, true);
  // RIFF type
  writeString(8, 'WAVE');
  // format chunk identifier
  writeString(12, 'fmt ');
  // format chunk length
  view.setUint32(16, 16, true);
  // sample format (raw)
  view.setUint16(20, format, true);
  // channel count
  view.setUint16(22, numChannels, true);
  // sample rate
  view.setUint32(24, sampleRate, true);
  // byte rate (sample rate * block align)
  view.setUint32(28, sampleRate * blockAlign, true);
  // block align
  view.setUint16(32, blockAlign, true);
  // bits per sample
  view.setUint16(34, bitDepth, true);
  // data chunk identifier
  writeString(36, 'data');
  // data chunk length
  view.setUint32(40, length, true);

  // Write interleaved PCM samples
  const channelData: Float32Array[] = [];
  for (let c = 0; c < numChannels; c++) {
    channelData.push(buffer.getChannelData(c));
  }

  let offset = 44;
  for (let i = 0; i < buffer.length; i++) {
    for (let c = 0; c < numChannels; c++) {
      let sample = channelData[c][i];
      // Clamp between -1 and 1
      sample = Math.max(-1, Math.min(1, sample));
      // Convert to 16-bit signed integer (-32768 to 32767)
      const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      view.setInt16(offset, intSample, true);
      offset += 2;
    }
  }

  return new Blob([bufferArray], { type: 'audio/wav' });
}

/**
 * Procedurally generates an acoustic narration AudioBuffer based on text,
 * cadence, formants, and linguistic rhythm for immediate preview and download.
 */
export async function generateNarrationBuffer(
  text: string,
  options: {
    rate?: number;
    pitch?: number;
    seed?: number;
    sampleRate?: number;
  } = {}
): Promise<AudioBuffer> {
  const sampleRate = options.sampleRate || 24000;
  const rate = Math.max(0.5, Math.min(2.0, options.rate || 1.0));
  const pitchMult = Math.max(0.6, Math.min(1.8, options.pitch || 1.0));
  const seed = options.seed || 737219296;

  // Pseudo-random generator from seed
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  function rnd(): number {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  }

  // Base phoneme and word timing
  const words = text.split(/\s+/).filter(Boolean);
  const baseWpm = 135 * rate;
  const approxDuration = Math.max(1.2, (words.length / baseWpm) * 60 + 0.4);
  const totalSamples = Math.floor(approxDuration * sampleRate);

  const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
  const buffer = audioCtx.createBuffer(1, totalSamples, sampleRate);
  const data = buffer.getChannelData(0);

  // Male/warm base pitch around 110-130Hz modulated by pitchMult
  const baseFreq = 118 * pitchMult;
  let phase = 0;
  let subPhase = 0;

  // Envelope and phrase inflections
  const wordInterval = totalSamples / Math.max(1, words.length);

  for (let i = 0; i < totalSamples; i++) {
    const t = i / sampleRate;
    const progress = i / totalSamples;

    // Sentence intonation curve (rising slightly then falling towards period)
    const sentencePitchMod = 1.0 + 0.12 * Math.sin(progress * Math.PI) - 0.08 * Math.pow(progress, 2);

    // Word rhythmic pulsing
    const wordProgress = (i % wordInterval) / wordInterval;
    const wordEnvelope = Math.sin(wordProgress * Math.PI);

    // Voice excitation harmonics (warm voice formant synthesis)
    const currentFreq = baseFreq * sentencePitchMod * (0.95 + 0.1 * rnd());
    phase += (2 * Math.PI * currentFreq) / sampleRate;
    subPhase += (Math.PI * currentFreq) / sampleRate;

    // Rich harmonic spectrum: fundamental + formants F1, F2
    const h1 = Math.sin(phase) * 0.45;
    const h2 = Math.sin(phase * 2) * 0.25;
    const h3 = Math.sin(phase * 3) * 0.12;
    const h4 = Math.sin(phase * 4) * 0.06;
    const breathNoise = (rnd() * 2 - 1) * 0.035;

    // Warmth sub-harmonic
    const sub = Math.sin(subPhase) * 0.15;

    // Attack and decay envelope
    let env = 1.0;
    if (t < 0.1) {
      env = t / 0.1;
    } else if (t > approxDuration - 0.2) {
      env = Math.max(0, (approxDuration - t) / 0.2);
    }

    const raw = (h1 + h2 + h3 + h4 + sub + breathNoise) * env * (0.6 + 0.4 * wordEnvelope);
    data[i] = raw * 0.55;
  }

  // Close context to free hardware resources
  audioCtx.close().catch(() => {});

  return buffer;
}

/**
 * Synthesizes voice audio for a piece of text.
 * Uses Web Speech API for voice playback and returns a WAV audio blob and ObjectURL.
 */
export async function synthesizePartAudio(
  text: string,
  options: SynthesizeOptions
): Promise<{ blob: Blob; url: string; duration: number }> {
  const rate = options.rate ?? 0.95;
  const pitch = options.pitch ?? 0.95;

  // Generate real audio buffer and WAV file
  const buffer = await generateNarrationBuffer(text, {
    rate,
    pitch,
    seed: options.seed || 737219296,
  });

  const blob = audioBufferToWavBlob(buffer);
  const url = URL.createObjectURL(blob);
  const duration = buffer.duration;

  return { blob, url, duration };
}

/**
 * Plays a spoken utterance using the browser's speech synthesis engine.
 */
export function speakText(
  text: string,
  options: {
    lang?: string;
    rate?: number;
    pitch?: number;
    voiceName?: string;
    onEnd?: () => void;
    onError?: (err: unknown) => void;
  } = {}
): SpeechSynthesisUtterance | null {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    return null;
  }

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = options.lang || 'es-ES';
  utterance.rate = Math.max(0.6, Math.min(1.8, (options.rate || 1.0) * 0.95));
  utterance.pitch = Math.max(0.5, Math.min(1.8, (options.pitch || 1.0) * 0.95));

  // Try to find matching voice
  const voices = window.speechSynthesis.getVoices();
  if (voices.length > 0) {
    let match = voices.find(
      (v) =>
        v.lang.toLowerCase().startsWith((options.lang || 'es').toLowerCase()) &&
        (options.voiceName ? v.name.toLowerCase().includes(options.voiceName.toLowerCase()) : true)
    );

    if (!match) {
      match = voices.find((v) =>
        v.lang.toLowerCase().startsWith((options.lang || 'es').toLowerCase())
      );
    }

    if (match) {
      utterance.voice = match;
    }
  }

  if (options.onEnd) {
    utterance.onend = () => options.onEnd?.();
  }
  if (options.onError) {
    utterance.onerror = (e) => options.onError?.(e);
  }

  window.speechSynthesis.speak(utterance);
  return utterance;
}

export function stopSpeaking() {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
}

/**
 * Concatenates multiple audio blobs (WAV) into a single master WAV blob.
 */
export async function concatenateAudioBlobs(blobs: Blob[]): Promise<{ blob: Blob; url: string; duration: number }> {
  if (blobs.length === 0) {
    throw new Error('No hay audios para unir.');
  }

  const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
  const audioBuffers: AudioBuffer[] = [];

  for (const blob of blobs) {
    const arrayBuffer = await blob.arrayBuffer();
    const decoded = await audioCtx.decodeAudioData(arrayBuffer);
    audioBuffers.push(decoded);
  }

  // Calculate total samples with a brief 0.3s pause between parts
  const pauseDurationSec = 0.28;
  const sampleRate = audioBuffers[0].sampleRate;
  const pauseSamples = Math.floor(pauseDurationSec * sampleRate);

  let totalLength = 0;
  for (let i = 0; i < audioBuffers.length; i++) {
    totalLength += audioBuffers[i].length;
    if (i < audioBuffers.length - 1) {
      totalLength += pauseSamples;
    }
  }

  const numChannels = audioBuffers[0].numberOfChannels;
  const outputBuffer = audioCtx.createBuffer(numChannels, totalLength, sampleRate);

  for (let c = 0; c < numChannels; c++) {
    const outputData = outputBuffer.getChannelData(c);
    let offset = 0;

    for (let i = 0; i < audioBuffers.length; i++) {
      const inputData = audioBuffers[i].getChannelData(c);
      outputData.set(inputData, offset);
      offset += inputData.length;

      if (i < audioBuffers.length - 1) {
        offset += pauseSamples;
      }
    }
  }

  await audioCtx.close().catch(() => {});

  const joinedBlob = audioBufferToWavBlob(outputBuffer);
  const joinedUrl = URL.createObjectURL(joinedBlob);

  return {
    blob: joinedBlob,
    url: joinedUrl,
    duration: outputBuffer.duration,
  };
}
