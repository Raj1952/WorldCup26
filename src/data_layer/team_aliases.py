"""Team name normalization — canonical names follow martj42 dataset conventions."""

from __future__ import annotations

__all__ = ["resolve_alias", "ALIAS_MAP", "get_flag_emoji", "get_flag_url",
           "get_flag_code", "COUNTRY_CODES", "FLAG_CODES"]

# lipis/flag-icons codes for SVG rendering (MIT / public-domain art).
# Differs from ISO 3166-1 for UK home nations: gb-eng / gb-sct / gb-wls
# NOT the Union Jack (gb) — these are separate FIFA members.
FLAG_CODES: dict[str, str] = {
    # WC2026 qualified teams (48) — exact canonical names as used in predictions
    "Algeria":                "dz",
    "Argentina":              "ar",
    "Australia":              "au",
    "Austria":                "at",
    "Belgium":                "be",
    "Bosnia and Herzegovina": "ba",
    "Brazil":                 "br",
    "Canada":                 "ca",
    "Cape Verde":             "cv",   # also "Cabo Verde" in some feeds
    "Colombia":               "co",
    "Croatia":                "hr",
    "Curaçao":                "cw",
    "Czech Republic":         "cz",   # fed as "Czechia" → alias resolves to this
    "DR Congo":               "cd",   # Congo DR / Congo, DR
    "Ecuador":                "ec",
    "Egypt":                  "eg",
    "England":                "gb-eng",  # ← subdivision flag, NOT Union Jack
    "France":                 "fr",
    "Germany":                "de",
    "Ghana":                  "gh",
    "Haiti":                  "ht",
    "Iran":                   "ir",   # IR Iran in FIFA feeds → alias resolves here
    "Iraq":                   "iq",
    "Ivory Coast":            "ci",   # Côte d'Ivoire → alias resolves here
    "Japan":                  "jp",
    "Jordan":                 "jo",
    "Mexico":                 "mx",
    "Morocco":                "ma",
    "Netherlands":            "nl",
    "New Zealand":            "nz",
    "Norway":                 "no",
    "Panama":                 "pa",
    "Paraguay":               "py",
    "Portugal":               "pt",
    "Qatar":                  "qa",
    "Saudi Arabia":           "sa",
    "Scotland":               "gb-sct",  # ← subdivision flag, NOT Union Jack
    "Senegal":                "sn",
    "South Africa":           "za",
    "South Korea":            "kr",   # Korea Republic → alias resolves here
    "Spain":                  "es",
    "Sweden":                 "se",
    "Switzerland":            "ch",
    "Tunisia":                "tn",
    "Turkey":                 "tr",   # Türkiye → alias resolves here
    "United States":          "us",   # USA → alias resolves here
    "Uruguay":                "uy",
    "Uzbekistan":             "uz",
    "Wales":                  "gb-wls",  # ← subdivision flag, NOT Union Jack

    # Extended coverage for historical data / other competitions
    "Afghanistan":            "af",   "Albania":              "al",
    "Angola":                 "ao",   "Armenia":              "am",
    "Azerbaijan":             "az",   "Bahrain":              "bh",
    "Belarus":                "by",   "Benin":                "bj",
    "Bolivia":                "bo",   "Botswana":             "bw",
    "Bulgaria":               "bg",   "Burkina Faso":         "bf",
    "Cameroon":               "cm",   "Chile":                "cl",
    "China":                  "cn",   "Congo":                "cg",
    "Costa Rica":             "cr",   "Cuba":                 "cu",
    "Denmark":                "dk",   "Dominican Republic":   "do",
    "El Salvador":            "sv",   "Equatorial Guinea":    "gq",
    "Estonia":                "ee",   "Ethiopia":             "et",
    "Finland":                "fi",   "Gabon":                "ga",
    "Gambia":                 "gm",   "Georgia":              "ge",
    "Greece":                 "gr",   "Guatemala":            "gt",
    "Guinea":                 "gn",   "Guinea-Bissau":        "gw",
    "Honduras":               "hn",   "Hungary":              "hu",
    "Iceland":                "is",   "India":                "in",
    "Indonesia":              "id",   "Ireland":              "ie",
    "Israel":                 "il",   "Italy":                "it",
    "Jamaica":                "jm",   "Kazakhstan":           "kz",
    "Kenya":                  "ke",   "Kosovo":               "xk",
    "Kuwait":                 "kw",   "Lebanon":              "lb",
    "Liberia":                "lr",   "Libya":                "ly",
    "Luxembourg":             "lu",   "Malaysia":             "my",
    "Mali":                   "ml",   "Malta":                "mt",
    "Mauritania":             "mr",   "Moldova":              "md",
    "Montenegro":             "me",   "Mozambique":           "mz",
    "Myanmar":                "mm",   "Namibia":              "na",
    "Nicaragua":              "ni",   "Nigeria":              "ng",
    "North Korea":            "kp",   "North Macedonia":      "mk",
    "Oman":                   "om",   "Pakistan":             "pk",
    "Palestine":              "ps",   "Peru":                 "pe",
    "Philippines":            "ph",   "Poland":               "pl",
    "Romania":                "ro",   "Russia":               "ru",
    "Rwanda":                 "rw",   "Serbia":               "rs",
    "Sierra Leone":           "sl",   "Slovakia":             "sk",
    "Slovenia":               "si",   "Syria":                "sy",
    "Tanzania":               "tz",   "Thailand":             "th",
    "Togo":                   "tg",   "Trinidad and Tobago":  "tt",
    "Uganda":                 "ug",   "Ukraine":              "ua",
    "United Arab Emirates":   "ae",   "Venezuela":            "ve",
    "Vietnam":                "vn",   "Yemen":                "ye",
    "Zambia":                 "zm",   "Zimbabwe":             "zw",
    "Antigua and Barbuda":    "ag",   "Bahamas":              "bs",
    "Barbados":               "bb",   "Belize":               "bz",
    "Comoros":                "km",   "Fiji":                 "fj",
    "Grenada":                "gd",   "Guyana":               "gy",
    "Papua New Guinea":       "pg",   "Solomon Islands":      "sb",
    "Suriname":               "sr",   "Timor-Leste":          "tl",
    "Eswatini":               "sz",   "Lesotho":              "ls",
    "Djibouti":               "dj",   "Seychelles":           "sc",
    "Vanuatu":                "vu",   "Chinese Taipei":       "tw",
    "Hong Kong":              "hk",   "Singapore":            "sg",
    "New Caledonia":          "nc",
}

# ISO 3166-1 alpha-2 codes for flag rendering
COUNTRY_CODES: dict[str, str] = {
    "Afghanistan": "af", "Albania": "al", "Algeria": "dz", "Angola": "ao",
    "Argentina": "ar", "Armenia": "am", "Australia": "au", "Austria": "at",
    "Azerbaijan": "az", "Bahrain": "bh", "Bangladesh": "bd", "Belarus": "by",
    "Belgium": "be", "Benin": "bj", "Bolivia": "bo", "Bosnia and Herzegovina": "ba",
    "Botswana": "bw", "Brazil": "br", "Bulgaria": "bg", "Burkina Faso": "bf",
    "Cameroon": "cm", "Canada": "ca", "Chile": "cl", "China": "cn",
    "Colombia": "co", "Congo": "cg", "Costa Rica": "cr", "Croatia": "hr",
    "Cuba": "cu", "Czech Republic": "cz", "DR Congo": "cd", "Denmark": "dk",
    "Dominican Republic": "do", "Ecuador": "ec", "Egypt": "eg",
    "El Salvador": "sv", "England": "gb", "Equatorial Guinea": "gq",
    "Estonia": "ee", "Ethiopia": "et", "Finland": "fi", "France": "fr",
    "Gabon": "ga", "Gambia": "gm", "Georgia": "ge", "Germany": "de",
    "Ghana": "gh", "Greece": "gr", "Guatemala": "gt", "Guinea": "gn",
    "Guinea-Bissau": "gw", "Haiti": "ht", "Honduras": "hn", "Hungary": "hu",
    "Iceland": "is", "India": "in", "Indonesia": "id", "Iran": "ir",
    "Iraq": "iq", "Ireland": "ie", "Israel": "il", "Italy": "it",
    "Ivory Coast": "ci", "Jamaica": "jm", "Japan": "jp", "Jordan": "jo",
    "Kazakhstan": "kz", "Kenya": "ke", "Kosovo": "xk", "Kuwait": "kw",
    "Lebanon": "lb", "Liberia": "lr", "Libya": "ly", "Luxembourg": "lu",
    "Malaysia": "my", "Mali": "ml", "Malta": "mt", "Mauritania": "mr",
    "Mexico": "mx", "Moldova": "md", "Montenegro": "me", "Morocco": "ma",
    "Mozambique": "mz", "Myanmar": "mm", "Namibia": "na", "Netherlands": "nl",
    "New Zealand": "nz", "Nicaragua": "ni", "Nigeria": "ng",
    "North Korea": "kp", "North Macedonia": "mk", "Norway": "no", "Oman": "om",
    "Pakistan": "pk", "Palestine": "ps", "Panama": "pa", "Paraguay": "py",
    "Peru": "pe", "Philippines": "ph", "Poland": "pl", "Portugal": "pt",
    "Qatar": "qa", "Romania": "ro", "Russia": "ru", "Rwanda": "rw",
    "Saudi Arabia": "sa", "Scotland": "gb", "Senegal": "sn", "Serbia": "rs",
    "Sierra Leone": "sl", "Slovakia": "sk", "Slovenia": "si",
    "South Africa": "za", "South Korea": "kr", "Spain": "es",
    "Sweden": "se", "Switzerland": "ch", "Syria": "sy", "Tanzania": "tz",
    "Thailand": "th", "Togo": "tg", "Trinidad and Tobago": "tt",
    "Tunisia": "tn", "Turkey": "tr", "Uganda": "ug", "Ukraine": "ua",
    "United Arab Emirates": "ae", "United States": "us", "Uruguay": "uy",
    "Uzbekistan": "uz", "Venezuela": "ve", "Vietnam": "vn", "Wales": "gb",
    "Yemen": "ye", "Zambia": "zm", "Zimbabwe": "zw",
    "Antigua and Barbuda": "ag", "Bahamas": "bs", "Barbados": "bb",
    "Belize": "bz", "Cape Verde": "cv", "Comoros": "km",
    "Curaçao": "cw", "Fiji": "fj", "Grenada": "gd", "Guyana": "gy",
    "New Caledonia": "nc", "Papua New Guinea": "pg", "Solomon Islands": "sb",
    "Suriname": "sr", "Chinese Taipei": "tw", "Hong Kong": "hk",
    "Singapore": "sg", "Brunei": "bn", "Cambodia": "kh",
    "Timor-Leste": "tl", "Eswatini": "sz", "Lesotho": "ls",
    "Benin": "bj", "Djibouti": "dj", "Seychelles": "sc",
    "El Salvador": "sv", "Costa Rica": "cr", "Vanuatu": "vu",
}

# Raw / alternate name → canonical name
ALIAS_MAP: dict[str, str] = {
    # USA variants
    "usa": "United States",
    "u.s.a.": "United States",
    "u.s.": "United States",
    "united states of america": "United States",

    # Korea
    "korea republic": "South Korea",
    "republic of korea": "South Korea",
    "korea dpr": "North Korea",
    "dpr korea": "North Korea",

    # Iran
    "ir iran": "Iran",
    "islamic republic of iran": "Iran",

    # Ivory Coast
    "côte d'ivoire": "Ivory Coast",
    "cote d'ivoire": "Ivory Coast",
    "cote divoire": "Ivory Coast",

    # Czech Republic
    "czechia": "Czech Republic",

    # Bosnia
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "bosnia & herzegovina": "Bosnia and Herzegovina",

    # Ireland
    "republic of ireland": "Ireland",

    # China
    "china pr": "China",
    "china, pr": "China",

    # Trinidad
    "trinidad & tobago": "Trinidad and Tobago",

    # North Macedonia (formerly FYR Macedonia)
    "north macedonia": "North Macedonia",
    "republic of north macedonia": "North Macedonia",
    "fyr macedonia": "North Macedonia",
    "macedonia": "North Macedonia",

    # Congo variants
    "dr congo": "DR Congo",
    "congo dr": "DR Congo",
    "democratic republic of the congo": "DR Congo",
    "congo, democratic republic of the": "DR Congo",
    "congo republic": "Congo",
    "republic of the congo": "Congo",

    # Cape Verde
    "cape verde islands": "Cape Verde",

    # São Tomé
    "sao tome and principe": "São Tomé and Príncipe",

    # Eswatini
    "swaziland": "Eswatini",

    # Timor-Leste
    "timor leste": "Timor-Leste",
    "east timor": "Timor-Leste",

    # Curaçao
    "curacao": "Curaçao",

    # Saint Vincent
    "saint vincent and grenadines": "Saint Vincent and the Grenadines",
    "st vincent and the grenadines": "Saint Vincent and the Grenadines",

    # Saint Kitts
    "saint kitts & nevis": "Saint Kitts and Nevis",
    "st kitts and nevis": "Saint Kitts and Nevis",

    # Antigua
    "antigua & barbuda": "Antigua and Barbuda",

    # Turkey
    "türkiye": "Turkey",

    # UAE
    "uae": "United Arab Emirates",
    "u.a.e.": "United Arab Emirates",

    # Historical / political name changes — map to modern
    "soviet union": "Russia",
    "west germany": "Germany",
    "east germany": "Germany",
    "yugoslavia": "Serbia",
    "czechoslovakia": "Czech Republic",

    # Football-data.org / openfootball variants
    "slovak republic": "Slovakia",
    "chinese taipei": "Chinese Taipei",
    "new zealand": "New Zealand",
    "central african republic": "Central African Republic",
}


def resolve_alias(raw_name: str) -> str:
    """Return canonical team name for any raw name variant."""
    if not raw_name:
        return raw_name
    key = raw_name.strip().lower()
    return ALIAS_MAP.get(key, raw_name.strip())


def get_flag_url(team: str, size: str = "24x18") -> str:
    """Return flagcdn.com URL for a team's country flag."""
    canonical = resolve_alias(team)
    code = COUNTRY_CODES.get(canonical, "").lower()
    if not code:
        return ""
    return f"https://flagcdn.com/{size}/{code}.png"


def get_flag_emoji(team: str) -> str:
    """Return regional indicator emoji for a team's flag."""
    canonical = resolve_alias(team)
    code = COUNTRY_CODES.get(canonical, "")
    if not code or "-" in code or len(code) != 2:
        return "🏳"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def get_flag_code(team: str) -> str:
    """
    Return the lipis/flag-icons code for a team.
    Returns empty string if not found (caller should handle fail-soft).
    """
    canonical = resolve_alias(team)
    return FLAG_CODES.get(canonical, "")
