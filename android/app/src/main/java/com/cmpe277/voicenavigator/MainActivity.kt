package com.cmpe277.voicenavigator

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.cmpe277.voicenavigator.ui.VoiceNavigatorApp
import com.cmpe277.voicenavigator.ui.theme.VoiceNavigatorTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            VoiceNavigatorTheme {
                VoiceNavigatorApp()
            }
        }
    }
}
