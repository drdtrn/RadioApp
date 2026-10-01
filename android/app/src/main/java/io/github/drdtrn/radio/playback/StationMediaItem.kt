package io.github.drdtrn.radio.playback

import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.MimeTypes
import io.github.drdtrn.radio.data.Station

/**
 * The MediaItem the player streams for [station]. The station name goes in
 * both `title` and `station`: PlaybackService later swaps `title` for the
 * stream's song title and keeps `station` as the stable name.
 */
fun Station.toMediaItem(): MediaItem = MediaItem.Builder()
    .setMediaId(stationuuid)
    .setUri(url)
    .apply { if (hls) setMimeType(MimeTypes.APPLICATION_M3U8) }
    .setMediaMetadata(
        MediaMetadata.Builder()
            .setTitle(name)
            .setStation(name)
            .setMediaType(MediaMetadata.MEDIA_TYPE_RADIO_STATION)
            .setIsBrowsable(false)
            .setIsPlayable(true)
            .build()
    )
    .build()

/** The station name a MediaItem from [toMediaItem] was built for. */
val MediaItem.stationName: String
    get() = (mediaMetadata.station ?: mediaMetadata.title)?.toString().orEmpty()
