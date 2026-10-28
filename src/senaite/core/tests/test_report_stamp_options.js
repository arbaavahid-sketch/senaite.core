const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
let listener;
let listeners = 0;
const requests = [];
const controller = {
  state: {report_options: {show_conditions: false, attachments_per_row: 3}},
  setState(update, callback) { Object.assign(this.state, update); callback(); },
  loadReports() { requests.push(JSON.parse(JSON.stringify(this.state.report_options))); }
};
const sandbox = {
  window: {impress: controller},
  document: {addEventListener(type, handler, capture) {
    assert.equal(type, 'change'); assert.equal(capture, true);
    listener = handler; listeners += 1;
  }}
};
const script = fs.readFileSync(process.env.STAMP_SCRIPT ||
  path.resolve(__dirname, '../browser/report_stamp_js/report_stamps.js'), 'utf8');
vm.runInNewContext(script, sandbox);
vm.runInNewContext(script, sandbox);
assert.equal(listeners, 1);
for (const value of ['valid', 'invalid', 'info', 'none', 'valid']) {
  let stopped = false;
  listener({target: {id: 'tppc-report-stamp', name: 'tppc_stamp', value},
            stopImmediatePropagation() { stopped = true; }});
  assert.equal(stopped, true);
  assert.equal(controller.state.report_options.tppc_stamp, value);
  assert.equal(requests.at(-1).tppc_stamp, value);
  assert.equal(controller.state.report_options.show_conditions, false);
  assert.equal(controller.state.report_options.attachments_per_row, 3);
  assert.equal(Object.hasOwn(controller.state, 'tppc_stamp'), false);
}
const count = requests.length;
listener({target: {id: 'show-remarks', name: 'show_remarks', value: 'on'},
          stopImmediatePropagation() { throw new Error('Unrelated event intercepted'); }});
assert.equal(requests.length, count);
listener({target: {id: 'tppc-report-stamp', name: 'tppc_stamp', value: 'untrusted'},
          stopImmediatePropagation() {}});
assert.equal(requests.at(-1).tppc_stamp, 'none');
console.log('PASS repeated choices, clearing, immutable report options, unrelated controls and duplicate registration');
