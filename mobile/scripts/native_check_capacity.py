#!/usr/bin/env python3
"""Read-only assessment of an explicitly declared remaining native-check budget.

This helper neither runs nor authorizes a compiler. It writes no receipts, caches
or temporary files. Its cap must match the owner's current ceiling. Source,
residency, process and toolchain checks and the running capacity guard remain
separate requirements. The existing runner does not invoke this helper yet.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess


COMPONENTS = (
    "module_cache_growth",
    "compiler_temporary_peak",
    "link_and_new_binary_peak",
    "remaining_app_typechecks_peak",
    "logs_receipts_preservation_growth",
)


def nonnegative_bytes(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer byte count")
    return value


def assess(*, owned_bytes, cap_bytes, free_bytes, reserve_bytes, components):
    """Conservatively sum declared peaks; never substitute unused cap for need."""
    values = {
        name: nonnegative_bytes(value, name)
        for name, value in {
            "owned_bytes": owned_bytes,
            "cap_bytes": cap_bytes,
            "free_bytes": free_bytes,
            "reserve_bytes": reserve_bytes,
        }.items()
    }
    if values["cap_bytes"] == 0:
        raise ValueError("cap_bytes must be positive")
    if set(components) != set(COMPONENTS):
        raise ValueError("Declare every remaining-budget component explicitly")
    budget = {name: nonnegative_bytes(components[name], name) for name in COMPONENTS}
    growth = sum(budget.values())
    if growth == 0:
        raise ValueError("A remaining compile/check plan cannot have an empty budget")
    projected_owned = owned_bytes + growth
    required_free = reserve_bytes + growth
    cap_ok = projected_owned <= cap_bytes
    reserve_ok = free_bytes >= required_free
    return {
        **values,
        "declared_remaining_components_bytes": budget,
        "declared_remaining_growth_peak_bytes": growth,
        "projected_owned_peak_bytes": projected_owned,
        "required_free_with_protected_reserve_bytes": required_free,
        "unused_cap_before_work_bytes": max(0, cap_bytes - owned_bytes),
        "already_over_cap_bytes": max(0, owned_bytes - cap_bytes),
        "cap_ok": cap_ok,
        "reserve_ok": reserve_ok,
        "within_declared_budget": cap_ok and reserve_ok,
        "scope": "Declared-budget arithmetic only; not native execution or acceptance",
        "estimate_is_not_a_measured_maximum": True,
    }


def allocated_bytes(root):
    output = subprocess.check_output(
        ["/usr/bin/du", "-sk", str(root)], text=True, timeout=15
    )
    return int(output.split()[0]) * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--canonical-cache-root", type=Path, required=True)
    parser.add_argument("--cap-bytes", type=int, required=True)
    parser.add_argument("--reserve-bytes", type=int, required=True)
    for name in COMPONENTS:
        parser.add_argument("--" + name.replace("_", "-") + "-bytes", type=int, required=True)
    args = parser.parse_args()
    try:
        packet = args.packet_root.resolve(strict=True)
        cache = args.canonical_cache_root.resolve(strict=True)
        if not packet.is_dir() or not cache.is_dir():
            raise ValueError("Both owned roots must be directories")
        if packet == cache or packet in cache.parents or cache in packet.parents:
            raise ValueError("Owned roots must be distinct and disjoint")
        if packet.stat().st_dev != cache.stat().st_dev:
            raise ValueError("Separate-volume free-space budgets are not supported")
        disk = os.statvfs(packet)
        result = assess(
            owned_bytes=allocated_bytes(packet) + allocated_bytes(cache),
            cap_bytes=args.cap_bytes,
            free_bytes=disk.f_bavail * disk.f_frsize,
            reserve_bytes=args.reserve_bytes,
            components={name: getattr(args, name + "_bytes") for name in COMPONENTS},
        )
        result["owned_roots"] = [str(packet), str(cache)]
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    return 0 if result["within_declared_budget"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
