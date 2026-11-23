// Helper for test_parity.py: runs the browser scripts under Node. Reads JSON on stdin, writes JSON on stdout.
const path = require('path');
const fh = require(path.join('..', 'src', 'listing_kit', 'static', 'checker.js'));
const mortgage = require(path.join('..', 'src', 'listing_kit', 'static', 'mortgage.js'));

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (c) => { input += c; });
process.stdin.on('end', () => {
  const req = JSON.parse(input);
  let out;
  if (req.op === 'check') {
    out = req.texts.map((t) => fh.check(t, req.rules).map((f) => [f.rule_id, f.start, f.end, f.severity]));
  } else {
    out = req.cases.map((c) => mortgage.monthlyPayment(c));
  }
  process.stdout.write(JSON.stringify(out));
});
