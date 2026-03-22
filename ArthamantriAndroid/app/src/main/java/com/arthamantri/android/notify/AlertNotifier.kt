package com.arthamantri.android.notify

import android.Manifest
import android.app.PendingIntent
import android.app.NotificationChannel
import android.app.KeyguardManager
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Build
import android.os.Looper
import android.provider.Settings
import androidx.annotation.ColorRes
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.core.DebugObservability

object AlertNotifier {
    data class AlertVisualStyle(
        @param:ColorRes val scrimColorRes: Int,
        @param:ColorRes val badgeBgColorRes: Int,
        @param:ColorRes val badgeTextColorRes: Int,
        val tagTextRes: Int,
        val notificationPriority: Int,
    )

    private val mainHandler = Handler(Looper.getMainLooper())
    private val explainabilityMarkers = listOf(
        "\nRisk level:",
        "\nWhy this alert:",
        "\nNext safe action:",
        "\nEssential-goal impact:",
        "\nजोखिम स्तर:",
        "\nक्यों दिखा:",
        "\nअगला सुरक्षित कदम:",
        "\nआवश्यक लक्ष्य प्रभाव:",
    )

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            AppConstants.Notifications.SAFETY_CHANNEL_ID,
            context.getString(R.string.notif_channel_name),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = context.getString(R.string.notif_channel_desc)
        }
        manager.createNotificationChannel(channel)
    }

    fun show(
        context: Context,
        title: String,
        body: String,
        alertId: String? = null,
        severity: String = "medium",
        pauseSeconds: Int = 0,
        whyThisAlert: String? = null,
        nextSafeAction: String? = null,
        essentialGoalImpact: String? = null,
        primaryActionLabel: String? = null,
        focusedActionLabels: List<String>? = null,
        proceedConfirmationLabel: String? = null,
        alertFamily: String? = null,
        showUsefulnessFeedback: Boolean = false,
        useFocusedPaymentActions: Boolean = false,
    ) {
        ensureChannel(context)
        val resolvedSeverity = normalizeSeverity(severity)
        val style = styleForSeverity(resolvedSeverity)
        val primaryBody = sanitizeBody(
            body = body,
            hasExplainabilitySections = !whyThisAlert.isNullOrBlank() ||
                !nextSafeAction.isNullOrBlank() ||
                !essentialGoalImpact.isNullOrBlank(),
        )

        mainHandler.post {
            val resolvedAlertId = alertId ?: java.util.UUID.randomUUID().toString()
            val keyguardManager = context.getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
            val canDrawOverlays = Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(context)
            DebugObservability.traceAsync(
                context = context,
                tag = AppConstants.LogTags.DEBUG_OBSERVABILITY,
                event = "alert_show_requested",
                fields = mapOf(
                    "alert_id" to resolvedAlertId,
                    "severity" to resolvedSeverity,
                    "alert_family" to alertFamily,
                    "can_draw_overlays" to canDrawOverlays.toString(),
                    "keyguard_locked" to keyguardManager.isKeyguardLocked.toString(),
                    "use_focused_payment_actions" to useFocusedPaymentActions.toString(),
                ),
            )
            if (keyguardManager.isKeyguardLocked) {
                DebugObservability.traceAsync(
                    context = context,
                    tag = AppConstants.LogTags.DEBUG_OBSERVABILITY,
                    event = "alert_show_aborted",
                    fields = mapOf(
                        "alert_id" to resolvedAlertId,
                        "reason" to "keyguard_locked",
                    ),
                )
                return@post
            }
            val alertIntent = buildAlertIntent(
                context = context,
                alertId = resolvedAlertId,
                title = title,
                primaryBody = primaryBody,
                severity = resolvedSeverity,
                pauseSeconds = pauseSeconds,
                whyThisAlert = whyThisAlert,
                nextSafeAction = nextSafeAction,
                essentialGoalImpact = essentialGoalImpact,
                primaryActionLabel = primaryActionLabel,
                focusedActionLabels = focusedActionLabels,
                proceedConfirmationLabel = proceedConfirmationLabel,
                alertFamily = alertFamily,
                showUsefulnessFeedback = showUsefulnessFeedback,
                useFocusedPaymentActions = useFocusedPaymentActions,
            )

            DebugObservability.traceAsync(
                context = context,
                tag = AppConstants.LogTags.DEBUG_OBSERVABILITY,
                event = "alert_overlay_attempted",
                fields = mapOf(
                    "alert_id" to resolvedAlertId,
                    "can_draw_overlays" to canDrawOverlays.toString(),
                ),
            )

            val overlayShown = if (canDrawOverlays) {
                OverlayAlertWindow.show(
                    context = context,
                    alertId = resolvedAlertId,
                    title = title,
                    message = primaryBody,
                    severity = resolvedSeverity,
                    pauseSeconds = pauseSeconds,
                    whyThisAlert = whyThisAlert,
                    nextSafeAction = nextSafeAction,
                    essentialGoalImpact = essentialGoalImpact,
                    primaryActionLabel = primaryActionLabel,
                    focusedActionLabels = focusedActionLabels,
                    proceedConfirmationLabel = proceedConfirmationLabel,
                    alertFamily = alertFamily,
                    showUsefulnessFeedback = showUsefulnessFeedback,
                    useFocusedPaymentActions = useFocusedPaymentActions,
                )
            } else {
                false
            }

            DebugObservability.traceAsync(
                context = context,
                tag = AppConstants.LogTags.DEBUG_OBSERVABILITY,
                event = "alert_overlay_result",
                fields = mapOf(
                    "alert_id" to resolvedAlertId,
                    "overlay_shown" to overlayShown.toString(),
                    "can_draw_overlays" to canDrawOverlays.toString(),
                ),
            )

            if (!overlayShown) {
                // Fallback when overlay permission is absent or blocked.
                val fallbackStarted = runCatching {
                    context.startActivity(alertIntent)
                    true
                }.getOrElse { false }
                DebugObservability.traceAsync(
                    context = context,
                    tag = AppConstants.LogTags.DEBUG_OBSERVABILITY,
                    event = "alert_activity_fallback_result",
                    fields = mapOf(
                        "alert_id" to resolvedAlertId,
                        "fallback_started" to fallbackStarted.toString(),
                    ),
                )
            }
            postAlertNotification(
                context = context,
                alertId = resolvedAlertId,
                title = title,
                primaryBody = primaryBody,
                style = style,
                alertIntent = alertIntent,
            )
        }
    }

    fun postReturnPathNotification(
        context: Context,
        alertId: String,
        title: String,
        body: String,
        severity: String,
        pauseSeconds: Int,
        whyThisAlert: String,
        nextSafeAction: String,
        essentialGoalImpact: String,
        primaryActionLabel: String,
        focusedActionLabels: List<String>? = null,
        proceedConfirmationLabel: String? = null,
        alertFamily: String?,
        showUsefulnessFeedback: Boolean,
        useFocusedPaymentActions: Boolean,
    ) {
        ensureChannel(context)
        val resolvedSeverity = normalizeSeverity(severity)
        val style = styleForSeverity(resolvedSeverity)
        val primaryBody = sanitizeBody(
            body = body,
            hasExplainabilitySections = whyThisAlert.isNotBlank() ||
                nextSafeAction.isNotBlank() ||
                essentialGoalImpact.isNotBlank(),
        )
        val alertIntent = buildAlertIntent(
            context = context,
            alertId = alertId,
            title = title,
            primaryBody = primaryBody,
            severity = resolvedSeverity,
            pauseSeconds = pauseSeconds,
            whyThisAlert = whyThisAlert,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
            primaryActionLabel = primaryActionLabel,
            focusedActionLabels = focusedActionLabels,
            proceedConfirmationLabel = proceedConfirmationLabel,
            alertFamily = alertFamily,
            showUsefulnessFeedback = showUsefulnessFeedback,
            useFocusedPaymentActions = useFocusedPaymentActions,
        )
        postAlertNotification(
            context = context,
            alertId = alertId,
            title = title,
            primaryBody = primaryBody,
            style = style,
            alertIntent = alertIntent,
        )
    }

    private fun buildAlertIntent(
        context: Context,
        alertId: String,
        title: String,
        primaryBody: String,
        severity: String,
        pauseSeconds: Int,
        whyThisAlert: String?,
        nextSafeAction: String?,
        essentialGoalImpact: String?,
        primaryActionLabel: String?,
        focusedActionLabels: List<String>?,
        proceedConfirmationLabel: String?,
        alertFamily: String?,
        showUsefulnessFeedback: Boolean,
        useFocusedPaymentActions: Boolean,
    ): Intent {
        return Intent(context, AlertDisplayActivity::class.java).apply {
            putExtra(AlertDisplayActivity.EXTRA_TITLE, title)
            putExtra(AlertDisplayActivity.EXTRA_MESSAGE, primaryBody)
            putExtra(AlertDisplayActivity.EXTRA_ALERT_ID, alertId)
            putExtra(AlertDisplayActivity.EXTRA_PAUSE_SECONDS, pauseSeconds)
            putExtra(AlertDisplayActivity.EXTRA_SEVERITY, severity)
            putExtra(AlertDisplayActivity.EXTRA_WHY_THIS_ALERT, whyThisAlert)
            putExtra(AlertDisplayActivity.EXTRA_NEXT_SAFE_ACTION, nextSafeAction)
            putExtra(AlertDisplayActivity.EXTRA_ESSENTIAL_GOAL_IMPACT, essentialGoalImpact)
            putExtra(AlertDisplayActivity.EXTRA_PRIMARY_ACTION_LABEL, primaryActionLabel)
            putStringArrayListExtra(
                AlertDisplayActivity.EXTRA_FOCUSED_ACTION_LABELS,
                ArrayList(focusedActionLabels ?: emptyList()),
            )
            putExtra(AlertDisplayActivity.EXTRA_PROCEED_CONFIRMATION_LABEL, proceedConfirmationLabel)
            putExtra(AlertDisplayActivity.EXTRA_ALERT_FAMILY, alertFamily)
            putExtra(AlertDisplayActivity.EXTRA_SHOW_USEFULNESS_FEEDBACK, showUsefulnessFeedback)
            putExtra(AlertDisplayActivity.EXTRA_USE_FOCUSED_PAYMENT_ACTIONS, useFocusedPaymentActions)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
    }

    private fun postAlertNotification(
        context: Context,
        alertId: String,
        title: String,
        primaryBody: String,
        style: AlertVisualStyle,
        alertIntent: Intent,
    ) {
        val pendingIntentFlags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val reopenIntent = PendingIntent.getActivity(
            context,
            notificationIdForAlert(alertId),
            alertIntent,
            pendingIntentFlags,
        )

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ActivityCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            DebugObservability.traceAsync(
                context = context,
                tag = AppConstants.LogTags.DEBUG_OBSERVABILITY,
                event = "alert_notification_skipped",
                fields = mapOf(
                    "alert_id" to alertId,
                    "reason" to "missing_post_notifications_permission",
                ),
            )
            return
        }

        val notification = NotificationCompat.Builder(context, AppConstants.Notifications.SAFETY_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(primaryBody)
            .setStyle(NotificationCompat.BigTextStyle().bigText(primaryBody))
            .setPriority(style.notificationPriority)
            .setCategory(NotificationCompat.CATEGORY_RECOMMENDATION)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setContentIntent(reopenIntent)
            .setAutoCancel(true)
            .setColor(ContextCompat.getColor(context, style.badgeTextColorRes))
            .build()

        NotificationManagerCompat.from(context).notify(notificationIdForAlert(alertId), notification)
        DebugObservability.traceAsync(
            context = context,
            tag = AppConstants.LogTags.DEBUG_OBSERVABILITY,
            event = "alert_notification_posted",
            fields = mapOf(
                "alert_id" to alertId,
                "notification_priority" to style.notificationPriority.toString(),
            ),
        )
    }

    private fun notificationIdForAlert(alertId: String): Int {
        return (alertId.hashCode() and Int.MAX_VALUE).takeIf { it != 0 } ?: AppConstants.Notifications.FULL_SCREEN_INTENT_ID
    }

    private fun sanitizeBody(body: String, hasExplainabilitySections: Boolean): String {
        if (!hasExplainabilitySections) {
            return body
        }
        var minIndex = -1
        for (marker in explainabilityMarkers) {
            val idx = body.indexOf(marker)
            if (idx >= 0 && (minIndex == -1 || idx < minIndex)) {
                minIndex = idx
            }
        }
        return if (minIndex > 0) body.substring(0, minIndex).trim() else body
    }

    fun normalizeSeverity(severity: String?): String {
        return when (severity?.trim()?.lowercase()) {
            "soft" -> "soft"
            "hard" -> "hard"
            else -> "medium"
        }
    }

    fun styleForSeverity(severity: String): AlertVisualStyle {
        return when (normalizeSeverity(severity)) {
            "soft" -> AlertVisualStyle(
                scrimColorRes = R.color.alert_soft_scrim,
                badgeBgColorRes = R.color.alert_soft_badge_bg,
                badgeTextColorRes = R.color.alert_soft_badge_text,
                tagTextRes = R.string.alert_tag_soft,
                notificationPriority = NotificationCompat.PRIORITY_DEFAULT,
            )
            "hard" -> AlertVisualStyle(
                scrimColorRes = R.color.alert_hard_scrim,
                badgeBgColorRes = R.color.alert_hard_badge_bg,
                badgeTextColorRes = R.color.alert_hard_badge_text,
                tagTextRes = R.string.alert_tag_hard,
                notificationPriority = NotificationCompat.PRIORITY_HIGH,
            )
            else -> AlertVisualStyle(
                scrimColorRes = R.color.alert_medium_scrim,
                badgeBgColorRes = R.color.alert_medium_badge_bg,
                badgeTextColorRes = R.color.alert_medium_badge_text,
                tagTextRes = R.string.alert_tag_medium,
                notificationPriority = NotificationCompat.PRIORITY_HIGH,
            )
        }
    }
}
