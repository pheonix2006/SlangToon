"""Theme pack definitions for full-pipeline art style diversification."""

import random
from typing import TypedDict


class ThemePack(TypedDict):
    id: str
    name_zh: str
    name_en: str
    world_setting: str
    visual_style: str


THEME_PACKS: list[ThemePack] = [
    {
        "id": "monster_hunter",
        "name_zh": "怪物猎人",
        "name_en": "Monster Hunter",
        "world_setting": (
            "A primal wilderness world where hunters team up to battle colossal "
            "dragons and beasts using giant swords, traps, and crafted armor. "
            "The setting features vast ecosystems, ancient ruins, and epic monster encounters."
        ),
        "visual_style": (
            "Monster Hunter game aesthetic with epic scale, giant monsters looming over "
            "hunters, detailed primal armor and weapons, majestic natural landscapes with "
            "ancient ruins, dramatic lighting during monster encounters"
        ),
    },
    {
        "id": "cyberpunk",
        "name_zh": "赛博朋克",
        "name_en": "Cyberpunk",
        "world_setting": (
            "A 2087 neon-lit megacity where hackers and corporate oligarchs wage shadow wars "
            "in cyberspace. Underground resistance fighters navigate a world of AI, implants, "
            "and digital surveillance."
        ),
        "visual_style": (
            "Neon cyan and magenta lights cutting through rain-slicked streets, holographic "
            "advertisements floating above crowds, dark atmospheric shading with high contrast, "
            "futuristic urban decay"
        ),
    },
    {
        "id": "harry_potter",
        "name_zh": "哈利波特",
        "name_en": "Harry Potter",
        "world_setting": (
            "A hidden magical world existing alongside modern society. Hogwarts castle with its "
            "moving staircases and floating candles, Diagon Alley shops, Quidditch matches, "
            "and the eternal struggle between dark and light wizards."
        ),
        "visual_style": (
            "Harry Potter film aesthetic with dark gothic castle interiors lit by floating candles, "
            "warm wand glow illuminating faces, rich burgundy and gold tones, magical sparkles "
            "and spells rendered as light trails"
        ),
    },
    {
        "id": "pokemon",
        "name_zh": "宝可梦",
        "name_en": "Pokémon",
        "world_setting": (
            "A vibrant world where people live alongside magical creatures called Pokémon. "
            "Trainers journey through grassy routes, challenge gym leaders, and forge bonds "
            "with their creature partners through adventure."
        ),
        "visual_style": (
            "Pokémon anime style with bright cheerful colors, cute and expressive creature "
            "designs, lush green fields and colorful gyms, clean bold outlines with soft shading"
        ),
    },
    {
        "id": "doraemon",
        "name_zh": "哆啦A梦",
        "name_en": "Doraemon",
        "world_setting": (
            "Everyday Japanese school life where a blue robot cat from the 22nd century uses "
            "amazing futuristic gadgets from his 4D pocket to help a lazy schoolboy navigate "
            "homework, bullies, and childhood adventures."
        ),
        "visual_style": (
            "Classic Doraemon manga style with simple rounded linework, warm bright everyday "
            "colors, clean white backgrounds, expressive cartoon faces with dot eyes"
        ),
    },
    {
        "id": "nba",
        "name_zh": "NBA篮球",
        "name_en": "NBA Basketball",
        "world_setting": (
            "The world of professional basketball — packed arenas, clutch moments on the court, "
            "buzzer-beaters, locker room speeches, draft day drama, and the intensity of "
            "championship playoffs."
        ),
        "visual_style": (
            "Dynamic sports photography style with high-speed freeze-frame action, dramatic court "
            "lighting from above, sweat and muscle texture detail, motion blur on fast breaks"
        ),
    },
    {
        "id": "steampunk",
        "name_zh": "蒸汽朋克",
        "name_en": "Steampunk",
        "world_setting": (
            "An alternate Victorian era where steam-powered machinery drives everything from "
            "airships to automata. Inventors in workshops create marvelous clockwork devices "
            "while aristocrats scheme in gaslit parlors."
        ),
        "visual_style": (
            "Brass gears, copper pipes, and steam clouds in warm brown-copper tones, Victorian "
            "fashion with goggles and corsets, intricate mechanical details, sepia-tinted atmosphere"
        ),
    },
    {
        "id": "space_opera",
        "name_zh": "太空歌剧",
        "name_en": "Space Opera",
        "world_setting": (
            "An interstellar civilization where massive fleets traverse the galaxy through "
            "wormholes. Different alien species navigate diplomacy, trade, and war among "
            "sparkling nebulae and ancient space stations."
        ),
        "visual_style": (
            "Deep space blue-purple nebulae as backdrop, sleek silver space stations with glowing "
            "engines, grand fleet formations, alien architecture with bioluminescent elements"
        ),
    },
    {
        "id": "film_noir",
        "name_zh": "侦探黑色电影",
        "name_en": "Film Noir",
        "world_setting": (
            "A 1940s rain-soaked American city where a world-weary private detective tracks a "
            "mysterious case through smoky bars, dim offices, and dangerous alleys. Everyone "
            "has secrets and nothing is what it seems."
        ),
        "visual_style": (
            "Black-and-white high contrast with dramatic venetian blind shadows, cigarette smoke "
            "curling through light beams, rain-streaked windows, deep shadows, vintage suits "
            "and fedora hats"
        ),
    },
    {
        "id": "pixel_art",
        "name_zh": "像素游戏",
        "name_en": "Pixel Art",
        "world_setting": (
            "A retro video game world where a pixel hero fights monsters, talks to NPCs, "
            "discovers hidden levels, and faces epic boss battles. The world operates on "
            "game logic with health bars, inventory, and experience points."
        ),
        "visual_style": (
            "16-bit pixel art style with bold saturated color blocks, pixelated dialogue boxes "
            "with retro fonts, visible pixel grid, classic RPG UI elements like health bars "
            "and inventory screens"
        ),
    },
    {
        "id": "chinese_ink",
        "name_zh": "中国水墨",
        "name_en": "Chinese Ink Wash",
        "world_setting": (
            "Ancient China's martial arts world — wandering swordsmen in bamboo forests, "
            "scholars debating in misty mountain pavilions, imperial court intrigue, and "
            "tea house gatherings along the Yangtze River."
        ),
        "visual_style": (
            "Traditional Chinese ink wash painting with expressive brush strokes, generous white "
            "space (liubai), ink gradient from deep black to pale gray, rice paper texture, "
            "subtle red seal stamps"
        ),
    },
    {
        "id": "ukiyo_e",
        "name_zh": "浮世绘",
        "name_en": "Ukiyo-e",
        "world_setting": (
            "Edo period Japan with its strict social hierarchy — samurai bound by bushido code, "
            "geishas in pleasure quarters, tea ceremonies, and ronin wandering the Tokaido road."
        ),
        "visual_style": (
            "Ukiyo-e woodblock print style with bold flat color areas, distinctive wave patterns, "
            "intricate kimono fabric designs, strong outlines, Mt. Fuji in backgrounds"
        ),
    },
    {
        "id": "ghibli",
        "name_zh": "吉卜力",
        "name_en": "Studio Ghibli",
        "world_setting": (
            "A gentle world where nature spirits coexist with humans, young protagonists embark "
            "on magical coming-of-age adventures, and every forest, castle, and sky holds wonder. "
            "Animism and environmental harmony are central themes."
        ),
        "visual_style": (
            "Studio Ghibli's signature hand-painted watercolor backgrounds with soft golden light, "
            "lush green countryside, towering cloud-filled skies, gentle wind flowing through grass"
        ),
    },
    {
        "id": "ancient_egypt",
        "name_zh": "古埃及",
        "name_en": "Ancient Egypt",
        "world_setting": (
            "Ancient Egypt along the Nile — pharaoh's court filled with intrigue, massive pyramid "
            "construction, priests performing rituals in towering temples, and scribes recording "
            "the affairs of a mighty civilization."
        ),
        "visual_style": (
            "Egyptian mural and hieroglyphic art style with gold and sandy tones, symmetrical "
            "compositions, stylized human figures in profile, hieroglyphic borders and decorations"
        ),
    },
    {
        "id": "vaporwave",
        "name_zh": "蒸汽波",
        "name_en": "Vaporwave",
        "world_setting": (
            "A surreal digital dreamscape where 90s consumer culture, ancient Greek aesthetics, "
            "and retro technology collide in a pastel-hazed liminal space. Shopping malls extend "
            "infinitely and Windows 95 dialogues float in the sky."
        ),
        "visual_style": (
            "Pink and purple gradient skies, classical Greek statues with pixelated glitches, "
            "palm trees against grid floors, retro computer UI elements, VHS scan lines, "
            "neon-cool color palette"
        ),
    },
    {
        "id": "street_graffiti",
        "name_zh": "街头涂鸦",
        "name_en": "Street Graffiti",
        "world_setting": (
            "Urban underground culture — graffiti artists tagging walls at midnight, rap battles "
            "in parking lots, skateboarders grinding rails, and a community bound by street cred "
            "and creative rebellion."
        ),
        "visual_style": (
            "Spray paint graffiti style with bold fluorescent colors dripping and blending on "
            "brick walls, stencil-cut edges, paint splatter effects, chainlink fences and "
            "concrete urban textures"
        ),
    },
    {
        "id": "medieval",
        "name_zh": "中世纪骑士",
        "name_en": "Medieval Knights",
        "world_setting": (
            "Medieval Europe with its feudal kingdoms — knights sworn to chivalric codes, "
            "castle sieges with trebuchets, grand feasts in torchlit halls, and courtly romance "
            "amid political betrayal."
        ),
        "visual_style": (
            "Medieval illuminated manuscript style with ornate gold leaf borders, chainmail and "
            "heraldic armor detail, castle battlements, parchment texture background, rich "
            "crimson and royal blue colors"
        ),
    },
    {
        "id": "post_apocalyptic",
        "name_zh": "末日废土",
        "name_en": "Post-Apocalyptic",
        "world_setting": (
            "Civilization has collapsed. Survivors scavenge through the ruins of once-great cities, "
            "building makeshift communities from scrap. Rusted cars line abandoned highways and "
            "nature reclaims concrete."
        ),
        "visual_style": (
            "Dusty yellow-brown wasteland tones, rusted metal and crumbling concrete, makeshift "
            "armor from scrap parts, gas masks and goggles, barren desert stretching to the horizon"
        ),
    },
]


def get_random_theme() -> ThemePack:
    """Return a randomly selected theme pack."""
    return random.choice(THEME_PACKS)


def get_theme_by_id(theme_id: str) -> ThemePack | None:
    """Look up a theme pack by its id. Returns None if not found."""
    for theme in THEME_PACKS:
        if theme["id"] == theme_id:
            return theme
    return None
