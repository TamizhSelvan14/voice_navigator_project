package com.cmpe277.voicenavigator.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cmpe277.voicenavigator.model.ChartDataDto
import com.cmpe277.voicenavigator.model.ChartSeriesDto

// Series colors — vivid, ordered by contrast
private val chartColors = listOf(
    Color(0xFF4F46E5), // Indigo
    Color(0xFFEA4335), // Red
    Color(0xFF10B981), // Emerald
    Color(0xFFF59E0B), // Amber
    Color(0xFF0EA5E9), // Sky
    Color(0xFFEC4899), // Pink
)

// ─────────────────────────────────────────────────────────────────────────────
// Public entry point
// ─────────────────────────────────────────────────────────────────────────────

@Composable
fun ChartCard(chartData: ChartDataDto) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Header
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.primaryContainer,
                ) {
                    Icon(
                        imageVector = when (chartData.type) {
                    "bar", "pie" -> Icons.Default.BarChart
                    else         -> Icons.Default.ShowChart
                },
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier
                            .padding(6.dp)
                            .size(16.dp),
                    )
                }
                Text(
                    chartData.title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

            when (chartData.type) {
                "pie"  -> PieChart(chartData.series)
                "bar"  -> BarChart(chartData.series)
                else   -> LineChart(chartData.series)
            }

            ChartLegend(chartData.series)
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Line chart with gradient area fill
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun LineChart(series: List<ChartSeriesDto>) {
    if (series.isEmpty()) return

    val allLabels  = series.flatMap { it.data_points.map { p -> p.label } }.distinct().sorted()
    val allValues  = series.flatMap { it.data_points.map { p -> p.value } }
    if (allLabels.isEmpty() || allValues.isEmpty()) return

    val minVal     = allValues.min()
    val maxVal     = allValues.max()
    val valRange   = if (maxVal - minVal < 0.001) 1.0 else maxVal - minVal
    val labelCount = allLabels.size
    val labelIndex = allLabels.withIndex().associate { (i, l) -> l to i }

    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(240.dp)
            .padding(start = 44.dp, end = 12.dp, top = 10.dp, bottom = 30.dp)
    ) {
        val w = size.width
        val h = size.height

        // ── Horizontal grid lines (5 divisions) ──────────────────────────
        for (i in 0..4) {
            val y = h - h * i / 4f
            drawLine(
                color = Color(0xFFE2E8F0),
                start = Offset(0f, y),
                end = Offset(w, y),
                strokeWidth = 1.dp.toPx(),
            )
            // Y-axis label
            val v = minVal + valRange * i / 4
            drawContext.canvas.nativeCanvas.drawText(
                formatNumber(v),
                -6.dp.toPx(),
                y + 4.dp.toPx(),
                android.graphics.Paint().apply {
                    textSize  = 9.dp.toPx()
                    color     = android.graphics.Color.parseColor("#94A3B8")
                    textAlign = android.graphics.Paint.Align.RIGHT
                }
            )
        }

        // ── X-axis labels ─────────────────────────────────────────────────
        val xStep = maxOf(1, labelCount / 5)
        for (i in allLabels.indices step xStep) {
            val x = if (labelCount <= 1) w / 2 else w * i.toFloat() / (labelCount - 1)
            drawContext.canvas.nativeCanvas.drawText(
                allLabels[i],
                x,
                h + 18.dp.toPx(),
                android.graphics.Paint().apply {
                    textSize  = 9.dp.toPx()
                    color     = android.graphics.Color.parseColor("#94A3B8")
                    textAlign = android.graphics.Paint.Align.CENTER
                }
            )
        }

        // ── Series: area fill + line + dots ──────────────────────────────
        series.forEachIndexed { idx, s ->
            val color  = chartColors[idx % chartColors.size]
            val sorted = s.data_points.sortedBy { it.label }
            if (sorted.size < 2) return@forEachIndexed

            fun xOf(pt: com.cmpe277.voicenavigator.model.DataPointDto): Float {
                val xi = labelIndex[pt.label] ?: 0
                return if (labelCount <= 1) w / 2 else w * xi.toFloat() / (labelCount - 1)
            }
            fun yOf(pt: com.cmpe277.voicenavigator.model.DataPointDto): Float =
                h - h * ((pt.value - minVal) / valRange).toFloat()

            // Area fill
            val fillPath = Path()
            sorted.forEachIndexed { i, pt ->
                if (i == 0) fillPath.moveTo(xOf(pt), yOf(pt)) else fillPath.lineTo(xOf(pt), yOf(pt))
            }
            fillPath.lineTo(xOf(sorted.last()), h)
            fillPath.lineTo(xOf(sorted.first()), h)
            fillPath.close()
            drawPath(
                fillPath,
                brush = Brush.verticalGradient(
                    colors = listOf(color.copy(alpha = 0.20f), color.copy(alpha = 0.03f)),
                    startY = 0f, endY = h,
                ),
            )

            // Line
            val linePath = Path()
            sorted.forEachIndexed { i, pt ->
                if (i == 0) linePath.moveTo(xOf(pt), yOf(pt)) else linePath.lineTo(xOf(pt), yOf(pt))
            }
            drawPath(
                linePath,
                color = color,
                style = Stroke(
                    width     = 2.5.dp.toPx(),
                    cap       = StrokeCap.Round,
                    join      = StrokeJoin.Round,
                ),
            )

            // Dots
            sorted.forEach { pt ->
                drawCircle(Color.White, radius = 4.dp.toPx(), center = Offset(xOf(pt), yOf(pt)))
                drawCircle(color,       radius = 3.dp.toPx(), center = Offset(xOf(pt), yOf(pt)))
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Bar chart
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun BarChart(series: List<ChartSeriesDto>) {
    if (series.isEmpty()) return

    val allLabels  = series.flatMap { it.data_points.map { p -> p.label } }.distinct().sorted()
    val allValues  = series.flatMap { it.data_points.map { p -> p.value } }
    if (allLabels.isEmpty() || allValues.isEmpty()) return

    val minVal   = 0.0   // bars always start at zero
    val maxVal   = allValues.max()
    val valRange = if (maxVal < 0.001) 1.0 else maxVal
    val labelCount = allLabels.size
    val seriesCount = series.size

    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(240.dp)
            .padding(start = 44.dp, end = 12.dp, top = 10.dp, bottom = 30.dp)
    ) {
        val w = size.width
        val h = size.height

        // Grid lines (5 divisions)
        for (i in 0..4) {
            val y = h - h * i / 4f
            drawLine(
                color       = Color(0xFFE2E8F0),
                start       = Offset(0f, y),
                end         = Offset(w, y),
                strokeWidth = 1.dp.toPx(),
            )
            val v = valRange * i / 4
            drawContext.canvas.nativeCanvas.drawText(
                formatNumber(v),
                -6.dp.toPx(),
                y + 4.dp.toPx(),
                android.graphics.Paint().apply {
                    textSize  = 9.dp.toPx()
                    color     = android.graphics.Color.parseColor("#94A3B8")
                    textAlign = android.graphics.Paint.Align.RIGHT
                }
            )
        }

        // Bars
        val groupWidth  = w / labelCount
        val barPadding  = groupWidth * 0.1f
        val totalBarW   = groupWidth - barPadding * 2
        val singleBarW  = totalBarW / seriesCount

        allLabels.forEachIndexed { gi, label ->
            val groupLeft = groupWidth * gi + barPadding

            series.forEachIndexed { si, s ->
                val pt    = s.data_points.find { it.label == label } ?: return@forEachIndexed
                val color = chartColors[si % chartColors.size]
                val barH  = (h * (pt.value - minVal) / valRange).toFloat()
                val left  = groupLeft + singleBarW * si
                drawRect(
                    color   = color,
                    topLeft = Offset(left, h - barH),
                    size    = Size(singleBarW - 2.dp.toPx(), barH),
                )
            }

            // X-axis label (every nth to avoid overlap)
            val xStep = maxOf(1, labelCount / 5)
            if (gi % xStep == 0) {
                drawContext.canvas.nativeCanvas.drawText(
                    label,
                    groupLeft + totalBarW / 2,
                    h + 18.dp.toPx(),
                    android.graphics.Paint().apply {
                        textSize  = 9.dp.toPx()
                        color     = android.graphics.Color.parseColor("#94A3B8")
                        textAlign = android.graphics.Paint.Align.CENTER
                    }
                )
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Pie chart
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun PieChart(series: List<ChartSeriesDto>) {
    if (series.isEmpty()) return

    val slices = series.map { s ->
        Pair(s.name, s.data_points.sumOf { it.value })
    }.filter { it.second > 0 }

    if (slices.isEmpty()) return
    val total = slices.sumOf { it.second }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(220.dp),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(modifier = Modifier.size(200.dp)) {
            var start = -90f
            slices.forEachIndexed { idx, (_, value) ->
                val sweep = (value / total * 360).toFloat()
                drawArc(
                    color      = chartColors[idx % chartColors.size],
                    startAngle = start,
                    sweepAngle = sweep,
                    useCenter  = true,
                    size       = Size(size.width, size.height),
                )
                start += sweep
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Legend
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun ChartLegend(series: List<ChartSeriesDto>) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        series.forEachIndexed { idx, s ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    shape = CircleShape,
                    color = chartColors[idx % chartColors.size],
                    modifier = Modifier.size(10.dp),
                ) {}
                Spacer(Modifier.width(8.dp))
                Text(
                    s.name,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Number formatting
// ─────────────────────────────────────────────────────────────────────────────

private fun formatNumber(value: Double): String = when {
    value >= 1_000_000_000 -> "%.1fB".format(value / 1_000_000_000)
    value >= 1_000_000     -> "%.1fM".format(value / 1_000_000)
    value >= 1_000         -> "%.1fK".format(value / 1_000)
    value == value.toLong().toDouble() -> value.toLong().toString()
    else                   -> "%.2f".format(value)
}

