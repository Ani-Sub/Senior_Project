"""
Risk category keywords and patterns for content detection.

Each category has:
- high_confidence: Direct matches that definitively indicate risk
- medium_confidence: Context-dependent terms (may need LLM verification)
- patterns: Regex patterns for more complex matching
"""

import re
from dataclasses import dataclass
from typing import Literal


RiskCategory = Literal[
    "self_harm",
    "violence", 
    "illegal_activity",
    "misinformation",
    "hate_speech",
    "harassment",
    "toxicity",
    "scam"
]

RISK_CATEGORIES: list[RiskCategory] = [
    "self_harm",
    "violence",
    "illegal_activity", 
    "misinformation",
    "hate_speech",
    "harassment",
    "toxicity",
    "scam"
]


@dataclass
class CategoryKeywords:
    """Keywords and patterns for a risk category."""
    high_confidence: list[str]      # Direct flags
    medium_confidence: list[str]    # Need context/LLM verification
    patterns: list[str]             # Regex patterns


# Risk category definitions
RISK_KEYWORDS: dict[RiskCategory, CategoryKeywords] = {
    "self_harm": CategoryKeywords(
        high_confidence=[
            "kill myself", "end my life", "suicide method", "how to die",
            "cut myself", "self harm", "want to die", "better off dead",
            "no reason to live", "ending it all"
        ],
        medium_confidence=[
            "suicidal", "self-harm", "hurting myself", "don't want to live",
            "life isn't worth", "can't go on", "give up on life",
            "harm myself", "overdose", "jump off"
        ],
        patterns=[
            r"(want|going|plan|tried)\s+to\s+(kill|hurt|harm)\s+(myself|yourself)",
            r"(best|easy|painless)\s+way\s+to\s+die",
        ]
    ),
    
    "violence": CategoryKeywords(
        high_confidence=[
            "kill you", "murder", "shoot up", "bomb threat", "terrorist attack",
            "mass shooting", "going to hurt", "beat you up", "death threat",
            "i'll find you", "you're dead"
        ],
        medium_confidence=[
            "violent", "attack", "assault", "weapon", "gun", "knife attack",
            "fight", "hurt someone", "revenge", "make them pay",
            "destroy", "eliminate"
        ],
        patterns=[
            r"(going|want|plan)\s+to\s+(kill|hurt|attack|shoot)",
            r"(threat|promise)\s+.{0,20}\s+(violence|harm|death)",
            r"(i'?ll|will|gonna)\s+(kill|hurt|destroy)\s+(you|them|him|her)"
        ]
    ),
    
    "illegal_activity": CategoryKeywords(
        high_confidence=[
            "how to hack", "steal money", "credit card fraud", "identity theft",
            "buy drugs", "sell drugs", "drug dealer", "money laundering",
            "tax evasion", "bypass security", "crack password", "exploit vulnerability",
            "ddos attack", "ransomware", "phishing tutorial"
        ],
        medium_confidence=[
            "hack", "fraud", "illegal", "drugs", "cocaine", "heroin", "meth",
            "fake id", "counterfeit", "smuggle", "trafficking", "dark web",
            "tor browser", "untraceable", "offshore account", "crypto scam"
        ],
        patterns=[
            r"how\s+to\s+(hack|steal|fraud|scam|bypass)",
            r"(buy|sell|get)\s+(drugs|cocaine|heroin|meth|pills)",
            r"(credit\s+card|identity)\s+(fraud|theft|steal)"
        ]
    ),
    
    "misinformation": CategoryKeywords(
        high_confidence=[
            "covid is fake", "vaccines cause autism", "flat earth proof",
            "election was stolen", "microchip in vaccine", "5g causes covid",
            "miracle cure", "doctors don't want you to know", "big pharma hiding",
            "cancer cure they're hiding", "government mind control"
        ],
        medium_confidence=[
            "fake news", "they're lying", "cover up", "conspiracy", "hoax",
            "don't trust", "mainstream media lies", "wake up sheeple",
            "do your research", "hidden truth", "they don't want you to know",
            "exposed", "whistleblower reveals", "suppressed information"
        ],
        patterns=[
            r"(vaccine|covid|5g|election).{0,30}(hoax|fake|lie|scam)",
            r"(cure|treatment).{0,20}(they|doctors|pharma).{0,20}(hide|hiding|suppress)",
            r"(government|media|they).{0,20}(lying|cover|hide|control)"
        ]
    ),
    
    "hate_speech": CategoryKeywords(
        high_confidence=[
            # Note: Using category descriptors rather than actual slurs
            "racial slur", "ethnic cleansing", "white supremacy", "kill all",
            "inferior race", "subhuman", "go back to your country",
            "don't belong here", "master race"
        ],
        medium_confidence=[
            "illegal immigrants", "those people", "they're all", "typical",
            "always the same", "what do you expect from", "thugs",
            "invasion", "replacement", "pure blood"
        ],
        patterns=[
            r"(all|every)\s+(jews|muslims|blacks|whites|asians|mexicans|immigrants)\s+(are|should)",
            r"(hate|kill|remove|deport)\s+(all\s+)?(jews|muslims|blacks|immigrants)",
        ]
    ),
    
    "harassment": CategoryKeywords(
        high_confidence=[
            "doxxing", "i know where you live", "posted your address",
            "found your family", "stalking you", "watching you",
            "send nudes or", "share your photos", "revenge porn"
        ],
        medium_confidence=[
            "loser", "pathetic", "worthless", "kill yourself", "kys",
            "nobody likes you", "you should quit", "embarrassing",
            "everyone hates you", "ugly", "fat", "stupid"
        ],
        patterns=[
            r"(found|posting|share).{0,20}(address|location|family|photos)",
            r"(you|your).{0,10}(deserve|should).{0,10}(die|suffer|hurt)"
        ]
    ),
    
    "toxicity": CategoryKeywords(
        high_confidence=[
            "kys", "kill yourself", "go die", "neck yourself",
            "hope you die", "cancer upon you", "rot in hell"
        ],
        medium_confidence=[
            "idiot", "moron", "trash", "garbage person", "waste of space",
            "shut up", "stfu", "nobody asked", "worst", "terrible person",
            "disgusting", "vile", "scum", "piece of"
        ],
        patterns=[
            r"(hope|wish)\s+(you|your\s+family)\s+(die|suffer|get\s+cancer)",
            r"you('re|\s+are)\s+(a\s+)?(trash|garbage|worthless|pathetic)"
        ]
    ),
    
    "scam": CategoryKeywords(
        high_confidence=[
            "guaranteed returns", "double your money", "risk free investment",
            "send me bitcoin", "wire transfer", "nigerian prince",
            "lottery winner", "claim your prize", "act now limited time",
            "make money fast", "work from home millionaire"
        ],
        medium_confidence=[
            "get rich quick", "passive income secret", "financial freedom",
            "exclusive opportunity", "once in a lifetime", "don't miss out",
            "limited spots", "dm me for details", "link in bio",
            "easy money", "crypto opportunity", "forex signals"
        ],
        patterns=[
            r"(guaranteed|easy|quick)\s+(money|profit|returns|income)",
            r"(send|wire|transfer)\s+(bitcoin|btc|eth|crypto|money)",
            r"(double|triple|10x)\s+your\s+(money|investment|crypto)"
        ]
    ),
}


def get_category_description(category: RiskCategory) -> str:
    """Get a human-readable description of a risk category."""
    descriptions = {
        "self_harm": "Content related to self-harm or suicide",
        "violence": "Threats of violence or violent content",
        "illegal_activity": "References to illegal activities (fraud, drugs, hacking)",
        "misinformation": "False or misleading health/political information",
        "hate_speech": "Discriminatory content targeting protected groups",
        "harassment": "Targeted harassment, doxxing, or stalking",
        "toxicity": "Generally toxic or abusive language",
        "scam": "Financial scams or fraudulent schemes"
    }
    return descriptions.get(category, "Unknown risk category")


def compile_patterns(category: RiskCategory) -> list[re.Pattern]:
    """Compile regex patterns for a category."""
    keywords = RISK_KEYWORDS.get(category)
    if not keywords:
        return []
    return [re.compile(p, re.IGNORECASE) for p in keywords.patterns]
