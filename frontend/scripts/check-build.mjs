import assert from 'node:assert/strict';
import { readdir } from 'node:fs/promises';

// Import the generated module graph, rather than source modules, so a vendor
// cycle that breaks React initialization also fails the production image build.
const assets = new URL('../dist/assets/', import.meta.url);
const chunks = await readdir(assets);
const vendorName = chunks.find(name => /^vendor-.*\.js$/.test(name));
assert.ok(vendorName, 'The production React vendor chunk is missing');
const vendor = await import(new URL(vendorName, assets).href);
assert.ok(Object.values(vendor).some(value =>
  typeof value?.createContext === 'function' && typeof value?.useState === 'function'),
  'React did not initialize in the generated vendor module graph');
console.log('Production React vendor initialization verified');
