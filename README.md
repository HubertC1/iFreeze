# iFreeze - Smart Fridge Recipe Bot

A LINE bot that provides recipe suggestions based on the contents of your smart fridge. The system uses computer vision to identify food items and their status, and an LLM to generate personalized recipe suggestions.

## Features

- LINE bot interface for user interaction
- Raspberry Pi camera integration for fridge monitoring
- Food item detection and status tracking
- Recipe suggestions based on available ingredients
- Spoilage detection and alerts

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env` file with the following variables:
```
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
DATABASE_URL=sqlite:///./ifreeze.db
YOLO_API_URL=your_yolo_api_url
LLM_API_URL=your_llm_api_url
```

3. Run the application:
```bash
uvicorn app.main:app --reload
```

## Project Structure

- `app/` - Main application directory
  - `main.py` - FastAPI application entry point
  - `models/` - Database models
  - `schemas/` - Pydantic schemas
  - `routers/` - API routes
  - `services/` - Business logic
  - `utils/` - Utility functions
  - `line_bot/` - LINE bot handlers
  - `camera/` - Raspberry Pi camera integration 