export interface LanguageConfig {
  code: string;
  name: string;
  nativeName: string;
  audioPromptUrl: string;
  defaultText: string;
}

export const SUPPORTED_LANGUAGES: Record<string, LanguageConfig> = {
  ar: {
    code: 'ar',
    name: 'Arabic',
    nativeName: 'العربية',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ar_f/ar_prompts2.flac',
    defaultText: 'في الشهر الماضي، وصلنا إلى معلم جديد بمليارين من المشاهدات على قناتنا على يوتيوب.'
  },
  da: {
    code: 'da',
    name: 'Danish',
    nativeName: 'Dansk',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/da_m1.flac',
    defaultText: 'Sidste måned nåede vi en ny milepæl med to milliarder visninger på vores YouTube-kanal.'
  },
  de: {
    code: 'de',
    name: 'German',
    nativeName: 'Deutsch',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/de_f1.flac',
    defaultText: 'Letzten Monat haben wir einen neuen Meilenstein erreicht: zwei Milliarden Aufrufe auf unserem YouTube-Kanal.'
  },
  el: {
    code: 'el',
    name: 'Greek',
    nativeName: 'Ελληνικά',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/el_m.flac',
    defaultText: 'Τον περασμένο μήνα, φτάσαμε σε ένα νέο ορόσημο με δύο δισεκατομμύρια προβολές στο κανάλι μας στο YouTube.'
  },
  en: {
    code: 'en',
    name: 'English',
    nativeName: 'English',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/en_f1.flac',
    defaultText: 'Last month, we reached a new milestone with two billion views on our YouTube channel.'
  },
  es: {
    code: 'es',
    name: 'Spanish',
    nativeName: 'Español',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/es_f1.flac',
    defaultText: 'El mes pasado alcanzamos un nuevo hito: dos mil millones de visualizaciones en nuestro canal de YouTube.'
  },
  fi: {
    code: 'fi',
    name: 'Finnish',
    nativeName: 'Suomi',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/fi_m.flac',
    defaultText: 'Viime kuussa saavutimme uuden virstanpylvään kahden miljardin katselukerran kanssa YouTube-kanavallamme.'
  },
  fr: {
    code: 'fr',
    name: 'French',
    nativeName: 'Français',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/fr_f1.flac',
    defaultText: 'Le mois dernier, nous avons atteint un nouveau jalon avec deux milliards de vues sur notre chaîne YouTube.'
  },
  he: {
    code: 'he',
    name: 'Hebrew',
    nativeName: 'עברית',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/he_m1.flac',
    defaultText: 'בחודש שעבר הגענו לאבן דרך חדשה עם שני מיליארד צפיות בערוץ היוטיוב שלנו.'
  },
  hi: {
    code: 'hi',
    name: 'Hindi',
    nativeName: 'हिन्दी',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/hi_f1.flac',
    defaultText: 'पिछले महीने हमने एक नया मील का पत्थर छुआ: हमारे YouTube चैनल पर दो अरब व्यूज़।'
  },
  it: {
    code: 'it',
    name: 'Italian',
    nativeName: 'Italiano',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/it_m1.flac',
    defaultText: 'Il mese scorso abbiamo raggiunto un nuovo traguardo: due miliardi di visualizzazioni sul nostro canale YouTube.'
  },
  ja: {
    code: 'ja',
    name: 'Japanese',
    nativeName: '日本語',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ja/ja_prompts1.flac',
    defaultText: '先月、私たちのYouTubeチャンネルで二十億回の再生回数という新たなマイルストーンに到達しました。'
  },
  ko: {
    code: 'ko',
    name: 'Korean',
    nativeName: '한국어',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ko_f.flac',
    defaultText: '지난달 우리는 유튜브 채널에서 이십억 조회수라는 새로운 이정표에 도달했습니다.'
  },
  ms: {
    code: 'ms',
    name: 'Malay',
    nativeName: 'Bahasa Melayu',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ms_f.flac',
    defaultText: 'Bulan lepas, kami mencapai pencapaian baru dengan dua bilion tontonan di saluran YouTube kami.'
  },
  nl: {
    code: 'nl',
    name: 'Dutch',
    nativeName: 'Nederlands',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/nl_m.flac',
    defaultText: 'Vorige maand bereikten we een nieuwe mijlpaal met twee miljard weergaven op ons YouTube-kanaal.'
  },
  no: {
    code: 'no',
    name: 'Norwegian',
    nativeName: 'Norsk',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/no_f1.flac',
    defaultText: 'Forrige måned nådde vi en ny milepæl med to milliarder visninger på YouTube-kanalen vår.'
  },
  pl: {
    code: 'pl',
    name: 'Polish',
    nativeName: 'Polski',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/pl_m.flac',
    defaultText: 'W zeszłym miesiącu osiągnęliśmy nowy kamień milowy z dwoma miliardami wyświetleń na naszym kanale YouTube.'
  },
  pt: {
    code: 'pt',
    name: 'Portuguese',
    nativeName: 'Português',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/pt_m1.flac',
    defaultText: 'No mês passado, alcançámos um novo marco: dois mil milhões de visualizações no nosso canal do YouTube.'
  },
  ru: {
    code: 'ru',
    name: 'Russian',
    nativeName: 'Русский',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ru_m.flac',
    defaultText: 'В прошлом месяце мы достигли нового рубежа: два миллиарда просмотров на нашем YouTube-канале.'
  },
  sv: {
    code: 'sv',
    name: 'Swedish',
    nativeName: 'Svenska',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/sv_f.flac',
    defaultText: 'Förra månaden nådde vi en ny milstolpe med två miljarder visningar på vår YouTube-kanal.'
  },
  sw: {
    code: 'sw',
    name: 'Swahili',
    nativeName: 'Kiswahili',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/sw_m.flac',
    defaultText: 'Mwezi uliopita, tulifika hatua mpya ya maoni ya bilioni mbili kweny kituo chetu cha YouTube.'
  },
  tr: {
    code: 'tr',
    name: 'Turkish',
    nativeName: 'Türkçe',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/tr_m.flac',
    defaultText: 'Geçen ay YouTube kanalımızda iki milyar görüntüleme ile yeni bir dönüm noktasına ulaştık.'
  },
  zh: {
    code: 'zh',
    name: 'Chinese',
    nativeName: '中文',
    audioPromptUrl: 'https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/zh_f2.flac',
    defaultText: '上个月，我们达到了一个新的里程碑。我们的YouTube频道观看次数达到了二十亿次，这绝对令人难以置信。'
  }
};

export interface VoicePreset {
  id: string;
  name: string;
  description: string;
  gender: 'male' | 'female';
  style: string;
}

export const PRESET_VOICES: VoicePreset[] = [
  {
    id: 'Brian Warm Clonacion Voz',
    name: 'Brian Warm Clonación Voz',
    description: 'Voz cálida y profunda para documentales históricos y crónicas',
    gender: 'male',
    style: 'Cálido, Profundo'
  },
  {
    id: 'Elena Narradora',
    name: 'Elena Narradora',
    description: 'Voz neutra, articulada y elegante para narración literaria',
    gender: 'female',
    style: 'Articulada, Solemne'
  },
  {
    id: 'Carlos Dramático',
    name: 'Carlos Dramático',
    description: 'Tono cinematográfico, misterioso y cautivante para relatos épicos',
    gender: 'male',
    style: 'Cinematográfico, Dramático'
  },
  {
    id: 'Lucía Documentales',
    name: 'Lucía Documentales',
    description: 'Claridad informativa con cadencia envolvente y pausada',
    gender: 'female',
    style: 'Envolvente, Explicativo'
  }
];

export const DEFAULT_SCRIPT_SAMPLE = `ESCENA 1 — El Gran Despertar
En el corazón de la antigua Europa, el año 1492 marcó el inicio de una era que transformaría el destino de 500 continentes y civilizaciones. Las carabelas zarparon hacia aguas desconocidas bajo el manto de un silencio impenetrable.

ESCENA 2 — La Tempestad en Altamar
Durante 40 días y 40 noches, los vientos del Atlántico pusieron a prueba el temple de más de 90 tripulantes. Cada ola amenazaba con devorar los sueños de una corona y el misterio de un nuevo mundo.

ESCENA 3 — Tierra Firme
Al clarear el día 12 de octubre, desde la cofa de la Pinta resonó un grito que quebró el horizonte. Eran exactamente las 2 de la madrugada cuando la historia cambió para siempre.`;
