# Dinn Bot - Animation Judging System

## Setup Instructions

### 1. Local Development

```bash
# Clone and setup
git clone &lt;repo&gt;
cd dinn-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run locally
python bot.py