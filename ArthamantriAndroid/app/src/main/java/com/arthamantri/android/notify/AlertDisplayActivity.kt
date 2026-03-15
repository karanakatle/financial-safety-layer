package com.arthamantri.android.notify

import android.content.res.ColorStateList
import android.os.Bundle
import android.os.CountDownTimer
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import java.util.UUID

class AlertDisplayActivity : AppCompatActivity() {
    private var pauseTimer: CountDownTimer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_alert_display)

        val alertId = intent.getStringExtra(EXTRA_ALERT_ID) ?: UUID.randomUUID().toString()
        val title = intent.getStringExtra(EXTRA_TITLE) ?: getString(R.string.alert_title_default)
        val message = intent.getStringExtra(EXTRA_MESSAGE)
            ?: getString(R.string.alert_body_default)
        val pauseSeconds = intent.getIntExtra(EXTRA_PAUSE_SECONDS, 0)
        val severity = intent.getStringExtra(EXTRA_SEVERITY).orEmpty()
        val whyThisAlert = intent.getStringExtra(EXTRA_WHY_THIS_ALERT).orEmpty()
        val nextSafeAction = intent.getStringExtra(EXTRA_NEXT_SAFE_ACTION).orEmpty()
        val essentialGoalImpact = intent.getStringExtra(EXTRA_ESSENTIAL_GOAL_IMPACT).orEmpty()
        val primaryActionLabel = intent.getStringExtra(EXTRA_PRIMARY_ACTION_LABEL).orEmpty()
        val useFocusedPaymentActions = intent.getBooleanExtra(EXTRA_USE_FOCUSED_PAYMENT_ACTIONS, false)

        findViewById<TextView>(R.id.alertTitle).text = title
        findViewById<TextView>(R.id.alertMessage).text = message
        bindExplainability(whyThisAlert, nextSafeAction, essentialGoalImpact)
        val dismissBtn = findViewById<Button>(R.id.dismissBtn)
        val usefulBtn = findViewById<Button>(R.id.usefulBtn)
        val notUsefulBtn = findViewById<Button>(R.id.notUsefulBtn)
        val pauseHint = findViewById<TextView>(R.id.alertPauseHint)
        val proceedConfirmGroup = findViewById<View>(R.id.alertProceedConfirmGroup)
        val confirmProceedBtn = findViewById<Button>(R.id.confirmProceedBtn)
        val reportMessage = buildReportMessage(message, whyThisAlert, nextSafeAction, essentialGoalImpact)

        configureActionMode(
            useFocusedPaymentActions = useFocusedPaymentActions,
            primaryActionLabel = primaryActionLabel,
            dismissBtn = dismissBtn,
            usefulBtn = usefulBtn,
            notUsefulBtn = notUsefulBtn,
        )
        applySeverityStyle(severity)
        setupPause(
            pauseSeconds = pauseSeconds,
            pauseHint = pauseHint,
            dismissBtn = dismissBtn,
            usefulBtn = usefulBtn,
            notUsefulBtn = notUsefulBtn,
            confirmProceedBtn = confirmProceedBtn,
            proceedConfirmGroup = proceedConfirmGroup,
        )

        if (useFocusedPaymentActions) {
            dismissBtn.setOnClickListener {
                hideProceedConfirmation(proceedConfirmGroup)
                reportAction(
                    alertId = alertId,
                    action = AppConstants.Domain.ALERT_ACTION_PAUSE,
                    title = title,
                    message = reportMessage,
                )
                startManualPause(
                    pauseSeconds = pauseSeconds,
                    pauseHint = pauseHint,
                    dismissBtn = dismissBtn,
                    usefulBtn = usefulBtn,
                    notUsefulBtn = notUsefulBtn,
                    confirmProceedBtn = confirmProceedBtn,
                    proceedConfirmGroup = proceedConfirmGroup,
                )
            }
            usefulBtn.setOnClickListener {
                hideProceedConfirmation(proceedConfirmGroup)
                reportAction(
                    alertId = alertId,
                    action = AppConstants.Domain.ALERT_ACTION_DECLINE,
                    title = title,
                    message = reportMessage,
                )
                finish()
            }
            notUsefulBtn.setOnClickListener {
                proceedConfirmGroup.visibility = View.VISIBLE
                confirmProceedBtn.isEnabled = dismissBtn.isEnabled
            }
            confirmProceedBtn.setOnClickListener {
                reportAction(
                    alertId = alertId,
                    action = AppConstants.Domain.ALERT_ACTION_PROCEED,
                    title = title,
                    message = reportMessage,
                )
                finish()
            }
        } else {
            usefulBtn.setOnClickListener {
                reportAction(
                    alertId = alertId,
                    action = AppConstants.Domain.ALERT_ACTION_USEFUL,
                    title = title,
                    message = reportMessage,
                )
                finish()
            }
            notUsefulBtn.setOnClickListener {
                reportAction(
                    alertId = alertId,
                    action = AppConstants.Domain.ALERT_ACTION_NOT_USEFUL,
                    title = title,
                    message = reportMessage,
                )
                finish()
            }
            dismissBtn.setOnClickListener {
                reportAction(
                    alertId = alertId,
                    action = AppConstants.Domain.ALERT_ACTION_DISMISSED,
                    title = title,
                    message = reportMessage,
                )
                finish()
            }
        }
    }

    override fun onDestroy() {
        pauseTimer?.cancel()
        pauseTimer = null
        super.onDestroy()
    }

    private fun setupPause(
        pauseSeconds: Int,
        pauseHint: TextView,
        dismissBtn: Button,
        usefulBtn: Button,
        notUsefulBtn: Button,
        confirmProceedBtn: Button,
        proceedConfirmGroup: View,
    ) {
        pauseTimer?.cancel()
        pauseTimer = null
        if (pauseSeconds <= 0) {
            pauseHint.text = ""
            setActionEnabledState(
                enabled = true,
                dismissBtn = dismissBtn,
                usefulBtn = usefulBtn,
                notUsefulBtn = notUsefulBtn,
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
            confirmProceedBtn = confirmProceedBtn,
            proceedConfirmGroup = proceedConfirmGroup,
        )
        pauseHint.text = getString(R.string.alert_pause_countdown, pauseSeconds)

        pauseTimer = object : CountDownTimer((pauseSeconds * 1000L), 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                val secondsLeft = ((millisUntilFinished + 999L) / 1000L).toInt()
                pauseHint.text = getString(R.string.alert_pause_countdown, secondsLeft)
            }

            override fun onFinish() {
                pauseHint.text = ""
                setActionEnabledState(
                    enabled = true,
                    dismissBtn = dismissBtn,
                    usefulBtn = usefulBtn,
                    notUsefulBtn = notUsefulBtn,
                    confirmProceedBtn = confirmProceedBtn,
                    proceedConfirmGroup = proceedConfirmGroup,
                )
            }
        }.start()
    }

    private fun startManualPause(
        pauseSeconds: Int,
        pauseHint: TextView,
        dismissBtn: Button,
        usefulBtn: Button,
        notUsefulBtn: Button,
        confirmProceedBtn: Button,
        proceedConfirmGroup: View,
    ) {
        val resolvedPauseSeconds = if (pauseSeconds > 0) {
            pauseSeconds
        } else {
            AppConstants.Timing.PAYMENT_DECISION_PAUSE_SECONDS
        }
        setupPause(
            pauseSeconds = resolvedPauseSeconds,
            pauseHint = pauseHint,
            dismissBtn = dismissBtn,
            usefulBtn = usefulBtn,
            notUsefulBtn = notUsefulBtn,
            confirmProceedBtn = confirmProceedBtn,
            proceedConfirmGroup = proceedConfirmGroup,
        )
    }

    private fun setActionEnabledState(
        enabled: Boolean,
        dismissBtn: Button,
        usefulBtn: Button,
        notUsefulBtn: Button,
        confirmProceedBtn: Button,
        proceedConfirmGroup: View,
    ) {
        dismissBtn.isEnabled = enabled
        usefulBtn.isEnabled = enabled
        notUsefulBtn.isEnabled = enabled
        confirmProceedBtn.isEnabled = enabled && proceedConfirmGroup.visibility == View.VISIBLE
    }

    private fun configureActionMode(
        useFocusedPaymentActions: Boolean,
        primaryActionLabel: String,
        dismissBtn: Button,
        usefulBtn: Button,
        notUsefulBtn: Button,
    ) {
        val proceedConfirmGroup = findViewById<View>(R.id.alertProceedConfirmGroup)
        val confirmProceedBtn = findViewById<Button>(R.id.confirmProceedBtn)
        proceedConfirmGroup.visibility = View.GONE
        if (useFocusedPaymentActions) {
            dismissBtn.text = getString(R.string.alert_action_pause)
            usefulBtn.text = getString(R.string.alert_action_decline)
            notUsefulBtn.text = getString(R.string.alert_action_proceed)
            notUsefulBtn.setBackgroundResource(R.drawable.bg_btn_low_emphasis)
            notUsefulBtn.setTextColor(ContextCompat.getColor(this, R.color.text_secondary))
            confirmProceedBtn.text = getString(R.string.alert_proceed_confirmation_confirm)
        } else {
            dismissBtn.text = if (primaryActionLabel.isNotBlank()) {
                primaryActionLabel
            } else {
                getString(R.string.alert_ack_long)
            }
            usefulBtn.text = getString(R.string.alert_feedback_useful)
            notUsefulBtn.text = getString(R.string.alert_feedback_not_useful)
            notUsefulBtn.setBackgroundResource(R.drawable.bg_btn_secondary)
            notUsefulBtn.setTextColor(ContextCompat.getColor(this, R.color.btn_secondary_text))
        }
    }

    private fun hideProceedConfirmation(proceedConfirmGroup: View) {
        proceedConfirmGroup.visibility = View.GONE
    }

    private fun reportAction(
        alertId: String,
        action: String,
        title: String,
        message: String,
    ) {
        AlertFeedbackReporter.report(
            context = this,
            alertId = alertId,
            action = action,
            channel = "fullscreen_activity",
            title = title,
            message = message,
        )
    }

    private fun buildReportMessage(
        message: String,
        whyThisAlert: String,
        nextSafeAction: String,
        essentialGoalImpact: String,
    ): String {
        return listOf(message, whyThisAlert, nextSafeAction, essentialGoalImpact)
            .filter { it.isNotBlank() }
            .joinToString("\n")
    }

    private fun bindExplainability(whyThisAlert: String, nextSafeAction: String, essentialGoalImpact: String) {
        val whyHeading = findViewById<TextView>(R.id.alertWhyHeading)
        val whyBody = findViewById<TextView>(R.id.alertWhyBody)
        val nextActionHeading = findViewById<TextView>(R.id.alertNextActionHeading)
        val nextActionBody = findViewById<TextView>(R.id.alertNextActionBody)
        val goalImpactHeading = findViewById<TextView>(R.id.alertGoalImpactHeading)
        val goalImpactBody = findViewById<TextView>(R.id.alertGoalImpactBody)

        if (whyThisAlert.isNotBlank()) {
            whyHeading.text = getString(R.string.alert_why_this_alert_label)
            whyHeading.visibility = View.VISIBLE
            whyBody.text = whyThisAlert
            whyBody.visibility = View.VISIBLE
        } else {
            whyHeading.visibility = View.GONE
            whyBody.visibility = View.GONE
        }

        if (nextSafeAction.isNotBlank()) {
            nextActionHeading.text = getString(R.string.alert_next_safe_action_label)
            nextActionHeading.visibility = View.VISIBLE
            nextActionBody.text = nextSafeAction
            nextActionBody.visibility = View.VISIBLE
        } else {
            nextActionHeading.visibility = View.GONE
            nextActionBody.visibility = View.GONE
        }

        if (essentialGoalImpact.isNotBlank()) {
            goalImpactHeading.text = getString(R.string.alert_essential_goal_impact_label)
            goalImpactHeading.visibility = View.VISIBLE
            goalImpactBody.text = essentialGoalImpact
            goalImpactBody.visibility = View.VISIBLE
        } else {
            goalImpactHeading.visibility = View.GONE
            goalImpactBody.visibility = View.GONE
        }
    }

    private fun applySeverityStyle(severity: String) {
        val style = AlertNotifier.styleForSeverity(severity)
        val scrim = findViewById<View>(R.id.alertScrim)
        val tag = findViewById<TextView>(R.id.alertTag)
        val title = findViewById<TextView>(R.id.alertTitle)
        val dismissBtn = findViewById<Button>(R.id.dismissBtn)

        scrim.setBackgroundColor(ContextCompat.getColor(this, style.scrimColorRes))
        tag.text = getString(style.tagTextRes)
        tag.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(this, style.badgeBgColorRes))
        tag.setTextColor(ContextCompat.getColor(this, style.badgeTextColorRes))
        title.setTextColor(ContextCompat.getColor(this, style.badgeTextColorRes))
        dismissBtn.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(this, style.badgeTextColorRes))
    }

    companion object {
        const val EXTRA_TITLE = AppConstants.IntentExtras.ALERT_TITLE
        const val EXTRA_MESSAGE = AppConstants.IntentExtras.ALERT_MESSAGE
        const val EXTRA_ALERT_ID = AppConstants.IntentExtras.ALERT_ID
        const val EXTRA_PAUSE_SECONDS = AppConstants.IntentExtras.ALERT_PAUSE_SECONDS
        const val EXTRA_SEVERITY = AppConstants.IntentExtras.ALERT_SEVERITY
        const val EXTRA_WHY_THIS_ALERT = AppConstants.IntentExtras.ALERT_WHY_THIS_ALERT
        const val EXTRA_NEXT_SAFE_ACTION = AppConstants.IntentExtras.ALERT_NEXT_SAFE_ACTION
        const val EXTRA_ESSENTIAL_GOAL_IMPACT = AppConstants.IntentExtras.ALERT_ESSENTIAL_GOAL_IMPACT
        const val EXTRA_PRIMARY_ACTION_LABEL = AppConstants.IntentExtras.ALERT_PRIMARY_ACTION_LABEL
        const val EXTRA_USE_FOCUSED_PAYMENT_ACTIONS = AppConstants.IntentExtras.ALERT_USE_FOCUSED_PAYMENT_ACTIONS
    }
}
