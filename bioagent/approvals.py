"""Human approval gates used by the workflow."""


def ask_for_approval(question: str, auto_approve: bool = False) -> bool:
    if auto_approve:
        print(f"{question} yes (--yes)")
        return True

    answer = input(f"{question} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}

