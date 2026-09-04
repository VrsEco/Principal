(function () {
  if (window.App32InputFormatters) return;

  const DIGITS = /\D/g;

  function onlyDigits(value) {
    return String(value ?? '').replace(DIGITS, '');
  }

  function cleanNumeric(value, { allowNegative = false } = {}) {
    let text = String(value ?? '').trim().replace(/\s+/g, '');
    text = text.replace(/\./g, '').replace(/,/g, '.').replace(/[^0-9.\-]/g, '');
    if (!allowNegative) text = text.replace(/\-/g, '');
    return text;
  }

  function normalizeNumericText(value, { decimals = 2, allowNegative = false, useGrouping = false } = {}) {
    let text = String(value ?? '').trim();
    if (!text) return '';
    text = text.replace(/\s+/g, '').replace(/\./g, '').replace(/,/g, '.').replace(/[^0-9.\-]/g, '');
    if (!allowNegative) text = text.replace(/\-/g, '');
    const negative = allowNegative && text.startsWith('-');
    text = text.replace(/\-/g, '');
    if (!/[0-9]/.test(text)) return negative ? '-' : '';
    const parts = text.split('.');
    const integerPart = (parts.shift() || '0').replace(/^0+(?=\d)/, '') || '0';
    const decimalPartRaw = parts.join('');
    const decimalPart = decimals > 0 ? decimalPartRaw.slice(0, decimals) : '';
    const grouped = useGrouping
      ? integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
      : integerPart;
    const signal = negative ? '-' : '';
    if (decimals > 0 && decimalPart) return `${signal}${grouped},${decimalPart}`;
    return `${signal}${grouped}`;
  }

  function formatCurrency(value) {
    const raw = String(value ?? '').trim();
    const negative = /^\s*-/.test(raw) || /^\s*\(/.test(raw);
    const digits = onlyDigits(value);
    if (!digits) return negative ? '-' : '';
    const cents = digits.padStart(3, '0');
    const integerPart = cents.slice(0, -2).replace(/^0+(?=\d)/, '') || '0';
    const formatted = `${integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${cents.slice(-2)}`;
    return negative && formatted !== '0,00' ? `-${formatted}` : formatted;
  }

  function parseCurrency(value) {
    const normalized = String(value ?? '').replace(/\./g, '').replace(',', '.').replace(/[^0-9.\-]/g, '');
    return normalized ? Number(normalized) : 0;
  }

  function formatInteger(value) {
    const digits = onlyDigits(value);
    if (!digits) return '';
    return digits.replace(/^0+(?=\d)/, '').replace(/\B(?=(\d{3})+(?!\d))/g, '.') || '0';
  }

  function parseInteger(value) {
    const digits = onlyDigits(value);
    return digits ? String(Number(digits)) : '';
  }

  function formatDecimal(value, decimals = 2) {
    return normalizeNumericText(value, { decimals, allowNegative: true, useGrouping: false });
  }

  function parseDecimal(value) {
    const normalized = String(value ?? '').replace(/\./g, '').replace(',', '.').replace(/[^0-9.\-]/g, '');
    return normalized ? Number(normalized) : 0;
  }

  function isCurrencyUnit(unit) {
    const normalized = String(unit ?? '').trim().toLowerCase();
    return normalized === 'r$'
      || normalized === 'brl'
      || normalized.includes('moeda')
      || normalized.includes('real');
  }

  function formatNumberBR(value, { minimumFractionDigits = 2, maximumFractionDigits = 2, empty = '—' } = {}) {
    if (value === null || value === undefined || value === '') return empty;
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return empty;
    return numeric.toLocaleString('pt-BR', { minimumFractionDigits, maximumFractionDigits });
  }

  function formatIndicatorValue(value, unit, { empty = '—' } = {}) {
    if (value === null || value === undefined || value === '') return empty;
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return empty;
    if (isCurrencyUnit(unit)) {
      return numeric.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }
    const formatted = formatNumberBR(numeric, { empty });
    const suffix = String(unit ?? '').trim();
    if (!suffix) return formatted;
    return suffix === '%' ? `${formatted}%` : `${formatted} ${suffix}`;
  }

  function formatPercent(value) {
    const formatted = normalizeNumericText(value, { decimals: 2, useGrouping: false });
    return formatted ? `${formatted}%` : '';
  }

  function parsePercent(value) {
    return parseDecimal(String(value ?? '').replace('%', ''));
  }

  function decimalHoursToClock(value) {
    const numeric = Number(value ?? '');
    if (!Number.isFinite(numeric)) return '';
    const totalMinutes = Math.round(numeric * 60);
    return minutesToClock(totalMinutes);
  }

  function minutesToClock(totalMinutes) {
    const minutesInt = Math.max(0, Number(totalMinutes || 0));
    const hours = Math.floor(minutesInt / 60);
    const minutes = minutesInt % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  }

  function normalizeClockInput(value) {
    const digits = onlyDigits(value).slice(0, 4);
    if (!digits) return '';
    if (digits.length <= 2) return digits;
    const hours = digits.slice(0, -2);
    const minutes = digits.slice(-2);
    return `${hours}:${minutes}`;
  }

  function parseClockToMinutes(value) {
    const normalized = normalizeClockInput(value);
    if (!normalized.includes(':')) return 0;
    const [hoursRaw, minutesRaw] = normalized.split(':');
    const hours = Number(hoursRaw || 0);
    const minutes = Number((minutesRaw || '0').slice(0, 2));
    if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return 0;
    return Math.max(0, hours * 60 + Math.min(minutes, 59));
  }

  function parseClockToDecimalHours(value) {
    const raw = String(value ?? '').trim();
    if (!raw) return 0;

    if (!raw.includes(':')) {
      const compact = raw.replace(/\s+/g, '');
      if (/[,.]/.test(compact)) {
        const normalizedDecimal = compact.includes(',')
          ? compact.replace(/\./g, '').replace(',', '.')
          : compact;
        const decimal = Number(normalizedDecimal.replace(/[^0-9.\-]/g, ''));
        if (Number.isFinite(decimal)) {
          return Math.max(0, Math.round((decimal + Number.EPSILON) * 100) / 100);
        }
      }

      const digits = onlyDigits(raw);
      if (digits && digits.length <= 2) {
        return Number(digits);
      }
      if (digits && digits.length > 2) {
        const clockValue = normalizeClockInput(digits);
        const totalMinutesFromDigits = parseClockToMinutes(clockValue);
        return Math.round(((totalMinutesFromDigits / 60) + Number.EPSILON) * 100) / 100;
      }
    }

    const totalMinutes = parseClockToMinutes(raw);
    return Math.round(((totalMinutes / 60) + Number.EPSILON) * 100) / 100;
  }

  function isValidDateParts(day, month, year) {
    const dayNumber = Number(day);
    const monthNumber = Number(month);
    const yearNumber = Number(year);
    const candidate = new Date(yearNumber, monthNumber - 1, dayNumber);
    return (
      candidate.getFullYear() === yearNumber
      && candidate.getMonth() + 1 === monthNumber
      && candidate.getDate() === dayNumber
    );
  }

  function formatDateYMD(value) {
    const raw = String(value ?? '').trim();
    if (!raw) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      const [year, month, day] = raw.split('-');
      return `${day}/${month}/${year}`;
    }
    const digits = onlyDigits(raw).slice(0, 8);
    if (digits.length <= 2) return digits;
    if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
    return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
  }

  function parseDateYMD(value) {
    const digits = onlyDigits(value).slice(0, 8);
    if (digits.length !== 8) return '';
    const day = digits.slice(0, 2);
    const month = digits.slice(2, 4);
    const year = digits.slice(4, 8);
    if (!isValidDateParts(day, month, year)) return '';
    return `${year}-${month}-${day}`;
  }

  function getFormat(element) {
    return String(element?.dataset?.format || '').trim().toLowerCase();
  }

  function formatValueByType(format, value) {
    if (value == null || value === '') return '';
    switch (format) {
      case 'currency': return formatCurrency(value);
      case 'integer':
      case 'score':
      case 'weight': return formatInteger(value);
      case 'decimal':
      case 'confidence':
      case 'note': return formatDecimal(value, 2);
      case 'percent': return formatPercent(value);
      case 'hours-decimal':
        if (String(value).includes(':')) return normalizeClockInput(value);
        return decimalHoursToClock(value);
      case 'duration-minutes':
        if (String(value).includes(':')) return normalizeClockInput(value);
        return minutesToClock(Number(value || 0));
      case 'date-ymd': return formatDateYMD(value);
      default: return value;
    }
  }

  function normalizeForSubmit(element) {
    const format = getFormat(element);
    const value = element.value;
    switch (format) {
      case 'currency': return parseCurrency(value).toFixed(2);
      case 'integer':
      case 'score':
      case 'weight': return parseInteger(value);
      case 'decimal':
      case 'confidence':
      case 'note': return String(parseDecimal(value));
      case 'percent': return String(parsePercent(value));
      case 'hours-decimal': return String(parseClockToDecimalHours(value));
      case 'duration-minutes': return String(parseClockToMinutes(value));
      case 'date-ymd': return parseDateYMD(value);
      default: return value;
    }
  }

  function bindInput(element) {
    if (!element || element.dataset.formatBound === '1') return;
    if (!getFormat(element)) return;
    element.dataset.formatBound = '1';

    const applyInputContract = () => {
      const format = getFormat(element);
      if (element.tagName === 'INPUT' && ['currency', 'integer', 'score', 'weight', 'decimal', 'confidence', 'note', 'percent', 'hours-decimal', 'duration-minutes', 'date-ymd'].includes(format)) {
        element.type = 'text';
      }
      if (format === 'currency' || format === 'integer' || format === 'score' || format === 'weight') {
        element.inputMode = 'numeric';
      } else if (format === 'decimal' || format === 'confidence' || format === 'note' || format === 'percent') {
        element.inputMode = 'decimal';
      } else if (format === 'hours-decimal' || format === 'duration-minutes' || format === 'date-ymd') {
        element.inputMode = 'numeric';
      }
    };

    const applyFormat = () => {
      applyInputContract();
      const format = getFormat(element);
      element.value = formatValueByType(format, element.value);
    };

    element.addEventListener('input', applyFormat);
    element.addEventListener('blur', applyFormat);
    applyInputContract();
    if (element.value) applyFormat();
  }

  function setFormat(element, format) {
    if (!element) return;
    element.dataset.format = format;
    bindInput(element);
    element.dispatchEvent(new Event('blur'));
  }

  function bindAll(root = document) {
    root.querySelectorAll('[data-format]').forEach(bindInput);
  }

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) return;
        if (node.matches?.('[data-format]')) bindInput(node);
        bindAll(node);
      });
    });
  });

  function normalizeFormElementValues(form) {
    const formatted = Array.from(form.querySelectorAll('[data-format]'));
    const snapshots = formatted.map((el) => ({ el, value: el.value }));
    formatted.forEach((el) => {
      const normalized = normalizeForSubmit(el);
      if (normalized !== '') el.value = normalized;
    });
    return () => snapshots.forEach(({ el, value }) => { el.value = value; });
  }

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const restore = normalizeFormElementValues(form);
    setTimeout(restore, 0);
  }, true);

  const NativeFormData = window.FormData;
  window.FormData = class extends NativeFormData {
    constructor(form, submitter) {
      let restore = null;
      if (form instanceof HTMLFormElement) {
        restore = normalizeFormElementValues(form);
      }
      super(form, submitter);
      if (restore) restore();
      if (form instanceof HTMLFormElement) {
        Array.from(form.querySelectorAll('[data-format][name]')).forEach((el) => {
          const normalized = normalizeForSubmit(el);
          this.set(el.name, normalized);
        });
      }
    }
  };

  window.App32InputFormatters = {
    bindAll,
    bindInput,
    setFormat,
    formatCurrency,
    formatIndicatorValue,
    formatNumberBR,
    formatValueByType,
    isCurrencyUnit,
    normalizeForSubmit,
    parseCurrency,
    parseDecimal,
    parsePercent,
    parseClockToMinutes,
    parseClockToDecimalHours,
    formatDateYMD,
    parseDateYMD,
    minutesToClock,
    decimalHoursToClock,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      bindAll(document);
      observer.observe(document.body, { childList: true, subtree: true });
    });
  } else {
    bindAll(document);
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();

