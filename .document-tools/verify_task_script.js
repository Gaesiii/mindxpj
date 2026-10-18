// Offline checks for the prepared Apps Script; not a live Google execution.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const folder = path.join(__dirname, '..', 'docs', 'project-management');
const source = fs.readFileSync(path.join(folder, 'create_task_sheet.gs'), 'utf8');
const ledger = JSON.parse(fs.readFileSync(path.join(folder, 'tasks.json'), 'utf8'));
const context = vm.createContext({console, Date});
vm.runInContext(source + '\nglobalThis.taskData = TASKS;', context);
assert.deepStrictEqual(JSON.parse(JSON.stringify(context.taskData)), ledger.tasks);
assert(context.readyFormula_(ledger.tasks.find(t => t.id === 'A16'), 32, 41).includes('Config!$B$6="APPROVED"'));
assert(context.readyFormula_(ledger.tasks[0], 2, 41).includes('IF(TRUE,'));

function simulate(taskId, completed, approved) {
  const rows = ledger.tasks.map(t => {
    const row = Array(21).fill('');
    row[0] = t.id;
    row[2] = t.phase;
    row[11] = t.deps.join(', ');
    row[14] = completed.includes(t.id) || t.id === taskId;
    return row;
  });
  let toasts = 0;
  const index = rows.findIndex(r => r[0] === taskId);
  const sheet = {
    getName: () => 'Tasks',
    getRange: (row, col, count, width) => {
      if (count === ledger.tasks.length && width === 21) return {getValues: () => rows};
      return {
        setValue(value) { rows[row - 2][col - 1] = value; return this; },
        clearContent() { rows[row - 2][col - 1] = ''; return this; }
      };
    }
  };
  const event = {
    range: {
      getSheet: () => sheet, getColumn: () => 15, getLastColumn: () => 15,
      getRow: () => index + 2, getLastRow: () => index + 2
    },
    source: {
      getSheetByName: () => ({getRange: () => ({getValue: () => approved ? 'APPROVED' : 'NOT_APPROVED'})}),
      toast: () => { toasts++; }
    }
  };
  context.handleTaskEdit(event);
  return {checked: rows[index][14], timestamp: rows[index][19], toasts};
}
const first = simulate('A01', [], false);
assert.strictEqual(first.checked, true);
assert(first.timestamp instanceof Date);
const blocked = simulate('A02', [], false);
assert.strictEqual(blocked.checked, false);
assert.strictEqual(blocked.toasts, 1);
const apiIds = ledger.tasks.filter(t => t.phase === 'API').map(t => t.id);
assert.strictEqual(simulate('A16', apiIds, false).checked, false);
const allowed = simulate('A16', apiIds, true);
assert.strictEqual(allowed.checked, true);
assert(allowed.timestamp instanceof Date);
assert.strictEqual(simulate('A16', apiIds.filter(id => id !== 'B12'), true).checked, false);
console.log('PASS: Apps Script parses; task constants match tasks.json.');
console.log('PASS: offline edit simulation rejects unmet dependencies and locked API gate.');
console.log('PASS: offline edit simulation accepts ready tasks and records finish time.');
console.log('Limit: no live Google spreadsheet was created or edited.');
