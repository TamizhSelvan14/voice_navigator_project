package com.cmpe277.voicenavigator.data

import com.cmpe277.voicenavigator.model.AskRequest
import com.cmpe277.voicenavigator.model.AskResponse
import com.cmpe277.voicenavigator.network.ApiClient

class VoiceNavigatorRepository {
    suspend fun ask(question: String, mode: String): AskResponse {
        return ApiClient.apiService.ask(
            AskRequest(
                question = question,
                mode = mode,
                top_k = 4,
            )
        )
    }
}
