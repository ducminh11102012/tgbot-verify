"""Unified SheerID verifier CLI (no Telegram dependency)."""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Type

from one.sheerid_verifier import SheerIDVerifier as OneVerifier
from k12.sheerid_verifier import SheerIDVerifier as K12Verifier
from spotify.sheerid_verifier import SheerIDVerifier as SpotifyVerifier
from Boltnew.sheerid_verifier import SheerIDVerifier as BoltVerifier
from youtube.sheerid_verifier import SheerIDVerifier as YoutubeVerifier

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerifyTarget:
    """Definition for a single verification target."""

    name: str
    verifier: Type


TARGETS: Dict[str, VerifyTarget] = {
    "one": VerifyTarget(name="Gemini One Pro", verifier=OneVerifier),
    "k12": VerifyTarget(name="ChatGPT Teacher K12", verifier=K12Verifier),
    "spotify": VerifyTarget(name="Spotify Student", verifier=SpotifyVerifier),
    "bolt": VerifyTarget(name="Bolt.new Teacher", verifier=BoltVerifier),
    "youtube": VerifyTarget(name="YouTube Premium Student", verifier=YoutubeVerifier),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sheerid-cli",
        description="Run SheerID verification directly from terminal/exe.",
    )
    parser.add_argument(
        "target",
        choices=TARGETS.keys(),
        help="Verification target to run.",
    )
    parser.add_argument("url", help="Full SheerID URL containing verificationId")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    return parser.parse_args()


def run_verification(target_key: str, url: str) -> Dict:
    target = TARGETS[target_key]
    verification_id = target.verifier.parse_verification_id(url)
    if not verification_id:
        raise ValueError("Invalid URL: cannot parse verificationId")

    verifier = target.verifier(verification_id)
    result = verifier.verify()
    result["target"] = target.name
    result["verification_id"] = verification_id
    return result


def main() -> int:
    args = parse_args()
    try:
        result = run_verification(args.target, args.url)
    except Exception as exc:
        logger.exception("Verification failed before processing")
        print(f"❌ {exc}")
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"Target: {result['target']}")
        print(f"Verification ID: {result['verification_id']}")
        print(f"Status: {'✅ Success' if result.get('success') else '❌ Failed'}")
        print(f"Message: {result.get('message')}")
        if result.get("redirect_url"):
            print(f"Redirect URL: {result['redirect_url']}")
        print("=" * 60)

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
