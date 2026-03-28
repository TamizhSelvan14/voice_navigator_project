package com.cmpe277.voicenavigator.network

import com.cmpe277.voicenavigator.model.AskRequest
import com.cmpe277.voicenavigator.model.AskResponse
import retrofit2.http.Body
import retrofit2.http.POST

interface ApiService {
    @POST("ask")
    suspend fun ask(@Body request: AskRequest): AskResponse
}
