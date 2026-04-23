const SHARED_DIMENSIONS = [
  {
    key: 'activity',
    title: 'Activity & Maintenance',
    question: 'How actively is the repository maintained?',
  },
  {
    key: 'documentation',
    title: 'Documentation Quality',
    question: 'Is the project well documented?',
  },
  {
    key: 'codeQuality',
    title: 'Code Quality',
    question: 'Code structure and best practices',
  },
  {
    key: 'community',
    title: 'Community Engagement',
    question: 'How engaged is the community?',
  },
  {
    key: 'reliability',
    title: 'Reliability & Testing',
    question: 'Testing coverage and CI/CD setup',
  },
  {
    key: 'security',
    title: 'Security & Best Practices',
    question: 'Security vulnerabilities and practices',
  },
  {
    key: 'maturity',
    title: 'Engineering Maturity',
    question: 'Project maturity and engineering practices',
  },
  {
    key: 'impact',
    title: 'Innovation & Impact',
    question: 'Project innovation and industry impact',
  },
]

const EXAMPLES = [
  'facebook/react',
  'vercel/next.js',
  'microsoft/vscode',
  'tailwindlabs/tailwindcss',
]

function makeDimension(base, extra) {
  return {
    ...base,
    score: extra.score,
    highlights: extra.highlights,
    strengths: extra.strengths,
    improvements: extra.improvements,
  }
}

const REPORTS = {
  'vaibhavkumar2005/cloud-native-ai-library-system': {
    repository: {
      owner: 'VaibhavKumar2005',
      name: 'cloud-native-ai-library-system',
      fullName: 'VaibhavKumar2005/cloud-native-ai-library-system',
      description:
        'Production-grade microservices architecture for secure RAG, built with Docker, React, Flask, and HashiCorp Vault.',
      stars: 0,
      forks: 0,
      tags: ['azure', 'devops', 'docker', 'kubernetes', 'microservices'],
      repoUrl: 'https://github.com/VaibhavKumar2005/cloud-native-ai-library-system',
    },
    summary: {
      overallScore: 45,
      grade: 'F',
      verdict: 'Critical - Urgent improvements required',
      dimensionCount: 8,
    },
    dimensions: [
      makeDimension(SHARED_DIMENSIONS[0], {
        score: 48,
        highlights: ['Extremely active: Committed today', 'High: 29 commits/30d', 'Very small team: 2 contributors', 'Very new: 3 months'],
        strengths: ['Extremely active: Committed today', 'High: 29 commits/30d', '100 commits'],
        improvements: ['Very small team: 2 contributors', 'Very new: 3 months'],
      }),
      makeDimension(SHARED_DIMENSIONS[1], {
        score: 78,
        highlights: ['README.md exists', 'Comprehensive README (9k characters)'],
        strengths: ['README.md exists', 'Comprehensive README (9k characters)', 'Excellently structured: Found 7/8 key sections', 'Has GitHub Wiki for extended documentation', 'Rich code examples: 10 code blocks'],
        improvements: [],
      }),
      makeDimension(SHARED_DIMENSIONS[2], {
        score: 55,
        highlights: ['Primary language: Python', 'Strong tooling: ci, docker, modern'],
        strengths: ['Primary language: Python', 'Strong tooling: ci, docker, modern', 'Substantial codebase (1MB)', 'Very descriptive commits (avg. 167 chars)', 'Good: 70% Conventional Commits'],
        improvements: [],
      }),
      makeDimension(SHARED_DIMENSIONS[3], {
        score: 5,
        highlights: ['Duo team: 2 contributors', '7 merged PRs', 'Very low visibility: 0 stars'],
        strengths: ['Duo team: 2 contributors', '7 merged PRs'],
        improvements: ['Very low visibility: 0 stars'],
      }),
      makeDimension(SHARED_DIMENSIONS[4], {
        score: 85,
        highlights: ['Comprehensive CI/CD: 5 GitHub Actions workflows detected', 'Test directory detected'],
        strengths: ['Comprehensive CI/CD: 5 GitHub Actions workflows detected', 'Test directory detected', 'Issue tracking enabled', 'Uses versioned releases', 'Licensed: MIT'],
        improvements: [],
      }),
      makeDimension(SHARED_DIMENSIONS[5], {
        score: 24,
        highlights: ['Industry-standard license: MIT', 'Add SECURITY.md for vulnerability reporting'],
        strengths: ['Industry-standard license: MIT'],
        improvements: ['Add SECURITY.md for vulnerability reporting', 'Enable Dependabot for security updates', 'Add security scanning (CodeQL, Snyk)', 'Only 3/10 commits signed'],
      }),
      makeDimension(SHARED_DIMENSIONS[6], {
        score: 25,
        highlights: ['Reasonable size: 1MB', 'Young: 0.3yr project'],
        strengths: ['Reasonable size: 1MB', 'Young: 0.3yr project', 'Well-structured codebase'],
        improvements: ['No releases - consider using semantic versioning'],
      }),
      makeDimension(SHARED_DIMENSIONS[7], {
        score: 13,
        highlights: ['New and actively developed', 'Leverages trending technologies'],
        strengths: ['New and actively developed', 'Leverages trending technologies'],
        improvements: ['Limited visibility - focus on marketing'],
      }),
    ],
    recommendations: [
      {
        title: 'Increase commit frequency',
        priority: 'high',
        summary: 'The repository has low recent activity. Try to commit regularly, even small improvements.',
        actionSteps: ['Set up a regular development schedule', 'Create a roadmap with milestones', 'Consider enabling automated dependency updates (Dependabot)'],
      },
      {
        title: 'Enhance code quality',
        priority: 'medium',
        summary: 'Improve maintainability and reliability of your codebase.',
        actionSteps: ['Add ESLint or language-specific linter', 'Set up code formatting (Prettier)', 'Use meaningful commit messages (Conventional Commits)', 'Add type checking (TypeScript or JSDoc)', 'Create coding standards document'],
      },
      {
        title: 'Build community engagement',
        priority: 'medium',
        summary: 'A strong community makes projects more sustainable and valuable.',
        actionSteps: ['Promote on Product Hunt, Hacker News, Reddit', 'Write blog posts about your project', 'Respond to issues within 48 hours', 'Label "good first issue" for new contributors', 'Create a Discord/Slack community', 'Share updates on Twitter/LinkedIn'],
      },
      {
        title: 'Strengthen security posture',
        priority: 'high',
        summary: 'Security is critical for user trust and project longevity.',
        actionSteps: ['Add a SECURITY.md policy with vulnerability reporting instructions', 'Enable Dependabot for automated dependency updates', 'Set up CodeQL or Snyk security scanning', 'Enable GPG commit signing for verification', 'Configure branch protection rules', 'Add a proper LICENSE file if missing'],
      },
      {
        title: 'Optimize for performance',
        priority: 'medium',
        summary: 'Performance improvements enhance user experience and adoption.',
        actionSteps: ['Optimize repository size (consider Git LFS for large files)', 'Implement code splitting and lazy loading', 'Add caching strategies where applicable', 'Use modern build tools (Vite, esbuild)', 'Document performance benchmarks', 'Profile and optimize hot paths'],
      },
      {
        title: 'Increase impact and visibility',
        priority: 'low',
        summary: 'Stand out by showcasing innovation and building community.',
        actionSteps: ['Write blog posts or articles about your project', 'Present at conferences or meetups', 'Add innovative features that solve real problems', 'Contribute to related open source projects', 'Build partnerships with complementary projects', 'Engage with tech communities (Reddit, HackerNews, X)'],
      },
    ],
    faqs: [
      'What does the health score measure?',
      'Is this data real-time?',
      'How is AI used in the analysis?',
      'Can I use this for private repositories?',
    ],
    relatedTools: ['API Designer', 'API Request Playground', 'API Pricing Comparison', 'Database Schema Designer'],
  },
  'facebook/react': {
    repository: {
      owner: 'facebook',
      name: 'react',
      fullName: 'facebook/react',
      description: 'The library for web and native user interfaces.',
      stars: 235000,
      forks: 48300,
      tags: ['javascript', 'frontend', 'ui', 'library', 'open-source'],
      repoUrl: 'https://github.com/facebook/react',
    },
    summary: {
      overallScore: 94,
      grade: 'A',
      verdict: 'Excellent - Strong engineering habits and ecosystem impact',
      dimensionCount: 8,
    },
    dimensions: SHARED_DIMENSIONS.map((dimension, index) =>
      makeDimension(dimension, [
        { score: 96, highlights: ['Consistent release cadence', 'Large maintainer team'], strengths: ['Consistent release cadence', 'Large maintainer team', 'Mature contribution flow'], improvements: [] },
        { score: 92, highlights: ['Deep docs ecosystem', 'Strong migration guidance'], strengths: ['Deep docs ecosystem', 'Strong migration guidance', 'API examples across use cases'], improvements: [] },
        { score: 95, highlights: ['Strong linting and testing culture', 'Clear package boundaries'], strengths: ['Strong linting and testing culture', 'Clear package boundaries', 'Long-lived code stewardship'], improvements: [] },
        { score: 98, highlights: ['Huge contributor and user base', 'High discussion volume'], strengths: ['Huge contributor and user base', 'High discussion volume', 'Strong PR review process'], improvements: [] },
        { score: 97, highlights: ['Robust CI coverage', 'Battle-tested release process'], strengths: ['Robust CI coverage', 'Battle-tested release process', 'Good regression prevention'], improvements: [] },
        { score: 91, highlights: ['Security process appears mature', 'Strong release hygiene'], strengths: ['Security process appears mature', 'Strong release hygiene'], improvements: ['Continue expanding signed release verification'] },
        { score: 95, highlights: ['High project maturity', 'Well-established versioning'], strengths: ['High project maturity', 'Well-established versioning', 'Stable governance'], improvements: [] },
        { score: 99, highlights: ['Massive ecosystem impact', 'Industry-defining project'], strengths: ['Massive ecosystem impact', 'Industry-defining project'], improvements: [] },
      ][index])
    ),
    recommendations: [
      {
        title: 'Sustain contributor onboarding',
        priority: 'low',
        summary: 'The project is healthy; the main opportunity is keeping new contributors productive at scale.',
        actionSteps: ['Keep issue triage fast', 'Refresh contributor docs for new React Compiler features', 'Maintain migration guides for major releases'],
      },
    ],
    faqs: ['What contributes most to an A grade?', 'How should maintainers interpret community metrics?'],
    relatedTools: ['Release Notes Generator', 'OSS Contributor Guide'],
  },
  'vercel/next.js': {
    repository: {
      owner: 'vercel',
      name: 'next.js',
      fullName: 'vercel/next.js',
      description: 'The React framework for the web.',
      stars: 136000,
      forks: 29300,
      tags: ['react', 'framework', 'ssr', 'frontend', 'typescript'],
      repoUrl: 'https://github.com/vercel/next.js',
    },
    summary: {
      overallScore: 91,
      grade: 'A',
      verdict: 'Excellent - Very strong maintenance, docs, and ecosystem pull',
      dimensionCount: 8,
    },
    dimensions: SHARED_DIMENSIONS.map((dimension) =>
      makeDimension(dimension, {
        score: dimension.key === 'security' ? 87 : dimension.key === 'impact' ? 98 : 92,
        highlights: ['High release velocity', 'Strong documentation and adoption'],
        strengths: ['High release velocity', 'Strong documentation and adoption', 'Clear product direction'],
        improvements: dimension.key === 'security' ? ['Continue tightening dependency and supply-chain visibility'] : [],
      })
    ),
    recommendations: [
      {
        title: 'Reduce migration friction',
        priority: 'low',
        summary: 'Healthy projects still benefit from tighter upgrade guidance as the framework evolves quickly.',
        actionSteps: ['Keep codemods updated', 'Publish clearer upgrade notes for major routing and caching changes'],
      },
    ],
    faqs: ['How much does ecosystem adoption affect the score?'],
    relatedTools: ['Bundle Analyzer', 'Changelog Assistant'],
  },
  'microsoft/vscode': {
    repository: {
      owner: 'microsoft',
      name: 'vscode',
      fullName: 'microsoft/vscode',
      description: 'Visual Studio Code',
      stars: 176000,
      forks: 32900,
      tags: ['editor', 'typescript', 'developer-tools', 'desktop', 'open-source'],
      repoUrl: 'https://github.com/microsoft/vscode',
    },
    summary: {
      overallScore: 93,
      grade: 'A',
      verdict: 'Excellent - Mature engineering operations with exceptional product reach',
      dimensionCount: 8,
    },
    dimensions: SHARED_DIMENSIONS.map((dimension) =>
      makeDimension(dimension, {
        score: dimension.key === 'community' ? 96 : dimension.key === 'security' ? 89 : 93,
        highlights: ['Mature maintainer workflow', 'Large release footprint'],
        strengths: ['Mature maintainer workflow', 'Large release footprint', 'Clear issue discipline'],
        improvements: dimension.key === 'security' ? ['Keep expanding signed artifact and disclosure visibility'] : [],
      })
    ),
    recommendations: [
      {
        title: 'Keep extension ecosystem aligned',
        priority: 'low',
        summary: 'The core repo is strong; ecosystem compatibility and communication remain the main scaling challenge.',
        actionSteps: ['Continue strong release notes', 'Document breaking API changes early'],
      },
    ],
    faqs: ['Why is a mature project still shown with recommendations?'],
    relatedTools: ['Release Train Planner', 'Maintainer Dashboard'],
  },
  'tailwindlabs/tailwindcss': {
    repository: {
      owner: 'tailwindlabs',
      name: 'tailwindcss',
      fullName: 'tailwindlabs/tailwindcss',
      description: 'A utility-first CSS framework for rapid UI development.',
      stars: 91000,
      forks: 4900,
      tags: ['css', 'framework', 'design-system', 'frontend', 'utility-first'],
      repoUrl: 'https://github.com/tailwindlabs/tailwindcss',
    },
    summary: {
      overallScore: 89,
      grade: 'A-',
      verdict: 'Strong - Excellent product momentum with a few maturity and security opportunities',
      dimensionCount: 8,
    },
    dimensions: SHARED_DIMENSIONS.map((dimension) =>
      makeDimension(dimension, {
        score: dimension.key === 'maturity' ? 82 : dimension.key === 'security' ? 84 : 90,
        highlights: ['Very strong adoption', 'Clear docs and release messaging'],
        strengths: ['Very strong adoption', 'Clear docs and release messaging', 'Focused maintainership'],
        improvements: dimension.key === 'maturity' ? ['Continue expanding long-term migration guidance'] : [],
      })
    ),
    recommendations: [
      {
        title: 'Deepen enterprise adoption signals',
        priority: 'low',
        summary: 'The project is already strong, but maturity signals can be made even clearer for larger engineering organizations.',
        actionSteps: ['Expand long-term support communication', 'Publish more benchmarking and migration case studies'],
      },
    ],
    faqs: ['How are framework ecosystems compared fairly?'],
    relatedTools: ['CSS Bundle Insights', 'Docs Quality Scanner'],
  },
}

function normalizeRepoInput(input) {
  const value = input.trim()
  if (!value) return ''

  try {
    const url = new URL(value)
    if (url.hostname.includes('github.com')) {
      const [owner, repo] = url.pathname.split('/').filter(Boolean)
      if (owner && repo) {
        return `${owner}/${repo.replace(/\.git$/i, '')}`.toLowerCase()
      }
    }
  } catch {
    // Ignore parse errors and treat the input as owner/name.
  }

  const [owner, repo] = value.replace(/^github\.com\//i, '').split('/').filter(Boolean)
  if (!owner || !repo) return ''
  return `${owner}/${repo.replace(/\.git$/i, '')}`.toLowerCase()
}

function createFallbackReport(repoKey) {
  const [owner = 'demo', name = 'repository'] = repoKey ? repoKey.split('/') : ['demo', 'repository']
  const fullName = `${owner}/${name}`

  return {
    repository: {
      owner,
      name,
      fullName,
      description: 'Demo analysis generated from a fallback heuristic dataset. Connect a live backend later for real repository signals.',
      stars: 0,
      forks: 0,
      tags: ['demo', 'analysis', 'github', 'frontend-only'],
      repoUrl: `https://github.com/${fullName}`,
    },
    summary: {
      overallScore: 62,
      grade: 'C+',
      verdict: 'Promising - Good foundation with clear opportunities to strengthen maturity and security',
      dimensionCount: 8,
    },
    dimensions: SHARED_DIMENSIONS.map((dimension) =>
      makeDimension(dimension, {
        score:
          dimension.key === 'documentation'
            ? 74
            : dimension.key === 'reliability'
              ? 68
              : dimension.key === 'security'
                ? 51
                : 60,
        highlights: ['Demo-mode estimate', 'Swap in live GitHub signals later'],
        strengths: ['The structure is ready for richer data sources', 'This fallback keeps the UX complete for unknown repositories'],
        improvements: ['Add live GitHub ingestion for accurate scores', 'Expand security and community signal collection'],
      })
    ),
    recommendations: [
      {
        title: 'Connect live repository analysis',
        priority: 'high',
        summary: 'This report is a polished demo. The next leverage point is replacing seeded scores with real GitHub metrics.',
        actionSteps: ['Add a backend endpoint for GitHub data fetch', 'Persist normalized repo analysis payloads', 'Replace fallback heuristics with computed scoring'],
      },
      {
        title: 'Harden security defaults',
        priority: 'medium',
        summary: 'Most repositories benefit immediately from stronger security hygiene.',
        actionSteps: ['Add SECURITY.md', 'Enable Dependabot', 'Enable code scanning and branch protection'],
      },
    ],
    faqs: [
      'What changes when live GitHub analysis is connected?',
      'How should I interpret a demo fallback score?',
    ],
    relatedTools: ['GitHub Metrics Explorer', 'Release Notes Generator'],
  }
}

export const repoHealthExamples = EXAMPLES

export function getRepoHealthReport(input) {
  const repoKey = normalizeRepoInput(input)
  if (!repoKey) return null

  return REPORTS[repoKey] ?? createFallbackReport(repoKey)
}

export function getDefaultRepoHealthReport() {
  return REPORTS['vaibhavkumar2005/cloud-native-ai-library-system']
}

export function normalizeRepoIdentifier(input) {
  return normalizeRepoInput(input)
}
