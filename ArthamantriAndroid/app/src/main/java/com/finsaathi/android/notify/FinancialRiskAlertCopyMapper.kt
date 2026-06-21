package com.finsaathi.android.notify

import com.finsaathi.android.R
import com.finsaathi.android.core.FinancialRiskCategory
import com.finsaathi.android.core.FinancialRiskLevel

data class FinancialRiskAlertCopyRes(
    val titleRes: Int,
    val bodyRes: Int,
    val whyRes: Int,
    val nextActionRes: Int,
    val primaryActionLabelRes: Int,
    val focusedActionLabelRes: List<Int> = emptyList(),
    val proceedConfirmationLabelRes: Int = 0,
)

object FinancialRiskAlertCopyMapper {
    fun copyFor(category: FinancialRiskCategory, level: FinancialRiskLevel): FinancialRiskAlertCopyRes {
        val isRed = level == FinancialRiskLevel.RED
        return FinancialRiskAlertCopyRes(
            titleRes = if (isRed) {
                R.string.alert_financial_risk_red_title
            } else {
                R.string.alert_financial_risk_yellow_title
            },
            bodyRes = bodyFor(category),
            whyRes = whyFor(category),
            nextActionRes = nextActionFor(category),
            primaryActionLabelRes = if (isRed) {
                R.string.alert_financial_risk_stop_verify
            } else {
                R.string.alert_ack_short
            },
            focusedActionLabelRes = if (isRed) {
                listOf(
                    R.string.alert_financial_risk_stop_verify,
                    R.string.alert_financial_risk_action_do_not_act,
                    R.string.alert_financial_risk_action_continue_after_check,
                )
            } else {
                emptyList()
            },
            proceedConfirmationLabelRes = if (isRed) {
                R.string.alert_financial_risk_proceed_confirmation_confirm
            } else {
                0
            },
        )
    }

    private fun bodyFor(category: FinancialRiskCategory): Int =
        when (category) {
            FinancialRiskCategory.UPFRONT_FEE_RISK -> R.string.alert_financial_risk_body_upfront_fee
            FinancialRiskCategory.SENSITIVE_DATA_REQUEST -> R.string.alert_financial_risk_body_sensitive_data
            FinancialRiskCategory.KYC_ACCOUNT_BLOCK_PRESSURE -> R.string.alert_financial_risk_body_kyc
            FinancialRiskCategory.GUARANTEED_RETURN_SCHEME -> R.string.alert_financial_risk_body_guaranteed_return
            FinancialRiskCategory.UNKNOWN_LINK_MONEY_PRESSURE -> R.string.alert_financial_risk_body_link_pressure
            FinancialRiskCategory.GENERIC_PROMOTION,
            FinancialRiskCategory.BENIGN_OR_ROUTINE -> R.string.alert_financial_risk_body_generic_promotion
        }

    private fun whyFor(category: FinancialRiskCategory): Int =
        when (category) {
            FinancialRiskCategory.UPFRONT_FEE_RISK -> R.string.alert_financial_risk_why_upfront_fee
            FinancialRiskCategory.SENSITIVE_DATA_REQUEST -> R.string.alert_financial_risk_why_sensitive_data
            FinancialRiskCategory.KYC_ACCOUNT_BLOCK_PRESSURE -> R.string.alert_financial_risk_why_kyc
            FinancialRiskCategory.GUARANTEED_RETURN_SCHEME -> R.string.alert_financial_risk_why_guaranteed_return
            FinancialRiskCategory.UNKNOWN_LINK_MONEY_PRESSURE -> R.string.alert_financial_risk_why_link_pressure
            FinancialRiskCategory.GENERIC_PROMOTION,
            FinancialRiskCategory.BENIGN_OR_ROUTINE -> R.string.alert_financial_risk_why_generic_promotion
        }

    private fun nextActionFor(category: FinancialRiskCategory): Int =
        when (category) {
            FinancialRiskCategory.SENSITIVE_DATA_REQUEST -> R.string.alert_financial_risk_next_sensitive_data
            FinancialRiskCategory.GENERIC_PROMOTION -> R.string.alert_financial_risk_next_read_carefully
            FinancialRiskCategory.BENIGN_OR_ROUTINE -> R.string.alert_financial_risk_next_read_carefully
            FinancialRiskCategory.UPFRONT_FEE_RISK,
            FinancialRiskCategory.KYC_ACCOUNT_BLOCK_PRESSURE,
            FinancialRiskCategory.GUARANTEED_RETURN_SCHEME,
            FinancialRiskCategory.UNKNOWN_LINK_MONEY_PRESSURE -> R.string.alert_financial_risk_next_stop_verify
        }
}
