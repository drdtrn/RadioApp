package io.github.drdtrn.radio.ui

import android.app.Application
import android.content.ComponentName
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import io.github.drdtrn.radio.R
import io.github.drdtrn.radio.data.COUNTRIES
import io.github.drdtrn.radio.data.Settings
import io.github.drdtrn.radio.data.SortOrder
import io.github.drdtrn.radio.data.Station
import io.github.drdtrn.radio.data.StationRepository
import io.github.drdtrn.radio.data.StationsResult
import io.github.drdtrn.radio.playback.PlaybackService
import io.github.drdtrn.radio.playback.stationName
import io.github.drdtrn.radio.playback.toMediaItem
import io.github.drdtrn.radio.playback.trackTitle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** What the now-playing bar shows. */
data class NowPlaying(
    val stationId: String,
    val stationName: String,
    val trackTitle: String?,
    val isPaused: Boolean,
    val isBuffering: Boolean,
)

data class RadioUiState(
    val stations: List<Station> = emptyList(),
    val isLoading: Boolean = false,
    /** "N stations · updated 1 Oct 20:56", or why loading failed. */
    val status: String? = null,
    val loadFailed: Boolean = false,
    val queries: Map<String, String> = emptyMap(),
    val sortOrder: SortOrder = SortOrder.NAME,
    /** Stations whose stream failed to play (shown with ⚠). */
    val failedStationIds: Set<String> = emptySet(),
    val volume: Int = 100,
    val nowPlaying: NowPlaying? = null,
)

class RadioViewModel(application: Application) : AndroidViewModel(application) {
    private val settings = Settings(application)
    private val repository = StationRepository(
        cacheFile = File(application.cacheDir, "stations.json"),
        countryCodes = COUNTRIES.map { it.code },
    )

    private val _state = MutableStateFlow(
        RadioUiState(volume = settings.volume, sortOrder = settings.sortOrder)
    )
    val state: StateFlow<RadioUiState> = _state.asStateFlow()

    /** Tab to open on, i.e. the one the user last had open. */
    val initialTab: Int = COUNTRIES.indexOfFirst { it.code == settings.lastTab }.coerceAtLeast(0)

    private var loadJob: Job? = null
    private var controller: MediaController? = null
    private val controllerFuture = MediaController.Builder(
        application,
        SessionToken(application, ComponentName(application, PlaybackService::class.java)),
    ).buildAsync()

    private val playerListener = object : Player.Listener {
        override fun onPlayerError(error: PlaybackException) {
            controller?.currentMediaItem?.let { markFailed(it.mediaId) }
        }

        override fun onEvents(player: Player, events: Player.Events) = syncNowPlaying(player)
    }

    init {
        controllerFuture.addListener({
            val connected = try {
                controllerFuture.get()
            } catch (_: Exception) {
                return@addListener // the service couldn't be bound; nothing to drive
            }
            controller = connected
            connected.volume = _state.value.volume / 100f
            connected.addListener(playerListener)
            // The service may already be playing (e.g. reopened from the notification).
            if (connected.playerError != null) connected.currentMediaItem?.let { markFailed(it.mediaId) }
            syncNowPlaying(connected)
        }, ContextCompat.getMainExecutor(application))
        loadStations(forceRefresh = false)
    }

    fun refresh() = loadStations(forceRefresh = true)

    private fun loadStations(forceRefresh: Boolean) {
        if (loadJob?.isActive == true) return // a load is already in flight
        _state.update { it.copy(isLoading = true) }
        loadJob = viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) { repository.getStations(forceRefresh) }
                _state.update {
                    it.copy(stations = result.stations, isLoading = false, loadFailed = false, status = statusLine(result))
                }
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                val reason = error.message ?: error.javaClass.simpleName
                _state.update {
                    it.copy(
                        isLoading = false,
                        loadFailed = true,
                        status = getApplication<Application>().getString(R.string.load_failed, reason),
                    )
                }
            }
        }
    }

    private fun statusLine(result: StationsResult): String {
        val app = getApplication<Application>()
        val count = app.resources.getQuantityString(R.plurals.station_count, result.stations.size, result.stations.size)
        val fetchedAt = result.cacheTimestamp ?: return count
        val updated = SimpleDateFormat("d MMM HH:mm", Locale.getDefault()).format(Date(fetchedAt))
        return app.getString(R.string.status_line, count, updated)
    }

    fun play(station: Station) {
        val player = controller ?: return
        _state.update { it.copy(failedStationIds = it.failedStationIds - station.stationuuid) }
        player.setMediaItem(station.toMediaItem())
        player.prepare()
        player.play()
    }

    fun togglePause() {
        val player = controller ?: return
        val item = player.currentMediaItem ?: return
        val playing = player.playWhenReady &&
            player.playbackState != Player.STATE_IDLE &&
            player.playbackState != Player.STATE_ENDED
        if (playing) {
            player.pause()
            return
        }
        // Resuming a failed station is a retry, which clears its warning.
        _state.update { it.copy(failedStationIds = it.failedStationIds - item.mediaId) }
        when (player.playbackState) {
            Player.STATE_IDLE -> player.prepare()
            Player.STATE_ENDED -> player.seekToDefaultPosition()
            Player.STATE_BUFFERING, Player.STATE_READY -> Unit // just paused
        }
        player.play()
    }

    fun setVolume(volume: Int) {
        val clamped = volume.coerceIn(0, 100)
        _state.update { it.copy(volume = clamped) }
        controller?.volume = clamped / 100f
        settings.volume = clamped
    }

    fun setQuery(countryCode: String, query: String) {
        _state.update { it.copy(queries = it.queries + (countryCode to query)) }
    }

    fun setSortOrder(order: SortOrder) {
        settings.sortOrder = order
        _state.update { it.copy(sortOrder = order) }
    }

    fun onTabSelected(index: Int) {
        settings.lastTab = COUNTRIES[index].code
    }

    private fun markFailed(stationId: String) {
        _state.update { it.copy(failedStationIds = it.failedStationIds + stationId) }
    }

    private fun syncNowPlaying(player: Player) {
        val item = player.currentMediaItem
        val nowPlaying = item?.let {
            val name = it.stationName
            NowPlaying(
                stationId = it.mediaId,
                stationName = name,
                trackTitle = trackTitle(name, "", player.mediaMetadata.title),
                isPaused = !player.playWhenReady,
                isBuffering = player.playWhenReady && player.playbackState == Player.STATE_BUFFERING,
            )
        }
        _state.update { it.copy(nowPlaying = nowPlaying) }
    }

    override fun onCleared() {
        controller?.removeListener(playerListener)
        MediaController.releaseFuture(controllerFuture)
        controller = null
    }
}
