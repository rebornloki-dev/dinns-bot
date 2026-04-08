from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import Config

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    total_dinns = Column(BigInteger, default=0)
    submission_count = Column(Integer, default=0)
    current_rank = Column(String(50), default="Bronze I")
    last_submission_time = Column(DateTime, nullable=True)
    penalty_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    submissions = relationship("Submission", back_populates="user", order_by="Submission.submitted_at.desc()")

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    perceptual_hash = Column(String(64), nullable=False)
    filename = Column(String(255))
    dinns_awarded = Column(Integer)
    beauty_score = Column(Float)
    visual_appeal_score = Column(Float)
    smoothness_score = Column(Float)
    frame_quality_score = Column(Float)
    overall_quality_score = Column(Float)
    ai_review = Column(Text)
    is_flagged = Column(Integer, default=0)  # 0=ok, 1=suspicious, 2=penalized
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="submissions")

class PenaltyLog(Base):
    __tablename__ = "penalty_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    admin_id = Column(BigInteger, nullable=False)
    reason = Column(Text)
    dinns_deducted = Column(Integer)
    previous_rank = Column(String(50))
    new_rank = Column(String(50))
    applied_at = Column(DateTime, default=datetime.utcnow)

class Database:
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()
    
    def get_or_create_user(self, session, discord_id: int, username: str):
        user = session.query(User).filter_by(discord_id=discord_id).first()
        if not user:
            user = User(discord_id=discord_id, username=username)
            session.add(user)
            session.commit()
        return user
    
    def get_user_by_id(self, session, discord_id: int):
        return session.query(User).filter_by(discord_id=discord_id).first()
    
    def get_leaderboard(self, session, limit: int = 10):
        return session.query(User).order_by(User.total_dinns.desc()).limit(limit).all()
    
    def check_duplicate_hash(self, session, perceptual_hash: str, threshold: int = 5):
        """Check for similar hashes within threshold"""
        from sqlalchemy import func
        similar = session.query(Submission).filter(
            func.hamming_distance(Submission.perceptual_hash, perceptual_hash) <= threshold
        ).first()
        return similar

db = Database()