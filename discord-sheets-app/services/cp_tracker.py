import difflib

FUZZY_THRESHOLD = 0.82


def load_cp_list(filepath: str) -> dict[str, str]:
    cp_map = {}
    current_cp = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("*"):
                member = line.lstrip("* ").strip()
                if current_cp and member:
                    cp_map[member.upper()] = current_cp
            else:
                current_cp = line
    return cp_map


def find_cp(member_name: str, cp_map: dict[str, str]) -> tuple:
    upper = member_name.upper()

    if upper in cp_map:
        return cp_map[upper], "exact"

    keys = list(cp_map.keys())
    matches = difflib.get_close_matches(upper, keys, n=1, cutoff=FUZZY_THRESHOLD)
    if matches:
        return cp_map[matches[0]], "fuzzy"

    return None, "not_found"


def process_members(members: list[str], cp_map: dict[str, str]) -> list[dict]:
    seen = set()
    results = []
    for member in members:
        key = member.upper()
        if key in seen:
            continue
        seen.add(key)
        cp, match_type = find_cp(member, cp_map)
        results.append({"member": member, "cp": cp or "", "match_type": match_type})
    return results


def load_cp_list_full(filepath: str) -> list[tuple[str, str]]:
    """Returns list of (original_name, cp_name) for all members."""
    result = []
    current_cp = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("*"):
                member = line.lstrip("* ").strip()
                if current_cp and member:
                    result.append((member, current_cp))
            else:
                current_cp = line
    return result


def list_all_cps(filepath: str) -> list[str]:
    cps = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("*"):
                cps.append(line)
    return cps


def add_member_to_cp_list(filepath: str, member_name: str, cp_name: str) -> bool:
    """Adds member under the given CP. Returns True if added, False if already exists."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Check if already exists (case-insensitive)
    existing = {l.strip().lstrip("* ").upper() for l in lines if l.strip().startswith("*")}
    if member_name.upper() in existing:
        return False

    # Find the CP section
    cp_line_idx = None
    for i, line in enumerate(lines):
        if line.strip() == cp_name:
            cp_line_idx = i
            break

    if cp_line_idx is None:
        # CP not found — append new section at end
        lines.append(f"\n{cp_name}\n\n* {member_name}\n")
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True

    # Find the last member line in this CP's section
    insert_after = cp_line_idx
    for i in range(cp_line_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("*"):
            break  # hit the next CP name
        if stripped.startswith("*"):
            insert_after = i

    lines.insert(insert_after + 1, f"* {member_name}\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True
