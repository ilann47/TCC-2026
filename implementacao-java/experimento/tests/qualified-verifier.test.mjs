import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {verifyAmendment} from '../verify-reduced.mjs';

const original=JSON.parse(fs.readFileSync('experimento/FROZEN-PROTOCOL.json','utf8'));
test('A1 validates its complete published inventory',()=>assert.equal(verifyAmendment(original),true));
test('A1 rejects changed measurement reference',()=>{
  const f=structuredClone(original);f.reference_rate=24;
  assert.throws(()=>verifyAmendment(f));
});
test('A1 rejects changed analysis source hash',()=>{
  const f=structuredClone(original);f.analytical_amendment.files.analysis.sha256='0'.repeat(64);
  assert.throws(()=>verifyAmendment(f));
});
test('A1 rejects incomplete provenance',()=>{
  const f=structuredClone(original);delete f.analytical_amendment.files.baseline_audit;
  assert.throws(()=>verifyAmendment(f));
});
test('A1 rejects a different controller than the adoption audit',()=>{
  const f=structuredClone(original);f.controller_sha256='0'.repeat(64);
  assert.throws(()=>verifyAmendment(f));
});
test('A1 rejects arbitrary revision and path traversal',()=>{
  let f=structuredClone(original);f.analytical_amendment.revision='other';
  assert.throws(()=>verifyAmendment(f));
  f=structuredClone(original);f.analytical_amendment.files.analysis.path='../outside';
  assert.throws(()=>verifyAmendment(f));
});
test('original schema is distinguishable from analytical resumption',()=>{
  const f=structuredClone(original);delete f.analytical_amendment;
  assert.equal(verifyAmendment(f),false);
});
