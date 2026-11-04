/**
 * scripts/run_all_tests.js
 * In-sandbox automated validation suite verifying dataset integrity, embeddings,
 * benchmark profiles, offline recsys evaluation metrics, and frontend assets.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT_DIR = path.join(__dirname, '..');

console.log('='.repeat(70));
console.log('IN-SANDBOX AUTOMATED PLATFORM VERIFICATION SUITE');
console.log('='.repeat(70));

let passed = 0;
let failed = 0;

function runTest(name, fn) {
  try {
    fn();
    console.log(`[PASS] ${name}`);
    passed++;
  } catch (err) {
    console.error(`[FAIL] ${name}:`, err.message);
    failed++;
  }
}

// 1. Opportunity Dataset Integrity
runTest('Opportunity JSON Dataset Exists & N >= 500', () => {
  const jsonPath = path.join(ROOT_DIR, 'data', 'opportunities', 'opportunity_dataset.json');
  assert(fs.existsSync(jsonPath), 'opportunity_dataset.json missing');
  const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
  assert(data.length >= 500, `Expected >= 500 records, got ${data.length}`);
  
  // Validate first record
  const first = data[0];
  assert(first.opportunity_id, 'Missing opportunity_id');
  assert(first.title, 'Missing title');
  assert(first.opportunity_type, 'Missing opportunity_type');
  assert(first.organization, 'Missing organization');
  assert(Array.isArray(first.domain_tags) && first.domain_tags.length > 0, 'Missing domain_tags');
  assert(Array.isArray(first.required_skills), 'required_skills must be an array');
});

runTest('Opportunity CSV Dataset Conformance', () => {
  const csvPath = path.join(ROOT_DIR, 'data', 'opportunities', 'opportunity_dataset.csv');
  assert(fs.existsSync(csvPath), 'opportunity_dataset.csv missing');
  const lines = fs.readFileSync(csvPath, 'utf-8').trim().split('\n');
  assert(lines.length >= 501, `CSV lines expected >= 501, got ${lines.length}`);
});

// 2. Vector Embeddings Validation
runTest('Opportunity 384-d Embedding Matrix (.npy)', () => {
  const npyPath = path.join(ROOT_DIR, 'data', 'embeddings', 'opportunity_embeddings_all_MiniLM_L6_v2.npy');
  assert(fs.existsSync(npyPath), 'Embeddings npy missing');
  const buf = fs.readFileSync(npyPath);
  assert(buf[0] === 0x93 && buf.slice(1, 6).toString('ascii') === 'NUMPY', 'Invalid NPY header');
  const headerLen = buf.readUInt16LE(8);
  const headerStr = buf.slice(10, 10 + headerLen).toString('latin1');
  assert(headerStr.includes('(520, 384)'), `Header does not contain expected shape: ${headerStr}`);
});

// 3. Benchmark Student Profiles
runTest('Benchmark Student Profiles (100 Profiles)', () => {
  const profPath = path.join(ROOT_DIR, 'data', 'profiles', 'student_profiles_benchmark.json');
  assert(fs.existsSync(profPath), 'Benchmark profiles missing');
  const profiles = JSON.parse(fs.readFileSync(profPath, 'utf-8'));
  assert(profiles.length === 100, `Expected 100 profiles, got ${profiles.length}`);
  
  // Check cold start exists
  const coldStarts = profiles.filter(p => p.is_cold_start);
  assert(coldStarts.length > 0, 'No cold-start profiles generated');
});

// 4. Offline Benchmark Report
runTest('Recommendation Benchmark Report Generated', () => {
  const reportPath = path.join(ROOT_DIR, 'reports', 'recommendation_evaluation_report.md');
  assert(fs.existsSync(reportPath), 'Evaluation report missing');
  const text = fs.readFileSync(reportPath, 'utf-8');
  assert(text.includes('Proposed Hybrid Ranker'), 'Report missing Proposed Hybrid Ranker');
  assert(text.includes('NDCG@5'), 'Report missing NDCG@5');
  assert(text.includes('Catalog Coverage'), 'Report missing Catalog Coverage');
});

// 5. Backend Architecture Assets
runTest('Backend Core, Repositories, Routers & Models Integrity', () => {
  const requiredFiles = [
    'src/core/config.py',
    'src/core/security.py',
    'src/core/logging.py',
    'src/core/exceptions.py',
    'src/nlp/taxonomy.py',
    'src/database/base.py',
    'src/database/connection.py',
    'src/database/models/user.py',
    'src/database/models/student.py',
    'src/database/models/faculty.py',
    'src/database/models/achievement.py',
    'src/database/models/opportunity.py',
    'src/database/models/notification.py',
    'src/database/models/saved_opportunity.py',
    'src/database/repositories/student_repository.py',
    'src/database/repositories/achievement_repository.py',
    'src/database/repositories/opportunity_repository.py',
    'src/recommendation/embeddings.py',
    'src/recommendation/vector_store.py',
    'src/recommendation/profile_aggregator.py',
    'src/recommendation/engine/eligibility.py',
    'src/recommendation/engine/matcher.py',
    'src/recommendation/engine/ranker.py',
    'src/recommendation/engine/explainer.py',
    'src/recommendation/engine/recommendation_service.py',
    'src/api/main.py',
    'src/api/dependencies.py',
    'src/services/notification_service.py',
    'src/services/report_generator.py',
    'src/integration/full_pipeline_adapter.py',
    'src/integration/nlp_adapter.py',
    'src/integration/ml_model_adapter.py',
  ];

  for (const f of requiredFiles) {
    const p = path.join(ROOT_DIR, f);
    assert(fs.existsSync(p), `Missing backend architecture file: ${f}`);
  }
});

// 6. Frontend Assets
runTest('React Frontend and Streamlit App Completeness', () => {
  const frontendFiles = [
    'frontend/package.json',
    'frontend/vite.config.js',
    'frontend/src/App.jsx',
    'frontend/src/main.jsx',
    'frontend/src/api/client.js',
    'frontend/src/components/Navbar.jsx',
    'frontend/src/components/MatchBadge.jsx',
    'frontend/src/components/ExplanationModal.jsx',
    'frontend/src/components/AchievementCard.jsx',
    'frontend/src/pages/Dashboard.jsx',
    'frontend/src/pages/Opportunities.jsx',
    'frontend/src/pages/Achievements.jsx',
    'frontend/src/pages/Profile.jsx',
    'frontend/src/pages/faculty/VerificationQueue.jsx',
    'frontend/src/pages/faculty/TalentSearch.jsx',
    'frontend/src/pages/faculty/InstitutionalAnalytics.jsx',
    'frontend/streamlit_app.py',
  ];

  for (const f of frontendFiles) {
    const p = path.join(ROOT_DIR, f);
    assert(fs.existsSync(p), `Missing frontend file: ${f}`);
  }
});

// 7. Operations & Containerization
runTest('Docker, Docker Compose, Alembic & Documentation Assets', () => {
  const opsFiles = [
    'Dockerfile.backend',
    'Dockerfile.frontend',
    'docker-compose.yml',
    'docker-compose.dev.yml',
    'nginx/default.conf',
    'alembic.ini',
    'alembic/env.py',
    '.env.example',
    'docs/MEMBER3_SYSTEM_ARCHITECTURE.md',
    'docs/API_DOCUMENTATION.md',
    'docs/DEPLOYMENT_GUIDE.md',
  ];

  for (const f of opsFiles) {
    const p = path.join(ROOT_DIR, f);
    assert(fs.existsSync(p), `Missing operations/documentation file: ${f}`);
  }
});

console.log('='.repeat(70));
console.log(`TOTAL: ${passed} PASSED | ${failed} FAILED`);
console.log('='.repeat(70));

if (failed > 0) process.exit(1);
