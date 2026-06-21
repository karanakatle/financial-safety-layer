package com.arthamantri.android.notify

import android.content.Context
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.core.FinancialRiskDetection
import com.arthamantri.android.repo.LiteracyRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.UUID

object FinancialRiskAlertPresenter {
    fun maybeShow(
        context: Context,
        detection: FinancialRiskDetection,
        source: String,
        rawMessage: String = "",
    ): Boolean {
        val routing = FinancialRiskAlertRouter.routeFor(detection)
        if (!routing.shouldShow) {
            return false
        }

        val copy = FinancialRiskAlertCopyMapper.copyFor(
            category = detection.category,
            level = routing.riskLevel,
        )
        val focusedActionLabels = copy.focusedActionLabelRes.map { context.getString(it) }
        val proceedConfirmationLabel = copy.proceedConfirmationLabelRes
            .takeIf { it != 0 }
            ?.let { context.getString(it) }
        val feedbackMetadata = AlertFeedbackMetadata(
            category = detection.category.wireValue,
            riskLevel = routing.riskLevel.name.lowercase(),
            sourceType = source,
            reasonCode = detection.reasonCode,
        )
        val humanReviewMetadata = HumanReviewPayloadBuilder.buildSupportMetadata(
            rawMessage = rawMessage,
            detection = detection,
            sourceType = source,
        )
        val alertId = "${AppConstants.Domain.LOCAL_FINANCIAL_RISK_ALERT_PREFIX}-${UUID.randomUUID()}"
        AlertNotifier.show(
            context = context,
            title = context.getString(copy.titleRes),
            body = context.getString(copy.bodyRes),
            alertId = alertId,
            severity = routing.severity,
            pauseSeconds = routing.pauseSeconds,
            whyThisAlert = context.getString(copy.whyRes),
            nextSafeAction = context.getString(copy.nextActionRes),
            primaryActionLabel = context.getString(copy.primaryActionLabelRes),
            focusedActionLabels = focusedActionLabels.takeIf { it.isNotEmpty() },
            proceedConfirmationLabel = proceedConfirmationLabel,
            alertFamily = AppConstants.Domain.ALERT_FAMILY_FINANCIAL_RISK,
            showUsefulnessFeedback = true,
            useFocusedPaymentActions = focusedActionLabels.isNotEmpty(),
            allowOverlay = routing.allowOverlay,
            feedbackMetadata = feedbackMetadata,
            humanReviewMetadata = humanReviewMetadata,
        )
        submitMetadataOnlyLog(context, alertId, detection, source)
        return true
    }

    private fun submitMetadataOnlyLog(
        context: Context,
        alertId: String,
        detection: FinancialRiskDetection,
        source: String,
    ) {
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                LiteracyRepository.submitAppLog(
                    context = context,
                    level = AppConstants.Domain.APP_LOG_LEVEL_WARN,
                    message = listOf(
                        "financial_risk_alert",
                        alertId,
                        source,
                        detection.riskLevel.name.lowercase(),
                        detection.category.wireValue,
                        detection.reasonCode,
                    ).joinToString(":"),
                    language = LiteracyRepository.language(context),
                    participantId = LiteracyRepository.participantId(context),
                )
            }
        }
    }
}
