#!/usr/bin/python

#    Copyright 2023 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


"""This module parses CLI arguments for the Trestle Bot."""

import argparse
import logging
import sys
from typing import List, Optional

import click

from trestlebot import bot, const, log
from trestlebot.github import GitHub, is_github_actions
from trestlebot.gitlab import GitLab, get_gitlab_root_url, is_gitlab_ci
from trestlebot.provider import GitProvider
from trestlebot.tasks.assemble_task import AssembleTask
from trestlebot.tasks.authored import types
from trestlebot.tasks.authored.ssp import AuthoredSSP, SSPIndex
from trestlebot.tasks.base_task import TaskBase
from trestlebot.tasks.regenerate_task import RegenerateTask


logger = logging.getLogger("trestle")


@click.group()
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def run(ctx: click.Context, verbose: bool):
    ctx.ensure_object(argparse.Namespace)
    ctx.obj.verbose = verbose
    log.set_log_level_from_args(ctx.obj)


@run.command()
@click.option(
    "--branch", type=str, required=True, help="Branch name to push changes to"
)
@click.option(
    "--markdown-path", required=True, type=str, help="Path to Trestle markdown files"
)
@click.option(
    "--oscal-model",
    required=True,
    type=str,
    help="OSCAL model type to run tasks on. Values can be catalog, profile, compdef, or ssp",
)
@click.option(
    "--file-patterns",
    required=True,
    type=str,
    help="Comma-separated list of file patterns to be used with `git add` in repository updates",
)
@click.option(
    "--working-dir",
    required=False,
    type=str,
    default=".",
    help="Working directory wit git repository",
)
@click.option(
    "--skip-items",
    type=str,
    required=False,
    help="Comma-separated list of items of the chosen model type to skip when running tasks",
)
@click.option(
    "--skip-assemble",
    required=False,
    is_flag=True,
    help="Skip assembly task. Defaults to false",
)
@click.option(
    "--skip-regenerate",
    required=False,
    is_flag=True,
    help="Skip regenerate task. Defaults to false.",
)
@click.option(
    "--check-only",
    required=False,
    is_flag=True,
    help="Runs tasks and exits with an error if there is a diff",
)
@click.option(
    "--working-dir",
    type=str,
    required=False,
    default=".",
    help="Working directory wit git repository",
)
@click.option(
    "--commit-message",
    type=str,
    required=False,
    default="chore: automatic updates",
    help="Commit message for automated updates",
)
@click.option(
    "--pull-request-title",
    type=str,
    required=False,
    default="Automatic updates from trestlebot",
    help="Customized title for submitted pull requests",
)
@click.option("--committer-name", type=str, required=True, help="Name of committer")
@click.option("--committer-email", type=str, required=True, help="Email for committer")
@click.option(
    "--author-name",
    required=False,
    type=str,
    help="Name for commit author if differs from committer",
)
@click.option(
    "--author-email",
    required=False,
    type=str,
    help="Email for commit author if differs from committer",
)
@click.option(
    "--ssp-index-path",
    required=False,
    type=str,
    default="ssp-index.json",
    help="Path to ssp index file",
)
@click.option(
    "--target-branch",
    type=str,
    help="Target branch or base branch to create a pull request against. \
        No pull request is created if unset",
)
@click.option(
    "--with-token",
    type=click.File("r"),
    required=False,
    default="-",
    help="Read token from standard input for authenticated \
        requests with Git provider (e.g. create pull requests)",
)
def auto_sync(
    branch: str,
    markdown_path: str,
    oscal_model: str,
    file_patterns: str,
    skip_items: str,
    skip_assemble: bool,
    skip_regenerate: bool,
    check_only: bool,
    working_dir: str,
    commit_message: str,
    pull_request_title: str,
    committer_name: str,
    committer_email: str,
    author_name: str,
    author_email: str,
    ssp_index_path: str,
    target_branch: str,
    with_token,
) -> None:
    """Automatically synchronize data."""

    pre_tasks: List[TaskBase] = []
    git_provider: Optional[GitProvider] = None

    authored_list: List[str] = [model.value for model in types.AuthoredType]

    # Pre-process flags

    if oscal_model:
        if oscal_model not in authored_list:
            logger.error(
                f"Invalid value {oscal_model} for oscal model. "
                f"Please use catalog, profile, compdef, or ssp."
            )
            sys.exit(const.ERROR_EXIT_CODE)

        if not markdown_path:
            logger.error("Must set markdown path with oscal model.")
            sys.exit(const.ERROR_EXIT_CODE)

        if oscal_model == "ssp" and ssp_index_path == "":
            logger.error("Must set ssp_index_path when using SSP as oscal model.")
            sys.exit(const.ERROR_EXIT_CODE)

        # Assuming an edit has occurred assemble would be run before regenerate.
        # Adding this to the list first
        if not skip_assemble:
            assemble_task = AssembleTask(
                working_dir,
                oscal_model,
                markdown_path,
                ssp_index_path,
                comma_sep_to_list(skip_items),
            )
            pre_tasks.append(assemble_task)
        else:
            logger.info("Assemble task skipped")

        if not skip_regenerate:
            regenerate_task = RegenerateTask(
                working_dir,
                oscal_model,
                markdown_path,
                ssp_index_path,
                comma_sep_to_list(skip_items),
            )
            pre_tasks.append(regenerate_task)
        else:
            logger.info("Regeneration task skipped")

    if target_branch:
        if not with_token:
            logger.error("with-token value cannot be empty")
            sys.exit(const.ERROR_EXIT_CODE)

        if is_github_actions():
            git_provider = GitHub(access_token=with_token.read().strip())
        elif is_gitlab_ci():
            server_api_url = get_gitlab_root_url()
            git_provider = GitLab(
                api_token=with_token.read().strip(), server_url=server_api_url
            )
        else:
            logger.error(
                (
                    "target-branch flag is set with an unset git provider. "
                    "To test locally, set the GITHUB_ACTIONS or GITLAB_CI environment variable."
                )
            )
            sys.exit(const.ERROR_EXIT_CODE)

    exit_code: int = const.SUCCESS_EXIT_CODE

    # Assume it is a successful run, if the bot
    # throws an exception update the exit code accordingly
    try:
        commit_sha, pr_number = bot.run(
            working_dir=working_dir,
            branch=branch,
            commit_name=committer_name,
            commit_email=committer_email,
            commit_message=commit_message,
            author_name=author_name,
            author_email=author_email,
            pre_tasks=pre_tasks,
            patterns=comma_sep_to_list(file_patterns),
            git_provider=git_provider,
            target_branch=target_branch,
            pull_request_title=pull_request_title,
            check_only=check_only,
        )

        # Print the full commit sha
        if commit_sha:
            print(f"Commit Hash: {commit_sha}")  # noqa: T201

        # Print the pr number
        if pr_number:
            print(f"Pull Request Number: {pr_number}")  # noqa: T201

    except Exception as e:
        exit_code = handle_exception(e)

    sys.exit(exit_code)


@run.command()
@click.option("--output", type=str, required=True, help="Name of the output SSP file")
@click.option("--profile", required=True, type=str, help="Name of the profile to use")
@click.option(
    "--component-definitions",
    required=False,
    type=str,
    help="Comma-separated list of component definitions to use",
)
@click.option(
    "--filtered-ssp",
    required=False,
    type=str,
    help="Comma-separated list of component definitions to use",
)
@click.option(
    "--leveraged-ssp",
    required=False,
    type=str,
    help="Comma-separated list of component definitions to use",
)
@click.option(
    "--markdown-path", required=True, type=str, help="Path to Trestle markdown files"
)
@click.option(
    "--working-dir",
    required=False,
    type=str,
    default=".",
    help="Working directory wit git repository",
)
@click.option(
    "--ssp-index-path",
    required=False,
    type=str,
    default="ssp-index.json",
    help="Path to ssp index file",
)
def create_new_ssp(
    output: str,
    profile: str,
    markdown_path: str,
    component_definitions: str,
    ssp_index_path: str,
    filtered_ssp: str,
    leveraged_ssp: str,
    working_dir: str,
) -> None:
    """Create a new SSP."""

    exit_code: int = const.SUCCESS_EXIT_CODE

    # Assume it is a successful run, if the bot
    # throws an exception update the exit code accordingly
    try:
        ssp_index = SSPIndex(ssp_index_path)
        authored_ssp = AuthoredSSP(working_dir, ssp_index)

        comps = comma_sep_to_list(component_definitions)
        if filtered_ssp:
            authored_ssp.create_new_with_filter(output, filtered_ssp, profile, comps)
        else:
            authored_ssp.create_new_default(
                output, profile, comps, markdown_path, leveraged_ssp
            )

    except Exception as e:
        exit_code = handle_exception(e)

    sys.exit(exit_code)


def handle_exception(
    exception: Exception, msg: str = "Exception occurred during execution"
) -> int:
    """Log the exception and return the exit code"""
    logger.error(msg + f": {exception}", exc_info=True)

    return const.ERROR_EXIT_CODE


def comma_sep_to_list(string: str) -> List[str]:
    """Convert comma-sep string to list of strings and strip."""
    string = string.strip() if string else ""
    return list(map(str.strip, string.split(","))) if string else []
