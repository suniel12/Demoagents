Phase 0 — Foundation (Days 1-2)
What you build: The skeleton. A single-tool agent that takes a GitHub repo URL and fetches basic repo metadata via the GitHub API.
The agent does:

Accept a repo URL as input
Call the GitHub REST API to fetch repo metadata (stars, forks, language, last commit, open issues, license)
Return a structured JSON summary

Tools registered:

github_repo_metadata — fetches repo-level info from GitHub API

AgentCI tests to write at this step:
This is where you establish the testing patterns that everything else builds on. Write these tests before you build the agent (TDD style — this becomes a great content angle: "we test-drove our agent development with AgentCI"):
Deterministic tests:

Given a known public repo (e.g., langchain-ai/langchain), the agent calls github_repo_metadata exactly once
The output contains all required fields (stars, language, license, last_commit_date)
Given a nonexistent repo URL, the agent returns a graceful error, not a crash or hallucination

Golden trace test:

Record the full trace for langchain-ai/langchain as your first golden trace
Assert: tool call count = 1, tool name = github_repo_metadata, input contains correct owner/repo parsed from URL

Cost guardrail test:

Total token usage for a single repo analysis stays under 2K tokens (it's a simple task at this phase)

What you learn for AgentCI: This phase validates that the basic framework works — trace capture, assertion syntax, golden trace recording, and cost tracking. You'll likely discover UX friction in how developers define tools and register them for testing. Fix that friction immediately.

Phase 1 — Multi-tool sequential calls (Days 3-5)
What you build: Expand the agent to call multiple tools in a fixed logical sequence. Now it doesn't just read metadata — it actually inspects the repository contents.
New tools added:

github_list_files — lists the directory structure of the repo
github_read_file — reads a specific file's contents
dependency_analyzer — parses package.json / requirements.txt / Cargo.toml and checks for known vulnerability counts via a public API (like OSV.dev)

The agent now does:

Fetch repo metadata (existing)
List the file tree to understand repo structure
Read key config files (README, package.json or requirements.txt, Dockerfile, CI config)
Analyze dependencies for known vulnerabilities
Produce a structured report with sections: Overview, Dependencies, Security Signals

AgentCI tests to write at this step:
Sequencing tests (this is the new capability):

Assert that github_repo_metadata is called before github_list_files (can't list files without knowing the repo exists)
Assert that dependency_analyzer is called after github_read_file for the manifest file (can't analyze deps before reading them)
Assert that github_read_file is called for at least README and the primary manifest file

Tool selection tests:

Given a Python repo, the agent reads requirements.txt or pyproject.toml, NOT package.json
Given a JavaScript repo, the agent reads package.json, NOT requirements.txt
Given a repo with no manifest file, the agent skips dependency analysis and notes it in the report

Regression tests:

Update the golden trace from Phase 0 — the tool call count should now be 4-6 (not 1)
New golden trace captures the full multi-step sequence

Output quality tests:

The report contains all expected sections
Vulnerability counts are integers, not hallucinated strings
If the repo has a README, the summary accurately reflects its contents (use LLM-as-judge for this assertion)

What you learn for AgentCI: This is where you discover whether your sequencing assertion API is intuitive. Can a developer easily say "tool A must come before tool B"? Can they express "tool C should only be called if tool B returned a certain condition"? You'll also hit the question of how to handle variable-length tool call sequences — the agent might read 3 files or 7 files depending on the repo. Your test framework needs to handle both. This is a real design decision for AgentCI.

Phase 2 — Conditional branching and dynamic tool selection (Days 6-9)
What you build: The agent now makes intelligent decisions about which tools to call based on what it discovers. This is where it stops being a script and starts being an agent.
New tools added:

github_actions_analyzer — reads CI/CD workflow files and evaluates configuration
license_checker — validates license compatibility
community_health_scorer — checks for CONTRIBUTING.md, issue templates, PR templates, CODE_OF_CONDUCT

The agent now does:

Everything from Phase 1
Conditionally analyze CI/CD — only if it finds .github/workflows/ or .circleci/ or Jenkinsfile in the file tree
Conditionally check license compatibility — only if a LICENSE file exists
Conditionally score community health — only if there are 50+ stars (small personal repos don't need this)
Produce an expanded report with new sections, and a composite "repo health score" (A through F)

AgentCI tests to write at this step:
Conditional execution tests (this is the new capability):

Given a repo WITH .github/workflows/, the agent calls github_actions_analyzer
Given a repo WITHOUT any CI config, the agent skips github_actions_analyzer and the report notes "No CI/CD detected"
Given a repo with 10 stars, community_health_scorer is NOT called
Given a repo with 500 stars, community_health_scorer IS called

Decision quality tests:

The composite health score is consistent with the sub-scores (a repo with critical vulnerabilities should not get an A)
The recommendations section references specific findings (not generic advice)

Negative testing / hallucination detection:

Given a repo with NO Dockerfile, the report doesn't mention Docker
Given a repo with zero vulnerabilities, the report doesn't invent security concerns

Cost guardrail tests (now meaningful):

A small repo (under 20 files) stays under 8K tokens total
A large monorepo doesn't exceed 30K tokens (the agent should sample, not read every file)
Total API calls to GitHub stay under 15 per analysis (rate limit awareness)

What you learn for AgentCI: Conditional branching is where most testing frameworks fall apart. You can't write a single golden trace that works for every repo because the tool call sequence varies. This forces you to design AgentCI's assertion model around patterns and constraints rather than exact sequences. This is a critical design insight that will differentiate AgentCI from competitors who only support deterministic trace matching. You'll probably need to invent something like "conditional trace segments" or "branching assertions" — and that becomes a feature you market.

Phase 3 — Error recovery and retry logic (Days 10-13)
What you build: The real world breaks. Now you make the agent handle it gracefully.
Failure modes to engineer and test:

GitHub API returns 403 (rate limited) — agent should wait and retry, or switch to unauthenticated endpoint with degraded results
A file read returns 404 (file was deleted between listing and reading) — agent should skip and continue, not crash
Dependency API times out — agent should note "dependency analysis unavailable" and still produce a partial report
Repo is private — agent should detect this immediately and return a clear error instead of hallucinating

No new tools. Instead, you wrap existing tools with error handling and retry logic.
AgentCI tests to write at this step:
Error recovery tests (this is the new capability):

Mock the GitHub API to return 403 on first call, 200 on retry — assert the agent retries and succeeds
Mock a file read to return 404 — assert the agent skips it, logs the skip, and continues the analysis
Mock the dependency API to timeout — assert the report contains a "partially analyzed" disclaimer
Given a private repo URL — assert the agent returns an error within 2 tool calls (doesn't keep trying)

Graceful degradation tests:

When 1 of 5 tools fails, the report still contains the other 4 sections
The composite score adjusts to reflect incomplete data (e.g., "B — based on partial analysis")
The report explicitly lists which analyses were skipped and why

Chaos testing:

Randomly fail 1 of N tool calls — assert the agent always produces a report (never crashes)
This is a test you can run 100 times and track the pass rate — beautiful for CI dashboards

What you learn for AgentCI: This phase teaches you how to build mock/stub infrastructure for tools. Developers need to simulate API failures in their test suites without calling real APIs. If AgentCI doesn't make mocking tools easy, developers will hate writing tests. You'll probably need a @agentci.mock(tool="github_api", response={"status": 403}) decorator or similar. This becomes another core feature.

Phase 4 — LLM-as-judge evaluation (Days 14-17)
What you build: The agent is now functionally complete. This phase is about evaluating output quality — not just whether the right tools were called, but whether the final report is actually good.
New AgentCI capability to dogfood:
LLM-as-judge assertions:

"Is this summary an accurate representation of the README?" (factual accuracy)
"Are the recommendations specific to this repo, or generic boilerplate?" (specificity)
"Does the security section mention all vulnerabilities found by the dependency analyzer?" (completeness)
"Is the report written clearly enough for a non-technical project manager to understand?" (readability)

Comparative evaluation:

Run the agent on the same repo with Claude vs GPT-4 vs Gemini as the backbone LLM
Compare reports side-by-side on accuracy, completeness, cost, and latency
Track which model produces better tool-calling decisions (this is pure gold for AgentCI marketing content)

Regression detection across model updates:

Save today's report as a golden output
When Anthropic ships a new Claude version, re-run and diff against the golden output
Alert if the composite score changes by more than one letter grade (potential regression)

What you learn for AgentCI: LLM-as-judge is where developers have the most uncertainty. How reliable is it? What prompts work? How do you handle disagreements between the judge and the developer's intuition? Your experience building these evals becomes directly transferable to documentation, blog posts, and templates that AgentCI users need. This is also where you discover what "eval primitives" to ship — accuracy, relevance, completeness, specificity, toxicity — as built-in AgentCI assertions.

Phase 5 — CI/CD integration showcase (Days 18-21)
What you build: Wire everything into a GitHub Actions workflow that runs on every commit to the agent's repo. This is the "full circle" moment — an AI agent being tested by your AI agent testing framework, running in CI, on every push.
The CI pipeline:

On push → run AgentCI test suite
Execute all Phase 0-4 tests against 3 fixture repos (small Python, large JS monorepo, empty/broken repo)
Assert all golden traces pass
Assert cost guardrails hold
Run LLM-as-judge evals
Generate a test report dashboard
If any test fails → block merge, show the diff

The marketing artifact this creates: A public GitHub repo where anyone can see the agent code, the AgentCI test suite, and the CI pipeline — all running live. Every green checkmark on every commit is proof that AgentCI works. This becomes the single most powerful sales tool you have — more convincing than any landing page or demo video.

The content calendar this generates
Each phase naturally produces a blog post that drives developer traffic:
WeekPostAngle1"Building an AI agent test-first with AgentCI"TDD for agents, novel concept2"How to test multi-step tool calling in AI agents"The hard problem, your solution3"When your agent should NOT call a tool"Conditional execution testing, very shareable4"Chaos testing for AI agents"Borrowed credibility from chaos engineering, catchy5"Claude vs GPT-4 vs Gemini: which is best for tool-calling agents?"Benchmark content, high SEO value6"We run 200 agent tests on every git push — here's how"The full CI/CD showcase
Each post links to the open-source repo. Each post demonstrates AgentCI. Each post targets a keyword developers are actually searching for. And by the time you've published all six, you have a body of work that no competitor in the agent testing space can match.