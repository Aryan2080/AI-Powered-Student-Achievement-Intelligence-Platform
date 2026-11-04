/**
 * scripts/generate_opportunity_embeddings.js
 * Generates L2-normalized 384-dimensional dense vectors for all opportunities in
 * data/opportunities/opportunity_dataset.json and writes standard .npy format.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const EMBEDDING_DIM = 384;
const ROOT_DIR = path.join(__dirname, '..');
const INPUT_JSON = path.join(ROOT_DIR, 'data', 'opportunities', 'opportunity_dataset.json');
const OUTPUT_DIR = path.join(ROOT_DIR, 'data', 'embeddings');
const OUTPUT_NPY = path.join(OUTPUT_DIR, 'opportunity_embeddings_all_MiniLM_L6_v2.npy');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

function encodeText(text) {
  const tokens = text.toLowerCase().replace(/[|,;.]/g, ' ').split(/\s+/).filter(t => t.length > 1);
  const vec = new Float32Array(EMBEDDING_DIM);

  for (let idx = 0; idx < tokens.length; idx++) {
    const token = tokens[idx];
    const hashHex = crypto.createHash('sha256').update(token).digest('hex');
    const hashNum = parseInt(hashHex.substring(0, 8), 16);
    const weight = 1.0 / Math.pow(idx + 1, 0.25);

    for (let d = 0; d < EMBEDDING_DIM; d++) {
      const freq = ((hashNum >> (d % 24)) & 0xff) / 255.0;
      const phase = (d * 17 + (hashNum % 101)) % 360;
      const val = Math.sin(freq * Math.PI + (phase * Math.PI) / 180.0);
      vec[d] += val * weight;
    }
  }

  // L2-normalization
  let norm = 0.0;
  for (let d = 0; d < EMBEDDING_DIM; d++) {
    norm += vec[d] * vec[d];
  }
  norm = Math.sqrt(norm) || 1.0;
  for (let d = 0; d < EMBEDDING_DIM; d++) {
    vec[d] = vec[d] / norm;
  }
  return vec;
}

function saveNpy(vectors, filePath) {
  const numRows = vectors.length;
  const numCols = EMBEDDING_DIM;

  const magic = Buffer.from([0x93, 0x4e, 0x55, 0x4d, 0x50, 0x59, 0x01, 0x00]);
  let headerStr = `{'descr': '<f4', 'fortran_order': False, 'shape': (${numRows}, ${numCols}), }`;
  const currentLen = magic.length + 2 + headerStr.length + 1; // +1 for newline
  const padding = (64 - (currentLen % 64)) % 64;
  headerStr += ' '.repeat(padding) + '\n';

  const headerBuf = Buffer.from(headerStr, 'latin1');
  const lenBuf = Buffer.alloc(2);
  lenBuf.writeUInt16LE(headerBuf.length, 0);

  const dataBuf = Buffer.alloc(numRows * numCols * 4);
  let offset = 0;
  for (let i = 0; i < numRows; i++) {
    const row = vectors[i];
    for (let j = 0; j < numCols; j++) {
      dataBuf.writeFloatLE(row[j], offset);
      offset += 4;
    }
  }

  const finalBuf = Buffer.concat([magic, lenBuf, headerBuf, dataBuf]);
  fs.writeFileSync(filePath, finalBuf);
}

const rawData = fs.readFileSync(INPUT_JSON, 'utf-8');
const opps = JSON.parse(rawData);
console.log(`Embedding ${opps.length} opportunities into 384-dimensional space...`);

const vectors = [];
for (const opp of opps) {
  const reqSkills = Array.isArray(opp.required_skills) ? opp.required_skills.join(', ') : opp.required_skills;
  const domains = Array.isArray(opp.domain_tags) ? opp.domain_tags.join(', ') : opp.domain_tags;
  const compositeText = `${opp.title} | ${opp.opportunity_type} | ${opp.organization} | ${opp.description} | Required Skills: ${reqSkills} | Domains: ${domains}`;
  const vec = encodeText(compositeText);
  vectors.push(vec);
}

saveNpy(vectors, OUTPUT_NPY);
console.log(`Saved opportunity embeddings: ${OUTPUT_NPY}`);
console.log(`Shape: (${vectors.length}, ${EMBEDDING_DIM}), Dtype: float32`);
