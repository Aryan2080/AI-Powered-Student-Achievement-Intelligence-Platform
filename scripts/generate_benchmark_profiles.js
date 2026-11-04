/**
 * scripts/generate_benchmark_profiles.js
 * Generates 100 benchmark student profiles for offline recommendation evaluation.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT_DIR = path.join(__dirname, '..');
const OUTPUT_DIR = path.join(ROOT_DIR, 'data', 'profiles');
const OUTPUT_JSON = path.join(OUTPUT_DIR, 'student_profiles_benchmark.json');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

let seed = 101;
function random() {
  seed = (seed * 9301 + 49297) % 233280;
  return seed / 233280;
}
function choice(arr) {
  return arr[Math.floor(random() * arr.length)];
}
function sample(arr, n) {
  const shuffled = [...arr].sort(() => 0.5 - random());
  return shuffled.slice(0, n);
}

const DEPARTMENTS = [
  "Computer Science", "Information Technology",
  "Artificial Intelligence & Data Science", "Electrical Engineering",
  "Electronics & Communication", "Software Engineering"
];

const SKILLS_POOL = [
  "Python", "PyTorch", "TensorFlow", "OpenCV", "SQL", "PostgreSQL",
  "Docker", "Kubernetes", "AWS", "Linux", "Git", "React", "Node.js",
  "FastAPI", "C++", "Java", "Scikit-learn", "NLP", "Computer Vision",
  "Deep Learning", "Data Engineering", "Cybersecurity", "REST API"
];

const DOMAINS_POOL = [
  "lbl_domain_ai", "lbl_domain_ml", "lbl_domain_nlp", "lbl_domain_cv",
  "lbl_domain_security", "lbl_domain_systems", "lbl_domain_web",
  "lbl_domain_data", "lbl_domain_hardware", "lbl_domain_other"
];

const CATEGORIES = [
  "PROJECT", "HACKATHON", "COMPETITION", "CERTIFICATION",
  "INTERNSHIP", "RESEARCH_PUBLICATION", "WORKSHOP"
];

const LEVELS = ["COLLEGE", "STATE", "NATIONAL", "INTERNATIONAL"];

function encodeText(text) {
  const EMBEDDING_DIM = 384;
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
  let norm = 0.0;
  for (let d = 0; d < EMBEDDING_DIM; d++) norm += vec[d] * vec[d];
  norm = Math.sqrt(norm) || 1.0;
  const res = [];
  for (let d = 0; d < EMBEDDING_DIM; d++) res.push(vec[d] / norm);
  return res;
}

const profiles = [];
for (let i = 1; i <= 100; i++) {
  const studentId = `STU-2026-${String(i).padStart(4, '0')}`;
  const dept = choice(DEPARTMENTS);
  const year = choice([1, 2, 3, 4]);
  const gpa = Math.round((choice([6.8, 7.2, 7.8, 8.2, 8.6, 9.1, 9.5])) * 10) / 10;
  
  // 15% cold start students (year 1 or 2 with zero achievements)
  const isColdStart = (i <= 15);
  const numDeclared = Math.floor(random() * 4) + 2;
  const declaredSkills = sample(SKILLS_POOL, numDeclared);
  const declaredInterests = sample(["Generative AI", "Distributed Systems", "Robotics", "Web Development", "Computer Vision", "Cybersecurity", "Fintech"], 2);

  const achievements = [];
  const skillProficiencies = {};
  for (const s of declaredSkills) {
    skillProficiencies[s] = {
      skill_name: s,
      proficiency_level: "INTERMEDIATE",
      evidence_count: 1,
      verified_count: 0
    };
  }

  const domainWeights = {};
  for (const dt of DOMAINS_POOL) domainWeights[dt] = 0.0;

  if (!isColdStart) {
    const numAch = Math.floor(random() * 4) + 1; // 1 to 4 achievements
    for (let a = 1; a <= numAch; a++) {
      const achCategory = choice(CATEGORIES);
      const achLevel = choice(LEVELS);
      const achSkills = sample(SKILLS_POOL, Math.floor(random() * 3) + 2);
      const achDomains = sample(DOMAINS_POOL, Math.floor(random() * 2) + 1);
      const verified = random() > 0.15; // 85% verified

      const achTitle = `${achCategory} in ${achDomains[0].replace('lbl_domain_', '').toUpperCase()} (${achLevel})`;
      const ach = {
        achievement_id: `ACH-${studentId}-${a}`,
        title: achTitle,
        category: achCategory,
        domain_tags: achDomains,
        skills: achSkills,
        level: achLevel,
        achievement_date: `2025-0${Math.floor(random() * 9) + 1}-15`,
        verified_flag: verified,
        confidence: verified ? 0.95 : 0.70
      };
      achievements.push(ach);

      for (const sk of achSkills) {
        if (!skillProficiencies[sk]) {
          skillProficiencies[sk] = {
            skill_name: sk,
            proficiency_level: "INTERMEDIATE",
            evidence_count: 0,
            verified_count: 0
          };
        }
        skillProficiencies[sk].evidence_count += 1;
        if (verified) skillProficiencies[sk].verified_count += 1;
        if (skillProficiencies[sk].verified_count >= 2) {
          skillProficiencies[sk].proficiency_level = "ADVANCED";
        }
      }

      for (const dt of achDomains) {
        domainWeights[dt] += (verified ? 1.25 : 0.8);
      }
    }
  }

  const verifiedSkills = Object.keys(skillProficiencies).filter(sk => skillProficiencies[sk].verified_count > 0);
  
  // Calculate profile composite text and embedding
  const profileText = `Student: ${studentId} | Dept: ${dept} | Year: ${year} | GPA: ${gpa} | Skills: ${[...declaredSkills, ...verifiedSkills].join(', ')} | Interests: ${declaredInterests.join(', ')} | Achievements: ${achievements.map(a => a.title).join('; ')}`;
  const profileVector = encodeText(profileText);

  // Normalize domain affinities
  const maxDw = Math.max(...Object.values(domainWeights)) || 1.0;
  const domainAffinities = {};
  for (const dt of DOMAINS_POOL) {
    domainAffinities[dt] = {
      domain_tag: dt,
      score: Math.round((domainWeights[dt] / maxDw) * 10000) / 10000,
      achievement_count: achievements.filter(a => a.domain_tags.includes(dt)).length
    };
  }

  profiles.push({
    student_id: studentId,
    department: dept,
    program: "B.Tech",
    year_of_study: year,
    gpa: gpa,
    declared_skills: declaredSkills,
    declared_interests: declaredInterests,
    career_goals: `Aspiring ${declaredInterests[0]} Engineer`,
    verified_skills: verifiedSkills,
    skill_proficiencies: skillProficiencies,
    domain_affinities: domainAffinities,
    achievements: achievements,
    profile_vector: profileVector,
    profile_text_hash: crypto.createHash('sha256').update(profileText).digest('hex').substring(0, 16),
    is_cold_start: isColdStart
  });
}

fs.writeFileSync(OUTPUT_JSON, JSON.stringify(profiles, null, 2), 'utf-8');
console.log(`Successfully generated ${profiles.length} benchmark profiles at ${OUTPUT_JSON}`);
