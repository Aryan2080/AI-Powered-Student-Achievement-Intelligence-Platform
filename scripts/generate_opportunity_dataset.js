/**
 * scripts/generate_opportunity_dataset.js
 * Generates canonical 520 opportunities and writes CSV and JSON.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const OUTPUT_DIR = path.join(__dirname, '..', 'data', 'opportunities');
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Seeded pseudo-random generator (LCG)
let seed = 42;
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

const DOMAIN_TAGS = [
  "lbl_domain_ai", "lbl_domain_ml", "lbl_domain_nlp", "lbl_domain_cv",
  "lbl_domain_security", "lbl_domain_systems", "lbl_domain_web",
  "lbl_domain_data", "lbl_domain_hardware", "lbl_domain_other"
];

const CANONICAL_SKILLS = [
  "Python", "Java", "C++", "C#", "Rust", "Go", "TypeScript", "JavaScript",
  "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
  "AWS", "Azure", "GCP", "Linux", "Git", "PyTorch", "TensorFlow", "Scikit-learn",
  "OpenCV", "HuggingFace", "BERT", "LLM", "NLP", "Pandas", "NumPy",
  "FastAPI", "Flask", "Django", "React", "Node.js", "GraphQL", "REST API",
  "CI/CD", "Terraform", "Kafka", "Spark", "Airflow", "FPGA", "Embedded C",
  "Cybersecurity", "Penetration Testing", "Cryptography", "Computer Vision",
  "Reinforcement Learning", "Deep Learning", "Data Engineering", "Microservices"
];

const DEPARTMENTS = [
  "Computer Science",
  "Information Technology",
  "Artificial Intelligence & Data Science",
  "Electrical Engineering",
  "Electronics & Communication",
  "Software Engineering",
  "Mechanical Engineering",
  "Robotics & Automation"
];

const ORGANIZATIONS_BY_TYPE = {
  HACKATHON: [
    "Major League Hacking (MLH)", "Smart India Hackathon", "ETHGlobal",
    "MIT Hackathon Society", "Google Cloud Developer Community",
    "HackMIT", "CalHacks", "PennApps", "Microsoft Student Developers",
    "AWS Builders Network", "NASA Space Apps Challenge", "Hackerearth Global"
  ],
  INTERNSHIP: [
    "Google Research", "Microsoft India Development Center", "Meta AI",
    "Amazon Web Services", "NVIDIA Deep Learning Institute", "Intel Labs",
    "Qualcomm Technologies", "IBM Research", "Cisco Systems", "Adobe Research",
    "Goldman Sachs Tech", "Palantir Technologies", "OpenAI Fellowships"
  ],
  RESEARCH_GRANT: [
    "National Science Foundation (NSF)", "IEEE Computer Society",
    "ACM SIGKDD Research Foundation", "DST India AI Mission",
    "Stanford AI Lab Fellowship", "MIT CSAIL Student Research Fund",
    "European Research Council", "Google PhD & Student Fellowship",
    "Microsoft Research Initiative", "Wellcome Leap Tech Foundations"
  ],
  COMPETITION: [
    "Kaggle Grandmaster League", "ACM-ICPC World Finals", "Google Hash Code",
    "International Collegiate Programming Contest", "Imagine Cup by Microsoft",
    "DARPA Robotics Challenge", "NeurIPS Machine Learning Competition",
    "CVPR Vision Challenge", "DEF CON CTF Student Qualifier"
  ],
  SCHOLARSHIP: [
    "Google Generation Scholarship", "Grace Hopper Celebration Scholar",
    "Microsoft Tuition & Tech Fellowship", "Reliance Foundation Scholar",
    "Adobe Women in Tech Scholarship", "Palantir Women in Tech Fund",
    "QS World University Merit Scholarship", "Tata Trust Merit Grant"
  ],
  CONFERENCE: [
    "NeurIPS 2026 Student Forum", "ICLR 2026 Student Workshop",
    "CVPR 2026 Computer Vision Symposium", "ACL 2026 NLP Research Showcase",
    "ACM SIGCOMM 2026", "IEEE ICASSP 2026", "KDD 2026 Data Mining Summit",
    "IEEE INFOCOM 2026", "USENIX Security Symposium Student Track"
  ]
};

const TITLES_BY_TYPE = {
  HACKATHON: [
    "National AI Innovation Hackathon",
    "Autonomous Agents & LLM Buildathon",
    "Smart Cities & IoT 48-Hour Hackathon",
    "Healthcare AI & Diagnostics Hackathon",
    "Global ClimateTech Solutions Hackathon",
    "Distributed Web3 & Cybersecurity Sprint",
    "Edge Computing & Robotics Hack Challenge",
    "High-Performance Cloud Systems Buildathon"
  ],
  INTERNSHIP: [
    "Summer Research Intern in Generative AI",
    "Computer Vision & Perception Engineering Intern",
    "Distributed Systems & Cloud Backend Intern",
    "Machine Learning Infrastructure Intern",
    "Data Science & Predictive Modeling Intern",
    "Firmware & Embedded Systems Engineering Intern",
    "Cybersecurity & Cloud Defense Intern",
    "Full-Stack Web & API Platform Intern"
  ],
  RESEARCH_GRANT: [
    "Undergraduate Innovation Fellowship in Neurosymbolic AI",
    "Student Exploration Grant for Green Computing & Systems",
    "Trustworthy Machine Learning Research Fellowship",
    "Applied NLP in Multilingual Education Grant",
    "Next-Generation Autonomous Robotics Research Grant",
    "Secure Hardware & Cryptography Student Grant"
  ],
  COMPETITION: [
    "Global Algorithmic Modeling Championship",
    "Zero-Shot Multimodal Learning Challenge",
    "National Cybersecurity Capture The Flag (CTF)",
    "Large-Scale Graph Neural Network Benchmark",
    "Competitive Systems Programming Invitational",
    "Medical Imaging Segmentation Grand Challenge"
  ],
  SCHOLARSHIP: [
    "Excellence in Computational Science Scholarship",
    "Women in Machine Learning Academic Fellowship",
    "Future Technology Leaders Merit Scholarship",
    "National Merit Scholarship for AI & Data Science",
    "Outstanding Young Engineer Fellowship"
  ],
  CONFERENCE: [
    "International Conference on Machine Learning Student Poster",
    "Computer Vision and Pattern Recognition Graduate Colloquium",
    "Association for Computational Linguistics Doctoral Consortium",
    "IEEE International Conference on Distributed Computing",
    "ACM Symposium on Cloud Computing Student Workshop"
  ]
};

function generate(totalCount = 520) {
  const opportunities = [];
  const types = Object.keys(ORGANIZATIONS_BY_TYPE);
  const now = new Date();

  for (let i = 1; i <= totalCount; i++) {
    const oppType = types[(i - 1) % types.length];
    const org = choice(ORGANIZATIONS_BY_TYPE[oppType]);
    const titleStem = choice(TITLES_BY_TYPE[oppType]);
    const numStr = String(i).padStart(4, '0');
    const oppId = `OPP-2026-${oppType.substring(0, 4)}-${numStr}`;

    const daysAhead = Math.floor(random() * 115) + 5;
    const deadlineDate = new Date(now.getTime() + daysAhead * 24 * 3600 * 1000);
    const startDate = new Date(deadlineDate.getTime() + (Math.floor(random() * 30) + 14) * 24 * 3600 * 1000);
    const endDate = new Date(startDate.getTime() + (Math.floor(random() * 60) + 2) * 24 * 3600 * 1000);

    const numReq = Math.floor(random() * 3) + 2;
    const numPref = Math.floor(random() * 3) + 1;
    const sampled = sample(CANONICAL_SKILLS, numReq + numPref);
    const reqSkills = sampled.slice(0, numReq);
    const prefSkills = sampled.slice(numReq);

    const derived = new Set();
    const skillText = sampled.join(' ').toLowerCase();
    if (skillText.includes('nlp') || skillText.includes('bert') || skillText.includes('llm') || skillText.includes('huggingface')) derived.add('lbl_domain_nlp');
    if (skillText.includes('opencv') || skillText.includes('vision') || skillText.includes('segmentation')) derived.add('lbl_domain_cv');
    if (skillText.includes('pytorch') || skillText.includes('tensorflow') || skillText.includes('scikit-learn') || skillText.includes('deep learning')) derived.add('lbl_domain_ml');
    if (skillText.includes('docker') || skillText.includes('kubernetes') || skillText.includes('aws') || skillText.includes('linux')) derived.add('lbl_domain_systems');
    if (skillText.includes('cybersecurity') || skillText.includes('cryptography') || skillText.includes('security')) derived.add('lbl_domain_security');
    if (skillText.includes('react') || skillText.includes('node.js') || skillText.includes('fastapi') || skillText.includes('rest api')) derived.add('lbl_domain_web');
    if (skillText.includes('sql') || skillText.includes('spark') || skillText.includes('pandas') || skillText.includes('data')) derived.add('lbl_domain_data');
    if (skillText.includes('fpga') || skillText.includes('embedded') || skillText.includes('robotics')) derived.add('lbl_domain_hardware');
    if (derived.size === 0) derived.add(choice(DOMAIN_TAGS));

    const domainTags = Array.from(derived).slice(0, 3).sort();
    const eligibleDepts = sample(DEPARTMENTS, Math.floor(random() * 3) + 2);
    const minGpas = [0.0, 6.0, 6.5, 7.0, 7.5, 8.0];
    const minGpa = choice(minGpas);
    const yearsPool = [1, 2, 3, 4];
    const eligibleYears = sample(yearsPool, Math.floor(random() * 3) + 2).sort();

    const locationTypes = ["REMOTE", "ON_SITE", "HYBRID"];
    const locType = choice(locationTypes);
    const stipends = [
      "$1,500 Monthly Stipend", "$2,500 Cash Prize + Certificate",
      "Full Tuition Coverage", "$5,000 Research Grant",
      "Travel Grant & Accommodation", "INR 1,00,000 Winner Reward",
      "INR 50,000 Stipend / Month", "PPO Opportunity + Certificate",
      "Funded Publication & Mentorship"
    ];
    const stipend = choice(stipends);

    const description = `${titleStem} hosted by ${org}. This premier ${oppType.toLowerCase().replace('_', ' ')} invites exceptional students specializing in ${eligibleDepts.slice(0, 2).join(', ')}. Participants will work on cutting-edge problems requiring proficiency in ${reqSkills.join(', ')}. Focus domains include ${domainTags.join(', ')}. Top performers are eligible for ${stipend} and institutional recognition.`;
    const title = `${titleStem} 2026 (${org})`;
    const compositeText = `${title} | ${oppType} | ${org} | ${description} | Skills: ${reqSkills.join(', ')} | Domains: ${domainTags.join(', ')}`;
    const textHash = crypto.createHash('sha256').update(compositeText).digest('hex').substring(0, 16);

    opportunities.push({
      opportunity_id: oppId,
      title: title,
      description: description,
      opportunity_type: oppType,
      organization: org,
      eligible_departments: eligibleDepts,
      eligible_years: eligibleYears,
      eligible_degree: ["B.Tech", "B.E.", "B.S.", "M.Tech"],
      min_gpa: minGpa,
      required_skills: reqSkills,
      preferred_skills: prefSkills,
      domain_tags: domainTags,
      deadline: deadlineDate.toISOString().split('T')[0],
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0],
      reward_or_stipend: stipend,
      location_type: locType,
      location: locType === "ON_SITE" ? "Bengaluru, India" : "Remote / Hybrid",
      external_url: `https://opportunities.university.edu/${oppId.toLowerCase()}`,
      status: "ACTIVE",
      collected_at: now.toISOString(),
      verified_at: now.toISOString(),
      source_name: `${org} Official Portal`,
      text_hash: textHash,
      embedding_version: "all-MiniLM-L6-v2"
    });
  }

  return opportunities;
}

const opps = generate(520);
const jsonPath = path.join(OUTPUT_DIR, 'opportunity_dataset.json');
const csvPath = path.join(OUTPUT_DIR, 'opportunity_dataset.csv');

fs.writeFileSync(jsonPath, JSON.stringify(opps, null, 2), 'utf-8');

// Write CSV
const header = [
  "opportunity_id", "title", "description", "opportunity_type",
  "organization", "eligible_departments", "eligible_years",
  "eligible_degree", "min_gpa", "required_skills", "preferred_skills",
  "domain_tags", "deadline", "start_date", "end_date",
  "reward_or_stipend", "location_type", "location", "external_url",
  "status", "collected_at", "verified_at", "source_name", "text_hash",
  "embedding_version"
];

function escapeCsv(val) {
  if (val === null || val === undefined) return '';
  const str = String(val);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

const rows = [header.join(',')];
for (const o of opps) {
  const row = [
    o.opportunity_id,
    escapeCsv(o.title),
    escapeCsv(o.description),
    o.opportunity_type,
    escapeCsv(o.organization),
    escapeCsv(o.eligible_departments.join(';')),
    escapeCsv(o.eligible_years.join(';')),
    escapeCsv(o.eligible_degree.join(';')),
    o.min_gpa,
    escapeCsv(o.required_skills.join(';')),
    escapeCsv(o.preferred_skills.join(';')),
    escapeCsv(o.domain_tags.join(';')),
    o.deadline,
    o.start_date,
    o.end_date,
    escapeCsv(o.reward_or_stipend),
    o.location_type,
    escapeCsv(o.location),
    o.external_url,
    o.status,
    o.collected_at,
    o.verified_at,
    escapeCsv(o.source_name),
    o.text_hash,
    o.embedding_version
  ];
  rows.push(row.join(','));
}

fs.writeFileSync(csvPath, rows.join('\n'), 'utf-8');
console.log(`Successfully generated ${opps.length} opportunities:`);
console.log(`JSON: ${jsonPath}`);
console.log(`CSV: ${csvPath}`);
