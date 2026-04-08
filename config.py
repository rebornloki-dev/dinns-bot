import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class RankTier:
    name: str
    min_dinns: int
    max_dinns: int
    multiplier_threshold: int  # submissions needed for multiplier
    multiplier: float
    
# Reserved section for custom ranks - easily editable
RANK_LADDER = [
    # Bronze Tier (x2 at 10 submissions)
    RankTier("Bronze I", 0, 500, 10, 2.0),
    RankTier("Bronze II", 500, 1000, 10, 2.0),
    RankTier("Bronze III", 1000, 2500, 10, 2.0),
    
    # Silver Tier (x2 at 10 submissions)
    RankTier("Silver I", 2500, 5000, 10, 2.0),
    RankTier("Silver II", 5000, 7500, 10, 2.0),
    RankTier("Silver III", 7500, 11000, 10, 2.0),
    
    # Gold Tier (x3 at 20 submissions)
    RankTier("Gold I", 11000, 15000, 20, 3.0),
    RankTier("Gold II", 15000, 20000, 20, 3.0),
    RankTier("Gold III", 20000, 25000, 20, 3.0),
    
    # Diamond Tier (x3 at 20 submissions)
    RankTier("Diamond I", 25000, 30000, 20, 3.0),
    RankTier("Diamond II", 30000, 50000, 20, 3.0),
    RankTier("Diamond III", 50000, 100000, 20, 3.0),
    
    # Star Tier (x4 at 30 submissions)
    RankTier("Star I", 100000, 150000, 30, 4.0),
    RankTier("Star II", 150000, 200000, 30, 4.0),
    RankTier("Star III", 200000, 250000, 30, 4.0),
    
    # Champion Tier (x4 at 30 submissions)
    RankTier("Champion I", 250000, 300000, 30, 4.0),
    RankTier("Champion II", 300000, 350000, 30, 4.0),
    RankTier("Champion III", 350000, 400000, 30, 4.0),
    
    # Pro Tier (x5 at 40 submissions)
    RankTier("Pro I", 400000, 450000, 40, 5.0),
    RankTier("Pro II", 450000, 500000, 40, 5.0),
    
    # Unreal Tier (x6 at 50 submissions)
    RankTier("Unreal", 500000, float('inf'), 50, 6.0),
]

class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    MIN_DINNS = 1400
    MAX_FILE_SIZE_MB = 25
    SUPPORTED_FORMATS = {'.gif', '.mp4', '.mov', '.webm', '.avi'}
    
    # Frame extraction settings
    MAX_FRAMES_TO_ANALYZE = 5  # Limit API calls
    FRAME_SAMPLE_INTERVAL = 10  # Sample every Nth frame
    
    # Duplicate detection sensitivity (0-64, lower = stricter)
    HASH_THRESHOLD = 10
    
    # Penalty settings
    PENALTY_REDUCTION_FACTOR = 0.5  # 50% reduction per penalty
    MAX_PENALTIES = 5
    
    @staticmethod
    def validate():
        required = ["DISCORD_TOKEN", "GROQ_API_KEY", "DATABASE_URL"]
        missing = [var for var in required if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")