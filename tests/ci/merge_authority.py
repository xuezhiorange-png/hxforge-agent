"""Deterministic local Git merge authority for CI current-base ephemeral merges.

Primary authority is the canonical ephemeral merge commit SHA computed locally.
GitHub synthetic refs/pull/<n>/merge is diagnostic only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

SCHEMA_VERSION: Final[str] = "hxforge-ci-current-base-ephemeral-merge-authority-v1"
CANONICAL_COMMIT_MESSAGE_BYTES: Final[bytes] = (
    b"hxforge-ci-current-base-ephemeral-merge-authority-v1\n"
)
PR_HEAD_REF_PREFIX: Final[str] = "refs/hxforge-ci/pr-head"
CURRENT_BASE_REF: Final[str] = "refs/hxforge-ci/current-base"
HXFORGE_RAW_PR_NUMBER_ENV: Final[str] = "HXFORGE_RAW_PR_NUMBER"
METADATA_TIP_MISMATCH_ERROR: Final[str] = "CURRENT_BASE_METADATA_TIP_MISMATCH"
REQUIRED_OBJECT_FORMAT: Final[str] = "sha1"

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_PR_NUMBER_ASCII_RE = re.compile(r"^[1-9][0-9]*$")


class MergeAuthorityError(Exception):
    """Raised when merge authority cannot be established fail-closed."""


@dataclass(frozen=True, slots=True)
class MergeAuthorityIdentity:
    schema_version: str
    base_sha: str
    pr_head_sha: str
    merge_tree_sha: str
    merge_sha: str


@dataclass(frozen=True, slots=True)
class InspectedCommit:
    sha: str
    tree_sha: str
    parents: tuple[str, ...]
    author_line: str
    committer_line: str
    message_bytes: bytes
    raw_header: str


@dataclass(frozen=True, slots=True)
class GitHubCandidateCommitStructure:
    sha: str
    tree_sha: str
    parents: tuple[str, ...]


class GitHubCandidateOutcome(StrEnum):
    ABSENT = "ABSENT"
    STALE_PARENT_BINDING = "STALE_PARENT_BINDING"
    INVALID_PARENT_COUNT = "INVALID_PARENT_COUNT"
    VALID_EQUIVALENT = "VALID_EQUIVALENT"
    TREE_MISMATCH = "TREE_MISMATCH"


class GitHubCandidateStatus(StrEnum):
    VALID_EQUIVALENT = "VALID_EQUIVALENT"
    STALE_PARENT_BINDING = "STALE_PARENT_BINDING"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class GitHubCandidateClassification:
    outcome: GitHubCandidateOutcome
    candidate_sha: str | None = None


def external_candidate_status(
    classification: GitHubCandidateClassification,
) -> GitHubCandidateStatus:
    """Map internal diagnostic classification to frozen external resolver status."""
    if classification.outcome == GitHubCandidateOutcome.ABSENT:
        return GitHubCandidateStatus.MISSING
    if classification.outcome in (
        GitHubCandidateOutcome.INVALID_PARENT_COUNT,
        GitHubCandidateOutcome.STALE_PARENT_BINDING,
    ):
        return GitHubCandidateStatus.STALE_PARENT_BINDING
    if classification.outcome == GitHubCandidateOutcome.VALID_EQUIVALENT:
        return GitHubCandidateStatus.VALID_EQUIVALENT
    raise MergeAuthorityError(
        "TREE_MISMATCH must fail closed before emitting external candidate status"
    )


def _validate_sha40(value: str, label: str) -> str:
    lowered = value.strip().lower()
    if not _SHA40_RE.fullmatch(lowered):
        raise MergeAuthorityError(f"{label} is not a 40-char lowercase SHA: {value!r}")
    return lowered


def validate_pr_number_lexical(value: str) -> int:
    """Reject PR numbers outside the exact ASCII lexical form ^[1-9][0-9]*$."""
    if not _PR_NUMBER_ASCII_RE.fullmatch(value):
        raise MergeAuthorityError(
            f"pr_number must match ASCII lexical form ^[1-9][0-9]*$: {value!r}"
        )
    return int(value, 10)


def validate_raw_pr_number_from_env() -> int:
    """Validate HXFORGE_RAW_PR_NUMBER from the environment as data-only input."""
    raw = os.environ.get(HXFORGE_RAW_PR_NUMBER_ENV)
    if raw is None:
        raise MergeAuthorityError(f"{HXFORGE_RAW_PR_NUMBER_ENV} environment variable is not set")
    return validate_pr_number_lexical(raw)


def sanitized_pr_number_text(value: str) -> str:
    """Return canonical ASCII decimal text after lexical validation."""
    return str(validate_pr_number_lexical(value))


def _validate_base_ref(base_ref: str) -> str:
    ref = base_ref.strip()
    if not ref:
        raise MergeAuthorityError("base_ref must be non-empty")
    full_ref = f"refs/heads/{ref}"
    _run_git(["git", "check-ref-format", full_ref])
    return ref


def resolve_current_base_sha(base_ref: str) -> str:
    """Independently resolve the current tip SHA of refs/heads/<base_ref>."""
    ref = _validate_base_ref(base_ref)
    _run_git(
        [
            "git",
            "fetch",
            "--no-tags",
            "--force",
            "origin",
            f"+refs/heads/{ref}:{CURRENT_BASE_REF}",
        ]
    )
    current_base_sha = _run_git(["git", "rev-parse", CURRENT_BASE_REF]).stdout.strip()
    current_base_sha = _validate_sha40(current_base_sha, "current_base_sha")
    _assert_commit_exists(current_base_sha)
    return current_base_sha


def _assert_metadata_tip_consistency(base_metadata_sha: str, current_base_sha: str) -> None:
    metadata = _validate_sha40(base_metadata_sha, "base_metadata_sha")
    current = _validate_sha40(current_base_sha, "current_base_sha")
    if metadata != current:
        raise MergeAuthorityError(
            f"{METADATA_TIP_MISMATCH_ERROR}: metadata={metadata} current_tip={current}"
        )


def _base_git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["LC_ALL"] = "C"
    env["TZ"] = "UTC"
    return env


def _commit_git_env() -> dict[str, str]:
    env = _base_git_env()
    env["GIT_AUTHOR_NAME"] = "HxForge CI"
    env["GIT_AUTHOR_EMAIL"] = "hxforge-ci@example.invalid"
    env["GIT_AUTHOR_DATE"] = "946684800 +0000"
    env["GIT_COMMITTER_NAME"] = "HxForge CI"
    env["GIT_COMMITTER_EMAIL"] = "hxforge-ci@example.invalid"
    env["GIT_COMMITTER_DATE"] = "946684800 +0000"
    return env


def _run_git_bytes(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    if args and args[0] == "git":
        args = ["git", "-c", "core.hooksPath=/dev/null", *args[1:]]
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=False,
        input=input_bytes,
        env=env if env is not None else _base_git_env(),
        cwd=cwd,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        detail = stderr or stdout or f"exit {completed.returncode}"
        raise MergeAuthorityError(f"git command failed ({' '.join(args)}): {detail}")
    return completed


def _run_git(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    if args and args[0] == "git":
        args = ["git", "-c", "core.hooksPath=/dev/null", *args[1:]]
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=input_bytes is None,
        input=input_bytes,
        env=env if env is not None else _base_git_env(),
        cwd=cwd,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() if isinstance(completed.stderr, str) else ""
        stdout = completed.stdout.strip() if isinstance(completed.stdout, str) else ""
        detail = stderr or stdout or f"exit {completed.returncode}"
        raise MergeAuthorityError(f"git command failed ({' '.join(args)}): {detail}")
    return completed


def git_version() -> str:
    return _run_git(["git", "--version"]).stdout.strip()


def git_object_format() -> str:
    return _run_git(["git", "rev-parse", "--show-object-format"]).stdout.strip()


def _expected_canonical_header_bytes(
    base_sha: str,
    pr_head_sha: str,
    merge_tree_sha: str,
) -> bytes:
    lines = (
        f"tree {merge_tree_sha}",
        f"parent {base_sha}",
        f"parent {pr_head_sha}",
        "author HxForge CI <hxforge-ci@example.invalid> 946684800 +0000",
        "committer HxForge CI <hxforge-ci@example.invalid> 946684800 +0000",
    )
    return "\n".join(lines).encode("ascii")


def _cat_file_raw_bytes(sha: str) -> bytes:
    commit_sha = _validate_sha40(sha, "commit sha")
    return _run_git_bytes(["git", "cat-file", "-p", commit_sha]).stdout


def inspect_canonical_commit_raw(
    sha: str,
    *,
    base_sha: str,
    pr_head_sha: str,
    merge_tree_sha: str,
) -> tuple[bytes, bytes]:
    """Inspect canonical merge commit raw bytes with fail-closed header verification."""
    raw = _cat_file_raw_bytes(sha)
    separator = raw.find(b"\n\n")
    if separator < 0:
        raise MergeAuthorityError(f"commit {sha} has no message separator")
    header_bytes = raw[:separator]
    message_bytes = raw[separator + 2 :]
    expected_header = _expected_canonical_header_bytes(base_sha, pr_head_sha, merge_tree_sha)
    if header_bytes != expected_header:
        raise MergeAuthorityError(
            "canonical commit header bytes mismatch: "
            f"expected {expected_header!r}, got {header_bytes!r}"
        )
    if message_bytes != CANONICAL_COMMIT_MESSAGE_BYTES:
        raise MergeAuthorityError(f"canonical commit message bytes mismatch: {message_bytes!r}")
    return header_bytes, message_bytes


def inspect_commit(sha: str) -> InspectedCommit:
    commit_sha = _validate_sha40(sha, "commit sha")
    raw = _run_git(["git", "cat-file", "-p", commit_sha]).stdout
    header, separator, message = raw.partition("\n\n")
    if not separator:
        raise MergeAuthorityError(f"commit {commit_sha} has no message separator")
    lines = header.splitlines()
    if not lines:
        raise MergeAuthorityError(f"commit {commit_sha} has empty header")
    tree_sha = ""
    parents: list[str] = []
    author_line = ""
    committer_line = ""
    for line in lines:
        if line.startswith("tree "):
            tree_sha = line.split()[1]
        elif line.startswith("parent "):
            parents.append(line.split()[1])
        elif line.startswith("author "):
            author_line = line[len("author ") :]
        elif line.startswith("committer "):
            committer_line = line[len("committer ") :]
        elif line.startswith("gpgsig ") or line.startswith("encoding "):
            raise MergeAuthorityError(f"commit {commit_sha} has forbidden header line: {line}")
    if not tree_sha:
        raise MergeAuthorityError(f"commit {commit_sha} missing tree header")
    return InspectedCommit(
        sha=commit_sha,
        tree_sha=tree_sha,
        parents=tuple(parents),
        author_line=author_line,
        committer_line=committer_line,
        message_bytes=message.encode("utf-8"),
        raw_header=header,
    )


def inspect_github_candidate_structure(sha: str) -> GitHubCandidateCommitStructure:
    """Inspect GitHub synthetic merge candidate authority-bearing structure only."""
    commit_sha = _validate_sha40(sha, "commit sha")
    _assert_commit_exists(commit_sha)
    raw = _cat_file_raw_bytes(commit_sha)
    separator = raw.find(b"\n\n")
    if separator < 0:
        raise MergeAuthorityError(f"commit {commit_sha} has no message separator")
    header_text = raw[:separator].decode("utf-8", errors="strict")
    tree_sha = ""
    parents: list[str] = []
    tree_count = 0
    for line in header_text.splitlines():
        if line.startswith(" "):
            continue
        if line.startswith("tree "):
            parts = line.split()
            if len(parts) != 2:
                raise MergeAuthorityError(
                    f"commit {commit_sha} has malformed tree header: {line!r}"
                )
            tree_count += 1
            if tree_count > 1:
                raise MergeAuthorityError(f"commit {commit_sha} has multiple tree headers")
            tree_sha = _validate_sha40(parts[1], "tree sha")
        elif line.startswith("parent "):
            parts = line.split()
            if len(parts) != 2:
                raise MergeAuthorityError(
                    f"commit {commit_sha} has malformed parent header: {line!r}"
                )
            parents.append(_validate_sha40(parts[1], "parent sha"))
    if not tree_sha:
        raise MergeAuthorityError(f"commit {commit_sha} missing tree header")
    return GitHubCandidateCommitStructure(
        sha=commit_sha,
        tree_sha=tree_sha,
        parents=tuple(parents),
    )


def _assert_full_history() -> None:
    shallow = _run_git(["git", "rev-parse", "--is-shallow-repository"]).stdout.strip()
    if shallow != "false":
        raise MergeAuthorityError(
            f"repository must not be shallow (rev-parse --is-shallow-repository={shallow!r})"
        )


def _assert_commit_exists(sha: str) -> None:
    _run_git(["git", "cat-file", "-e", f"{sha}^{{commit}}"])


def _assert_tree_exists(tree_sha: str) -> None:
    _run_git(["git", "cat-file", "-e", f"{tree_sha}^{{tree}}"])


def acquire_objects(
    pr_number: int,
    current_base_sha: str,
    pr_head_sha: str,
) -> None:
    """Phase B: acquire Git objects from the frozen SHA pair only."""
    base = _validate_sha40(current_base_sha, "current_base_sha")
    head = _validate_sha40(pr_head_sha, "pr_head_sha")
    _assert_full_history()
    _run_git(
        [
            "git",
            "fetch",
            "--no-tags",
            "--force",
            "origin",
            f"+{base}:{CURRENT_BASE_REF}",
        ]
    )
    fetched_base = _run_git(["git", "rev-parse", CURRENT_BASE_REF]).stdout.strip()
    if fetched_base != base:
        raise MergeAuthorityError(
            f"{CURRENT_BASE_REF} mismatch: expected {base}, got {fetched_base}"
        )
    _run_git(["git", "checkout", "--detach", base])
    head_now = _run_git(["git", "rev-parse", "HEAD"]).stdout.strip()
    if head_now != base:
        raise MergeAuthorityError(f"HEAD after base checkout mismatch: {head_now} != {base}")
    pr_head_ref = PR_HEAD_REF_PREFIX
    _run_git(
        [
            "git",
            "fetch",
            "--no-tags",
            "--force",
            "origin",
            f"+refs/pull/{pr_number}/head:{pr_head_ref}",
        ]
    )
    fetched_head = _run_git(["git", "rev-parse", pr_head_ref]).stdout.strip()
    if fetched_head != head:
        raise MergeAuthorityError(f"{pr_head_ref} mismatch: expected {head}, got {fetched_head}")
    _assert_commit_exists(base)
    _assert_commit_exists(head)
    merge_base = _run_git(["git", "merge-base", base, head]).stdout.strip()
    if not merge_base:
        raise MergeAuthorityError("merge-base returned empty result")
    _validate_sha40(merge_base, "merge_base")


def compute_merge_tree(base_sha: str, pr_head_sha: str) -> str:
    base = _validate_sha40(base_sha, "base_sha")
    head = _validate_sha40(pr_head_sha, "pr_head_sha")
    completed = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "merge-tree", "--write-tree", base, head],
        check=False,
        capture_output=True,
        text=True,
        env=_base_git_env(),
    )
    if completed.returncode != 0:
        raise MergeAuthorityError(
            "merge-tree failed (conflict or missing ancestry): "
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    tree_sha = completed.stdout.strip().splitlines()[-1].strip()
    if not tree_sha:
        raise MergeAuthorityError("merge-tree returned empty tree SHA")
    tree_sha = _validate_sha40(tree_sha, "merge_tree_sha")
    _assert_tree_exists(tree_sha)
    return tree_sha


def _verify_canonical_raw_commit(
    commit_sha: str,
    *,
    base_sha: str,
    pr_head_sha: str,
    merge_tree_sha: str,
) -> None:
    inspect_canonical_commit_raw(
        commit_sha,
        base_sha=base_sha,
        pr_head_sha=pr_head_sha,
        merge_tree_sha=merge_tree_sha,
    )


def build_canonical_ephemeral_merge(
    base_sha: str,
    pr_head_sha: str,
    merge_tree_sha: str,
) -> str:
    base = _validate_sha40(base_sha, "base_sha")
    head = _validate_sha40(pr_head_sha, "pr_head_sha")
    tree = _validate_sha40(merge_tree_sha, "merge_tree_sha")
    completed = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "i18n.commitEncoding=UTF-8",
            "commit-tree",
            tree,
            "-p",
            base,
            "-p",
            head,
        ],
        check=False,
        capture_output=True,
        text=False,
        input=CANONICAL_COMMIT_MESSAGE_BYTES,
        env=_commit_git_env(),
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise MergeAuthorityError(f"commit-tree failed: {detail}")
    merge_sha = completed.stdout.decode("ascii").strip()
    merge_sha = _validate_sha40(merge_sha, "merge_sha")
    _verify_canonical_raw_commit(
        merge_sha,
        base_sha=base,
        pr_head_sha=head,
        merge_tree_sha=tree,
    )
    return merge_sha


def classify_github_candidate(
    candidate_sha: str | None,
    base_sha: str,
    pr_head_sha: str,
    merge_tree_sha: str,
) -> GitHubCandidateClassification:
    if candidate_sha is None:
        return GitHubCandidateClassification(
            outcome=GitHubCandidateOutcome.ABSENT, candidate_sha=None
        )
    candidate = _validate_sha40(candidate_sha, "candidate_sha")
    base = _validate_sha40(base_sha, "base_sha")
    head = _validate_sha40(pr_head_sha, "pr_head_sha")
    tree = _validate_sha40(merge_tree_sha, "merge_tree_sha")
    inspected = inspect_github_candidate_structure(candidate)
    if len(inspected.parents) != 2:
        return GitHubCandidateClassification(
            outcome=GitHubCandidateOutcome.INVALID_PARENT_COUNT,
            candidate_sha=candidate,
        )
    if inspected.parents[0] != base or inspected.parents[1] != head:
        return GitHubCandidateClassification(
            outcome=GitHubCandidateOutcome.STALE_PARENT_BINDING,
            candidate_sha=candidate,
        )
    if inspected.tree_sha == tree:
        return GitHubCandidateClassification(
            outcome=GitHubCandidateOutcome.VALID_EQUIVALENT,
            candidate_sha=candidate,
        )
    return GitHubCandidateClassification(
        outcome=GitHubCandidateOutcome.TREE_MISMATCH,
        candidate_sha=candidate,
    )


def fetch_github_merge_candidate(pr_number: int) -> str | None:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "fetch",
            "--no-tags",
            "--force",
            "origin",
            f"refs/pull/{pr_number}/merge",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=_base_git_env(),
    )
    if completed.returncode != 0:
        return None
    return _run_git(["git", "rev-parse", "FETCH_HEAD"]).stdout.strip()


def resolve_merge_authority(
    pr_number: int,
    base_ref: str,
    base_metadata_sha: str,
    pr_head_sha: str,
    *,
    github_candidate_sha: str | None = None,
) -> tuple[MergeAuthorityIdentity, GitHubCandidateClassification]:
    current_base_sha = resolve_current_base_sha(base_ref)
    _assert_metadata_tip_consistency(base_metadata_sha, current_base_sha)
    acquire_objects(pr_number, current_base_sha, pr_head_sha)
    merge_tree_sha = compute_merge_tree(current_base_sha, pr_head_sha)
    merge_sha = build_canonical_ephemeral_merge(current_base_sha, pr_head_sha, merge_tree_sha)
    identity = MergeAuthorityIdentity(
        schema_version=SCHEMA_VERSION,
        base_sha=current_base_sha,
        pr_head_sha=pr_head_sha,
        merge_tree_sha=merge_tree_sha,
        merge_sha=merge_sha,
    )
    classification = classify_github_candidate(
        github_candidate_sha, current_base_sha, pr_head_sha, merge_tree_sha
    )
    if classification.outcome == GitHubCandidateOutcome.TREE_MISMATCH:
        raise MergeAuthorityError(
            "GitHub synthetic merge candidate has matching parents but different tree"
        )
    if not identity.merge_sha:
        raise MergeAuthorityError("resolve-authority produced empty merge-sha")
    return identity, classification


def _assert_resolver_git_binding(
    resolver_git_version: str,
    resolver_git_object_format: str,
) -> None:
    local_version = git_version()
    local_format = git_object_format()
    if local_version != resolver_git_version:
        raise MergeAuthorityError(
            f"git-version mismatch: resolver={resolver_git_version!r} local={local_version!r}"
        )
    if local_format != resolver_git_object_format:
        raise MergeAuthorityError(
            "git-object-format mismatch: "
            f"resolver={resolver_git_object_format!r} local={local_format!r}"
        )
    if resolver_git_object_format != REQUIRED_OBJECT_FORMAT:
        raise MergeAuthorityError(
            f"resolver git-object-format must be {REQUIRED_OBJECT_FORMAT!r}, "
            f"got {resolver_git_object_format!r}"
        )


def materialize_and_verify(
    pr_number: int,
    current_base_sha: str,
    pr_head_sha: str,
    expected_merge_tree_sha: str,
    expected_merge_sha: str,
    *,
    resolver_git_version: str,
    resolver_git_object_format: str,
) -> MergeAuthorityIdentity:
    _assert_resolver_git_binding(resolver_git_version, resolver_git_object_format)
    acquire_objects(pr_number, current_base_sha, pr_head_sha)
    merge_tree_sha = compute_merge_tree(current_base_sha, pr_head_sha)
    merge_sha = build_canonical_ephemeral_merge(current_base_sha, pr_head_sha, merge_tree_sha)
    identity = MergeAuthorityIdentity(
        schema_version=SCHEMA_VERSION,
        base_sha=current_base_sha,
        pr_head_sha=pr_head_sha,
        merge_tree_sha=merge_tree_sha,
        merge_sha=merge_sha,
    )
    if identity.merge_tree_sha != expected_merge_tree_sha:
        raise MergeAuthorityError(
            "materialized merge_tree_sha mismatch: "
            f"expected {expected_merge_tree_sha}, got {identity.merge_tree_sha}"
        )
    if identity.merge_sha != expected_merge_sha:
        raise MergeAuthorityError(
            "materialized merge_sha mismatch: "
            f"expected {expected_merge_sha}, got {identity.merge_sha}"
        )
    _run_git(["git", "checkout", "--detach", identity.merge_sha])
    head = _run_git(["git", "rev-parse", "HEAD"]).stdout.strip()
    if head != identity.merge_sha:
        raise MergeAuthorityError(
            f"HEAD after materialize mismatch: {head} != {identity.merge_sha}"
        )
    return identity


def _write_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


def _cmd_validate_pr_number_env(_args: argparse.Namespace) -> int:
    number = validate_raw_pr_number_from_env()
    canonical = str(number)
    _write_github_output("pr-number", canonical)
    sys.stdout.write(canonical)
    return 0


def _cmd_resolve(args: argparse.Namespace) -> int:
    pr_number = validate_pr_number_lexical(args.pr_number)
    base_ref = _validate_base_ref(args.base_ref)
    base_metadata_sha = _validate_sha40(args.base_metadata_sha, "base_metadata_sha")
    pr_head_sha = _validate_sha40(args.pr_head_sha, "pr_head_sha")
    object_format = git_object_format()
    if object_format != REQUIRED_OBJECT_FORMAT:
        raise MergeAuthorityError(f"unsupported git-object-format {object_format!r}, require sha1")
    version = git_version()
    github_candidate: str | None = None
    if not args.skip_github_candidate:
        github_candidate = fetch_github_merge_candidate(pr_number)
    identity, classification = resolve_merge_authority(
        pr_number,
        base_ref,
        base_metadata_sha,
        pr_head_sha,
        github_candidate_sha=github_candidate,
    )
    external_status = external_candidate_status(classification)
    _write_github_output("pr-number", str(pr_number))
    _write_github_output("base-ref", base_ref)
    _write_github_output("base-metadata-sha", base_metadata_sha)
    _write_github_output("base-sha", identity.base_sha)
    _write_github_output("pr-head-sha", identity.pr_head_sha)
    _write_github_output("merge-tree-sha", identity.merge_tree_sha)
    _write_github_output("merge-sha", identity.merge_sha)
    _write_github_output("git-version", version)
    _write_github_output("git-object-format", object_format)
    _write_github_output("github-candidate-status", external_status.value)
    if classification.candidate_sha is not None:
        _write_github_output("github-candidate-sha", classification.candidate_sha)
    return 0


def _cmd_materialize(args: argparse.Namespace) -> int:
    pr_number = validate_pr_number_lexical(args.pr_number)
    materialize_and_verify(
        pr_number,
        _validate_sha40(args.base_sha, "base_sha"),
        _validate_sha40(args.pr_head_sha, "pr_head_sha"),
        _validate_sha40(args.expected_merge_tree_sha, "expected_merge_tree_sha"),
        _validate_sha40(args.expected_merge_sha, "expected_merge_sha"),
        resolver_git_version=args.resolver_git_version,
        resolver_git_object_format=args.resolver_git_object_format,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tests.ci.merge_authority")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_env_parser = subparsers.add_parser("validate-pr-number-env")
    validate_env_parser.set_defaults(func=_cmd_validate_pr_number_env)

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("--pr-number", required=True)
    resolve_parser.add_argument("--base-ref", required=True)
    resolve_parser.add_argument("--base-metadata-sha", required=True)
    resolve_parser.add_argument("--pr-head-sha", required=True)
    resolve_parser.add_argument("--skip-github-candidate", action="store_true")
    resolve_parser.set_defaults(func=_cmd_resolve)

    materialize_parser = subparsers.add_parser("materialize")
    materialize_parser.add_argument("--pr-number", required=True)
    materialize_parser.add_argument("--base-sha", required=True)
    materialize_parser.add_argument("--pr-head-sha", required=True)
    materialize_parser.add_argument("--expected-merge-tree-sha", required=True)
    materialize_parser.add_argument("--expected-merge-sha", required=True)
    materialize_parser.add_argument("--resolver-git-version", required=True)
    materialize_parser.add_argument("--resolver-git-object-format", required=True)
    materialize_parser.set_defaults(func=_cmd_materialize)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except MergeAuthorityError as exc:
        print(f"merge-authority-error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
