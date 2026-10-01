package io.github.drdtrn.radio.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.displayCutout
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.layout.union
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import io.github.drdtrn.radio.R
import io.github.drdtrn.radio.data.COUNTRIES
import io.github.drdtrn.radio.data.Country
import io.github.drdtrn.radio.data.SortOrder
import io.github.drdtrn.radio.data.Station
import io.github.drdtrn.radio.data.stationsFor
import kotlin.math.roundToInt
import kotlinx.coroutines.launch

private val WIDE_LAYOUT_MIN_WIDTH = 600.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RadioScreen(viewModel: RadioViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val pagerState = rememberPagerState(initialPage = viewModel.initialTab) { COUNTRIES.size }
    val scope = rememberCoroutineScope()

    LaunchedEffect(pagerState.currentPage) { viewModel.onTabSelected(pagerState.currentPage) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(stringResource(R.string.app_name))
                        state.status?.let {
                            Text(
                                it,
                                style = MaterialTheme.typography.bodySmall,
                                color = if (state.loadFailed) {
                                    MaterialTheme.colorScheme.error
                                } else {
                                    MaterialTheme.colorScheme.onSurfaceVariant
                                },
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                },
                actions = {
                    SortMenu(state.sortOrder, viewModel::setSortOrder)
                    IconButton(onClick = viewModel::refresh, enabled = !state.isLoading) {
                        Icon(painterResource(R.drawable.ic_refresh), stringResource(R.string.refresh))
                    }
                },
            )
        },
        bottomBar = {
            NowPlayingBar(
                nowPlaying = state.nowPlaying,
                failed = state.nowPlaying?.stationId in state.failedStationIds,
                volume = state.volume,
                onTogglePause = viewModel::togglePause,
                onVolumeChange = viewModel::setVolume,
            )
        },
    ) { padding ->
        Column(
            Modifier
                .padding(padding)
                .consumeWindowInsets(padding)
                .imePadding()
        ) {
            PrimaryTabRow(selectedTabIndex = pagerState.currentPage) {
                COUNTRIES.forEachIndexed { index, country ->
                    Tab(
                        selected = pagerState.currentPage == index,
                        onClick = { scope.launch { pagerState.animateScrollToPage(index) } },
                        text = { Text(country.label) },
                    )
                }
            }
            HorizontalPager(state = pagerState, modifier = Modifier.weight(1f)) { page ->
                val country = COUNTRIES[page]
                CountryPage(
                    country = country,
                    state = state,
                    onQueryChange = { viewModel.setQuery(country.code, it) },
                    onPlay = viewModel::play,
                    onRefresh = viewModel::refresh,
                )
            }
        }
    }
}

@Composable
private fun SortMenu(current: SortOrder, onSelect: (SortOrder) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { expanded = true }) {
            Icon(painterResource(R.drawable.ic_sort), stringResource(R.string.sort))
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            listOf(
                SortOrder.NAME to R.string.sort_by_name,
                SortOrder.BITRATE to R.string.sort_by_bitrate,
            ).forEach { (order, label) ->
                DropdownMenuItem(
                    text = { Text(stringResource(label)) },
                    leadingIcon = { RadioButton(selected = order == current, onClick = null) },
                    onClick = {
                        onSelect(order)
                        expanded = false
                    },
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CountryPage(
    country: Country,
    state: RadioUiState,
    onQueryChange: (String) -> Unit,
    onPlay: (Station) -> Unit,
    onRefresh: () -> Unit,
) {
    val query = state.queries[country.code].orEmpty()
    val stations = remember(state.stations, country.code, query, state.sortOrder) {
        stationsFor(state.stations, country.code, query, state.sortOrder)
    }
    val focusManager = LocalFocusManager.current

    Column(Modifier.fillMaxSize()) {
        OutlinedTextField(
            value = query,
            onValueChange = onQueryChange,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            placeholder = { Text(stringResource(R.string.search_hint)) },
            leadingIcon = { Icon(painterResource(R.drawable.ic_search), contentDescription = null) },
            trailingIcon = {
                if (query.isNotEmpty()) {
                    IconButton(onClick = { onQueryChange("") }) {
                        Icon(painterResource(R.drawable.ic_close), stringResource(R.string.clear_search))
                    }
                }
            },
            singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { focusManager.clearFocus() }),
        )
        PullToRefreshBox(
            isRefreshing = state.isLoading && state.stations.isNotEmpty(),
            onRefresh = onRefresh,
            modifier = Modifier.weight(1f),
        ) {
            LazyColumn(Modifier.fillMaxSize()) {
                when {
                    stations.isNotEmpty() -> items(stations, key = { it.stationuuid }) { station ->
                        StationRow(
                            station = station,
                            playing = station.stationuuid == state.nowPlaying?.stationId,
                            failed = station.stationuuid in state.failedStationIds,
                            onClick = {
                                focusManager.clearFocus()
                                onPlay(station)
                            },
                        )
                    }
                    state.isLoading -> item { CenteredMessage(stringResource(R.string.loading_stations), progress = true) }
                    state.loadFailed && state.stations.isEmpty() -> item {
                        CenteredMessage(state.status.orEmpty()) {
                            Button(onClick = onRefresh) { Text(stringResource(R.string.retry)) }
                        }
                    }
                    query.isNotBlank() -> item { CenteredMessage(stringResource(R.string.no_matches, query.trim())) }
                    else -> item { CenteredMessage(stringResource(R.string.no_stations)) }
                }
            }
        }
    }
}

@Composable
private fun StationRow(station: Station, playing: Boolean, failed: Boolean, onClick: () -> Unit) {
    val accent = MaterialTheme.colorScheme.primary
    ListItem(
        modifier = Modifier.clickable(role = Role.Button, onClick = onClick),
        leadingContent = {
            val (icon, tint) = when {
                failed -> R.drawable.ic_warning to MaterialTheme.colorScheme.error
                playing -> R.drawable.ic_equalizer to accent
                else -> R.drawable.ic_radio to MaterialTheme.colorScheme.onSurfaceVariant
            }
            Icon(painterResource(icon), contentDescription = null, tint = tint)
        },
        headlineContent = {
            Text(
                station.name, // a failed stream gets the ⚠ icon instead of the desktop's "⚠ " prefix
                fontWeight = if (playing) FontWeight.Bold else null,
                color = if (playing) accent else MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                // Like the desktop app: Arabic names would otherwise hug the right edge.
                textAlign = TextAlign.Left,
            )
        },
        supportingContent = when {
            failed -> {
                { Text(stringResource(R.string.stream_failed_short), color = MaterialTheme.colorScheme.error) }
            }
            station.tags.isNotEmpty() -> {
                {
                    Text(
                        station.tags.joinToString(", "),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        textAlign = TextAlign.Left,
                    )
                }
            }
            else -> null
        },
        trailingContent = {
            Text(
                if (station.bitrate > 0) stringResource(R.string.bitrate_kbps, station.bitrate) else "—",
                style = MaterialTheme.typography.labelMedium,
            )
        },
        colors = ListItemDefaults.colors(
            containerColor = if (playing) {
                MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.5f)
            } else {
                MaterialTheme.colorScheme.surface
            },
        ),
    )
}

@Composable
private fun CenteredMessage(
    text: String,
    progress: Boolean = false,
    action: (@Composable () -> Unit)? = null,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 32.dp, vertical = 64.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        if (progress) CircularProgressIndicator()
        Text(text, textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.onSurfaceVariant)
        action?.invoke()
    }
}

@Composable
private fun NowPlayingBar(
    nowPlaying: NowPlaying?,
    failed: Boolean,
    volume: Int,
    onTogglePause: () -> Unit,
    onVolumeChange: (Int) -> Unit,
) {
    Surface(color = MaterialTheme.colorScheme.surfaceContainer, tonalElevation = 3.dp) {
        BoxWithConstraints(
            Modifier
                .windowInsetsPadding(
                    WindowInsets.systemBars.union(WindowInsets.displayCutout)
                        .only(WindowInsetsSides.Horizontal + WindowInsetsSides.Bottom)
                )
                .padding(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 4.dp)
        ) {
            if (maxWidth >= WIDE_LAYOUT_MIN_WIDTH) {
                // Landscape / tablets: one row, so the station list keeps its height.
                Row(verticalAlignment = Alignment.CenterVertically) {
                    NowPlayingInfo(nowPlaying, failed, onTogglePause, Modifier.weight(1f))
                    Spacer(Modifier.width(24.dp))
                    VolumeRow(volume, onVolumeChange, Modifier.width(320.dp))
                }
            } else {
                Column {
                    NowPlayingInfo(nowPlaying, failed, onTogglePause)
                    VolumeRow(volume, onVolumeChange)
                }
            }
        }
    }
}

@Composable
private fun NowPlayingInfo(
    nowPlaying: NowPlaying?,
    failed: Boolean,
    onTogglePause: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        val showPause = nowPlaying != null && !nowPlaying.isPaused && !failed
        Box(contentAlignment = Alignment.Center) {
            FilledIconButton(
                onClick = onTogglePause,
                enabled = nowPlaying != null,
                modifier = Modifier.size(52.dp),
            ) {
                Icon(
                    painterResource(if (showPause) R.drawable.ic_pause else R.drawable.ic_play),
                    stringResource(if (showPause) R.string.pause else R.string.play),
                )
            }
            if (nowPlaying?.isBuffering == true && !failed) {
                CircularProgressIndicator(Modifier.size(52.dp), strokeWidth = 2.dp)
            }
        }
        Spacer(Modifier.width(16.dp))
        Column(Modifier.weight(1f)) {
            Text(
                nowPlaying?.stationName ?: stringResource(R.string.nothing_playing),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                textAlign = TextAlign.Left,
                modifier = Modifier.fillMaxWidth(),
            )
            val subtitle = when {
                nowPlaying == null -> stringResource(R.string.idle_hint)
                failed -> stringResource(R.string.stream_failed)
                nowPlaying.isBuffering -> stringResource(R.string.connecting)
                nowPlaying.trackTitle != null -> nowPlaying.trackTitle
                nowPlaying.isPaused -> stringResource(R.string.paused)
                else -> stringResource(R.string.live)
            }
            Text(
                subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = if (failed) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                textAlign = TextAlign.Left,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun VolumeRow(volume: Int, onVolumeChange: (Int) -> Unit, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        Icon(
            painterResource(R.drawable.ic_volume),
            contentDescription = stringResource(R.string.volume),
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.width(12.dp))
        Slider(
            value = volume.toFloat(),
            onValueChange = { onVolumeChange(it.roundToInt()) },
            valueRange = 0f..100f,
            modifier = Modifier.weight(1f),
        )
        Text(
            stringResource(R.string.volume_percent, volume),
            style = MaterialTheme.typography.labelMedium,
            textAlign = TextAlign.End,
            modifier = Modifier.widthIn(min = 48.dp),
        )
    }
}
