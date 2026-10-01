package io.github.drdtrn.radio.playback

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class TrackTitleTest {
    private val name = "Radio Kosova"
    private val url = "http://stream.example/tarateel"

    @Test
    fun showsARealTitle() {
        assertEquals("Artist - Song", trackTitle(name, url, "  Artist - Song "))
    }

    @Test
    fun hidesMissingBlankAndPunctuationOnlyTitles() {
        assertNull(trackTitle(name, url, null))
        assertNull(trackTitle(name, url, ""))
        assertNull(trackTitle(name, url, " - "))
    }

    @Test
    fun hidesTheStationNameAndTheUrlFallback() {
        assertNull(trackTitle(name, url, "radio kosova"))
        assertNull(trackTitle(name, url, "tarateel"))
        assertEquals("tarateel", trackTitle(name, "", "tarateel"))
    }
}
