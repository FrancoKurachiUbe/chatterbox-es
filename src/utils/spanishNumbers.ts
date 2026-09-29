const UNITS = [
  "cero",
  "uno",
  "dos",
  "tres",
  "cuatro",
  "cinco",
  "seis",
  "siete",
  "ocho",
  "nueve"
];

const TEENS: Record<number, string> = {
  10: "diez",
  11: "once",
  12: "doce",
  13: "trece",
  14: "catorce",
  15: "quince",
  16: "dieciséis",
  17: "diecisiete",
  18: "dieciocho",
  19: "diecinueve"
};

const TENS: Record<number, string> = {
  20: "veinte",
  30: "treinta",
  40: "cuarenta",
  50: "cincuenta",
  60: "sesenta",
  70: "setenta",
  80: "ochenta",
  90: "noventa"
};

const HUNDREDS: Record<number, string> = {
  100: "cien",
  200: "doscientos",
  300: "trescientos",
  400: "cuatrocientos",
  500: "quinientos",
  600: "seiscientos",
  700: "setecientos",
  800: "ochocientos",
  900: "novecientos"
};

export function numberToSpanish(n: number): string {
  if (n < 0) return `menos ${numberToSpanish(Math.abs(n))}`;
  if (n < 10) return UNITS[n];
  if (n in TEENS) return TEENS[n];
  if (n < 30) return `veinti${UNITS[n - 20]}`;

  if (n < 100) {
    const tens = Math.floor(n / 10) * 10;
    const units = n % 10;
    if (units === 0) return TENS[tens];
    return `${TENS[tens]} y ${UNITS[units]}`;
  }

  if (n < 1000) {
    const hundreds = Math.floor(n / 100) * 100;
    const remainder = n % 100;
    if (n === 100) return "cien";
    const prefix = HUNDREDS[hundreds];
    if (remainder === 0) return prefix;
    return `${prefix} ${numberToSpanish(remainder)}`;
  }

  if (n < 2000) {
    const remainder = n % 1000;
    if (remainder === 0) return "mil";
    return `mil ${numberToSpanish(remainder)}`;
  }

  if (n < 1000000) {
    const thousands = Math.floor(n / 1000);
    const remainder = n % 1000;
    let result = `${numberToSpanish(thousands)} mil`;
    if (remainder) {
      result += ` ${numberToSpanish(remainder)}`;
    }
    return result;
  }

  return n.toString();
}

export function normalizeNumbersForTTS(text: string, languageId: string): string {
  if (languageId !== 'es') {
    return text;
  }

  return text.replace(/\b\d{1,6}\b/g, (match) => {
    try {
      const val = parseInt(match, 10);
      if (val > 999999) return match;
      return numberToSpanish(val);
    } catch {
      return match;
    }
  });
}
