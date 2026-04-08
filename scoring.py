import os
import base64
import json
from typing import Dict, List
from groq import Groq
from config import Config

class AnimationScorer:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.model = "llama-3.2-11b-vision-preview"  # Vision-capable model
    
    def encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def score_animation(self, frame_paths: List[str]) -> Dict:
        """
        Analyze animation frames using Groq vision model
        Returns structured scoring data
        """
        if not frame_paths:
            raise ValueError("No frames provided")
        
        # Prepare content with multiple frames
        content = [
            {
                "type": "text",
                "text": """Analyze these animation frames and provide a strict, fair evaluation. 
                Return ONLY a JSON object with this exact structure:
                {
                    "beauty_score": 0-100,
                    "visual_appeal_score": 0-100,
                    "smoothness_score": 0-100,
                    "frame_quality_score": 0-100,
                    "overall_quality_score": 0-100,
                    "total_dinns": calculated value (1400-10000),
                    "review": "brief constructive feedback"
                }
                
                Scoring criteria:
                - Beauty: artistic merit, color harmony, composition
                - Visual Appeal: eye-catching elements, creativity
                - Smoothness: motion fluidity, frame consistency
                - Frame Quality: resolution clarity, rendering quality
                - Overall: weighted combination
                
                Dinns calculation: Base 1400 + (avg_score * 86). Max ~10000.
                Be strict: average submissions should score 1400-3000.
                Professional work: 4000-7000.
                Exceptional work: 7000+."""
            }
        ]
        
        # Add frames (limit to first 3 for API efficiency)
        for frame_path in frame_paths[:3]:
            base64_image = self.encode_image(frame_path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": content
                }],
                temperature=0.3,  # Consistent scoring
                max_tokens=500
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content
            
            # Find JSON in response (handle markdown code blocks)
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]
            else:
                json_str = response_text
            
            result = json.loads(json_str.strip())
            
            # Enforce minimum Dinns
            result["total_dinns"] = max(Config.MIN_DINNS, result.get("total_dinns", Config.MIN_DINNS))
            
            return result
            
        except Exception as e:
            # Fallback scoring if AI fails
            print(f"AI scoring error: {e}")
            return {
                "beauty_score": 50,
                "visual_appeal_score": 50,
                "smoothness_score": 50,
                "frame_quality_score": 50,
                "overall_quality_score": 50,
                "total_dinns": Config.MIN_DINNS,
                "review": "System fallback - animation analyzed with default parameters"
            }