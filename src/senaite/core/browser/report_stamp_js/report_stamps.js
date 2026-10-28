/* IMPRESS custom resource: keep repeated stamp selections in report_options. */
(function () {
  'use strict';
  if (window.tppcReportStampListenerInstalled) return;
  window.tppcReportStampListenerInstalled = true;

  document.addEventListener('change', function (event) {
    var target = event.target;
    if (!target || target.id !== 'tppc-report-stamp' || target.name !== 'tppc_stamp') return;
    var controller = window.impress;
    if (!controller || !controller.state || typeof controller.setState !== 'function' ||
        typeof controller.loadReports !== 'function') return;
    var value = target.value;
    if (['none', 'valid', 'invalid', 'info'].indexOf(value) === -1) value = 'none';
    var options = Object.assign({}, controller.state.report_options || {});
    options.tppc_stamp = value;
    // Handle this custom control before the stock native change listener.
    // It must remain inside report_options on every change, not become a
    // root-level controller key after its first selection.
    event.stopImmediatePropagation();
    controller.setState({report_options: options}, function () {
      controller.loadReports();
    });
  }, true);
}());
