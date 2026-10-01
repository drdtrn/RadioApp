package io.github.drdtrn.radio

import android.media.AudioManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import io.github.drdtrn.radio.ui.RadioScreen
import io.github.drdtrn.radio.ui.RadioTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        // The hardware volume keys adjust media volume even before anything plays.
        volumeControlStream = AudioManager.STREAM_MUSIC
        setContent {
            RadioTheme {
                // Back and Home leave the radio playing; Close quits for real,
                // removing the app from the recent apps too.
                RadioScreen(onClose = ::finishAndRemoveTask)
            }
        }
    }
}
