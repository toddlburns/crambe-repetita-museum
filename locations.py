#!/usr/bin/env python3
"""Consolidate `location` into a COUNTRY facet, split the detail into `city`, and backfill.

Todd, 2026-09-07: *"i'd like for you to consolidate location tags into things that make more
sense … in some cases, let's go with more detail. in some cases, let's get less granular! and
let's make sure that everything has a location tag that possibly can."*

The facet was 96 values at four different granularities at once — countries (United States 582),
bare cities (New York 63, Paris 3, Vienna 1), "City, State" (Chicago, Illinois 10), and bare US
states (Ohio 1). As one browsable list that is useless: nothing is comparable to anything.

So the split is exactly his two directions at once:

  **LESS granular** — `location` now always means the COUNTRY. One value per country, every item
  comparable to every other.
  **MORE granular** — a new `city` facet carries the detail that used to be crushed into the
  same list, and it gains the cities that were previously invisible because they sat inside a
  "City, State" string.

⚠️ THE STATE IS DROPPED FROM THE TAG AND THAT LOSES NOTHING. The 44 "Town, State" values are
almost all trademarks (67 items), and every one of those records carries the full address in its
verification text — "The Cooper Alloy Foundry Company, Hillside, New Jersey. 1950." The tag is a
facet, not the record.

## Backfill, in order of confidence — never a guess

1. An item's own existing location, mapped.
2. **Person propagation.** A designer/artist/illustrator/photographer who carries exactly ONE
   country across the items that do have one lends it to their items that do not. 559 of 587
   people are unambiguous that way. Anyone with two countries on record is skipped, not averaged.
3. **The record label's home.** For a sleeve, the design was commissioned where the label was.
   ⚠️ This is a PROXY, not a fact about the designer: a Japanese pressing of a Blue Note record
   is still a US design. The table below is only labels whose home is not in question.

Anything none of those reaches keeps no location. That is the point — an empty facet is honest,
a guessed one is not.

    python3 locations.py --report     # print what would change, write nothing
    python3 locations.py --apply
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "crvi_registry.json")

PEOPLE = ("designer", "artist", "illustrator", "photographer", "art director", "typographer")

# ---- every location value in use on 2026-09-07 -> (country, city or None) -------------------
# ⚠️ TWO OF THESE ARE CORRECTIONS, NOT NORMALISATIONS:
#   "Melbourne" was on Manet's *The Melon*. Melbourne is where the painting HANGS (the National
#   Gallery of Victoria), not where it was made. `location` means where the work comes from, so
#   it becomes France with no city. If any other record turns out to name its holding museum
#   this way, it is the same bug.
#   "Georgia" is the COUNTRY, not the US state — it is on two Kirill Zdanevich paintings.
MAP = {
    # already a country: pass through
    **{c: (c, None) for c in (
        "United States", "Germany", "France", "United Kingdom", "Japan", "Italy", "Russia",
        "Poland", "Ghana", "Belgium", "Chile", "Austria", "Mexico", "China", "Netherlands",
        "Switzerland", "Nigeria", "Denmark", "Spain", "Venezuela", "South Africa", "Iran",
        "India", "Norway", "Pakistan", "Serbia", "Colombia", "Argentina", "Brazil",
        "South Korea", "Lebanon", "Sweden", "Finland", "Dominican Republic", "Kenya",
        "Palestine", "Georgia")},
    # bare cities
    "New York": ("United States", "New York"),
    "Chicago": ("United States", "Chicago"),
    "Los Angeles": ("United States", "Los Angeles"),
    "Philadelphia": ("United States", "Philadelphia"),
    "Paris": ("France", "Paris"),
    "London": ("United Kingdom", "London"),
    "Vienna": ("Austria", "Vienna"),
    "Oslo": ("Norway", "Oslo"),
    "Montpellier": ("France", "Montpellier"),
    "Besançon": ("France", "Besançon"),
    "Tsukuba": ("Japan", "Tsukuba"),
    "Edge Moor": ("United States", "Edge Moor"),
    # bare US states — country only, no city to give
    "Ohio": ("United States", None),
    "Pennsylvania": ("United States", None),
    # corrections
    "Melbourne": ("France", None),
    # "City, Country"
    "Pavia, Italy": ("Italy", "Pavia"),
    "Puteaux, France": ("France", "Puteaux"),
    "Cappelle-au-Bois, Belgium": ("Belgium", "Cappelle-au-Bois"),
}

# ---- record labels whose home country is not in question ------------------------------------
LABEL_COUNTRY = {
    "United States": [
        "Blue Note", "Prestige", "Fania Records", "Atlantic", "Capitol", "Columbia", "New Jazz",
        "Impulse!", "Riverside", "Riverside Records", "Tamla", "Elektra", "Douglas", "Liberty",
        "United Artists", "Pacific Jazz", "MCA", "MCA Records", "King", "MGM Records",
        "Casablanca", "Ralph", "Ralph Records", "Stax", "Okeh", "RCA Victor", "RCA", "Tommy Boy",
        "Verve", "Verve Records", "EmArcy", "Alegre Records", "Tico Records", "Inca Records",
        "Vaya Records", "Candid", "Motown", "Soul", "HotWax", "Hot Wax", "Invictus", "Volt",
        "Epic", "Westbound", "Arista", "Enterprise", "Reprise", "Reprise Records", "Curtom",
        "Hi", "TK", "Spring", "Philadelphia International", "Solar", "Perspective",
        "Perspective Records", "Laface", "Skin Graft", "Windham Hill", "Holy Mountain",
        "Mahogani Music", "Planet E", "Jive", "Uptown", "Tuff City", "Wild Pitch", "ESP Disk",
        "Nonesuch", "Seeland", "Kranky", "Ghostly International", "Thrill Jockey", "Matador",
        "Hefty Records", "Composers Recordings Inc.", "Milestone", "Subharmonic", "Rykodisc",
        "Kudu", "Columbia Masterworks", "Jazz West", "Vee-Jay", "Dell", "Bethlehem",
        "Playboy Records", "Jazzland", "Contemporary", "Vanguard", "Red Star", "Sleeping Bag",
        "Craft Recordings", "Hospital Productions", "Sister Polygon Records", "Paw Tracks",
        "Asthmatic Kitty", "Beer On The Rug", "Rvng Intl.", "Mulatta", "Plus 8 Records",
        "Bathing Records, Inc.", "Fresh", "Sub Rosa",
    ],
    "United Kingdom": [
        "Warp Records", "Warp", "Virgin", "Honest Jon's Records", "Honest Jon's", "Planet Mu",
        "Tru Thoughts", "Go! Beat", "Esquire", "Island Records", "Ninja Tune", "Mute",
        "Rough Trade", "Hyperdub", "Rephlex", "Young Turks", "Creation", "Jeepster Records",
        "Stiff Records", "Parlophone", "Harvest", "Charisma", "Decca", "Real World", "Tempa",
        "Werk Discs", "Junior Boy's Own", "Hard Hands", "Pork Recordings", "Far Out Recordings",
        "One-Handed Music", "Freestyle", "Soundway", "Type", "DDS", "Subtext",
        "Public Information", "Trunk", "Hot Air", "Ricky-Tick", "F-Beat", "Reaction",
        "No Pain In Pop", "Fetish Records", "Coloursound Library",
        "History Always Favours The Winners", "Streetwave Music", "Filter",
        "Applied Rhythmic Technology", "Jack Trax", "Slip-N-Slide", "Egg", "Amaryllis",
    ],
    "Germany": [
        "Deutsche Grammophon", "ECM Records", "Kompakt", "Mille Plateaux", "Sky Records",
        "Brain", "Ata Tak", "ZickZack", "Fünfundvierzig", "Kosmische Musik", "Klang Elektronik",
        "Playhouse", "Faitiche", "Macro", "Selected Sound", "Studio IK7", "MPS", "Software",
        "Pan",
    ],
    "Netherlands": ["Philips", "Polydor", "Phonogram", "Slowscan"],
    "Japan": ["Alfa", "Yen", "Trattoria", "Victor", "ポリドール", "Noble", "Yaki Record"],
    "Austria": ["G-Stone Recordings", "G-Stone", "Cheap"],
    "Italy": ["Vedette Records", "Cramps", "Right Tempo", "Cenacolo", "nova musicha - n."],
    "France": ["Pôle Records", "Yellow Productions", "Shelter Press", "Épie", "Flower"],
    "Spain": ["Grabaciones Accidentales", "Elefant Records"],
    "Norway": ["Smalltown Supersound", "Uniton"],
    "New Zealand": ["Flying Nun Records"],
    "Australia": ["Efficient Space", "Modular Recordings"],
    "Cuba": ["Areito"],
    "Turkey": ["Goksoy Plakçlik"],
    "Canada": ["Absurd Recordings"],
    "Denmark": ["AMDISCS"],
}
LABEL = {lab: country for country, labs in LABEL_COUNTRY.items() for lab in labs}

# ---- makers whose country is not in question ------------------------------------------------
# ⚠️ THIS IS THE MAKER'S COUNTRY, which is how the facet has always been used here — Klutsis is
# tagged Russia even for a sheet held in Washington, Awazu Japan for a poster printed for UCLA.
# It is deliberately SHORT. Anyone genuinely transnational is left out rather than pinned:
# Mati Klarwein (49 items) was born in Hamburg, raised in Israel and worked in Paris, New York
# and Deià; Kim Laughton (27) is British and based in Shanghai; Barry Blitt is Canadian and
# works for a New York magazine. Guessing one country for those would be inventing a fact.
MAKER_COUNTRY = {
    "Robert Beatty": "United States",
    "Barney Bubbles": "United Kingdom",
    "Andrew Kuo": "United States",
    "Yayoi Kusama": "Japan",
    "Seymour Chwast": "United States",
    "Milton Glaser": "United States",
    "Saul Bass": "United States",
    "Paul Rand": "United States",
    "Ed Ruscha": "United States",
    "Cindy Sherman": "United States",
    "Carrie Mae Weems": "United States",
    "Man Ray": "United States",
    "Bruce Nauman": "United States",
    "Peter Max": "United States",
    "Eric Yahnker": "United States",
    "Tauba Auerbach": "United States",
    "Amy Sherald": "United States",
    "John Currin": "United States",
    "Alan Aldridge": "United Kingdom",
    "The Designers Republic": "United Kingdom",
    "Non-Format": "Norway",
    "Zeke Clough": "United Kingdom",
    "Kiyoshi Awazu": "Japan",
    "Koichi Sato": "Japan",
    "Takenobu Igarashi": "Japan",
    "Tetsuya Ishida": "Japan",
    "Yasumasa Morimura": "Japan",
    "Gustav Klutsis": "Russia",
    "Filippo Tommaso Marinetti": "Italy",
    "Roberto Matta": "Chile",
    "Emil Nolde": "Germany",
    "Dick Higgins": "United States",
    "László Moholy-Nagy": "Hungary",
    "Anni Albers": "Germany",
    "Josef Albers": "Germany",
    "Alphonse Mucha": "Czechia",
    "Neo Rauch": "Germany",
    "Frank Auerbach": "United Kingdom",
    "Paul McCarthy": "United States",
    "René Magritte": "Belgium",
    "Robert Delaunay": "France",
    "Sonia Delaunay": "France",
    "Ruth Asawa": "United States",
    "On Kawara": "Japan",
    "Reid Miles": "United States",
    "Izzy Sanabria": "United States",
    "Ingo Swann": "United States",
    "Peter Lloyd": "United Kingdom",
    "Lynn Goldsmith": "United States",
    "Maurizio Cattelan": "Italy",
    "Herbert Bayer": "Austria",
    # Todd, 2026-09-07: "Jan Sawka should be polish". He left Poland for the United States in
    # 1977, which is why he was held back on the first pass; his country here is Poland.
    "Jan Sawka": "Poland",
}

# ⚠️ EVERY trademark in this archive comes from one of three AMERICAN compendia — "Trademarks of
# the 20s and 30s", "Trademarks of the 40s and 50s" and "American Trademarks: A Compendium".
# The 69 that carry a location are all US towns. So a trademark whose verification cites one of
# those books is a US mark, even when its owner's town was never recovered from the caption.
TRADEMARK_BOOKS = ("Trademarks of the", "American Trademarks")

US_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming", "District of Columbia",
}


def resolve(value):
    """(country, city) for a location value, or None.

    ⚠️ THE 44 "Town, State" VALUES ARE MOSTLY TRADEMARKS and they must not fall through — an
    earlier pass mapped only the explicit table and silently DROPPED the location from 66 items
    that already had one. Anything of the form "<place>, <US state>" is the United States, and
    "<place>, <country>" is that country; the head becomes the city either way.
    ⚠️ "Georgia" is checked as a whole value FIRST, because it is a country here (two Kirill
    Zdanevich paintings) as well as a US state name in the tail position.
    """
    if value in MAP:
        return MAP[value]
    if ", " in value:
        head, _, tail = value.rpartition(", ")
        if tail in US_STATES:
            return ("United States", head)
        if tail in MAP and MAP[tail][1] is None:
            return (MAP[tail][0], head)
    return None


def tags_of(v):
    return (v.get("tags") or []) + (v.get("extra_tags") or [])


def main():
    apply = "--apply" in sys.argv
    reg = json.load(open(REG))
    live = [v for v in reg["items"].values() if not v.get("deleted")]

    # pass 1 — map what exists, and learn each person's country
    resolved = {}          # id -> (country, city, why)
    unmapped = []          # ⚠️ anything the table cannot resolve is REPORTED, never dropped

    # ⚠️ RE-RUNNING THIS SCRIPT MUST NOT DESTROY WHAT IT BUILT. After the first --apply a value
    # like "Chicago, Illinois" no longer exists: the item carries location=United States and
    # city=Chicago. A second run reading only `location` resolves city=None for every item, and
    # the write at the end would then drop EVERY city tag in the archive. So an existing `city`
    # tag is read here and carried through, which makes the script idempotent.
    existing_city = {}
    for v in live:
        for t in tags_of(v):
            if t["k"] == "city":
                existing_city[v["id"]] = t["v"]
                break

    for v in live:
        for t in tags_of(v):
            if t["k"] == "location":
                got = resolve(t["v"])
                if got:
                    city = got[1] or existing_city.get(v["id"])
                    resolved[v["id"]] = (got[0], city, "mapped from %r" % t["v"])
                else:
                    unmapped.append((v["id"], t["v"]))
                break
    person = collections.defaultdict(set)
    for v in live:
        got = resolved.get(v["id"])
        if not got:
            continue
        for t in tags_of(v):
            if t["k"] in PEOPLE:
                person[t["v"]].add(got[0])
    single = {p: list(cs)[0] for p, cs in person.items() if len(cs) == 1}

    # pass 2 — backfill
    fills = collections.Counter()
    for v in live:
        if v["id"] in resolved:
            continue
        ts = tags_of(v)
        who = next((t["v"] for t in ts if t["k"] in PEOPLE and t["v"] in single), None)
        if who:
            resolved[v["id"]] = (single[who], None, "from %s" % who)
            fills["person"] += 1
            continue
        lab = next((t["v"] for t in ts if t["k"] == "label" and t["v"] in LABEL), None)
        if lab:
            resolved[v["id"]] = (LABEL[lab], None, "from label %s" % lab)
            fills["label"] += 1
            continue
        mk = v.get("maker")
        if mk in MAKER_COUNTRY:
            resolved[v["id"]] = (MAKER_COUNTRY[mk], None, "maker %s" % mk)
            fills["maker"] += 1
            continue
        named = next((t["v"] for t in ts if t["k"] in PEOPLE and t["v"] in MAKER_COUNTRY), None)
        if named:
            resolved[v["id"]] = (MAKER_COUNTRY[named], None, "credited %s" % named)
            fills["maker"] += 1
            continue
        ver = v.get("verification") or ""
        if any(t["k"] == "type" and t["v"] == "trademark" for t in ts) \
           and any(b in ver for b in TRADEMARK_BOOKS):
            resolved[v["id"]] = ("United States", None, "American trademark compendium")
            fills["trademark"] += 1

    before = sum(1 for v in live if any(t["k"] == "location" for t in tags_of(v)))
    countries = collections.Counter(c for c, _, _ in resolved.values())
    cities = collections.Counter(city for _, city, _ in resolved.values() if city)
    print("items: %d" % len(live))
    print("with a location  before: %d   after: %d" % (before, len(resolved)))
    print("backfilled: %s" % dict(fills))
    print("countries: %d   cities: %d" % (len(countries), len(cities)))
    print("\ntop countries:", countries.most_common(12))
    print("\ncities:", cities.most_common(14))
    still = [v["id"] for v in live if v["id"] not in resolved]
    print("\nstill without a location: %d" % len(still))
    if unmapped:
        print("⚠️ UNMAPPED location values (these would LOSE their tag — fix the table):")
        for i, val in unmapped:
            print("   %s  %r" % (i, val))

    if not apply:
        print("\n(report only — re-run with --apply)")
        return
    for v in live:
        got = resolved.get(v["id"])
        keep = [t for t in (v.get("tags") or []) if t["k"] not in ("location", "city")]
        if got:
            keep.append({"k": "location", "v": got[0]})
            if got[1]:
                keep.append({"k": "city", "v": got[1]})
        v["tags"] = keep
        if v.get("extra_tags"):
            v["extra_tags"] = [t for t in v["extra_tags"] if t["k"] not in ("location", "city")]
    json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)
    print("\nwritten to crvi_registry.json — now rebuild:")
    print('  python3 -c "import json,payload; payload.write(json.load(open(\'crvi_registry.json\')),\'.\')"')
    print("  python3 crvi_hue.py --write && python3 build.py")


if __name__ == "__main__":
    main()
