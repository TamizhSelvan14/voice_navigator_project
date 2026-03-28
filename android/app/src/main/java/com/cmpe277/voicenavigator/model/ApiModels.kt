package com.cmpe277.voicenavigator.model

data class AskRequest(
    val question: String,
    val mode: String,
    val top_k: Int? = null,
)

data class CitationDto(
    val source: String,
    val page: Int,
    val domain: String,
    val score: Double,
    val preview: String,
)

data class AskResponse(
    val answer: String,
    val mode: String,
    val citations: List<CitationDto>,
    val used_llm: Boolean,
)
