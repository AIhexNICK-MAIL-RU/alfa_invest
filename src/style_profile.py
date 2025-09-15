from dataclasses import dataclass
from typing import List


@dataclass
class StyleProfile:
    voice_instructions: str
    hashtags: List[str]

    @staticmethod
    def default() -> "StyleProfile":
        return StyleProfile(
            voice_instructions=(
                "Кратко, деловым тоном, простыми фразами. Без воды. "
                "Разбивай на короткие абзацы и маркированные списки при необходимости."
            ),
            hashtags=["#альфаиндекс", "#чтокупить"],
        )


