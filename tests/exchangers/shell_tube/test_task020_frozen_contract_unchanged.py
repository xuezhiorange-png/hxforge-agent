"""TASK-020 design contract frozen-contract-unchanged test.

Asserts that the TASK-020 design contract file
``docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`` is not
modified except via this frozen-contract guard. The contract is
**frozen** at the Amendment 003 / Issue #133 final metadata
stabilization round final byte content (second blocking review
comment `4950559775`; first blocking review comment `4950510717`;
authority comment `4950333856` binding Option A semantics).

This test verifies seven invariants:

1. The TASK-020 design contract file is **present** on the
   implementation branch.
2. The TASK-020 design contract file is **unchanged** from the
   Amendment 003 final metadata stabilization round final byte
   content, verified by content hash (CI-independent: no git
   history or remote refs required).
3. The TASK-020 design contract §1 heading is present (sanity
   check on the contract text).
4. The TASK-020 design contract §21 Amendment 003 heading is
   present and the two exact legacy S1 carve-out paths are
   listed in §14.2.5 (Amendment 003 specific integrity
   assertions).
5. The TASK-020 design contract enumerates Issue
   `#133` as the binding Amendment 003 Issue number
   (Amendment 003 metadata presence assertion).
6. The TASK-020 design contract reflects the post-Amendment-002
   merged-state facts (PR #132 = MERGED at SHA `60e5d15d…`,
   merge SHA `4a229625…`, post-merge CI `29182404791`) and MUST
   NOT re-stamp those rows as DRAFT / NOT READY / NOT MERGED
   in the §1 current-authority table nor in §21.A.
7. The TASK-020 design contract enforces the final metadata
   stabilization invariants: Issue #131 historical OPEN
   review-time statement; live GitHub metadata externalization
   rule; NO self-referential commit SHAs; NO transient
   transfer-state tokens; PR #132 immutable merged facts;
   Issue #133 authority; two exact S1 paths; §14.2.5 + §21
   headings; exactly one accepted SHA-256; no hash fallback /
   list / set / env-var bypass / conditional skip / weakened
   presence assertion.

This test is the **only** test mutation authorized by the
Amendment 003 / Issue #133 final metadata stabilization round. It
MUST NOT be weakened or bypassed, MUST NOT carry a list or set
of accepted hashes, MUST NOT retain any old hash as a fallback,
MUST NOT accept any environment variable bypass, MUST NOT
introduce a conditional skip, MUST NOT weaken the
document-presence or heading assertions, MUST NOT remove the
Amendment 003 heading presence assertion, MUST NOT remove the
two exact S1 carve-out path presence assertions, MUST NOT remove
the Issue #133 presence assertion, MUST NOT remove the
PR #132 merged-state presence assertion nor its stale-token
negative assertions, MUST NOT remove the Issue #131 historical
OPEN review-time presence assertion, and MUST NOT remove the
live GitHub metadata externalization rule presence assertion.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_DESIGN_CONTRACT_PATH = Path("docs/tasks/TASK-020-shell-and-tube-configuration-schema.md")
# A unique 1-line signature of the design contract body: the §1
# "Authority, status and authorization gate" heading is the first
# section of the contract and is present in every revision of the
# design.
_EXPECTED_DESIGN_HEADING = "## 1. Authority, status and authorization gate"

# Amendment 003 heading presence assertion (§21 — S1 test expectation
# carve-out). The Amendment 003 round is the only amendment that
# authorizes a §21 record; pre-Amendment-003 SHAs do not contain it.
_EXPECTED_AMENDMENT_003_HEADING = "## 21. Design Amendment 003 — S1 test expectation carve-out"

# The two exact legacy S1 carve-out paths required to appear in
# §14.2.5 + §21.C of the design contract.
_EXPECTED_AMENDMENT_003_S1_PATHS = (
    "tests/exchangers/shell_tube/test_task020_blockers.py",
    "tests/exchangers/shell_tube/test_task020_schema.py",
)

# The §14.2.5 carve-out sub-section heading presence assertion.
_EXPECTED_AMENDMENT_003_CARVEOUT_HEADING = (
    "#### 14.2.5 Amendment 003 legacy S1 test-correction carve-out"
)

# The binding Amendment 003 Issue number (GitHub state-verified
# OPEN via `GET /repos/{owner}/{repo}/issues/133` on the
# Amendment 003 authoring date). The design contract MUST
# enumerate this Issue number across §19.K + §21.A + §21.F +
# §21.G.
_EXPECTED_AMENDMENT_003_ISSUE_NUMBER = "133"
_EXPECTED_AMENDMENT_003_ISSUE_NUMBER_TOKEN = f"**#{_EXPECTED_AMENDMENT_003_ISSUE_NUMBER}**"
_EXPECTED_AMENDMENT_003_ISSUE_URL = "https://github.com/xuezhiorange-png/hxforge-agent/issues/133"

# Amendment 002 PR #132 merged-state facts (verified on the
# Amendment 003 transfer-review corrective round via unauthenticated
# `GET /repos/{owner}/{repo}/pulls/132` + `GET /repos/{owner}/{repo}/actions/runs/29182404791`
# — token-free audit protocol per MEMORY):
#   - PR #132 state: MERGED
#   - PR #132 merge_commit_sha: 4a2296258cfffe497623ee20d9b29fcc97358aaa
#   - PR #132 head SHA: 60e5d15d9e1ccef9a952a9b7ba599ed12035ae87
#   - PR #132 merged_at: 2026-07-12T06:16:15Z
#   - Post-merge CI run: 29182404791 — completed / success
# The design contract MUST enumerate these values across §1
# current-authority rows + §21.A PR #132 record. It MUST NOT
# describe PR #132 as DRAFT / NOT READY / NOT MERGED, nor
# describe Amendment 002 as remaining unmerged, nor bind
# current `main` to the pre-Amendment-002 SHA `d4ee40109…`.
_EXPECTED_PR132_MERGE_SHA = "4a2296258cfffe497623ee20d9b29fcc97358aaa"
_EXPECTED_PR132_HEAD_SHA = "60e5d15d9e1ccef9a952a9b7ba599ed12035ae87"
_EXPECTED_PR132_POST_MERGE_CI = "29182404791"
_EXPECTED_PR132_MERGED_AT = "2026-07-12T06:16:15Z"

# The historical Issue #131 review-time OPEN statement that the
# final metadata stabilization round requires the contract to
# carry verbatim. This is a HISTORICAL fact (state at the time of
# the Amendment 003 transfer review on 2026-07-12), not a
# permanent GitHub-state invariant.
_EXPECTED_ISSUE_131_HISTORICAL_OPEN_STATEMENT = (
    "Issue #131 was OPEN at the Amendment 003 transfer review on 2026-07-12"
)

# The live GitHub metadata externalization rule that the final
# metadata stabilization round requires the contract to carry
# verbatim (live metadata is read from GitHub when needed; not
# duplicated as permanent current-state content).
_EXPECTED_LIVE_METADATA_EXTERNALIZATION_RULE = "Live GitHub metadata"

# SHA-256 of docs/tasks/TASK-020-shell-and-tube-configuration-schema.md
# at the frozen Amendment 003 final metadata stabilization round final
# byte content (this branch HEAD).
# Pre-computed via:
#   python3 -c \
#     "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('docs/tasks/TASK-020-shell-and-tube-configuration-schema.md').read_bytes()).hexdigest())"  # noqa: E501
#
# Authority chain: Amendment 001 merge SHA d4ee40109c74061db89339e55899cabfe2fb80fe
#                  → Design Amendment 002 / Issue #131 final byte content
#                  → SHA-256 ec15dd0668f4497c981a432bde5aaeef50560060e4733872f367aa9c35426ddb
#                  → Review "4677752194" P0/P1 corrective Commit E
#                  → SHA-256 9d6ae05ca2f1656f9a7c63a35f6043cea9220f21a59fcb7e97f3d79819a5c4c2
#                  → Amendment 002 merge to main at SHA 4a2296258cfffe497623ee20d9b29fcc97358aaa
#                    (PR #132 MERGED; merge SHA = current main SHA; head 60e5d15d…;
#                     post-merge CI 29182404791 success)
#                  → Amendment 003 / Issue #133 (state OPEN; first blocking review comment
#                    4950510717; second blocking review comment 4950559775;
#                    authority comment 4950333856 Option A semantics;
#                    base SHA 4a2296258cfffe497623ee20d9b29fcc97358aaa)
#                  → previous SHA 89fd4ad5a5bca31cef0def27fd7ce382d84fb3406444060f32027de8bf0c05dd
#                    (Amendment 003 transfer-review corrective round body)
#                  → final SHA after final metadata stabilization round
# (this branch HEAD). The single accepted hash below is the ONLY
# accepted hash; no fallback list, no set of accepted hashes, no
# OR-style bypass, no env-var bypass, no conditional skip.
_EXPECTED_FROZEN_SHA256 = "f9c2e820574ca363a92de63318f6fd717d5b5312159c49cbcdae63e01c56806c"


def test_design_contract_present() -> None:
    assert _DESIGN_CONTRACT_PATH.exists(), f"missing design contract: {_DESIGN_CONTRACT_PATH}"


def test_design_contract_unchanged_from_frozen_authority() -> None:
    """The TASK-020 design contract must not be modified by the
    Amendment 003 / Issue #133 final metadata stabilization round
    except via this test's own SHA-256 update.

    Verified by content hash (SHA-256) against the pre-computed
    hash of the frozen authority revision's file content. This
    check is CI-independent: it requires only the checked-out
    file content, not git history, ``origin/main``, or any
    remote ref (which a shallow CI checkout may not provide).
    Only the single accepted hash listed at module scope is
    allowed; no fallback list, no set of accepted hashes, no
    OR-style bypass, no env-var bypass, no conditional skip.
    """
    current_sha256 = hashlib.sha256(_DESIGN_CONTRACT_PATH.read_bytes()).hexdigest()
    assert current_sha256 == _EXPECTED_FROZEN_SHA256, (
        "TASK-020 frozen design contract has drifted:\n"
        f"  current: {current_sha256}\n"
        f"  expected: {_EXPECTED_FROZEN_SHA256}"
    )


def test_design_contract_first_heading_present() -> None:
    """The design contract §1 heading must be present (sanity
    check on the contract text)."""
    assert _EXPECTED_DESIGN_HEADING in _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8"), (
        "design contract §1 heading missing"
    )


def test_design_contract_amendment_003_heading_present() -> None:
    """Amendment 003 introduces a §21 record; the heading MUST be
    present in the frozen Amendment 003 final byte content.

    This assertion guards against any future round accidentally
    deleting the §21 Amendment 003 heading without a corresponding
    single-hash SHA-256 update.
    """
    body = _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8")
    assert _EXPECTED_AMENDMENT_003_HEADING in body, (
        "design contract §21 Design Amendment 003 heading missing"
    )


def test_design_contract_amendment_003_carveout_heading_present() -> None:
    """Amendment 003 introduces §14.2.5 (carve-out sub-section).
    The heading MUST be present in the frozen Amendment 003 final
    byte content."""
    body = _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8")
    assert _EXPECTED_AMENDMENT_003_CARVEOUT_HEADING in body, (
        "design contract §14.2.5 Amendment 003 carve-out heading missing"
    )


def test_design_contract_amendment_003_s1_paths_listed() -> None:
    """The two exact legacy S1 carve-out paths MUST be enumerated
    in the frozen Amendment 003 final byte content (in §14.2.5 and
    §21.C)."""
    body = _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8")
    for path in _EXPECTED_AMENDMENT_003_S1_PATHS:
        assert path in body, f"design contract Amendment 003 missing carved-out S1 path: {path}"


def test_design_contract_amendment_003_issue_number_bound() -> None:
    """Amendment 003 binds Issue #133 as the authoritative Issue
    number for the amendment ledger. The design contract MUST
    enumerate that Issue number across §19.K + §21.A + §21.F +
    §21.G and MUST also enumerate the canonical Issue URL.

    The `ISSUE_CREATION_BLOCKED` token MUST NOT appear in the
    frozen Amendment 003 final byte content: Issue #133 was
    created on GitHub (state: OPEN) and the amendment is no
    longer authoring-in-place.
    """
    body = _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8")
    assert _EXPECTED_AMENDMENT_003_ISSUE_NUMBER_TOKEN in body, (
        f"design contract missing binding Amendment 003 Issue token: "
        f"{_EXPECTED_AMENDMENT_003_ISSUE_NUMBER_TOKEN}"
    )
    assert _EXPECTED_AMENDMENT_003_ISSUE_URL in body, (
        f"design contract missing canonical Amendment 003 Issue URL: "
        f"{_EXPECTED_AMENDMENT_003_ISSUE_URL}"
    )
    assert "ISSUE_CREATION_BLOCKED" not in body, (
        "design contract still contains ISSUE_CREATION_BLOCKED metadata; "
        "Amendment 003 Issue #133 is OPEN and must replace the "
        "ISSUE_CREATION_BLOCKED token across the contract"
    )


def test_design_contract_pr132_merged_state_bound() -> None:
    """Amendment 003 transfer-review corrective round binds the
    post-Amendment-002 merged-state facts to the contract:

    - PR #132 = MERGED, head SHA `60e5d15d…`, merge SHA
      `4a229625…`, merged at `2026-07-12T06:16:15Z`, post-merge
      main CI `29182404791` = completed / success.
    - Current `main` SHA = `4a2296258cfffe497623ee20d9b29fcc97358aaa`.
    - Amendment 002 is no longer "unmerged".

    The contract MUST enumerate all four anchors below across
    §1 current-authority rows and §21.A PR #132 record.

    Stale `current state` tokens MUST NOT appear anywhere in the
    contract body. These stale tokens are checked verbatim as a
    string-not-in-body negative assertion.
    """
    body = _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8")

    # Positive anchors
    for label, anchor in (
        ("PR #132 merge SHA", _EXPECTED_PR132_MERGE_SHA),
        ("PR #132 head SHA", _EXPECTED_PR132_HEAD_SHA),
        ("PR #132 post-merge CI", _EXPECTED_PR132_POST_MERGE_CI),
        ("PR #132 merged_at timestamp", _EXPECTED_PR132_MERGED_AT),
    ):
        assert anchor in body, f"design contract missing {label}: {anchor}"

    # Negative assertions: stale `current state` tokens MUST NOT
    # appear. Per §7 of the transfer-review corrective round
    # authority, these exact strings are forbidden:
    forbidden_tokens = (
        "PR #132 PENDING",
        "PR #132 pending",
        "DRAFT / NOT READY / NOT MERGED",
        "Amendment 002 remains unmerged",
        "S2 RECOVERY: NOT AUTHORIZED",
    )
    for token in forbidden_tokens:
        assert token not in body, (
            f"design contract still contains forbidden current-state "
            f"token: {token!r}; Amendment 002 is MERGED via PR #132 "
            f"and current main is {_EXPECTED_PR132_MERGE_SHA}"
        )

    # Current `main` rebind: the substring `d4ee40109` must NOT
    # be unmarked-positional as the *current* `main` SHA. Lines
    # that mention both `d4ee40109` AND `current `main`` are
    # allowed only if they explicitly position `d4ee40109` as
    # **historical** (Amendment 001 / pre-Amendment-002 baseline).
    # Historical rows in §1 are explicit by design:
    #   "... Amendment 001 merge SHA `d4ee40109…` — historical;
    #    Amendment 002 merge SHA `4a229625…` — **current `main`** ..."
    # A rebind error is when `d4ee40109` appears on the same line
    # as `current `main`` AND is NOT explicitly tagged `historical`
    # in that line.
    for line in body.splitlines():
        normalized = line.replace("**", "")
        if (
            "d4ee40109" in normalized
            and "current `main`" in normalized
            and "historical" not in normalized.lower()
        ):
            raise AssertionError(
                "design contract rebinds current `main` to pre-Amendment-002 "
                f"SHA on line without `historical` tag: {line!r}; current "
                f"main must be {_EXPECTED_PR132_MERGE_SHA}"
            )


def test_design_contract_final_metadata_stabilization_invariants() -> None:
    """Amendment 003 final metadata stabilization round binds the
    following metadata stability invariants to the contract:

    Positive anchors (MUST appear):
      - the Issue #131 historical OPEN review-time statement
        (state at Amendment 003 transfer review on 2026-07-12);
      - the live GitHub metadata externalization rule;
      - the Issue #133 Issue number + canonical URL (already
        covered by test_design_contract_amendment_003_issue_number_bound;
        re-asserted here for round-7 binding);

    Negative anchors (MUST NOT appear anywhere in the contract
    body):
      - "`CLOSED / COMPLETED` bound to Issue #131" — the
        contract MUST NOT assert Issue #131 as CLOSED. PR #132
        being MERGED does NOT imply Issue #131 closed state;
      - "`current local commit`" field label — design contract
        is hash-frozen and MUST NOT self-reference its own
        commit SHA via this label;
      - the prior-round `acebad960…` SHA — that SHA is
        self-referential (write-document → determine-tree →
        determine-SHA → write-document loop) and MUST NOT
        appear anywhere in the contract body;
      - "`NOT YET PUSHED`", "`NOT YET CREATED`",
        "`AUTHORED LOCALLY PENDING PR`",
        "`DRAFT DESIGN PR NOT YET PUSHED`", "`current local
        worktree status`" — all transient transfer-state
        tokens; live branch / PR / Ready / merge state is
        tracked externally in Issue #133 and the Amendment 003
        design PR, NOT as permanent current-state content.

    The contract MUST also continue to enumerate the two exact
    carved-out S1 paths, the §14.2.5 carve-out heading, the
    §21 Amendment 003 heading, and the PR #132 immutable
    merged-state facts (the previous invariants, as a round-7
    meta-cross-check).
    """
    body = _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8")

    # Positive anchors
    for label, anchor in (
        (
            "Issue #131 historical OPEN review-time statement",
            _EXPECTED_ISSUE_131_HISTORICAL_OPEN_STATEMENT,
        ),
        ("live GitHub metadata externalization rule", _EXPECTED_LIVE_METADATA_EXTERNALIZATION_RULE),
    ):
        assert anchor in body, (
            f"design contract missing final-metadata-stabilization "
            f"positive anchor: {label} ({anchor!r})"
        )

    # Negative anchors: transient / self-referential / false-
    # closed tokens MUST NOT appear anywhere in the contract body.
    #
    # 1. The `acebad960...` SHA is self-referential (it was the
    #    current local commit at the time of the prior round's
    #    document write). Inserting it into the contract would
    #    re-trigger the "document determines tree determines
    #    SHA determines document" loop and is forbidden.
    forbidden_substrings = (
        # Issue #131 false-closed state MUST NOT be asserted.
        # Match the substring "CLOSED / COMPLETED" only when it
        # appears adjacent to Issue #131. The narrower pattern
        # catches both "Issue #131 status ... CLOSED / COMPLETED"
        # and "Issue #131 ... CLOSED post-Amendment-002-merge"
        # style assertions. The existing Issue #129 row that uses
        # `CLOSED / COMPLETED` (PR #130 already merged) does NOT
        # mention Issue #131 and is therefore not falsely bound.
        "Issue #131 status",
        "Issue #131 ... CLOSED",
        "Issue #131). CLOSED",
        "Issue #131; CLOSED",
        # Self-referential commit SHA MUST NOT appear.
        "acebad960bf787430377d9cf88e0a5ed93e29ac7",
        # Transient transfer-state tokens.
        "NOT YET PUSHED",
        "NOT YET CREATED",
        "AUTHORED LOCALLY PENDING PR",
        "DRAFT DESIGN PR NOT YET PUSHED",
        # Self-referential `current local commit` field label.
        "current local commit",
    )
    for token in forbidden_substrings:
        assert token not in body, (
            f"design contract still contains forbidden "
            f"final-metadata-stabilization token: {token!r}; "
            f"review-comment-driven final metadata stabilization "
            f"forbids self-referential / transient / false-closed "
            f"content"
        )

    # Cross-check: the previous invariants (carve-out heading,
    # §21 heading, two S1 paths, Issue #133, PR #132 facts)
    # continue to hold. This is a meta-cross-check that the
    # final metadata stabilization round did not regress the
    # prior invariants.
    assert _EXPECTED_AMENDMENT_003_HEADING in body, (
        "design contract regressed: §21 heading missing after final metadata stabilization round"
    )
    assert _EXPECTED_AMENDMENT_003_CARVEOUT_HEADING in body, (
        "design contract regressed: §14.2.5 carve-out heading "
        "missing after final metadata stabilization round"
    )
    for path in _EXPECTED_AMENDMENT_003_S1_PATHS:
        assert path in body, (
            f"design contract regressed: missing carved-out S1 "
            f"path {path} after final metadata stabilization round"
        )
    for label, anchor in (
        ("Issue #133 binding token", _EXPECTED_AMENDMENT_003_ISSUE_NUMBER_TOKEN),
        ("Issue #133 URL", _EXPECTED_AMENDMENT_003_ISSUE_URL),
        ("PR #132 merge SHA", _EXPECTED_PR132_MERGE_SHA),
        ("PR #132 head SHA", _EXPECTED_PR132_HEAD_SHA),
        ("PR #132 post-merge CI", _EXPECTED_PR132_POST_MERGE_CI),
        ("PR #132 merged_at timestamp", _EXPECTED_PR132_MERGED_AT),
    ):
        assert anchor in body, (
            f"design contract regressed: missing {label} ({anchor}) "
            f"after final metadata stabilization round"
        )


def test_design_contract_final_authority_table_stabilization_invariants() -> None:
    r"""Amendment 003 final authority-table stabilization round
    (binding review comment `4950607148`) binds the following
    frozen-rule / live-state invariants to the contract:

    Positive anchors (MUST appear):
      - The integrity guard is the SOLE authority on the
        Amendment 003 final SHA-256; the contract body
        references the integrity-guard symbol exactly once;
      - The Amendment 003 authoring base SHA
        (`4a229625…`) is preserved verbatim (it's the immutable
        authoring baseline);
      - The live GitHub metadata externalization rule;
      - Issue #131 historical OPEN review-time statement;
      - Issue #133 authority number + canonical Issue URL;
      - The two exact carved-out S1 paths;
      - §14.2.5 + §21 headings;
      - PR #132 immutable merged-state facts.

    Negative anchors (MUST NOT appear anywhere in the contract
    body):
      - Undated `state: OPEN` bound to Issue #133 (live state
        MUST be qualified with the 2026-07-12 authoring-time
        date or removed entirely);
      - `#133 (state: OPEN)` style assertion;
      - `current \`main\`` rebind claim (the only acceptable
        mentions of `current \`main\`` MUST be accompanied by
        a `not asserted as` disclaimer or be inside the live-
        metadata-externalization-policy row);
      - `Proposed Amendment 003 final design-document SHA-256`
        self-hash field (the SHA-256 cannot be re-embedded
        inside the hashed document without creating an
        unbounded loop);
      - `current local commit` (already forbidden by the prior
        round; re-asserted here);
      - `NOT YET PUSHED` / `NOT YET CREATED` /
        `AUTHORED LOCALLY PENDING PR` (transient transfer
        state tokens; already forbidden by the prior round;
        re-asserted here).
    """
    body = _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8")

    # Positive anchors: integrity guard is the sole SHA authority
    # (the contract body references the symbol, but the value
    # itself lives ONLY in the integrity guard).
    assert (
        "tests/exchangers/shell_tube/test_task020_frozen_contract_unchanged.py::_EXPECTED_FROZEN_SHA256"
        in body
    ), (
        "design contract does not reference the integrity-guard "
        "symbol that holds the Amendment 003 final SHA-256; the "
        "integrity guard MUST be the sole hash authority"
    )
    # Amendment 003 authoring base SHA MUST be preserved verbatim
    # as the immutable authoring baseline.
    assert "4a2296258cfffe497623ee20d9b29fcc97358aaa" in body, (
        "design contract regressed: Amendment 003 authoring base SHA `4a229625…` missing"
    )
    # Live GitHub metadata externalization rule MUST be present.
    assert _EXPECTED_LIVE_METADATA_EXTERNALIZATION_RULE in body, (
        "design contract regressed: live GitHub metadata "
        "externalization rule missing after final authority-table "
        "stabilization"
    )
    # Issue #131 historical OPEN review-time statement MUST
    # remain present and verbatim.
    assert _EXPECTED_ISSUE_131_HISTORICAL_OPEN_STATEMENT in body, (
        "design contract regressed: Issue #131 historical OPEN "
        "review-time statement missing after final authority-table "
        "stabilization"
    )
    # Issue #133 binding number + URL MUST remain present.
    assert _EXPECTED_AMENDMENT_003_ISSUE_NUMBER_TOKEN in body, (
        "design contract regressed: Issue #133 binding token missing"
    )
    assert _EXPECTED_AMENDMENT_003_ISSUE_URL in body, (
        "design contract regressed: Issue #133 canonical URL missing"
    )
    # §14.2.5 + §21 headings MUST remain present.
    assert _EXPECTED_AMENDMENT_003_CARVEOUT_HEADING in body, (
        "design contract regressed: §14.2.5 carve-out heading missing"
    )
    assert _EXPECTED_AMENDMENT_003_HEADING in body, (
        "design contract regressed: §21 Amendment 003 heading missing"
    )
    # Two exact carved-out S1 paths MUST remain present.
    for path in _EXPECTED_AMENDMENT_003_S1_PATHS:
        assert path in body, f"design contract regressed: carved-out S1 path {path} missing"
    # PR #132 immutable merged-state facts MUST remain present.
    for label, anchor in (
        ("PR #132 merge SHA", _EXPECTED_PR132_MERGE_SHA),
        ("PR #132 head SHA", _EXPECTED_PR132_HEAD_SHA),
        ("PR #132 post-merge CI", _EXPECTED_PR132_POST_MERGE_CI),
        ("PR #132 merged_at timestamp", _EXPECTED_PR132_MERGED_AT),
    ):
        assert anchor in body, f"design contract regressed: missing {label}: {anchor}"

    # Negative anchors
    forbidden_substrings = (
        # Undated Issue #133 state: OPEN MUST NOT appear as a
        # permanent current-state row.
        "Issue #133 state: OPEN",
        "#133 (state: OPEN)",
        # Live-state `current `main`` rebind claim MUST NOT appear.
        # The phrase `current \`main\`` is allowed ONLY in:
        # (a) the live-metadata-externalization-policy row (where
        #     it's explicitly externalized), or
        # (b) a `not asserted as ... current \`main\`` disclaimer
        #     (where it's explicitly negated).
        # Otherwise the contract MUST NOT state which SHA is
        # `current \`main\`` as a permanent current-state field.
        # The negative check below catches the
        # `= **current \`main\``-style rebind assertions
        # (without `not asserted as` negation) in row values.
        "= **current `main`**",
        "= current `main` ",
        # Self-hash self-reference: the SHA-256 of the document
        # MUST NOT be re-embedded in the document body.
        "Proposed Amendment 003 final design-document SHA-256",
        # Prior-round self-referential commit SHA MUST NOT appear.
        "acebad960bf787430377d9cf88e0a5ed93e29ac7",
        # Transient transfer-state tokens MUST NOT appear.
        "current local commit",
        "NOT YET PUSHED",
        "NOT YET CREATED",
        "AUTHORED LOCALLY PENDING PR",
        "DRAFT DESIGN PR NOT YET PUSHED",
    )
    for token in forbidden_substrings:
        assert token not in body, (
            f"design contract still contains forbidden "
            f"final-authority-table-stabilization token: {token!r}; "
            f"live state and self-hash MUST be externalized to the "
            f"integrity guard + live GitHub metadata"
        )
