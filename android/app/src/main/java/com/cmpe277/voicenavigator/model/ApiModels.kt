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

data class DataPointDto(
    val label: String,
    val value: Double,
)

data class ChartSeriesDto(
    val name: String,
    val data_points: List<DataPointDto>,
)

data class ChartDataDto(
    val title: String,
    val x_label: String,
    val y_label: String,
    val type: String,
    val series: List<ChartSeriesDto>,
)

data class AskResponse(
    val answer: String,
    val mode: String,
    val citations: List<CitationDto>,
    val used_llm: Boolean,
    val chart_data: ChartDataDto? = null,
)
