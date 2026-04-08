from config import RANK_LADDER, Config
from database import User

class RankManager:
    @staticmethod
    def get_rank_from_dinns(dinns: int) -> str:
        """Determine rank based on Dinns amount"""
        for tier in RANK_LADDER:
            if tier.min_dinns <= dinns < tier.max_dinns:
                return tier.name
        return "Unreal"  # Default to highest
    
    @staticmethod
    def get_multiplier(rank_name: str, submission_count: int) -> float:
        """Calculate multiplier based on rank and submission count"""
        for tier in RANK_LADDER:
            if tier.name == rank_name:
                if submission_count >= tier.multiplier_threshold:
                    return tier.multiplier
                return 1.0
        return 1.0
    
    @staticmethod
    def apply_multiplier(base_dinns: int, rank_name: str, submission_count: int) -> int:
        """Apply rank multiplier to base dinns"""
        multiplier = RankManager.get_multiplier(rank_name, submission_count)
        return int(base_dinns * multiplier)
    
    @staticmethod
    def get_next_rank_info(current_rank: str):
        """Get info about next rank tier"""
        for i, tier in enumerate(RANK_LADDER):
            if tier.name == current_rank and i + 1 < len(RANK_LADDER):
                next_tier = RANK_LADDER[i + 1]
                return {
                    "name": next_tier.name,
                    "dinns_needed": next_tier.min_dinns,
                    "multiplier_at": next_tier.multiplier_threshold
                }
        return None
    
    @staticmethod
    def get_rank_progress(user: User) -> dict:
        """Get progress info toward next rank"""
        current_tier = None
        for tier in RANK_LADDER:
            if tier.name == user.current_rank:
                current_tier = tier
                break
        
        if not current_tier:
            return {}
        
        next_info = RankManager.get_next_rank_info(user.current_rank)
        if not next_info:
            return {"current": user.current_rank, "status": "Max Rank Achieved"}
        
        dinns_to_next = max(0, next_info["dinns_needed"] - user.total_dinns)
        submissions_to_multiplier = max(0, current_tier.multiplier_threshold - user.submission_count)
        
        return {
            "current": user.current_rank,
            "current_multiplier": RankManager.get_multiplier(user.current_rank, user.submission_count),
            "next_rank": next_info["name"],
            "dinns_to_next": dinns_to_next,
            "submissions_to_multiplier": submissions_to_multiplier,
            "multiplier_unlocked_at": current_tier.multiplier_threshold
        }