(function () {
  if (window.App32DateUtils) return;

  function parseCalendarDate(value) {
    if (value === null || value === undefined || value === '') return null;
    const raw = String(value).trim();
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (match) {
      const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
      return Number.isNaN(date.getTime()) ? null : date;
    }
    const date = new Date(raw);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function todayIso(date = new Date()) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  function startOfLocalDay(value = new Date()) {
    const date = value instanceof Date ? value : parseCalendarDate(value);
    if (!date || Number.isNaN(date.getTime())) return null;
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  function formatCalendarDatePtBr(value, fallback = '—') {
    const date = parseCalendarDate(value);
    return date ? date.toLocaleDateString('pt-BR') : fallback;
  }

  function formatCalendarDateTimePtBr(value, fallback = '—') {
    const date = parseCalendarDate(value);
    return date ? date.toLocaleString('pt-BR') : fallback;
  }

  window.App32DateUtils = {
    parseCalendarDate,
    todayIso,
    startOfLocalDay,
    formatCalendarDatePtBr,
    formatCalendarDateTimePtBr,
  };
})();
