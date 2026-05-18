"""Main CLI entry point for the multi-agent system.

Usage
-----
    python main.py                          # interactive prompt
    python main.py "Build a memory app"     # inline requirement
    echo "Build a memory app" | python main.py
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _banner(role: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {role}")
    print("=" * width)


def _print_state(state) -> None:  # type: ignore[type-arg]
    from models import AgentRole

    if state.requirement_spec:
        _banner("BUSINESS ANALYST  –  Clarified Requirements")
        spec = state.requirement_spec
        if spec.clarified_requirements:
            for req in spec.clarified_requirements:
                print(f"  • {req}")
        if spec.research_sources:
            print("\n  Web research:")
            for source in spec.research_sources:
                print(f"    – {source}")
        if spec.user_flows:
            print("\n  User flows:")
            for flow in spec.user_flows:
                print(f"    – {flow}")
        if spec.inputs:
            print("\n  Inputs:")
            for item in spec.inputs:
                print(f"    – {item}")
        if spec.outputs:
            print("\n  Outputs:")
            for item in spec.outputs:
                print(f"    – {item}")
        if spec.color_palette:
            print("\n  Color palette:")
            for color in spec.color_palette:
                print(f"    – {color}")
        if spec.assumptions:
            print("\n  Assumptions:")
            for a in spec.assumptions:
                print(f"    – {a}")
        if spec.out_of_scope:
            print("\n  Out of scope:")
            for o in spec.out_of_scope:
                print(f"    – {o}")
        if spec.feedback:
            print(f"\n  Feedback: {spec.feedback}")

    if state.architecture_spec:
        _banner("ARCHITECT  –  System Architecture")
        arch = state.architecture_spec
        if arch.research_sources:
            print("  Web research:")
            for source in arch.research_sources:
                print(f"    – {source}")
        if arch.architectural_requirements:
            print("\n  Architectural requirements:")
            for item in arch.architectural_requirements:
                print(f"    – {item}")
        print(f"  Overview : {arch.system_overview}")
        if arch.components:
            print("\n  Components:")
            for c in arch.components:
                print(f"    – {c.get('description', '')}")
        if arch.technology_stack:
            print(f"\n  Stack    : {', '.join(arch.technology_stack)}")
        if arch.authentication_strategy:
            print(f"\n  Authentication : {arch.authentication_strategy}")
        if arch.user_journeys:
            print("\n  User journeys:")
            for journey in arch.user_journeys:
                print(f"    – {journey}")
        if arch.user_flows:
            print("\n  User flows:")
            for flow in arch.user_flows:
                print(f"    – {flow}")
        if arch.inputs:
            print("\n  Inputs:")
            for item in arch.inputs:
                print(f"    – {item}")
        if arch.outputs:
            print("\n  Outputs:")
            for item in arch.outputs:
                print(f"    – {item}")
        if arch.styling_guidance:
            print("\n  Styling:")
            for item in arch.styling_guidance:
                print(f"    – {item}")
        if arch.scalability_notes:
            print(f"\n  Scalability : {arch.scalability_notes}")
        if arch.performance_notes:
            print(f"\n  Performance : {arch.performance_notes}")
        if arch.deployment_strategy:
            print(f"\n  Deployment  : {arch.deployment_strategy}")

    if state.build_result:
        _banner("BUILDER  –  Build & Deploy Result")
        build = state.build_result
        status = "✅ SUCCESS" if build.success else "❌ FAILURE"
        print(f"  Status   : {status}")
        if build.artifacts:
            print("\n  Artifacts:")
            for a in build.artifacts:
                print(f"    – {a}")
        if build.deployment_url:
            print(f"\n  URL      : {build.deployment_url}")
        if build.errors:
            print("\n  Errors:")
            for e in build.errors:
                print(f"    – {e}")

    if state.test_result:
        _banner("TESTER  –  Test Results")
        t = state.test_result
        print(f"  Passed   : {'✅' if t.passed else '❌'}")
        print(f"  Run/Pass/Fail : {t.tests_run}/{t.tests_passed}/{t.tests_failed}")
        print(f"  Coverage : {t.coverage_percent:.0f}%")
        if t.failures:
            print("\n  Failures:")
            for f in t.failures:
                print(f"    – {f}")
        if t.iteration_needed:
            agent_name = t.suggested_agent.value if t.suggested_agent else "N/A"
            print(f"\n  ⚠ Iteration needed → {agent_name}")
            if t.iteration_reason:
                print(f"    Reason: {t.iteration_reason}")

    if state.iteration_count:
        print(f"\n  Total iterations: {state.iteration_count}")


def main() -> None:
    from orchestrator import Orchestrator

    # Resolve requirement from CLI args, stdin, or interactive prompt.
    if len(sys.argv) > 1:
        requirement = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        requirement = sys.stdin.read().strip()
    else:
        print("Multi-Agent System")
        print("------------------")
        requirement = input("Enter your requirement: ").strip()
        if not requirement:
            print("No requirement provided. Exiting.")
            sys.exit(0)

    print(f"\nRequirement: {requirement}\n")

    orchestrator = Orchestrator()
    state = orchestrator.run(requirement)

    _print_state(state)
    print("\n" + "=" * 60)
    final = "✅ PASSED" if (state.test_result and state.test_result.passed) else "⚠ NEEDS REVIEW"
    print(f"  Final status: {final}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
