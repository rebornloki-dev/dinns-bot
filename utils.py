import os
import cv2
import imagehash
from PIL import Image
import tempfile
from pathlib import Path
from config import Config

class AnimationProcessor:
    @staticmethod
    def extract_frames(file_path: str, max_frames: int = 5) -> list:
        """Extract frames from GIF or video file"""
        frames = []
        suffix = Path(file_path).suffix.lower()
        
        if suffix == '.gif':
            frames = AnimationProcessor._extract_gif_frames(file_path, max_frames)
        else:
            frames = AnimationProcessor._extract_video_frames(file_path, max_frames)
        
        return frames
    
    @staticmethod
    def _extract_gif_frames(file_path: str, max_frames: int) -> list:
        """Extract frames from GIF"""
        frames = []
        try:
            with Image.open(file_path) as gif:
                total_frames = gif.n_frames
                step = max(1, total_frames // max_frames)
                
                for i in range(0, min(total_frames, max_frames * step), step):
                    gif.seek(i)
                    frame = gif.copy().convert('RGB')
                    temp_path = tempfile.mktemp(suffix='.jpg')
                    frame.save(temp_path, 'JPEG')
                    frames.append(temp_path)
        except Exception as e:
            print(f"GIF extraction error: {e}")
        
        return frames
    
    @staticmethod
    def _extract_video_frames(file_path: str, max_frames: int) -> list:
        """Extract frames from video using OpenCV"""
        frames = []
        cap = cv2.VideoCapture(file_path)
        
        if not cap.isOpened():
            return frames
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, total_frames // max_frames)
        
        for i in range(0, min(total_frames, max_frames * step), step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                temp_path = tempfile.mktemp(suffix='.jpg')
                pil_img.save(temp_path, 'JPEG')
                frames.append(temp_path)
        
        cap.release()
        return frames
    
    @staticmethod
    def compute_hash(file_path: str) -> str:
        """Compute perceptual hash for duplicate detection"""
        try:
            # For videos/GIFs, hash the middle frame
            frames = AnimationProcessor.extract_frames(file_path, max_frames=1)
            if frames:
                with Image.open(frames[0]) as img:
                    phash = str(imagehash.phash(img))
                # Cleanup temp frame
                os.remove(frames[0])
                return phash
        except Exception as e:
            print(f"Hash computation error: {e}")
        
        return ""
    
    @staticmethod
    def validate_file(filename: str, file_size: int) -> tuple:
        """Validate file type and size"""
        suffix = Path(filename).suffix.lower()
        
        if suffix not in Config.SUPPORTED_FORMATS:
            return False, f"Unsupported format. Use: {', '.join(Config.SUPPORTED_FORMATS)}"
        
        if file_size > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
            return False, f"File too large. Max: {Config.MAX_FILE_SIZE_MB}MB"
        
        return True, "Valid"