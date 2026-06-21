package com.finsaathi.android.notify

data class AlertFeedbackMetadata(
    val category: String,
    val riskLevel: String,
    val sourceType: String,
    val reasonCode: String? = null,
) {
    fun safeSummary(): String {
        return listOf(
            "category=${safeValue(category)}",
            "risk_level=${safeValue(riskLevel)}",
            "source_type=${safeValue(sourceType)}",
            "reason_code=${safeValue(reasonCode)}",
        ).joinToString("\n")
    }

    private fun safeValue(value: String?): String {
        val normalized = value
            ?.trim()
            ?.lowercase()
            ?.replace(Regex("[^a-z0-9_.-]"), "_")
            ?.trim('_', '.', '-')
            .orEmpty()
        return normalized.ifBlank { "unknown" }.take(MAX_VALUE_LENGTH)
    }

    companion object {
        private const val MAX_VALUE_LENGTH = 80

        fun fromNullableFields(
            category: String?,
            riskLevel: String?,
            sourceType: String?,
            reasonCode: String?,
        ): AlertFeedbackMetadata? {
            if (category.isNullOrBlank() && riskLevel.isNullOrBlank() && sourceType.isNullOrBlank()) {
                return null
            }
            return AlertFeedbackMetadata(
                category = category.orEmpty(),
                riskLevel = riskLevel.orEmpty(),
                sourceType = sourceType.orEmpty(),
                reasonCode = reasonCode,
            )
        }
    }
}
