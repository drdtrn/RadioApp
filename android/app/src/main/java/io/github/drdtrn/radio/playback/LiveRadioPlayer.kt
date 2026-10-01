@file:androidx.annotation.OptIn(UnstableApi::class)

package io.github.drdtrn.radio.playback

import androidx.media3.common.ForwardingPlayer
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi

/**
 * Makes pause/resume behave like a radio: resuming jumps back to the live
 * broadcast instead of playing audio that was buffered before the pause
 * (from a connection the server has likely dropped since).
 *
 * Every play/pause path (the app, the notification, the lock screen,
 * headset buttons) goes through the session's player, i.e. through here.
 */
class LiveRadioPlayer(player: Player) : ForwardingPlayer(player) {
    private var pausedByUser = false

    init {
        player.addListener(object : Player.Listener {
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                pausedByUser = false // a new station starts fresh anyway
            }
        })
    }

    override fun pause() {
        super.pause()
        pausedByUser = true
    }

    override fun play() {
        if (pausedByUser && playbackState != STATE_IDLE) {
            seekToDefaultPosition() // reconnects to the live edge
        }
        pausedByUser = false
        super.play()
    }
}
