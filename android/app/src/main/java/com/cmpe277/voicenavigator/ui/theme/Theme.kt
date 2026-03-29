package com.cmpe277.voicenavigator.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary              = Indigo600,
    onPrimary            = White,
    primaryContainer     = Indigo100,
    onPrimaryContainer   = Indigo900,
    secondary            = Sky600,
    onSecondary          = White,
    secondaryContainer   = Sky100,
    onSecondaryContainer = Sky900,
    tertiary             = Emerald500,
    onTertiary           = White,
    tertiaryContainer    = Emerald50,
    onTertiaryContainer  = Emerald900,
    error                = Rose500,
    onError              = White,
    errorContainer       = Rose100,
    onErrorContainer     = Rose900,
    background           = Slate50,
    onBackground         = Slate900,
    surface              = White,
    onSurface            = Slate900,
    surfaceVariant       = Slate100,
    onSurfaceVariant     = Slate600,
    outline              = Slate200,
    outlineVariant       = Slate100,
)

@Composable
fun VoiceNavigatorTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        content     = content,
    )
}
