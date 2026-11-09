import assert from 'node:assert/strict';
import test from 'node:test';
import { drawShareCard } from './share_card_canvas.mjs';

function render(card) {
  const painted = [];
  const context = {font: '', fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
    measureText(text) { return {width: [...text].length * parseFloat(this.font) * 0.6}; },
    fillText(text, x, y) { painted.push({text, x, y, size: parseFloat(this.font)}); }};
  globalThis.window = {shareFont: 'monospace', shareInk: '#2c3e50', shareBackground: '#faf9f7'};
  globalThis.document = {createElement: () => ({getContext: () => context, toDataURL: () => 'data:image/png;base64,test'})};
  const result = drawShareCard({title: 'TEST 2027', description: 'Description', category: 'CCF A', timezone: 'AoE', ...card});
  assert.ok(painted.every(p => p.y + p.size <= 630 && p.x >= 0));
  return {painted, ...result};
}
const fields = [['abstract_deadline', 'Abstract'], ['deadline', 'Paper'], ['rebuttal_deadline', 'Rebuttal'], ['decision_deadline', 'Decision']];
const deadline = (round, [field, label], raw = '2026-10-25 23:59:59') => ({round, field, label, raw});

test('AAAI has all four types and unchanged timestamps', () => {
  const deadlines = fields.map(f => deadline(1, f));
  const {report, painted} = render({deadlines});
  assert.deepEqual(report.deadlines, deadlines);
  assert.equal(painted.filter(p => p.text === '2026-10-25 23:59:59').length, 4);
  assert.ok(painted.some(p => p.text === 'Timezone: AoE'));
});
test('VLDB includes every one of 24 dates across 12 original rounds', () => {
  const deadlines = Array.from({length: 12}, (_, i) => fields.slice(0, 2).map(f => deadline(i + 1, f))).flat();
  const {report, painted} = render({deadlines, round_count: 12});
  assert.deepEqual(report.deadlines, deadlines);
  assert.equal(report.renderedDeadlines, 24);
  assert.ok(painted.some(p => p.text === 'R12'));
  assert.equal(painted.filter(p => p.text === '2026-10-25 23:59:59').length, 24);
});
test('SIGMOD preserves all dates and times in split-line cells', () => {
  const deadlines = Array.from({length: 4}, (_, i) => fields.map(f => deadline(i + 1, f))).flat();
  const {report, painted} = render({deadlines});
  assert.deepEqual(report.deadlines, deadlines);
  assert.equal(painted.filter(p => p.text === '2026-10-25').length, 16);
  assert.equal(painted.filter(p => p.text === '23:59:59').length, 16);
});
test('unknown dates have an explicit empty state, never invented timestamps', () => {
  const {report, painted} = render({deadlines: []});
  assert.equal(report.renderedDeadlines, 0);
  assert.ok(painted.some(p => p.text === 'Deadline dates to be announced'));
});
test('13 rounds fail explicitly instead of omitting data', () => {
  assert.throws(() => render({deadlines: Array.from({length: 13}, (_, i) => deadline(i + 1, fields[1]))}), /13 rounds.*limit; no dates omitted/);
});
test('long dates and duplicate fields cannot be silently truncated', () => {
  assert.throws(() => render({deadlines: [deadline(1, fields[0], 'X'.repeat(200))]}), /cannot fit without truncation/);
  assert.throws(() => render({deadlines: [deadline(1, fields[0]), deadline(1, fields[0]), deadline(2, fields[0])]}), /duplicate round\/field/);
});
test('text stays inert and noncontiguous source round identity survives', () => {
  const {painted} = render({title: '<img onerror=evil()>', round_count: 3, deadlines: [deadline(3, fields[1])]});
  assert.ok(painted.some(p => p.text === '<img onerror=evil()>'));
  assert.ok(painted.some(p => p.text === 'DEADLINES · Round 3'));
});
