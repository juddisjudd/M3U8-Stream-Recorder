# M3U8 Stream Recorder

M3U8 Stream Recorder is a desktop application built with PyQt6 that allows users to record M3U8 streams using FFmpeg.

## Features

- Add and manage multiple M3U8 streams
- Start and stop recording streams
- Automatically update stream durations
- Clear stopped streams
- Select folder to save recordings
- Check file integrity using FFprobe

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/juddisjudd/M3U8-Stream-Recorder.git
    cd m3u8-stream-recorder
    ```

2. Create a virtual environment (optional but recommended):
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Make sure FFmpeg and FFprobe are installed on your system and accessible via the command line.

## Usage

1. Run the application:
    ```sh
    python m3u8r.py
    ```

2. Enter the M3U8 URL and Stream Name, then click "Add Stream".

3. Click "Start" to begin recording. The stream status and duration will be updated automatically.

4. Click "Stop" to stop recording.

5. Use the "Clear Stopped" button to remove stopped streams from the list.

6. Select the folder where recordings will be saved using the "Select Folder" button.

## Dependencies

- PyQt6
- FFmpeg
- FFprobe
