package com.finsaathi.android.notify

import com.finsaathi.android.R
import com.finsaathi.android.core.FinancialRiskCategory
import com.finsaathi.android.core.FinancialRiskLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class FinancialRiskAlertCopyMapperTest {
    @Test
    fun `all detector categories map to complete alert copy`() {
        FinancialRiskCategory.entries.forEach { category ->
            val copy = FinancialRiskAlertCopyMapper.copyFor(category, FinancialRiskLevel.RED)

            assertTrue("${category.name} title missing", copy.titleRes != 0)
            assertTrue("${category.name} body missing", copy.bodyRes != 0)
            assertTrue("${category.name} why missing", copy.whyRes != 0)
            assertTrue("${category.name} next action missing", copy.nextActionRes != 0)
            assertTrue("${category.name} primary action missing", copy.primaryActionLabelRes != 0)
        }
    }

    @Test
    fun `sensitive data copy uses explicit do not share next action`() {
        val copy = FinancialRiskAlertCopyMapper.copyFor(
            FinancialRiskCategory.SENSITIVE_DATA_REQUEST,
            FinancialRiskLevel.RED,
        )

        assertEquals(R.string.alert_financial_risk_body_sensitive_data, copy.bodyRes)
        assertEquals(R.string.alert_financial_risk_why_sensitive_data, copy.whyRes)
        assertEquals(R.string.alert_financial_risk_next_sensitive_data, copy.nextActionRes)
        assertEquals(R.string.alert_financial_risk_stop_verify, copy.primaryActionLabelRes)
    }

    @Test
    fun `upfront fee red copy maps to stop and verify path`() {
        val copy = FinancialRiskAlertCopyMapper.copyFor(
            FinancialRiskCategory.UPFRONT_FEE_RISK,
            FinancialRiskLevel.RED,
        )

        assertEquals(R.string.alert_financial_risk_red_title, copy.titleRes)
        assertEquals(R.string.alert_financial_risk_body_upfront_fee, copy.bodyRes)
        assertEquals(R.string.alert_financial_risk_why_upfront_fee, copy.whyRes)
        assertEquals(R.string.alert_financial_risk_next_stop_verify, copy.nextActionRes)
    }

    @Test
    fun `red financial risk copy exposes focused safe action labels`() {
        val copy = FinancialRiskAlertCopyMapper.copyFor(
            FinancialRiskCategory.UPFRONT_FEE_RISK,
            FinancialRiskLevel.RED,
        )

        assertEquals(R.string.alert_financial_risk_stop_verify, copy.primaryActionLabelRes)
        assertEquals(
            listOf(
                R.string.alert_financial_risk_stop_verify,
                R.string.alert_financial_risk_action_do_not_act,
                R.string.alert_financial_risk_action_continue_after_check,
            ),
            copy.focusedActionLabelRes,
        )
        assertEquals(
            R.string.alert_financial_risk_proceed_confirmation_confirm,
            copy.proceedConfirmationLabelRes,
        )
    }

    @Test
    fun `yellow financial risk copy does not enable focused action labels`() {
        val copy = FinancialRiskAlertCopyMapper.copyFor(
            FinancialRiskCategory.GENERIC_PROMOTION,
            FinancialRiskLevel.YELLOW,
        )

        assertTrue(copy.focusedActionLabelRes.isEmpty())
        assertEquals(0, copy.proceedConfirmationLabelRes)
    }

    @Test
    fun `generic and benign categories use careful-reading fallback copy`() {
        listOf(
            FinancialRiskCategory.GENERIC_PROMOTION,
            FinancialRiskCategory.BENIGN_OR_ROUTINE,
        ).forEach { category ->
            val copy = FinancialRiskAlertCopyMapper.copyFor(category, FinancialRiskLevel.YELLOW)

            assertEquals(R.string.alert_financial_risk_yellow_title, copy.titleRes)
            assertEquals(R.string.alert_financial_risk_body_generic_promotion, copy.bodyRes)
            assertEquals(R.string.alert_financial_risk_why_generic_promotion, copy.whyRes)
            assertEquals(R.string.alert_financial_risk_next_read_carefully, copy.nextActionRes)
            assertEquals(R.string.alert_ack_short, copy.primaryActionLabelRes)
        }
    }
}
