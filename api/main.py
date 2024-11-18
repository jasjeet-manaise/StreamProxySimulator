from fastapi import FastAPI, Request, Response, HTTPException, WebSocket
import httpx
import asyncio
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import hashlib
from proxy import ProxySettings
from typing import List, Optional
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

SITE = os.getenv("SITE_URL", "localhost:8000")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (or specify your frontend URL)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

proxies = {}

# WebSocket clients
clients: List[WebSocket] = []


# Helper function to broadcast logs to WebSocket clients
async def broadcast_log(message: str):
    for client in clients:
        try:
            await client.send_text(message)
        except Exception as e:
            print(f"Error sending log to client: {e}")


# Function to log messages and send them to WebSocket clients
async def log_message(message: str):
    print(message)  # Print to server logs
    await broadcast_log(message)
    
async def handle_audio_delay(proxy: ProxySettings):
    if proxy.is_delaying:
        # Skip making the request if delay is active
        await log_message("Audio segment request blocked due to active delay.")
        return None

    proxy.audio_segment_count += 1
    await log_message(f"Received audio segment request #{proxy.audio_segment_count}")

    if proxy.audio_delay_enabled and proxy.audio_segment_count % proxy.delay_after_segments == 0:
        proxy.is_delaying = True
        await log_message(f"Starting delay of {proxy.delay_duration} seconds for audio requests...")

        # Schedule resetting `is_delaying` after the delay duration
        asyncio.create_task(unblock_audio(proxy))

        return None  # Skip the request during the delay period

    return True  # Indicate the request can proceed



async def unblock_audio(proxy: ProxySettings):
    await asyncio.sleep(proxy.delay_duration)
    proxy.is_delaying = False
    await log_message("Audio delay period ended. Resuming normal request handling.")


async def handle_segment_failure(proxy: ProxySettings):
    await log_message(f"Failing segment request with error code {proxy.segment_failure_code}")
    return Response(
        content=f"Simulated failure with error code {proxy.segment_failure_code}",
        status_code=proxy.segment_failure_code
    )

async def handle_packet_drop(proxy: ProxySettings):
    if proxy.drop_packets_enabled:
        await log_message("Dropping all playlist requests to simulate connection timeout.")
        proxy.is_dropping_playlist = True


# Function to handle stuck playlist logic
async def handle_stuck_playlist(proxy: ProxySettings):
    if proxy.is_playlist_stuck and proxy.cached_playlist_content:
        await log_message("Serving cached playlist content due to stuck playlist.")
        return Response(
            content=proxy.cached_playlist_content,
            media_type="application/vnd.apple.mpegurl" if ".m3u8" in proxy.path else "application/dash+xml"
        )

async def fetch_and_cache_content(proxy: ProxySettings):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(proxy.target_url)
            if response.status_code == 200:
                await log_message("Successfully cached segment content.")
                return await response.aread()
            else:
                await log_message(f"Failed to fetch segment content: {response.status_code}")
                return None
    except Exception as e:
        await log_message(f"Error fetching segment content: {e}")
        return None


# Function to reset the stuck playlist state
async def reset_stuck_playlist(proxy: ProxySettings):
    await log_message("Starting stuck playlist recovery timer...")
    await asyncio.sleep(proxy.stuck_recovery_timeout)
    if proxy.is_playlist_stuck:
        await log_message("Recovery timeout reached. Resuming normal playlist streaming.")
        proxy.is_playlist_stuck = False
        proxy.cached_playlist_content = None

async def handle_segment_logic(proxy: ProxySettings):
    proxy.segment_count += 1
    await log_message(f"Playlist request count: {proxy.segment_count}")

    # Check for stuck playlist condition
    if proxy.is_stuck_playlist_enabled and proxy.segment_count % proxy.playlist_stick_threshold == 0:
        if not proxy.is_playlist_stuck:
            await log_message("Stuck playlist condition met. Caching content and setting is_playlist_stuck to True.")
            proxy.is_playlist_stuck = True

            # Fetch and cache the current playlist
            if proxy.cached_playlist_content is None:
                proxy.cached_playlist_content = await fetch_and_cache_content(proxy)

            # Schedule recovery from stuck state after timeout
            asyncio.create_task(reset_stuck_playlist(proxy))

        return await handle_stuck_playlist(proxy)

    # Serve cached playlist if in stuck state
    if proxy.is_playlist_stuck:
        return await handle_stuck_playlist(proxy)
    
    # Check for segment failure condition
    if proxy.segment_failure_enabled and proxy.segment_count % proxy.segment_failure_frequency == 0:
        await log_message("Triggering segment failure.")
        return await handle_segment_failure(proxy)

    # Check for packet drop condition
    if proxy.drop_packets_enabled and proxy.segment_count % proxy.drop_after_playlists == 0:
        await log_message("Triggering segment drop simulation.")
        await handle_packet_drop(proxy)

    return None


# Proxy request function
async def proxy_request(proxy: ProxySettings, request: Request):
    if proxy.is_dropping_playlist:
        await log_message("Simulating connection timeout by dropping the playlist request.")
        await asyncio.sleep(60)
        return Response(content="Connection timeout simulated.", status_code=504)

    target_url = proxy.target_url

    # Centralized segment logic handler
    if ".m3u8" in proxy.path or ".mpd" in proxy.path:
        segment_response = await handle_segment_logic(proxy)
        if segment_response:
            return segment_response
        
    # Check for audio delay condition
    if proxy.audio_delay_enabled and "audio" in proxy.path:
        should_continue = await handle_audio_delay(proxy)
        if should_continue is None:
            # Do not make the GET request, return a 404 (Not Found) response
            return Response(content="", status_code=404)

    async with httpx.AsyncClient() as client:
        headers = {key: value for key, value in request.headers.items() if key.lower() != 'host'}
        async with client.stream(request.method, target_url, headers=headers, content=await request.body()) as response:
            return Response(
                content=await response.aread(),
                headers=dict(response.headers),
                status_code=response.status_code
            )


class GenerateUrlRequest(BaseModel):
    url: str
    simulate: str
    segments: Optional[int] = None
    delay: Optional[int] = None
    playlistStickThreshold: Optional[int] = None
    stuckRecoveryTimeout: Optional[int] = None
    dropAfterPlaylists: Optional[int] = None
    segmentFailureFrequency: Optional[int] = None
    segmentFailureCode: Optional[int] = None


@app.post("/generateurl")
async def generateurl(body: GenerateUrlRequest):
    params = body.dict()
    dict_str = str(sorted(params.items()))
    hash = hashlib.sha256(dict_str.encode()).hexdigest()

    proxies[hash] = ProxySettings(params)

    generated_url = f"{SITE}/stream/uid_{hash}"

    return {"generatedUrl": generated_url}


@app.api_route("/stream/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
async def stream(request: Request, path: str):
    uid = ProxySettings.get_uid(request.url.path, 'uid')
    print("uid", uid)
    if uid in proxies.keys():
        proxy = proxies[uid]
        proxy.update_url(request)
    else:
        await log_message('Error: Proxy server not generated')
        raise HTTPException(status_code=400, detail="Bad request")

    if not proxy.session_started and (".m3u8" in request.url.path or ".mpd" in request.url.path):
        await log_message(f"Session start detected: {request.url.path}")
        proxy.session_started = True
    return await proxy_request(proxy, request)


# WebSocket endpoint for log streaming
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    await log_message("Client connected to WebSocket for logs.")
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        clients.remove(websocket)
        await log_message("Client disconnected from WebSocket.")
