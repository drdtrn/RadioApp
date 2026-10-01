@file:androidx.annotation.OptIn(UnstableApi::class)

package io.github.drdtrn.radio.playback

import android.app.PendingIntent
import android.content.Intent
import android.os.Bundle
import android.os.SystemClock
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.Metadata
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.extractor.metadata.icy.IcyInfo
import androidx.media3.extractor.metadata.id3.TextInformationFrame
import androidx.media3.session.CommandButton
import androidx.media3.session.DefaultMediaNotificationProvider
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import androidx.media3.session.SessionCommand
import androidx.media3.session.SessionResult
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import io.github.drdtrn.radio.MainActivity
import io.github.drdtrn.radio.R

/**
 * Owns the player and keeps it running while the app is in the background,
 * with the usual media notification and lock-screen controls. The UI drives
 * it through a MediaController (see RadioViewModel).
 *
 * Leaving the app (Back, Home) keeps the radio playing; closing it (the Close
 * button in the app or the notification, or swiping it out of the recent
 * apps) stops playback and the service.
 */
class PlaybackService : MediaSessionService() {
    private var session: MediaSession? = null
    private var lastReconnectAt = 0L

    override fun onCreate() {
        super.onCreate()
        val exoPlayer = ExoPlayer.Builder(this)
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC)
                    .build(),
                /* handleAudioFocus = */ true, // pause for calls and other players
            )
            .setHandleAudioBecomingNoisy(true) // pause when headphones are unplugged
            .setWakeMode(C.WAKE_MODE_NETWORK) // keep Wi-Fi and CPU awake with the screen off
            .build()
        // Audio only, like mpv --no-video: don't fetch the video of TV-style HLS streams.
        exoPlayer.trackSelectionParameters = exoPlayer.trackSelectionParameters.buildUpon()
            .setTrackTypeDisabled(C.TRACK_TYPE_VIDEO, true)
            .build()
        exoPlayer.addListener(StreamListener(exoPlayer))

        val openApp = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val closeButton = CommandButton.Builder(CommandButton.ICON_UNDEFINED)
            .setCustomIconResId(R.drawable.ic_power)
            .setDisplayName(getString(R.string.close_app))
            .setSessionCommand(CLOSE_COMMAND)
            .setSlots(CommandButton.SLOT_FORWARD) // right after play/pause
            .build()
        session = MediaSession.Builder(this, LiveRadioPlayer(exoPlayer))
            .setSessionActivity(openApp)
            .setCallback(SessionCallback())
            .setMediaButtonPreferences(listOf(closeButton))
            .build()
        setMediaNotificationProvider(
            DefaultMediaNotificationProvider.Builder(this).build().apply {
                setSmallIcon(R.drawable.ic_notification)
            }
        )
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? = session

    /** Swiping the app out of the recent apps closes it, even while playing. */
    override fun onTaskRemoved(rootIntent: Intent?) = close()

    /** Stop the radio and remove the notification, then let the service end. */
    private fun close() {
        session?.player?.run {
            stop()
            clearMediaItems() // an empty player has no notification, even if the UI is still bound
        }
        pauseAllPlayersAndStopSelf()
    }

    override fun onDestroy() {
        session?.run {
            player.release()
            release()
        }
        session = null
        super.onDestroy()
    }

    /** Song titles from the stream's metadata, and reconnecting dropped streams. */
    private inner class StreamListener(private val player: ExoPlayer) : Player.Listener {
        override fun onMetadata(metadata: Metadata) {
            val streamTitle = metadata.streamTitle() ?: return
            val item = player.currentMediaItem ?: return
            val stationName = item.stationName
            val song = trackTitle(stationName, item.localConfiguration?.uri?.toString().orEmpty(), streamTitle)
            val title = song ?: stationName
            if (item.mediaMetadata.title?.toString() == title) return
            // Updating the item's metadata (rather than relying on the stream
            // metadata ExoPlayer merges in) is what reaches the notification
            // and lock screen. Same URI, so playback carries on uninterrupted.
            val updated = item.buildUpon()
                .setMediaMetadata(
                    item.mediaMetadata.buildUpon()
                        .setTitle(title)
                        .setArtist(if (song != null) stationName else null)
                        .build()
                )
                .build()
            player.replaceMediaItem(player.currentMediaItemIndex, updated)
        }

        override fun onPlaybackStateChanged(playbackState: Int) {
            // A live stream never ends by itself: the server closed the
            // connection (e.g. after a network switch). Rejoin it, but not in
            // a tight loop if the server keeps hanging up straight away.
            if (playbackState != Player.STATE_ENDED || !player.playWhenReady) return
            val now = SystemClock.elapsedRealtime()
            if (now - lastReconnectAt < RECONNECT_MIN_INTERVAL_MS) return
            lastReconnectAt = now
            player.seekToDefaultPosition() // from ENDED this reloads the stream
        }
    }

    private inner class SessionCallback : MediaSession.Callback {
        override fun onConnect(
            session: MediaSession,
            controller: MediaSession.ControllerInfo,
        ): MediaSession.ConnectionResult {
            // Start from the defaults the builder picks: untrusted apps only get
            // read-only commands, and can't close the app.
            val (sessionCommands, playerCommands) = if (controller.isTrusted) {
                MediaSession.ConnectionResult.DEFAULT_SESSION_COMMANDS.buildUpon().add(CLOSE_COMMAND).build() to
                    MediaSession.ConnectionResult.DEFAULT_PLAYER_COMMANDS
            } else {
                MediaSession.ConnectionResult.DEFAULT_UNTRUSTED_SESSION_COMMANDS to
                    MediaSession.ConnectionResult.DEFAULT_UNTRUSTED_PLAYER_COMMANDS
            }
            return MediaSession.ConnectionResult.AcceptedResultBuilder(session, controller)
                .setAvailableSessionCommands(sessionCommands)
                .setAvailablePlayerCommands(
                    // Live radio has no previous/next track, so keep those buttons off the notification.
                    playerCommands.buildUpon()
                        .removeAll(
                            Player.COMMAND_SEEK_TO_PREVIOUS,
                            Player.COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM,
                            Player.COMMAND_SEEK_TO_NEXT,
                            Player.COMMAND_SEEK_TO_NEXT_MEDIA_ITEM,
                        )
                        .build()
                )
                .build()
        }

        override fun onCustomCommand(
            session: MediaSession,
            controller: MediaSession.ControllerInfo,
            customCommand: SessionCommand,
            args: Bundle,
        ): ListenableFuture<SessionResult> {
            if (customCommand.customAction != CLOSE_COMMAND.customAction) {
                return super.onCustomCommand(session, controller, customCommand, args)
            }
            close()
            return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
        }
    }

    companion object {
        /** Sent by the app's Close button and the notification's: stop playback and quit. */
        val CLOSE_COMMAND = SessionCommand("io.github.drdtrn.radio.CLOSE", Bundle.EMPTY)

        private const val RECONNECT_MIN_INTERVAL_MS = 10_000L
    }
}

/**
 * The "now playing" text in a metadata update: Icecast/Shoutcast streams send
 * an ICY StreamTitle, HLS streams ID3 title/artist frames.
 */
private fun Metadata.streamTitle(): String? {
    var id3Title: String? = null
    var id3Artist: String? = null
    for (index in 0 until length()) {
        when (val entry = get(index)) {
            is IcyInfo -> return entry.title
            is TextInformationFrame -> when (entry.id) {
                "TIT2" -> id3Title = entry.values.firstOrNull()
                "TPE1" -> id3Artist = entry.values.firstOrNull()
            }
        }
    }
    return when {
        id3Title.isNullOrBlank() -> null
        id3Artist.isNullOrBlank() -> id3Title
        else -> "$id3Artist - $id3Title"
    }
}
