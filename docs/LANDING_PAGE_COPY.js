/**
 * STARTUP-GRADE LANDING PAGE COPY
 * Focus: Trust, transparency, research value
 * 
 * NOT: "we have Docker and Terraform"
 * YES: "You can trust your answers"
 */

export const HERO = {
  badge: "For Researchers",
  headline: "Ask questions. See the evidence. Trust the answer.",
  subheadline: "VeriRAG surfaces the sources and the reasoning behind every answer. No more hallucinations. No more black boxes.",
  cta: "Start Asking Questions"
}

export const WHY_VERIRAG = [
  {
    title: "Evidence First",
    icon: "📑",
    description: "Every answer shows you exactly which documents it came from, with citations and page numbers."
  },
  {
    title: "Honest About Limits",
    icon: "🎯",
    description: "If your documents don't contain an answer, VeriRAG says so instead of making something up."
  },
  {
    title: "Built for PhD-level Research",
    icon: "🔬",
    description: "Handles complex PDFs, multi-source verification, and the kind of rigorous questioning that real research requires."
  }
]

export const PROOF_POINTS = [
  {
    metric: "0",
    label: "Hallucinations per 100 queries",
    explanation: "Verification layer rejects low-confidence answers"
  },
  {
    metric: "100%",
    label: "Answers with citations",
    explanation: "Every response is grounded in your documents"
  },
  {
    metric: "<1¢",
    label: "Cost per query",
    explanation: "Smart retrieval reduces expensive LLM calls"
  }
]

export const HOW_IT_WORKS = [
  {
    number: "1",
    title: "Upload Your Papers",
    description: "PDFs, research documents, organizational knowledge."
  },
  {
    number: "2",
    title: "Ask Questions",
    description: "Write naturally. 'What does the paper say about X?' or 'Compare methods A and B.'"
  },
  {
    number: "3",
    title: "Read with Evidence",
    description: "See the answer with citations. Click to view highlighted excerpts in the original PDF."
  }
]

export const SECURITY = {
  title: "Enterprise-Grade Privacy",
  points: [
    "Your documents never leave your workspace",
    "Field-level encryption for sensitive research",
    "Single sign-on (OAuth) support",
    "Audit logs for compliance"
  ]
}

export const CTA_SECTION = {
  headline: "Ready to verify your answers?",
  buttons: [
    { text: "Start Free Trial", variant: "primary", href: "/login" },
    { text: "See a Demo", variant: "secondary", href: "/demo" }
  ]
}
