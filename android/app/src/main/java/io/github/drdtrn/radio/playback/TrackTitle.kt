package io.github.drdtrn.radio.playback

/**
 * The song/programme title worth showing for a station, or null.
 *
 * Mirrors the desktop app's track_title(): a title that just repeats the
 * station name, or is the tail of the stream URL, tells the listener
 * nothing. Stations with an empty "Artist - Title" tag send " - ", which is
 * dropped too.
 */
fun trackTitle(stationName: String, stationUrl: String, mediaTitle: CharSequence?): String? {
    val title = mediaTitle?.toString()?.trim().orEmpty()
    if (title.none { it.isLetterOrDigit() }) return null
    if (title.equals(stationName.trim(), ignoreCase = true)) return null
    if (stationUrl.isNotEmpty() && stationUrl.trimEnd('/').endsWith(title)) return null
    return title
}
