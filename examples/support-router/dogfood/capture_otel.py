"""Capture a live support-router interaction as an OTel GenAI trace.

Instruments the underlying OpenAI chat-completions calls with openllmetry
(opentelemetry-instrumentation-openai) and writes a flat JSON span list — the
shape `ciagent import` auto-detects as `otel-genai`. This is the F7 dogfood:
a real production-style failure captured the way a customer's stack would emit
it, then imported into a gated regression test.

Usage:
    python dogfood/capture_otel.py "What plan am I currently on?" -o dogfood/trace.json

Notes baked in from the Responses-vs-ChatCompletions split:
  - openllmetry instruments the chat-completions path only; the Agents SDK can
    route through the Responses API, which would produce an empty capture. We
    pin chat_completions so the underlying calls are visible.
  - TRACELOOP_TRACE_CONTENT=true is required, or openllmetry emits token counts
    with no messages and ciagent's round-trip gate correctly rejects the
    contentless export.
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv


def _build_exporter(collected):
    from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

    class CollectExporter(SpanExporter):
        """Accumulate spans in the fixture shape: name + unix-nano window + flat attrs."""

        def export(self, spans):
            for s in spans:
                collected.append(
                    {
                        "name": s.name,
                        "startTimeUnixNano": str(s.start_time),
                        "endTimeUnixNano": str(s.end_time),
                        "attributes": dict(s.attributes or {}),
                    }
                )
            return SpanExportResult.SUCCESS

        def shutdown(self):
            pass

        def force_flush(self, timeout_millis=30000):
            return True

    return CollectExporter()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", help="Customer query to run through the support router")
    ap.add_argument("-o", "--out", default="dogfood/trace.json", help="Output span JSON path")
    ap.add_argument(
        "-m", "--model", default=None,
        help="Pin the agent model (e.g. gpt-4o-mini). Default: SDK default.",
    )
    args = ap.parse_args()

    # Content capture must be on BEFORE the instrumentor patches openai.
    os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "true")
    load_dotenv()

    # Pin chat-completions: openllmetry only instruments that path.
    try:
        from agents import set_default_openai_api

        set_default_openai_api("chat_completions")
    except Exception as e:  # noqa: BLE001 — best-effort; empty capture is the real signal
        print(f"[warn] could not pin chat_completions api: {e}", file=sys.stderr)

    from opentelemetry import trace as otel_trace
    from opentelemetry.instrumentation.openai import OpenAIInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    collected: list[dict] = []
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_build_exporter(collected)))
    otel_trace.set_tracer_provider(provider)
    OpenAIInstrumentor().instrument(tracer_provider=provider)

    # Import AFTER instrumentation so the patched openai client is in effect.
    trace = None
    final_output = None
    if args.model:
        # Pin a specific model (e.g. gpt-4o-mini) via RunConfig, without
        # mutating the demo's own run.py. We only need the openllmetry spans;
        # the native AgentCI processor is not required here.
        import asyncio

        from agents import Runner, RunConfig
        from agents.exceptions import InputGuardrailTripwireTriggered
        from agents.tracing import set_trace_processors

        from support_router.agents.triage import triage_agent

        set_trace_processors([])

        async def _run():
            try:
                res = await Runner.run(
                    triage_agent, args.query, run_config=RunConfig(model=args.model)
                )
                return str(res.final_output)
            except InputGuardrailTripwireTriggered as e:
                return f"[BLOCKED by input guardrail] {e}"

        final_output = asyncio.run(_run())
    else:
        from support_router.run import run_agent

        trace = run_agent(args.query)
        final_output = trace.metadata.get("final_output") if trace else None
    provider.force_flush()

    if not collected:
        print(
            "[error] no spans captured — openllmetry saw no chat-completions "
            "calls. The Agents SDK likely used the Responses API; the "
            "set_default_openai_api pin above should prevent this.",
            file=sys.stderr,
        )
        sys.exit(3)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(collected, f, indent=2, default=str)

    print(f"captured {len(collected)} span(s) -> {args.out}")
    if args.model:
        print(f"  model (pinned):  {args.model}")
    if trace is not None:
        print(f"  agents involved: {getattr(trace, 'agents_involved', None)}")
    print(f"  final_output:    {str(final_output)[:240]}")


if __name__ == "__main__":
    main()
