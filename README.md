# iFreeze - Smart Fridge Recipe Bot

A LINE bot that provides recipe suggestions based on the contents of your smart fridge. The system uses computer vision to identify food items and their status, and an LLM to generate personalized recipe suggestions.

## Project Structure

- `app/` - FastAPI backend server
  - Runs on localhost using uvicorn
  - Handles API endpoints and business logic
  - Serves the frontend application

- `liff-frontend/` - Frontend application
  - Built using npm
  - Served by the FastAPI backend

- `hubear.py` - Raspberry Pi server
  - Handles camera operations and picture taking
  - Receives and processes LINE bot orders
  - Runs on the Raspberry Pi device

- `object_detection/` - Grounded DINO implementation
  - Handles food item detection
  - See its own README for specific setup instructions

## Setup

1. Clone the repository and install dependencies:

```bash
# Backend setup
cd app
pip install -r requirements.txt

# Frontend setup
cd ../liff-frontend
npm install
```

2. Create a `.env` file in the root directory with the following variables:

```env
# LINE Bot Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# Frontend Configuration
VITE_NGROK_URL_BASE=your_ngrok_url

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Raspberry Pi Configuration
RPI_HOST=your_rpi_ip_address
RPI_USER=your_rpi_username

# API Endpoints
PROCESSING_API_BASE=your_gpu_server_ngrok_url
RPI_API_BASE=your_rpi_server_ngrok_url
```

3. Running the application:

```bash
# Start the backend server
cd app
uvicorn main:app --reload

# Start the frontend development server
cd ../liff-frontend
npm run dev

# On Raspberry Pi
python hubear.py
```

## Features

- LINE bot interface for user interaction
- Raspberry Pi camera integration for fridge monitoring
- Food item detection using Grounded DINO
- Recipe suggestions based on available ingredients
- Spoilage detection and alerts

## Additional Documentation

- For object detection setup and usage, refer to the README in the `object_detection/` directory
- For frontend development, refer to the documentation in the `liff-frontend/` directory 