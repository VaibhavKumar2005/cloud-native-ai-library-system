# Contributing to VeriRAG

Thank you for your interest in contributing! Follow these guidelines to help us improve VeriRAG.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. All contributors must adhere to our code of conduct.

---

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16 with pgvector
- Redis 7+

### Local Development Setup

1. **Clone & enter the repo:**
   ```bash
   git clone https://github.com/VaibhavKumar2005/cloud-native-ai-library-system.git
   cd cloud-native-ai-library-system
   ```

2. **Backend setup:**
   ```bash
   cd apps/backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Frontend setup:**
   ```bash
   cd apps/frontend
   npm install
   ```

4. **Start services:**
   ```bash
   docker-compose up -d
   ```

5. **Run tests:**
   ```bash
   # Backend
   cd apps/backend
   pytest tests/

   # Frontend
   cd apps/frontend
   npm run lint
   npm run build
   ```

---

## Contribution Workflow

### 1. Create a Branch

Use semantic branch naming:

```bash
git checkout -b feature/add-pdf-highlight
git checkout -b fix/citation-parsing-bug
git checkout -b docs/update-readme
```

### 2. Make Changes

- Follow PEP 8 for Python
- Follow ESLint rules for JavaScript (run `npm run lint` before committing)
- Write tests for new features
- Update documentation

### 3. Commit with Clear Messages

```bash
git commit -m "feat: add PDF highlighting on citation click

- Implement PDFViewer component
- Add highlight text extraction
- Update ResearchGradeAnswer to support PDF panel
- Tests: 3 new unit tests"
```

**Format:** `type(scope): short description`  
**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

### 4. Push & Open a Pull Request

```bash
git push origin feature/add-pdf-highlight
```

Then open a PR with:
- Clear description of changes
- Link to any related issues
- Screenshots (if UI changes)
- Tests confirming the change

### 5. Code Review

- At least one approval required
- All CI checks must pass
- Address feedback promptly

---

## Development Guidelines

### Testing Requirements

- **Backend:** Minimum 70% code coverage
- **Frontend:** All components with props must have snapshots
- Run tests before every commit: `npm run lint && pytest tests/`

### Code Style

**Python (Backend):**
```bash
# Format with Black
black apps/backend/

# Check with Pylint
pylint apps/backend/ai_engine/
```

**JavaScript (Frontend):**
```bash
# Format with Prettier
npm run format

# Lint
npm run lint
```

### Documentation

- Update `README.md` for architecture changes
- Add docstrings to functions (Python)
- Add JSDoc comments to React components
- Document API endpoints in code

---

## Areas for Contribution

### 🔥 High-Impact (We Need Help)

- [ ] **PDF Highlight Feature** — Click citation → see text highlighted in original PDF
- [ ] **Query Suggestions** — Smart prompts for first-time users
- [ ] **Mobile UI** — Responsive dashboard for tablets
- [ ] **More LLM Support** — OpenAI, Anthropic, Ollama backends

### 📚 Medium-Impact

- [ ] **Better Error Messages** — More helpful guidance
- [ ] **BibTeX Export** — Download citations in academic format
- [ ] **Query History** — Save and rerun previous questions
- [ ] **Dark Mode** — Additional theme support

### 🐛 Bugs & Fixes

Check [Issues](https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/issues) for bugs labeled `good-first-issue` or `help-wanted`.

---

## Security Vulnerability Reporting

**Do NOT open public issues for security bugs.**

Email: [security@verirag.dev](mailto:security@verirag.dev)

See [SECURITY.md](.github/SECURITY.md) for full details.

---

## Project Structure

```
.
├── apps/
│   ├── backend/           # Django + DRF API
│   │   ├── ai_engine/     # RAG pipeline + verification
│   │   ├── librarian/     # Document management
│   │   └── manage.py
│   └── frontend/          # React + Vite
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   └── lib/
│       └── vite.config.js
├── ops/                   # Infrastructure (Terraform)
├── tests/                 # Test suite
├── docs/                  # Documentation
└── README.md
```

---

## Commit Message Examples

```bash
# Good
git commit -m "fix(rag): resolve chunk ordering in synthesis

Previously chunks were sorted by ID instead of relevance.
Now using cosine distance for proper ordering in LLM synthesis.

Fixes #42"

# Good
git commit -m "feat(frontend): add PDF highlight on citation

Users can click any citation to view the highlighted
excerpt in the original PDF.

- New PDFViewer component
- Update ResearchGradeAnswer
- Add citation click handler"

# Bad
git commit -m "stuff" 
git commit -m "updates"
git commit -m "fix bug"
```

---

## Performance Considerations

- Query latency should be <500ms
- Vector search should use pgvector fast operators
- Frontend components should memoize expensive renders
- API responses should be <1MB

---

## Before Submitting

Run this checklist:

- [ ] Tests pass locally (`pytest` + `npm run test`)
- [ ] Linting passes (`npm run lint`, `black`, `pylint`)
- [ ] Build succeeds (`npm run build`)
- [ ] Git history is clean (meaningful commits)
- [ ] Documentation updated
- [ ] No console errors/warnings
- [ ] Branch is up-to-date with `main`

---

## Questions?

- **Discussions:** [GitHub Discussions](https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/discussions)
- **Issues:** [GitHub Issues](https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/issues)
- **Email:** dev@verirag.dev

---

**Welcome to the VeriRAG community!** 🚀
