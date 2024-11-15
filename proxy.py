from fastapi import Request
import re

class ProxySettings:
    def __init__(self, settings: dict):
        # Session and segment tracking
        self.session_started = False
        self.segment_count = 1

        # Target server for proxying requests
        self.target_server = settings.get('url', "")

        # Audio delay settings
        self.audio_delay_enabled = settings.get('simulate', 'delayAudio') == 'delayAudio'
        self.delay_after_segments = settings.get('segments', 0)
        self.delay_duration = settings.get('delay', 0)
        self.is_delaying = False

        # Stuck playlist simulation
        self.is_stuck_playlist_enabled = settings.get('simulate') == 'stuckPlaylist'
        self.playlist_stick_threshold = settings.get('playlistStickThreshold', 0)
        self.stuck_recovery_timeout = settings.get('stuckRecoveryTimeout', 0)
        self.playlist_request_count = 0
        self.cached_playlist_content = None
        self.is_playlist_stuck = False

        # Packet drop simulation
        self.drop_packets_enabled = settings.get('simulate') == 'dropPacket'
        self.drop_after_playlists = settings.get('dropAfterPlaylists', 0)
        self.is_dropping_packets = False

        # Segment failure simulation
        self.segment_failure_enabled = settings.get('simulate') == 'segmentFailure'
        self.segment_failure_frequency = settings.get('segmentFailureFrequency', 0)
        self.segment_failure_code = settings.get('segmentFailureCode', 404)

        self.target_url = ''
        self.path = ''
        self.query = ''

    @staticmethod
    def get_uid(url, key):
        if f'{key}_' in url:
            path_parts = url.split('/')
            for part in path_parts:
                if part.startswith(f'{key}_'):
                    return part.split('_')[1]
        return None

    def update_url(self, request: Request):
        if self.target_url == '':
            pattern = r'/stream/uid_[^/]+/'
            self.path = "/" + re.sub(pattern, '', request.url.path, count=1)
            self.query = request.url.query
            self.target_url = f"{self.target_server}{self.path}?{self.query}"