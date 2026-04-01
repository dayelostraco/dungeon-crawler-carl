import textwrap

BOX_WIDTH = 52
WRAP_WIDTH = 60


def _wrap(text: str, indent: str = "  ") -> str:
    """Wrap text at WRAP_WIDTH, preserving words, with indent."""
    lines = textwrap.wrap(text, width=WRAP_WIDTH)
    return ("\n" + indent).join(lines)


def print_achievement(achievement: dict) -> None:
    """
    Print a formatted achievement block to the terminal.
    achievement: dict with keys title, description, reward
    """
    title: str = achievement.get("title", "Unknown Achievement")
    description: str = achievement.get("description", "")
    reward: str = achievement.get("reward", "")

    top    = "╔" + "═" * (BOX_WIDTH - 2) + "╗"
    middle = "║  ACHIEVEMENT UNLOCKED" + " " * (BOX_WIDTH - 24) + "║"
    bottom = "╚" + "═" * (BOX_WIDTH - 2) + "╝"
    divider = "─" * BOX_WIDTH

    desc_wrapped = _wrap(description, indent="  ")
    reward_wrapped = _wrap(reward, indent="          ")

    print()
    print(top)
    print(middle)
    print(bottom)
    print()
    print(f"  ★  {title}")
    print()
    print(f"  {desc_wrapped}")
    print()
    print(f"  REWARD  {reward_wrapped}")
    print()
    print(divider)
    print()
