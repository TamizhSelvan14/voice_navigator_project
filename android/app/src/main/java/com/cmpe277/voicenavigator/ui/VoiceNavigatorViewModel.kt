package com.cmpe277.voicenavigator.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cmpe277.voicenavigator.data.VoiceNavigatorRepository
import com.cmpe277.voicenavigator.model.AskResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class VoiceNavigatorViewModel : ViewModel() {
    private val repository = VoiceNavigatorRepository()

    private val _uiState = MutableStateFlow(VoiceNavigatorUiState())
    val uiState: StateFlow<VoiceNavigatorUiState> = _uiState.asStateFlow()

    fun updateQuestion(value: String) {
        _uiState.value = _uiState.value.copy(question = value)
    }

    fun updateMode(value: String) {
        _uiState.value = _uiState.value.copy(mode = value)
    }

    fun askQuestion() {
        val current = _uiState.value
        if (current.question.isBlank()) return

        viewModelScope.launch {
            _uiState.value = current.copy(isLoading = true, error = null)
            runCatching {
                repository.ask(current.question.trim(), current.mode)
            }.onSuccess { response ->
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    response = response,
                    error = null,
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = throwable.message ?: "Unknown error",
                )
            }
        }
    }
}

data class VoiceNavigatorUiState(
    val mode: String = "DMV",
    val question: String = "",
    val isLoading: Boolean = false,
    val response: AskResponse? = null,
    val error: String? = null,
)
