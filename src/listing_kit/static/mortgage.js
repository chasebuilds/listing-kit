/* Monthly payment estimate. Same formula as listing_kit/mortgage.py. An estimate, not a quote. */
(function (root) {
  'use strict';
  function monthlyPayment(o) {
    var loan = o.price * (1 - o.downPct / 100);
    var n = o.years * 12;
    var r = o.ratePct / 100 / 12;
    var pi = r === 0 ? loan / n : (loan * r) / (1 - Math.pow(1 + r, -n));
    var tax = (o.price * (o.taxRatePct || 0)) / 100 / 12;
    var ins = (o.insurancePerYear || 0) / 12;
    var hoa = o.hoaMonthly || 0;
    return { loan: loan, principal_interest: pi, tax: tax, insurance: ins, hoa: hoa, total: pi + tax + ins + hoa };
  }
  var api = { monthlyPayment: monthlyPayment };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Mortgage = api;
})(typeof window !== 'undefined' ? window : globalThis);
