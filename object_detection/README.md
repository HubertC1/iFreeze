# Local Server with Ngrok Tunnel

This project sets up a local server on port 8000 and exposes it to the internet using ngrok.

## Prerequisites

- Python 3.x
- ngrok account and authtoken
- pip (Python package manager)
- pip install --upgrade --ignore-installed blinker
## Installing Ngrok on Linux

1. **Download ngrok**
   ```bash
   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
   ```

2. **Extract the downloaded file**
   ```bash
   tar -xvzf ngrok-v3-stable-linux-amd64.tgz
   ```

3. **Move ngrok to a directory in your PATH**
   ```bash
   mv ngrok /usr/local/bin/
   ```

4. **Verify the installation**
   ```bash
   ngrok version
   ```

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Ngrok**
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```
   Replace `YOUR_AUTHTOKEN` with your ngrok authtoken from https://dashboard.ngrok.com/get-started/your-authtoken

## Running the Server

1. **Start the Local Server**
   ```bash
   python app.py
   ```
   This will start your server on http://localhost:8000

2. **Start Ngrok Tunnel**
   In a new terminal window:
   ```bash
   ngrok http 8000
   ```

## Accessing Your Server

- **Local Access**: http://localhost:8000
- **Public Access**: Your ngrok URL will be displayed in the ngrok terminal window
  - It will look like: `https://[random-subdomain].ngrok.io`
  - You can also check the ngrok web interface at http://localhost:4040

## Available Endpoints

1. **Home** (`GET /`)
   - Returns welcome message and available endpoints
   - Example: `curl http://localhost:8000/`

2. **File Upload** (`POST /upload`)
   - Upload files to the server
   - Example: `curl -X POST -F "file=@your_file.txt" http://localhost:8000/upload`

3. **Status** (`GET /status`)
   - Check server status and list uploaded files
   - Example: `curl http://localhost:8000/status`

## Important Notes

- The ngrok URL changes each time you restart ngrok (unless you have a paid plan)
- Keep both the Python server and ngrok running to maintain the tunnel
- Uploaded files are stored in the `uploads` directory
- To stop the servers, press `Ctrl+C` in both terminal windows

## Troubleshooting

1. If port 8000 is already in use:
   - Change the port in `app.py` and update the ngrok command accordingly
   - Example: `ngrok http 8001` if you changed to port 8001

2. If ngrok connection fails:
   - Check your internet connection
   - Verify your authtoken is correct
   - Ensure no firewall is blocking the connection 