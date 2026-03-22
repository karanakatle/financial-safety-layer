package com.arthamantri.android.notify

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.PixelFormat
import android.os.Build
import android.os.CountDownTimer
import android.provider.Settings
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import java.util.UUID

object OverlayAlertWindow {
    private var overlayView: View? = null
    private var pauseTimer: CountDownTimer? = null
    private var currentAlertId: String? = null
    private var currentTerminalOutcomeReported: Boolean = false
    private var currentTitle: String = ""
    private var currentMessage: String = ""
    private var currentWhyThisAlert: String = ""
    private var currentNextSafeAction: String = ""
    private var currentEssentialGoalImpact: String = ""
    private var currentSeverity: String = "medium"
    private var currentAlertFamily: String = ""
    private var currentPrimaryActionLabel: String = ""
    private var currentFocusedActionLabels: List<String> = emptyList()
    private var currentProceedConfirmationLabel: String = ""
    private var currentShowUsefulnessFeedback: Boolean = false
    private var currentUseFocusedPaymentActions: Boolean = false
    private var currentPauseSeconds: Int = 0

    fun show(
        context: Context,
        alertId: String,
        title: String,
        message: String,
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
    ): Boolean {
        if (!canShowOverlay(context)) {
            return false
        }

        val appContext = context.applicationContext
        val wm = appContext.getSystemService(Context.WINDOW_SERVICE) as WindowManager

        if (overlayView != null) {
            if (currentAlertId != null && currentAlertId != alertId) {
                reportTerminalOutcome(appContext, AppConstants.Domain.ALERT_ACTION_REPLACED)
            }
            updateContent(
                alertId = alertId,
                title = title,
                message = message,
                severity = severity,
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
            return true
        }

        val view = LayoutInflater.from(appContext).inflate(R.layout.view_overlay_alert, null, false)
        view.findViewById<TextView>(R.id.overlayAlertTitle).text = title
        view.findViewById<TextView>(R.id.overlayAlertMessage).text = message
        applySeverityStyle(view, severity)
        bindExplainability(
            view = view,
            whyThisAlert = whyThisAlert,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
        )

        currentAlertId = alertId
        currentTerminalOutcomeReported = false
        currentTitle = title
        currentMessage = message
        currentWhyThisAlert = whyThisAlert.orEmpty()
        currentNextSafeAction = nextSafeAction.orEmpty()
        currentEssentialGoalImpact = essentialGoalImpact.orEmpty()
        currentSeverity = severity
        currentAlertFamily = alertFamily.orEmpty()
        currentPrimaryActionLabel = primaryActionLabel.orEmpty()
        currentFocusedActionLabels = focusedActionLabels ?: emptyList()
        currentProceedConfirmationLabel = proceedConfirmationLabel.orEmpty()
        currentShowUsefulnessFeedback = showUsefulnessFeedback
        currentUseFocusedPaymentActions = useFocusedPaymentActions
        currentPauseSeconds = pauseSeconds

        bindActionMode(
            view = view,
            appContext = appContext,
            primaryActionLabel = primaryActionLabel,
            focusedActionLabels = focusedActionLabels,
            proceedConfirmationLabel = proceedConfirmationLabel,
            alertFamily = alertFamily,
            showUsefulnessFeedback = showUsefulnessFeedback,
            useFocusedPaymentActions = useFocusedPaymentActions,
        )
        setupPause(view, pauseSeconds)

        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            type,
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.CENTER
        }

        wm.addView(view, params)
        overlayView = view
        return true
    }

    fun dismiss(context: Context) {
        val view = overlayView ?: return
        pauseTimer?.cancel()
        pauseTimer = null
        val appContext = context.applicationContext
        val wm = appContext.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        runCatching { wm.removeView(view) }
        overlayView = null
        resetCurrentAlertState()
    }

    private fun updateContent(
        alertId: String,
        title: String,
        message: String,
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
    ) {
        val view = overlayView ?: return
        val isNewAlert = currentAlertId != alertId
        currentAlertId = alertId
        if (isNewAlert) {
            currentTerminalOutcomeReported = false
        }
        currentTitle = title
        currentMessage = message
        currentWhyThisAlert = whyThisAlert.orEmpty()
        currentNextSafeAction = nextSafeAction.orEmpty()
        currentEssentialGoalImpact = essentialGoalImpact.orEmpty()
        currentSeverity = severity
        currentAlertFamily = alertFamily.orEmpty()
        currentPrimaryActionLabel = primaryActionLabel.orEmpty()
        currentFocusedActionLabels = focusedActionLabels ?: emptyList()
        currentProceedConfirmationLabel = proceedConfirmationLabel.orEmpty()
        currentShowUsefulnessFeedback = showUsefulnessFeedback
        currentUseFocusedPaymentActions = useFocusedPaymentActions
        currentPauseSeconds = pauseSeconds
        view.findViewById<TextView>(R.id.overlayAlertTitle).text = title
        view.findViewById<TextView>(R.id.overlayAlertMessage).text = message
        applySeverityStyle(view, severity)
        bindExplainability(
            view = view,
            whyThisAlert = whyThisAlert,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
        )
        bindActionMode(
            view = view,
            appContext = view.context.applicationContext,
            primaryActionLabel = primaryActionLabel,
            focusedActionLabels = focusedActionLabels,
            proceedConfirmationLabel = proceedConfirmationLabel,
            alertFamily = alertFamily,
            showUsefulnessFeedback = showUsefulnessFeedback,
            useFocusedPaymentActions = useFocusedPaymentActions,
        )
        setupPause(view, pauseSeconds)
    }

    private fun bindExplainability(
        view: View,
        whyThisAlert: String?,
        nextSafeAction: String?,
        essentialGoalImpact: String?,
    ) {
        val whyHeading = view.findViewById<TextView>(R.id.overlayWhyHeading)
        val whyBody = view.findViewById<TextView>(R.id.overlayWhyBody)
        val nextActionHeading = view.findViewById<TextView>(R.id.overlayNextActionHeading)
        val nextActionBody = view.findViewById<TextView>(R.id.overlayNextActionBody)
        val goalImpactHeading = view.findViewById<TextView>(R.id.overlayGoalImpactHeading)
        val goalImpactBody = view.findViewById<TextView>(R.id.overlayGoalImpactBody)

        val whyValue = whyThisAlert?.trim().orEmpty()
        if (whyValue.isNotEmpty()) {
            whyHeading.visibility = View.VISIBLE
            whyBody.visibility = View.VISIBLE
            whyBody.text = whyValue
        } else {
            whyHeading.visibility = View.GONE
            whyBody.visibility = View.GONE
        }

        val nextActionValue = nextSafeAction?.trim().orEmpty()
        if (nextActionValue.isNotEmpty()) {
            nextActionHeading.visibility = View.VISIBLE
            nextActionBody.visibility = View.VISIBLE
            nextActionBody.text = nextActionValue
        } else {
            nextActionHeading.visibility = View.GONE
            nextActionBody.visibility = View.GONE
        }

        val goalImpactValue = essentialGoalImpact?.trim().orEmpty()
        if (goalImpactValue.isNotEmpty()) {
            goalImpactHeading.visibility = View.VISIBLE
            goalImpactBody.visibility = View.VISIBLE
            goalImpactBody.text = goalImpactValue
        } else {
            goalImpactHeading.visibility = View.GONE
            goalImpactBody.visibility = View.GONE
        }
    }

    private fun bindActionMode(
        view: View,
        appContext: Context,
        primaryActionLabel: String?,
        focusedActionLabels: List<String>?,
        proceedConfirmationLabel: String?,
        alertFamily: String?,
        showUsefulnessFeedback: Boolean,
        useFocusedPaymentActions: Boolean,
    ) {
        val dismissBtn = view.findViewById<Button>(R.id.overlayDismissBtn)
        val usefulBtn = view.findViewById<Button>(R.id.overlayUsefulBtn)
        val notUsefulBtn = view.findViewById<Button>(R.id.overlayNotUsefulBtn)
        val trustedPersonBtn = view.findViewById<Button>(R.id.overlayTrustedPersonBtn)
        val supportBtn = view.findViewById<Button>(R.id.overlaySupportBtn)
        val usefulnessHint = view.findViewById<TextView>(R.id.overlayUsefulnessHint)
        val feedbackRow = view.findViewById<View>(R.id.overlayFeedbackRow)
        val proceedConfirmGroup = view.findViewById<View>(R.id.overlayProceedConfirmGroup)
        val confirmProceedBtn = view.findViewById<Button>(R.id.overlayConfirmProceedBtn)
        proceedConfirmGroup.visibility = View.GONE

        if (useFocusedPaymentActions) {
            val defaultLabels = if (alertFamily == AppConstants.Domain.ALERT_FAMILY_ACCOUNT_ACCESS) {
                listOf(
                    view.context.getString(R.string.alert_action_pause),
                    view.context.getString(R.string.alert_action_protect_account),
                    view.context.getString(R.string.alert_action_continue_anyway),
                )
            } else {
                listOf(
                    view.context.getString(R.string.alert_action_pause),
                    view.context.getString(R.string.alert_action_decline),
                    view.context.getString(R.string.alert_action_proceed),
                )
            }
            val resolvedLabels = if ((focusedActionLabels ?: emptyList()).size >= 3) {
                focusedActionLabels ?: emptyList()
            } else {
                defaultLabels
            }
            dismissBtn.text = resolvedLabels[0]
            usefulBtn.text = resolvedLabels[1]
            notUsefulBtn.text = resolvedLabels[2]
            trustedPersonBtn.visibility = View.VISIBLE
            trustedPersonBtn.text = view.context.getString(R.string.alert_action_trusted_person)
            supportBtn.visibility = View.VISIBLE
            supportBtn.text = view.context.getString(R.string.alert_action_support)
            usefulnessHint.visibility = View.GONE
            feedbackRow.visibility = View.VISIBLE
            notUsefulBtn.setBackgroundResource(R.drawable.bg_btn_low_emphasis)
            notUsefulBtn.setTextColor(ContextCompat.getColor(view.context, R.color.text_secondary))
            confirmProceedBtn.text = proceedConfirmationLabel?.takeIf { it.isNotBlank() } ?: view.context.getString(
                if (alertFamily == AppConstants.Domain.ALERT_FAMILY_ACCOUNT_ACCESS) {
                    R.string.alert_access_proceed_confirmation_confirm
                } else {
                    R.string.alert_proceed_confirmation_confirm
                }
            )

            dismissBtn.setOnClickListener {
                proceedConfirmGroup.visibility = View.GONE
                reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_PAUSE)
                val resolvedPauseSeconds = if (currentPauseSeconds > 0) {
                    currentPauseSeconds
                } else {
                    AppConstants.Timing.PAYMENT_DECISION_PAUSE_SECONDS
                }
                setupPause(view, resolvedPauseSeconds)
            }
            usefulBtn.setOnClickListener {
                proceedConfirmGroup.visibility = View.GONE
                reportTerminalOutcome(appContext, AppConstants.Domain.ALERT_ACTION_DECLINE)
                dismiss(appContext)
            }
            trustedPersonBtn.setOnClickListener {
                proceedConfirmGroup.visibility = View.GONE
                launchTrustedPersonHandoff(appContext, view.context)
            }
            supportBtn.setOnClickListener {
                proceedConfirmGroup.visibility = View.GONE
                launchSupportPath(appContext, view.context)
            }
            notUsefulBtn.setOnClickListener {
                proceedConfirmGroup.visibility = View.VISIBLE
                confirmProceedBtn.isEnabled = dismissBtn.isEnabled
            }
            confirmProceedBtn.setOnClickListener {
                reportTerminalOutcome(appContext, AppConstants.Domain.ALERT_ACTION_PROCEED)
                dismiss(appContext)
            }
        } else {
            dismissBtn.text = if (!primaryActionLabel.isNullOrBlank()) {
                primaryActionLabel
            } else {
                view.context.getString(R.string.alert_ack_short)
            }
            usefulBtn.text = view.context.getString(R.string.alert_feedback_useful)
            notUsefulBtn.text = view.context.getString(R.string.alert_feedback_not_useful)
            trustedPersonBtn.visibility = View.GONE
            supportBtn.visibility = View.GONE
            notUsefulBtn.setBackgroundResource(R.drawable.bg_btn_secondary)
            notUsefulBtn.setTextColor(ContextCompat.getColor(view.context, R.color.btn_secondary_text))
            val shouldShowFeedback = showUsefulnessFeedback ||
                alertFamily == AppConstants.Domain.ALERT_FAMILY_CASHFLOW
            usefulnessHint.visibility = if (shouldShowFeedback) View.VISIBLE else View.GONE
            feedbackRow.visibility = if (shouldShowFeedback) View.VISIBLE else View.GONE

            dismissBtn.setOnClickListener {
                reportTerminalOutcome(appContext, AppConstants.Domain.ALERT_ACTION_DISMISSED)
                dismiss(appContext)
            }
            usefulBtn.setOnClickListener {
                reportTerminalOutcome(appContext, AppConstants.Domain.ALERT_ACTION_USEFUL)
                dismiss(appContext)
            }
            notUsefulBtn.setOnClickListener {
                reportTerminalOutcome(appContext, AppConstants.Domain.ALERT_ACTION_NOT_USEFUL)
                dismiss(appContext)
            }
        }
    }

    private fun setupPause(view: View, pauseSeconds: Int) {
        pauseTimer?.cancel()
        pauseTimer = null
        val pauseHint = view.findViewById<TextView>(R.id.overlayPauseHint)
        val dismissBtn = view.findViewById<Button>(R.id.overlayDismissBtn)
        val usefulBtn = view.findViewById<Button>(R.id.overlayUsefulBtn)
        val notUsefulBtn = view.findViewById<Button>(R.id.overlayNotUsefulBtn)
        val trustedPersonBtn = view.findViewById<Button>(R.id.overlayTrustedPersonBtn)
        val supportBtn = view.findViewById<Button>(R.id.overlaySupportBtn)
        val confirmProceedBtn = view.findViewById<Button>(R.id.overlayConfirmProceedBtn)
        val proceedConfirmGroup = view.findViewById<View>(R.id.overlayProceedConfirmGroup)

        if (pauseSeconds <= 0) {
            pauseHint.visibility = View.GONE
            setActionEnabledState(
                enabled = true,
                dismissBtn = dismissBtn,
                usefulBtn = usefulBtn,
                notUsefulBtn = notUsefulBtn,
                trustedPersonBtn = trustedPersonBtn,
                supportBtn = supportBtn,
                confirmProceedBtn = confirmProceedBtn,
                proceedConfirmGroup = proceedConfirmGroup,
            )
            return
        }

        setActionEnabledState(
            enabled = false,
            dismissBtn = dismissBtn,
            usefulBtn = usefulBtn,
            notUsefulBtn = notUsefulBtn,
            trustedPersonBtn = trustedPersonBtn,
            supportBtn = supportBtn,
            confirmProceedBtn = confirmProceedBtn,
            proceedConfirmGroup = proceedConfirmGroup,
        )
        pauseHint.visibility = View.VISIBLE
        pauseHint.text = view.context.getString(R.string.alert_pause_countdown, pauseSeconds)

        pauseTimer = object : CountDownTimer((pauseSeconds * 1000L), 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                val secondsLeft = ((millisUntilFinished + 999L) / 1000L).toInt()
                pauseHint.text = view.context.getString(R.string.alert_pause_countdown, secondsLeft)
            }

            override fun onFinish() {
                pauseHint.visibility = View.GONE
                setActionEnabledState(
                    enabled = true,
                    dismissBtn = dismissBtn,
                    usefulBtn = usefulBtn,
                    notUsefulBtn = notUsefulBtn,
                    trustedPersonBtn = trustedPersonBtn,
                    supportBtn = supportBtn,
                    confirmProceedBtn = confirmProceedBtn,
                    proceedConfirmGroup = proceedConfirmGroup,
                )
            }
        }.start()
    }

    private fun setActionEnabledState(
        enabled: Boolean,
        dismissBtn: Button,
        usefulBtn: Button,
        notUsefulBtn: Button,
        trustedPersonBtn: Button,
        supportBtn: Button,
        confirmProceedBtn: Button,
        proceedConfirmGroup: View,
    ) {
        dismissBtn.isEnabled = enabled
        usefulBtn.isEnabled = enabled
        notUsefulBtn.isEnabled = enabled
        trustedPersonBtn.isEnabled = enabled
        supportBtn.isEnabled = enabled
        confirmProceedBtn.isEnabled = enabled && proceedConfirmGroup.visibility == View.VISIBLE
    }

    private fun launchTrustedPersonHandoff(appContext: Context, viewContext: Context) {
        reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_TRUSTED_PERSON_REQUESTED)

        val launched = TrustedPersonHandoffLauncher.launch(
            context = appContext,
            title = currentTitle,
            body = currentMessage,
            nextSafeAction = currentNextSafeAction,
        )

        if (!launched) {
            reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_TRUSTED_PERSON_FAILED)
            Toast.makeText(
                viewContext,
                viewContext.getString(R.string.alert_trusted_person_launch_failed),
                Toast.LENGTH_SHORT,
            ).show()
            return
        }

        reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_TRUSTED_PERSON_LAUNCHED)
        postReturnPathNotification(appContext)
        dismiss(appContext)
    }

    private fun launchSupportPath(appContext: Context, viewContext: Context) {
        reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_SUPPORT_REQUESTED)

        val launched = SupportEscalationLauncher.launch(
            context = appContext,
            alertId = currentAlertId ?: UUID.randomUUID().toString(),
            title = currentTitle,
            body = currentMessage,
            severity = currentSeverity,
            pauseSeconds = currentPauseSeconds,
            whyThisAlert = currentWhyThisAlert,
            nextSafeAction = currentNextSafeAction,
            essentialGoalImpact = currentEssentialGoalImpact,
            primaryActionLabel = currentPrimaryActionLabel,
            focusedActionLabels = currentFocusedActionLabels,
            proceedConfirmationLabel = currentProceedConfirmationLabel,
            useFocusedPaymentActions = currentUseFocusedPaymentActions,
        )

        if (!launched) {
            reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_SUPPORT_FAILED)
            Toast.makeText(
                viewContext,
                viewContext.getString(R.string.alert_support_launch_failed),
                Toast.LENGTH_SHORT,
            ).show()
            return
        }

        reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_SUPPORT_OPENED)
        postReturnPathNotification(appContext)
        dismiss(appContext)
    }

    private fun reportFeedback(context: Context, action: String) {
        AlertFeedbackReporter.report(
            context = context,
            alertId = currentAlertId ?: UUID.randomUUID().toString(),
            action = action,
            channel = "overlay_window",
            title = currentTitle,
            message = buildCurrentReportMessage(),
        )
    }

    private fun reportTerminalOutcome(context: Context, action: String) {
        if (currentTerminalOutcomeReported) {
            return
        }
        currentTerminalOutcomeReported = true
        reportFeedback(context, action)
    }

    private fun buildCurrentReportMessage(): String {
        return listOf(
            currentMessage,
            currentWhyThisAlert,
            currentNextSafeAction,
            currentEssentialGoalImpact,
        ).filter { it.isNotBlank() }.joinToString("\n")
    }

    private fun resetCurrentAlertState() {
        currentAlertId = null
        currentTerminalOutcomeReported = false
        currentTitle = ""
        currentMessage = ""
        currentWhyThisAlert = ""
        currentNextSafeAction = ""
        currentEssentialGoalImpact = ""
        currentSeverity = "medium"
        currentAlertFamily = ""
        currentPrimaryActionLabel = ""
        currentFocusedActionLabels = emptyList()
        currentProceedConfirmationLabel = ""
        currentShowUsefulnessFeedback = false
        currentUseFocusedPaymentActions = false
        currentPauseSeconds = 0
    }

    private fun postReturnPathNotification(context: Context) {
        val alertId = currentAlertId ?: return
        AlertNotifier.postReturnPathNotification(
            context = context,
            alertId = alertId,
            title = currentTitle,
            body = currentMessage,
            severity = currentSeverity,
            pauseSeconds = currentPauseSeconds,
            whyThisAlert = currentWhyThisAlert,
            nextSafeAction = currentNextSafeAction,
            essentialGoalImpact = currentEssentialGoalImpact,
            primaryActionLabel = currentPrimaryActionLabel,
            focusedActionLabels = currentFocusedActionLabels,
            proceedConfirmationLabel = currentProceedConfirmationLabel,
            alertFamily = currentAlertFamily.ifBlank { null },
            showUsefulnessFeedback = currentShowUsefulnessFeedback,
            useFocusedPaymentActions = currentUseFocusedPaymentActions,
        )
    }

    private fun canShowOverlay(context: Context): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(context)
    }

    private fun applySeverityStyle(view: View, severity: String) {
        val context = view.context
        val style = AlertNotifier.styleForSeverity(severity)
        val scrim = view.findViewById<View>(R.id.overlayScrim)
        val tag = view.findViewById<TextView>(R.id.overlayAlertTag)
        val title = view.findViewById<TextView>(R.id.overlayAlertTitle)
        val dismissBtn = view.findViewById<Button>(R.id.overlayDismissBtn)

        scrim.setBackgroundColor(ContextCompat.getColor(context, style.scrimColorRes))
        tag.text = context.getString(style.tagTextRes)
        tag.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(context, style.badgeBgColorRes))
        tag.setTextColor(ContextCompat.getColor(context, style.badgeTextColorRes))
        title.setTextColor(ContextCompat.getColor(context, style.badgeTextColorRes))
        dismissBtn.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(context, style.badgeTextColorRes))
    }
}
