package com.arthamantri.android.core

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class EssentialGoalCategoryConfig(
    val id: String,
    val labelKey: String,
    val legacyAliases: List<String> = emptyList(),
)

data class EssentialGoalBucketConfig(
    val id: String,
    val labelKey: String,
    val seedBoosts: Map<String, Int> = emptyMap(),
)

data class EssentialGoalPromptConfig(
    val questionKey: String,
    val labelKey: String,
    val helpKey: String,
    val optional: Boolean,
    val guidanceOnly: Boolean,
    val buckets: List<EssentialGoalBucketConfig> = emptyList(),
)

data class EssentialGoalCohortConfig(
    val id: String,
    val labelKey: String,
    val supportedCategories: List<String>,
    val defaultPriorities: List<String>,
    val affordabilityPrompt: EssentialGoalPromptConfig,
)

data class EssentialGoalSetupConfig(
    val configVersion: String,
    val activePriorityLimit: Int,
    val selectionSources: List<String>,
    val futureRankingInputs: List<String>,
    val categories: List<EssentialGoalCategoryConfig>,
    val cohorts: List<EssentialGoalCohortConfig>,
) {
    fun cohort(id: String): EssentialGoalCohortConfig {
        val normalized = id.trim().lowercase().replace("-", "_").replace(" ", "_")
        return cohorts.firstOrNull { it.id == normalized } ?: cohorts.first()
    }

    fun category(id: String): EssentialGoalCategoryConfig? {
        val normalized = normalizeGoalId(id)
        return categories.firstOrNull { it.id == normalized }
    }

    fun normalizeGoalId(raw: String?): String {
        val normalized = raw.orEmpty().trim().lowercase().replace("-", "_").replace(" ", "_")
        if (normalized.isBlank()) {
            return ""
        }
        categories.forEach { category ->
            if (category.id == normalized || category.legacyAliases.any { it == normalized }) {
                return category.id
            }
        }
        return ""
    }
}

data class EssentialGoalSelectionPlan(
    val allSelectedEssentials: List<String>,
    val activePriorityEssentials: List<String>,
    val selectionSource: String,
    val goalSourceMap: Map<String, String>,
    val affordabilityQuestionKey: String?,
    val affordabilityBucketId: String?,
)

object EssentialGoalSetupConfigLoader {
    private const val ASSET_PATH = "essential_goal_setup_config.json"

    @Volatile
    private var cached: EssentialGoalSetupConfig? = null

    fun load(context: Context): EssentialGoalSetupConfig {
        cached?.let { return it }
        val parsed = parse(
            context.assets.open(ASSET_PATH).bufferedReader(Charsets.UTF_8).use { it.readText() },
        )
        cached = parsed
        return parsed
    }

    internal fun parse(json: String): EssentialGoalSetupConfig {
        val root = JSONObject(json)
        return EssentialGoalSetupConfig(
            configVersion = root.optString("config_version", "essential_goal_setup_v1"),
            activePriorityLimit = root.optInt("active_priority_limit", 6).coerceAtLeast(1),
            selectionSources = root.optJSONArray("selection_sources").toStringList(),
            futureRankingInputs = root.optJSONArray("future_ranking_inputs").toStringList(),
            categories = root.optJSONArray("categories").toCategoryList(),
            cohorts = root.optJSONArray("cohorts").toCohortList(),
        )
    }

    private fun JSONArray?.toStringList(): List<String> {
        if (this == null) {
            return emptyList()
        }
        return buildList {
            for (index in 0 until length()) {
                val value = optString(index).trim()
                if (value.isNotBlank()) {
                    add(value)
                }
            }
        }
    }

    private fun JSONArray?.toCategoryList(): List<EssentialGoalCategoryConfig> {
        if (this == null) {
            return emptyList()
        }
        return buildList {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                val id = item.optString("id").trim()
                val labelKey = item.optString("label_key").trim()
                if (id.isBlank() || labelKey.isBlank()) {
                    continue
                }
                add(
                    EssentialGoalCategoryConfig(
                        id = id,
                        labelKey = labelKey,
                        legacyAliases = item.optJSONArray("legacy_aliases").toStringList(),
                    ),
                )
            }
        }
    }

    private fun JSONArray?.toBucketList(): List<EssentialGoalBucketConfig> {
        if (this == null) {
            return emptyList()
        }
        return buildList {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                val boostsJson = item.optJSONObject("seed_boosts") ?: JSONObject()
                val boosts = mutableMapOf<String, Int>()
                boostsJson.keys().forEach { key ->
                    boosts[key] = boostsJson.optInt(key, 0)
                }
                add(
                    EssentialGoalBucketConfig(
                        id = item.optString("id").trim(),
                        labelKey = item.optString("label_key").trim(),
                        seedBoosts = boosts,
                    ),
                )
            }
        }
    }

    private fun JSONArray?.toCohortList(): List<EssentialGoalCohortConfig> {
        if (this == null) {
            return emptyList()
        }
        return buildList {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                val promptJson = item.optJSONObject("affordability_prompt") ?: JSONObject()
                add(
                    EssentialGoalCohortConfig(
                        id = item.optString("id").trim(),
                        labelKey = item.optString("label_key").trim(),
                        supportedCategories = item.optJSONArray("supported_categories").toStringList(),
                        defaultPriorities = item.optJSONArray("default_priorities").toStringList(),
                        affordabilityPrompt = EssentialGoalPromptConfig(
                            questionKey = promptJson.optString("question_key").trim(),
                            labelKey = promptJson.optString("label_key").trim(),
                            helpKey = promptJson.optString("help_key").trim(),
                            optional = promptJson.optBoolean("optional", true),
                            guidanceOnly = promptJson.optBoolean("guidance_only", true),
                            buckets = promptJson.optJSONArray("buckets").toBucketList(),
                        ),
                    ),
                )
            }
        }
    }
}

object EssentialGoalSetupPlanner {
    fun userSelected(
        config: EssentialGoalSetupConfig,
        cohortId: String,
        orderedSelections: List<String>,
        affordabilityBucketId: String?,
    ): EssentialGoalSelectionPlan {
        val normalizedSelections = normalizeOrderedSelections(config, orderedSelections)
        val active = normalizedSelections.take(config.activePriorityLimit)
        val prompt = config.cohort(cohortId).affordabilityPrompt
        return EssentialGoalSelectionPlan(
            allSelectedEssentials = normalizedSelections,
            activePriorityEssentials = active,
            selectionSource = "user_selected",
            goalSourceMap = normalizedSelections.associateWith { "user_selected" },
            affordabilityQuestionKey = prompt.questionKey.ifBlank { null },
            affordabilityBucketId = affordabilityBucketId?.takeIf { it.isNotBlank() },
        )
    }

    fun seeded(
        config: EssentialGoalSetupConfig,
        cohortId: String,
        affordabilityBucketId: String?,
    ): EssentialGoalSelectionPlan {
        val cohort = config.cohort(cohortId)
        val boosts = cohort.affordabilityPrompt.buckets.firstOrNull { it.id == affordabilityBucketId }?.seedBoosts.orEmpty()
        val defaultRank = cohort.defaultPriorities.withIndex().associate { it.value to it.index }
        val globalRank = config.categories.withIndex().associate { it.value.id to it.index }
        val ordered = cohort.supportedCategories
            .mapNotNull { config.normalizeGoalId(it).takeIf { id -> id.isNotBlank() } }
            .distinct()
            .sortedWith(
                compareBy<String>(
                    { -(boosts[it] ?: 0) },
                    { defaultRank[it] ?: Int.MAX_VALUE },
                    { globalRank[it] ?: Int.MAX_VALUE },
                ),
            )
        val seeded = ordered.take(config.activePriorityLimit)
        return EssentialGoalSelectionPlan(
            allSelectedEssentials = seeded,
            activePriorityEssentials = seeded,
            selectionSource = "system_auto_seeded",
            goalSourceMap = seeded.associateWith { "system_auto_seeded" },
            affordabilityQuestionKey = cohort.affordabilityPrompt.questionKey.ifBlank { null },
            affordabilityBucketId = affordabilityBucketId?.takeIf { it.isNotBlank() },
        )
    }

    private fun normalizeOrderedSelections(config: EssentialGoalSetupConfig, orderedSelections: List<String>): List<String> {
        val normalized = mutableListOf<String>()
        orderedSelections.forEach { raw ->
            val goalId = config.normalizeGoalId(raw)
            if (goalId.isNotBlank() && !normalized.contains(goalId)) {
                normalized += goalId
            }
        }
        return normalized
    }
}
