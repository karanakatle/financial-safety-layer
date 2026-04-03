package com.arthamantri.android.core

import org.junit.Assert.assertEquals
import org.junit.Test

class EssentialGoalSetupPlannerTest {
    private val config = EssentialGoalSetupConfig(
        configVersion = "test",
        activePriorityLimit = 6,
        selectionSources = listOf("user_selected", "system_auto_seeded"),
        futureRankingInputs = emptyList(),
        categories = listOf(
            EssentialGoalCategoryConfig(id = "ration", labelKey = "goal_ration"),
            EssentialGoalCategoryConfig(id = "rent", labelKey = "goal_rent"),
            EssentialGoalCategoryConfig(id = "cooking_fuel", labelKey = "goal_cooking_fuel", legacyAliases = listOf("fuel")),
            EssentialGoalCategoryConfig(id = "transport", labelKey = "goal_transport"),
            EssentialGoalCategoryConfig(id = "mobile_recharge", labelKey = "goal_mobile_recharge"),
            EssentialGoalCategoryConfig(id = "medicine", labelKey = "goal_medicine"),
            EssentialGoalCategoryConfig(id = "work_inputs", labelKey = "goal_work_inputs"),
        ),
        cohorts = listOf(
            EssentialGoalCohortConfig(
                id = "daily_cashflow_worker",
                labelKey = "cohort_daily_cashflow_worker",
                supportedCategories = listOf(
                    "ration",
                    "rent",
                    "cooking_fuel",
                    "transport",
                    "mobile_recharge",
                    "medicine",
                    "work_inputs",
                ),
                defaultPriorities = listOf(
                    "ration",
                    "rent",
                    "cooking_fuel",
                    "transport",
                    "mobile_recharge",
                    "medicine",
                ),
                affordabilityPrompt = EssentialGoalPromptConfig(
                    questionKey = "daily_earnings_range",
                    labelKey = "money_setup_affordability_daily_label",
                    helpKey = "money_setup_affordability_daily_help",
                    optional = true,
                    guidanceOnly = true,
                    buckets = listOf(
                        EssentialGoalBucketConfig(
                            id = "1000_1499",
                            labelKey = "money_bucket_daily_1000_1499",
                            seedBoosts = mapOf("work_inputs" to 7, "rent" to 6),
                        ),
                    ),
                ),
            ),
        ),
    )

    @Test
    fun userSelectedPreservesSelectionOrderAndCapsActivePriorities() {
        val plan = EssentialGoalSetupPlanner.userSelected(
            config = config,
            cohortId = "daily_cashflow_worker",
            orderedSelections = listOf("fuel", "ration", "transport", "rent", "medicine", "mobile_recharge", "work_inputs"),
            affordabilityBucketId = null,
        )

        assertEquals(
            listOf("cooking_fuel", "ration", "transport", "rent", "medicine", "mobile_recharge", "work_inputs"),
            plan.allSelectedEssentials,
        )
        assertEquals(
            listOf("cooking_fuel", "ration", "transport", "rent", "medicine", "mobile_recharge"),
            plan.activePriorityEssentials,
        )
        assertEquals("user_selected", plan.selectionSource)
    }

    @Test
    fun seededUsesBucketBoostsDeterministically() {
        val plan = EssentialGoalSetupPlanner.seeded(
            config = config,
            cohortId = "daily_cashflow_worker",
            affordabilityBucketId = "1000_1499",
        )

        assertEquals(
            listOf("work_inputs", "rent", "ration", "cooking_fuel", "transport", "mobile_recharge"),
            plan.activePriorityEssentials,
        )
        assertEquals("system_auto_seeded", plan.selectionSource)
        assertEquals("1000_1499", plan.affordabilityBucketId)
    }
}
