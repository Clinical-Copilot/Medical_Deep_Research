# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

"""
Entry point script for the DeerFlow project.
"""

import argparse
import asyncio

from InquirerPy import inquirer

from src.config.questions import BUILT_IN_QUESTIONS
from src.workflow import run_agent_workflow_async


def ask(
    question,
    debug=False,
    max_plan_iterations=1,
    max_step_num=3,
    output_format="long-report",
    human_feedback=False,
):
    """Run the agent workflow with the given question.

    Args:
        question: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        output_format: Output format - "long-report", "short-report", or custom requirements (default: "long-report")
        human_feedback: Whether to require human feedback on plans (default: False for auto-accept)
    """
    asyncio.run(
        run_agent_workflow_async(
            user_input=question,
            debug=debug,
            max_plan_iterations=max_plan_iterations,
            max_step_num=max_step_num,
            output_format=output_format,
            human_feedback=human_feedback,
        )
    )


def main(
    debug=False, max_plan_iterations=1, max_step_num=3, output_format="long-report", human_feedback=False
):
    """Interactive mode with built-in questions.

    Args:
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        output_format: Output format - "long-report", "short-report", or custom requirements (default: "long-report")
        human_feedback: Whether to require human feedback on plans (default: False for auto-accept)
    """
    # Choose questions
    questions = BUILT_IN_QUESTIONS
    ask_own_option = "[Ask my own question]"

    # Select a question
    initial_question = inquirer.select(
        message="What do you want to know?",
        choices=[ask_own_option] + questions,
    ).execute()

    if initial_question == ask_own_option:
        initial_question = inquirer.text(
            message="What do you want to know?",
        ).execute()

    # Pass all parameters to ask function
    ask(
        question=initial_question,
        debug=debug,
        max_plan_iterations=max_plan_iterations,
        max_step_num=max_step_num,
        output_format=output_format,
        human_feedback=human_feedback,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Medical Deep Research")
    parser.add_argument("query", nargs="*", help="The query to process")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode with built-in questions",
    )
    parser.add_argument(
        "--max_plan_iterations",
        type=int,
        default=1,
        help="Maximum number of plan iterations (default: 1)",
    )
    parser.add_argument(
        "--max_step_num",
        type=int,
        default=3,
        help="Maximum number of steps in a plan (default: 3)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--output_format",
        type=str,
        default="long-report",
        help="Output format - 'long-report', 'short-report', or custom requirements (e.g., 'focus on technical details, include code examples')",
    )
    parser.add_argument(
        "--human_feedback",
        action="store_true",
        help="Require human feedback on plans (default: False - auto-accept plans)",
    )

    args = parser.parse_args()

    if args.interactive:
        # Pass command line arguments to main function
        main(
            debug=args.debug,
            max_plan_iterations=args.max_plan_iterations,
            max_step_num=args.max_step_num,
            output_format=args.output_format,
            human_feedback=args.human_feedback,
        )
    else:
        # Parse user input from command line arguments or user input
        if args.query:
            user_query = " ".join(args.query)
        else:
            user_query = input("Enter your query: ")

        # Run the agent workflow with the provided parameters
        ask(
            question=user_query,
            debug=args.debug,
            max_plan_iterations=args.max_plan_iterations,
            max_step_num=args.max_step_num,
            output_format=args.output_format,
            human_feedback=args.human_feedback,
        )
