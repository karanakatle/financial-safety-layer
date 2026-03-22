package com.arthamantri.android.notify

import android.content.Context
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.model.UpiRequestInspectResponse
import com.arthamantri.android.repo.LiteracyRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.UUID

object PaymentInspectionAlertPresenter {
    fun maybeShow(
        context: Context,
        inspection: UpiRequestInspectResponse,
        requestKind: String,
        amount: Double?,
        payeeLabel: String,
        payeeHandle: String,
        rawText: String,
    ): Boolean {
        if (!inspection.should_warn) {
            return false
        }
        if (!hasMeaningfulPaymentContext(requestKind, amount, payeeLabel, payeeHandle, rawText)) {
            return false
        }

        val body = inspection.message?.trim().orEmpty()
        if (body.isBlank()) {
            return false
        }

        val scenario = inspection.scenario?.trim().orEmpty()
        val riskLevel = inspection.risk_level?.trim().orEmpty()
        val isFallback = scenario == "unknown"

        AlertNotifier.show(
            context = context,
            title = context.getString(
                if (isFallback) R.string.alert_payment_uncertain_title else R.string.alert_payment_risk_title
            ),
            body = body,
            alertId = inspection.alert_id,
            severity = severityForRisk(riskLevel, isFallback),
            pauseSeconds = pauseSecondsForRisk(riskLevel, isFallback),
            whyThisAlert = inspection.why_this_alert,
            nextSafeAction = inspection.next_best_action,
            primaryActionLabel = context.getString(R.string.alert_payment_ack_long),
            alertFamily = AppConstants.Domain.ALERT_FAMILY_PAYMENT,
            useFocusedPaymentActions = true,
        )
        return true
    }

    fun showLocalFallback(
        context: Context,
        requestKind: String,
        amount: Double?,
        payeeLabel: String,
        payeeHandle: String,
        rawText: String,
    ): Boolean {
        if (!hasMeaningfulPaymentContext(requestKind, amount, payeeLabel, payeeHandle, rawText)) {
            return false
        }

        val alertId = "${AppConstants.Domain.LOCAL_PAYMENT_FALLBACK_ALERT_PREFIX}-${UUID.randomUUID()}"

        AlertNotifier.show(
            context = context,
            title = context.getString(R.string.alert_payment_uncertain_title),
            body = context.getString(R.string.alert_payment_fallback_body),
            alertId = alertId,
            severity = "medium",
            pauseSeconds = 3,
            whyThisAlert = context.getString(R.string.alert_payment_fallback_why),
            nextSafeAction = context.getString(R.string.alert_payment_fallback_next),
            primaryActionLabel = context.getString(R.string.alert_payment_ack_long),
            alertFamily = AppConstants.Domain.ALERT_FAMILY_PAYMENT,
            useFocusedPaymentActions = true,
        )
        CoroutineScope(Dispatchers.IO).launch {
            LiteracyRepository.submitAppLog(
                context = context,
                level = AppConstants.Domain.APP_LOG_LEVEL_WARN,
                message = buildFallbackLogMessage(
                    alertId = alertId,
                    requestKind = requestKind,
                    amount = amount,
                    payeeLabel = payeeLabel,
                    payeeHandle = payeeHandle,
                ),
                language = LiteracyRepository.language(context),
                participantId = LiteracyRepository.participantId(context),
            )
        }
        return true
    }

    private fun buildFallbackLogMessage(
        alertId: String,
        requestKind: String,
        amount: Double?,
        payeeLabel: String,
        payeeHandle: String,
    ): String {
        return listOf(
            "payment_fallback_shown",
            alertId,
            requestKind.ifBlank { AppConstants.PaymentInspection.REQUEST_KIND_UNKNOWN },
            amount?.toString() ?: "unknown",
            payeeLabel.ifBlank { "unknown" },
            payeeHandle.ifBlank { "unknown" },
        ).joinToString(":")
    }

    private fun hasMeaningfulPaymentContext(
        requestKind: String,
        amount: Double?,
        payeeLabel: String,
        payeeHandle: String,
        rawText: String,
    ): Boolean {
        if (rawText.isNotBlank()) {
            return true
        }
        if (!payeeHandle.isBlank() || !payeeLabel.isBlank()) {
            return true
        }
        if (amount != null && amount > 0) {
            return true
        }
        return requestKind.isNotBlank() && requestKind != AppConstants.PaymentInspection.REQUEST_KIND_UNKNOWN
    }

    private fun severityForRisk(riskLevel: String, isFallback: Boolean): String {
        return when {
            riskLevel.equals("critical", ignoreCase = true) -> "hard"
            riskLevel.equals("high", ignoreCase = true) -> "hard"
            isFallback -> "medium"
            else -> "medium"
        }
    }

    private fun pauseSecondsForRisk(riskLevel: String, isFallback: Boolean): Int {
        return when {
            riskLevel.equals("critical", ignoreCase = true) -> 5
            riskLevel.equals("high", ignoreCase = true) -> 5
            isFallback -> 3
            else -> 0
        }
    }
}
