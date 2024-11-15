from fastapi import FastAPI, Request, Response, HTTPException, WebSocket
import httpx
import asyncio
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import hashlib
from proxy import ProxySettings
from typing import List, Optional

app = FastAPI()

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


# Function to handle packet drop logic for playlist requests
async def handle_packet_drop_for_playlists(proxy: ProxySettings):
    if proxy.drop_packets_enabled:
        await log_message("Dropping all playlist requests to simulate connection timeout.")
        proxy.is_dropping_packets = True


# Function to handle stuck playlist logic
async def handle_stuck_playlist(proxy: ProxySettings):
    proxy.playlist_request_count += 1
    await log_message(f"Playlist request count: {proxy.playlist_request_count}")

    if proxy.drop_packets_enabled and proxy.playlist_request_count > proxy.drop_after_playlists and not proxy.is_dropping_packets:
        await handle_packet_drop_for_playlists(proxy)

    if proxy.is_stuck_playlist_enabled and proxy.playlist_request_count > proxy.playlist_stick_threshold:
        proxy.is_playlist_stuck = True

        if proxy.cached_playlist_content is not None:
            await log_message("Serving cached playlist to simulate stuck playlist.")
            return Response(
                content=proxy.cached_playlist_content,
                media_type="application/vnd.apple.mpegurl" if ".m3u8" in proxy.path else "application/dash+xml"
            )

        if proxy.cached_playlist_content is None:
            await log_message("Stuck playlist detected. Starting recovery timer...")
            asyncio.create_task(reset_stuck_playlist(proxy))

    return None


# Function to reset the stuck playlist state
async def reset_stuck_playlist(proxy: ProxySettings):
    await asyncio.sleep(proxy.stuck_recovery_timeout)
    if proxy.is_playlist_stuck:
        await log_message("Recovering from stuck playlist state after timeout.")
        proxy.is_playlist_stuck = False
        proxy.playlist_request_count = 0
        proxy.cached_playlist_content = None


# Function to handle audio delay logic
async def handle_audio_delay(proxy: ProxySettings):
    if proxy.session_started and "audio" in proxy.path:
        proxy.segment_count += 1
        await log_message(f"Received {proxy.segment_count} audio segment request")

        if proxy.segment_count > proxy.delay_after_segments and not proxy.is_delaying:
            is_delaying = True
            await log_message(f"Delaying response for {proxy.delay_duration} seconds...")
            await asyncio.sleep(proxy.delay_duration)
            proxy.is_delaying = False
            proxy.segment_count = 0
            await log_message("Resuming normal response streaming...")


# Function to handle segment failure logic
async def handle_segment_failure(proxy: ProxySettings):
    if proxy.segment_failure_enabled and (".m3u8" in proxy.path or ".mpd" in proxy.path):
        proxy.segment_count += 1
        await log_message(f"Segment request count: {proxy.segment_count}")

        # Fail every nth segment request
        if proxy.segment_count % (proxy.segment_failure_frequency + 1) == 0:
            await log_message(f"Failing segment request with error code {proxy.segment_failure_code}")
            return Response(
                content=f"Simulated failure with error code {proxy.segment_failure_code}",
                status_code=proxy.segment_failure_code
            )

    return None


# Proxy request function with bandwidth limiting
async def proxy_request(proxy: ProxySettings, request: Request):
    if proxy.is_dropping_packets:
        await log_message("Simulating connection timeout by dropping the playlist request.")
        await asyncio.sleep(60)
        return Response(content="Connection timeout simulated.", status_code=504)

    target_url = proxy.target_url

    # Handle stuck playlist logic
    if ".m3u8" in proxy.path or ".mpd" in proxy.path:
        stuck_response = await handle_stuck_playlist(proxy)
        if stuck_response:
            return stuck_response

    # Handle segment failure logic
    segment_failure_response = await handle_segment_failure(proxy)
    if segment_failure_response:
        return segment_failure_response

    # Proxy the request to the target server
    async with httpx.AsyncClient() as client:
        headers = {key: value for key, value in request.headers.items() if key.lower() != 'host'}
        async with client.stream(
                request.method,
                target_url,
                headers=headers,
                content=await request.body()
        ) as response:

            # Cache playlist content if stuck playlist condition is triggered
            if proxy.is_playlist_stuck and proxy.cached_playlist_content is None:
                proxy.cached_playlist_content = await response.aread()
                await log_message("Cached playlist content for stuck simulation.")

            # Handle audio delay if enabled
            if proxy.audio_delay_enabled:
                await handle_audio_delay(proxy)

            # Stream the response back to the client
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


@app.api_route("/generateurl", methods=["POST"])
async def generateurl(request: Request, body: GenerateUrlRequest):
    url = body.url
    simulate = body.simulate
    segments = body.segments
    delay = body.delay
    playlistStickThreshold = body.playlistStickThreshold
    stuck_recovery_timeout = body.stuckRecoveryTimeout
    drop_after_playlists = body.dropAfterPlaylists
    segment_failure_frequency = body.segmentFailureFrequency
    segment_failure_code = body.segmentFailureCode

    params = {
        "url": url,
        "simulate": simulate,
        "segments": segments,
        "delay": delay,
        "playlistStickThreshold": playlistStickThreshold,
        "stuckRecoveryTimeout": stuck_recovery_timeout,
        "dropAfterPlaylists": drop_after_playlists,
        "segmentFailureFrequency": segment_failure_frequency,
        "segmentFailureCode": segment_failure_code
    }

    dict_str = str(sorted(params.items()))
    hash = hashlib.sha256(dict_str.encode()).hexdigest()

    proxies[hash] = ProxySettings(params)

    generated_url = f"localhost:8000/stream/uid_{hash}"

    return {"generatedUrl": generated_url}


@app.api_route("/stream/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
async def stream(request: Request, path: str):
    uid = ProxySettings.get_uid(request.url.path, 'uid')

    if uid in proxies.keys():
        proxy = proxies[uid]
        proxy.update_url(request)
    else:
        await log_message('Error : proxy server not generated')
        raise HTTPException(status_code=400, detail="Bad request")

    if not proxy.session_started and (".m3u8" in request.url.path or ".mpd" in request.url.path):
        await log_message(f'Session start detected:{request.url.path}')
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