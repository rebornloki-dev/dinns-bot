import os
import asyncio
import tempfile
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from config import Config
from database import db, User, Submission, PenaltyLog
from ranking import RankManager
from scoring import AnimationScorer
from utils import AnimationProcessor

# Initialize
Config.validate()

class DinnBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)  # Prefix not used but required
        self.scorer = AnimationScorer()
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"Bot synced. Logged in as {self.user}")

bot = DinnBot()

@bot.tree.command(name="submit", description="Submit an animation for judging")
@app_commands.describe(
    animation="Upload your animation (GIF, MP4, MOV, WEBM)",
    description="Optional description of your animation"
)
async def submit(interaction: discord.Interaction, animation: discord.Attachment, description: str = None):
    """Submit animation for Dinns judging"""
    await interaction.response.defer(thinking=True)
    
    # Validate file
    valid, msg = AnimationProcessor.validate_file(animation.filename, animation.size)
    if not valid:
        return await interaction.followup.send(f"❌ {msg}", ephemeral=True)
    
    session = db.get_session()
    try:
        # Get or create user
        user = db.get_or_create_user(session, interaction.user.id, str(interaction.user))
        
        # Download file
        temp_path = tempfile.mktemp(suffix=Path(animation.filename).suffix)
        await animation.save(temp_path)
        
        # Check for duplicates
        perceptual_hash = AnimationProcessor.compute_hash(temp_path)
        duplicate = session.query(Submission).filter_by(perceptual_hash=perceptual_hash).first()
        
        if duplicate:
            os.remove(temp_path)
            
            # Flag for admin review if same user
            if duplicate.user_id == user.id:
                new_sub = Submission(
                    user_id=user.id,
                    file_hash="",
                    perceptual_hash=perceptual_hash + "_DUPLICATE",
                    filename=animation.filename,
                    is_flagged=1  # Flagged for admin review
                )
                session.add(new_sub)
                session.commit()
                
                return await interaction.followup.send(
                    "⚠️ **Duplicate Detected!** This appears to be a re-upload of a previous submission. "
                    "Admins have been notified for review.", ephemeral=True
                )
            else:
                return await interaction.followup.send(
                    "⚠️ This animation has been submitted before by another user. "
                    "Your submission has been recorded but flagged for review.", ephemeral=True
        )
        
        # Extract frames
        frames = AnimationProcessor.extract_frames(temp_path, Config.MAX_FRAMES_TO_ANALYZE)
        if not frames:
            os.remove(temp_path)
            return await interaction.followup.send("❌ Could not process animation frames.", ephemeral=True)
        
        # AI Scoring
        scoring_result = bot.scorer.score_animation(frames)
        
        # Calculate final Dinns with multiplier
        base_dinns = scoring_result["total_dinns"]
        final_dinns = RankManager.apply_multiplier(base_dinns, user.current_rank, user.submission_count)
        
        # Update user
        user.total_dinns += final_dinns
        user.submission_count += 1
        user.last_submission_time = datetime.utcnow()
        
        # Check rank up
        new_rank = RankManager.get_rank_from_dinns(user.total_dinns)
        rank_up = new_rank != user.current_rank
        user.current_rank = new_rank
        
        # Save submission
        submission = Submission(
            user_id=user.id,
            file_hash="",  # Could add MD5 here if needed
            perceptual_hash=perceptual_hash,
            filename=animation.filename,
            dinns_awarded=final_dinns,
            beauty_score=scoring_result["beauty_score"],
            visual_appeal_score=scoring_result["visual_appeal_score"],
            smoothness_score=scoring_result["smoothness_score"],
            frame_quality_score=scoring_result["frame_quality_score"],
            overall_quality_score=scoring_result["overall_quality_score"],
            ai_review=scoring_result["review"]
        )
        session.add(submission)
        session.commit()
        
        # Cleanup
        os.remove(temp_path)
        for frame in frames:
            if os.path.exists(frame):
                os.remove(frame)
        
        # Build response embed
        embed = discord.Embed(
            title="🎬 Animation Judged!",
            description=f"**{animation.filename}**",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="🎨 Beauty", value=f"{scoring_result['beauty_score']}/100", inline=True)
        embed.add_field(name="👁️ Visual Appeal", value=f"{scoring_result['visual_appeal_score']}/100", inline=True)
        embed.add_field(name="🌊 Smoothness", value=f"{scoring_result['smoothness_score']}/100", inline=True)
        embed.add_field(name="📐 Frame Quality", value=f"{scoring_result['frame_quality_score']}/100", inline=True)
        embed.add_field(name="⭐ Overall", value=f"{scoring_result['overall_quality_score']}/100", inline=True)
        embed.add_field(name="💰 Base Dinns", value=f"{base_dinns}", inline=True)
        
        multiplier = RankManager.get_multiplier(user.current_rank, user.submission_count)
        if multiplier > 1:
            embed.add_field(name="⚡ Multiplier", value=f"x{multiplier}", inline=True)
        
        embed.add_field(name="🏆 Total Dinns", value=f"**+{final_dinns}**", inline=True)
        embed.add_field(name="💎 Your Total", value=f"{user.total_dinns}", inline=True)
        
        if rank_up:
            embed.add_field(name="🎉 RANK UP!", value=f"Promoted to **{new_rank}**", inline=False)
        
        embed.add_field(name="📝 Review", value=scoring_result["review"], inline=False)
        embed.set_footer(text=f"Submission #{user.submission_count} • Rank: {user.current_rank}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        session.rollback()
        print(f"Error in submit: {e}")
        await interaction.followup.send("❌ An error occurred processing your submission. Admins notified.", ephemeral=True)
    finally:
        session.close()

@bot.tree.command(name="leaderboard", description="View the top animators by Dinns")
@app_commands.describe(limit="Number of users to show (max 25)")
async def leaderboard(interaction: discord.Interaction, limit: int = 10):
    """Display Dinns leaderboard"""
    await interaction.response.defer()
    
    if limit > 25:
        limit = 25
    elif limit < 1:
        limit = 10
    
    session = db.get_session()
    try:
        top_users = db.get_leaderboard(session, limit)
        
        embed = discord.Embed(
            title="🏆 Dinns Leaderboard",
            description=f"Top {len(top_users)} Animators",
            color=discord.Color.blue()
        )
        
        for idx, user in enumerate(top_users, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"#{idx}")
            progress = RankManager.get_rank_progress(user)
            multiplier = progress.get("current_multiplier", 1)
            
            value = f"💰 {user.total_dinns:,} Dinns\n"
            value += f"🎖️ {user.current_rank}\n"
            value += f"📊 {user.submission_count} submissions\n"
            if multiplier > 1:
                value += f"⚡ x{multiplier} multiplier active"
            
            embed.add_field(
                name=f"{medal} {user.username}",
                value=value,
                inline=False
            )
        
        embed.set_footer(text=f"Total participants: {session.query(User).count()}")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Leaderboard error: {e}")
        await interaction.followup.send("❌ Error loading leaderboard.", ephemeral=True)
    finally:
        session.close()

@bot.tree.command(name="admin_penalty", description="Apply penalty to user (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    user="User to penalize",
    amount="Dinns to deduct",
    reason="Reason for penalty"
)
async def admin_penalty(interaction: discord.Interaction, user: discord.User, amount: int, reason: str):
    """Admin command to deduct Dinns for cheating"""
    await interaction.response.defer(ephemeral=True)
    
    session = db.get_session()
    try:
        db_user = db.get_user_by_id(session, user.id)
        if not db_user:
            return await interaction.followup.send("User not found in database.", ephemeral=True)
        
        previous_rank = db_user.current_rank
        
        # Apply penalty
        db_user.total_dinns = max(0, db_user.total_dinns - amount)
        db_user.penalty_count += 1
        db_user.current_rank = RankManager.get_rank_from_dinns(db_user.total_dinns)
        
        # Log penalty
        log = PenaltyLog(
            user_id=db_user.id,
            admin_id=interaction.user.id,
            reason=reason,
            dinns_deducted=amount,
            previous_rank=previous_rank,
            new_rank=db_user.current_rank
        )
        session.add(log)
        session.commit()
        
        embed = discord.Embed(
            title="🔨 Penalty Applied",
            color=discord.Color.red()
        )
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Deducted", value=f"-{amount} Dinns", inline=True)
        embed.add_field(name="New Total", value=f"{db_user.total_dinns}", inline=True)
        embed.add_field(name="Previous Rank", value=previous_rank, inline=True)
        embed.add_field(name="New Rank", value=db_user.current_rank, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Notify user
        try:
            await user.send(
                f"⚠️ **Penalty Applied**\n"
                f"You lost {amount} Dinns for: {reason}\n"
                f"New balance: {db_user.total_dinns} | Rank: {db_user.current_rank}"
            )
        except:
            pass
            
    except Exception as e:
        session.rollback()
        print(f"Penalty error: {e}")
        await interaction.followup.send("Error applying penalty.", ephemeral=True)
    finally:
        session.close()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    else:
        print(f"Command error: {error}")

if __name__ == "__main__":
    bot.run(Config.DISCORD_TOKEN)