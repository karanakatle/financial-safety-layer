package com.arthamantri.android.sms

import android.content.Context
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import java.util.Locale
import kotlin.math.roundToInt

data class CashflowFallbackGuidance(
    val body: String,
    val whyThisAlert: String,
    val nextSafeAction: String,
)

object CashflowFallbackGuidanceBuilder {
    fun build(
        context: Context,
        signalType: String,
        amount: Double?,
    ): CashflowFallbackGuidance? {
        val bodyRes = when (signalType) {
            AppConstants.Domain.SMS_SIGNAL_EXPENSE -> R.string.alert_cashflow_fallback_body
            AppConstants.Domain.SMS_SIGNAL_PARTIAL -> R.string.alert_cashflow_fallback_partial_body
            else -> return null
        }
        val nextRes = when (signalType) {
            AppConstants.Domain.SMS_SIGNAL_EXPENSE -> R.string.alert_cashflow_fallback_next_expense
            AppConstants.Domain.SMS_SIGNAL_PARTIAL -> R.string.alert_cashflow_fallback_next_partial
            else -> return null
        }
        val whyText = amount?.takeIf { it > 0.0 }?.let { resolvedAmount ->
            context.getString(
                R.string.alert_cashflow_fallback_why_amount,
                formatAmount(resolvedAmount),
            )
        } ?: context.getString(R.string.alert_cashflow_fallback_why)
        return CashflowFallbackGuidance(
            body = context.getString(bodyRes),
            whyThisAlert = whyText,
            nextSafeAction = context.getString(nextRes),
        )
    }

    private fun formatAmount(amount: Double): String {
        val rounded = ((amount * 10.0).roundToInt()) / 10.0
        return if (rounded % 1.0 == 0.0) {
            rounded.toInt().toString()
        } else {
            String.format(Locale.US, "%.1f", rounded)
        }
    }
}
