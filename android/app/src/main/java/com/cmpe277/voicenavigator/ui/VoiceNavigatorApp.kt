package com.cmpe277.voicenavigator.ui

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun VoiceNavigatorApp(viewModel: VoiceNavigatorViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    var tts by remember { mutableStateOf<TextToSpeech?>(null) }

    DisposableEffect(Unit) {
        val speaker = TextToSpeech(context) { }
        tts = speaker
        onDispose {
            speaker.stop()
            speaker.shutdown()
        }
    }

    val speechPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { }

    val speechLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val matches = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            val spokenText = matches?.firstOrNull().orEmpty()
            if (spokenText.isNotBlank()) {
                viewModel.updateQuestion(spokenText)
            }
        }
    }

    fun launchSpeechInput() {
        val permission = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
        if (permission != PackageManager.PERMISSION_GRANTED) {
            speechPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            return
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak your question")
        }
        speechLauncher.launch(intent)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "Voice Navigator",
            style = MaterialTheme.typography.headlineMedium,
        )

        Text(
            text = "Ask grounded questions from the DMV handbook or ESG food-security reports.",
            style = MaterialTheme.typography.bodyMedium,
        )

        ModeSelector(
            selectedMode = state.mode,
            onModeSelected = viewModel::updateMode,
        )

        OutlinedTextField(
            value = state.question,
            onValueChange = viewModel::updateQuestion,
            label = { Text("Question") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 3,
        )

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = { launchSpeechInput() }) {
                Text("Use Voice")
            }
            Button(onClick = { viewModel.askQuestion() }) {
                Text("Ask")
            }
        }

        when {
            state.isLoading -> CircularProgressIndicator()
            state.error != null -> ErrorCard(message = state.error ?: "Unknown error")
            state.response != null -> ResultCard(
                response = state.response!!,
                onSpeak = { tts?.speak(it, TextToSpeech.QUEUE_FLUSH, null, "voice_navigator_answer") },
            )
        }
    }
}

@Composable
private fun ModeSelector(selectedMode: String, onModeSelected: (String) -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text("Mode", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            listOf("DMV", "ESG").forEach { mode ->
                Row {
                    RadioButton(
                        selected = selectedMode == mode,
                        onClick = { onModeSelected(mode) }
                    )
                    Text(text = mode, modifier = Modifier.padding(top = 12.dp))
                }
            }
        }
    }
}

@Composable
private fun ErrorCard(message: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text("Error", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(4.dp))
            Text(message)
        }
    }
}

@Composable
private fun ResultCard(response: com.cmpe277.voicenavigator.model.AskResponse, onSpeak: (String) -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Answer", style = MaterialTheme.typography.titleMedium)
            Text(response.answer)
            OutlinedButton(onClick = { onSpeak(response.answer) }) {
                Text("Read Answer")
            }
            Text("Sources", style = MaterialTheme.typography.titleMedium)
            response.citations.forEach { citation ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Text("${citation.source} | page ${citation.page}")
                        Text(citation.preview)
                    }
                }
            }
        }
    }
}
