// Self-contained function serialized into Chromium. Conference values are data.
// Date cells are NEVER ellipsized: an unsupported density/width fails the build.
export function drawShareCard(card) {
  const deadlines = card.deadlines || [];
  const rounds = [...new Set(deadlines.map(d => d.round))].sort((a, b) => a - b);
  if (rounds.length > 12) throw new Error(`${card.title}: ${rounds.length} rounds exceed the 12-round readable share-card limit; no dates omitted`);
  const fields = ['abstract_deadline', 'deadline', 'rebuttal_deadline', 'decision_deadline']
    .filter(field => deadlines.some(d => d.field === field));
  if (deadlines.some(d => !fields.includes(d.field))) throw new Error(`${card.title}: unsupported deadline type`);
  const canvas = document.createElement('canvas'); canvas.width = 1200; canvas.height = 630;
  const ctx = canvas.getContext('2d', {alpha: false});
  ctx.fillStyle = window.shareBackground; ctx.fillRect(0, 0, 1200, 630);
  ctx.textBaseline = 'top';
  const painted = [], muted = '#67727e', accent = '#d9554f';
  function line(value, x, y, size, color = window.shareInk, width = 1040, strict = false) {
    let text = String(value || '').replace(/\s+/g, ' ').trim();
    ctx.font = `${size}px ${window.shareFont}`; ctx.fillStyle = color;
    if (strict && ctx.measureText(text).width > width) throw new Error(`${card.title}: deadline text cannot fit without truncation: ${text}`);
    if (!strict && ctx.measureText(text).width > width) {
      while (text && ctx.measureText(text + '…').width > width) text = text.slice(0, -1);
      text += '…';
    }
    if (y + size > 625) throw new Error(`${card.title}: share-card vertical overflow`);
    ctx.fillText(text, x, y);
    return text;
  }
  function rule(y) {
    ctx.strokeStyle = '#e5ded6'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(64, y); ctx.lineTo(1136, y); ctx.stroke();
  }
  line('CCFDDL Open Deadlines', 64, 30, 25, accent);
  line(card.title, 64, 73, 48);
  line(card.description, 64, 132, 21, muted);
  line(card.category, 64, 169, 19, muted);
  rule(202);
  line(rounds.length === 1 && card.round_count > 1 ? `DEADLINES · Round ${rounds[0]}` : 'DEADLINES', 64, 220, 20);
  line(`Timezone: ${card.timezone || 'not listed'}`, 620, 220, 20, muted, 516, true);
  if (!deadlines.length) {
    line('Deadline dates to be announced', 64, 300, 28, muted);
  } else if (rounds.length === 1) {
    const rowHeight = 64;
    deadlines.forEach((item, index) => {
      const y = 271 + index * rowHeight;
      line(item.label, 64, y, 26, window.shareInk, 400, true);
      line(item.raw, 512, y, 26, window.shareInk, 624, true);
      painted.push(item);
      rule(y + 47);
    });
  } else {
    const roundWidth = 88, left = 64 + roundWidth;
    const width = (1072 - roundWidth) / fields.length;
    const splitTime = rounds.length <= 6;
    const font = fields.length <= 2 ? 23 : 20;
    const rowHeight = splitTime ? Math.min(60, 284 / rounds.length) : 284 / rounds.length;
    line('Round', 64, 258, 18, muted, roundWidth);
    fields.forEach((field, i) => line(deadlines.find(d => d.field === field).label, left + i * width, 258, 20, muted, width - 10, true));
    rounds.forEach((round, row) => {
      const y = 291 + row * rowHeight;
      line(`R${round}`, 64, y, 20, muted, roundWidth, true);
      fields.forEach((field, i) => {
        const x = left + i * width;
        const matches = deadlines.filter(d => d.round === round && d.field === field);
        if (matches.length > 1) throw new Error(`${card.title}: duplicate round/field would hide a date`);
        const item = matches[0];
        if (!item) { line('—', x, y, font, muted, width - 10); return; }
        if (splitTime) {
          const [date, time] = item.raw.split(' ');
          line(date, x, y, font, window.shareInk, width - 10, true);
          if (time) line(time, x, y + 26, 18, muted, width - 10, true);
        } else {
          line(item.raw, x, y, Math.min(font, 19), window.shareInk, width - 10, true);
        }
        painted.push(item);
      });
    });
  }
  rule(580);
  line(`Conference: ${card.date || 'dates not listed'} · ${card.place || 'location not listed'}`, 64, 595, 15, muted, 900);
  line('ccfddl.com', 964, 593, 22, accent, 172);
  return {encoded: canvas.toDataURL('image/png').split(',')[1],
    report: {renderedDeadlines: painted.length, deadlines: painted, rounds: rounds.length, timezone: card.timezone}};
}
