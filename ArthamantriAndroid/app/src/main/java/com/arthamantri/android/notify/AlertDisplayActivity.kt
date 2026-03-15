package com.arthamantri.android.notify

import android.content.Intent
import android.content.res.ColorStateList
import android.os.Bundle
import android.os.CountDownTimer
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import java.util.UUID

class AlertDisplayActivity : AppCompatActivity() {
    private var pauseTimer: CountDownTimer? = null

    private lateinit var alertId: String
    private lateinit var alertTitle: String
    private lateinit var alertBody: String
    private lateinit var alertSeverity: String
    private var alertPauseSeconds: Int = 0
    private var useFocusedPaymentActions: Boolean = false
    private lateinit var whyThisAlert: String
    private lateinit var nextSafeAction: String
    private lateinit var essentialGoalImpact: String
    private lateinit var primaryActionLabel: String
    private lateinit var reportMessage: String

    private lateinit var dismissBtn: Button
    private lateinit var usefulBtn: Button
    private lateinit var notUsefulBtn: Button
    private lateinit var trustedPersonBtn: Button
    private lateinit var supportBtn: Button
    private lateinit var pauseHint: TextView
    private lateinit var proceedConfirmGroup: View
    private lateinit var confirmProceedBtn: Button

    private var terminalOutcomeReported = false
    private var userLeaving = false
    private var helperHandoffInProgress = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_alert_display)

        bindViews()
        bindBackPress()
        applyAlertIntent(intent, shouldResetTransientState = false)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        applyAlertIntent(intent, shouldResetTransientState = true)
    }

    override fun onResume() {
        super.onResume()
        userLeaving = false
        helperHandoffInProgress = false
    }

    override fun onUserLeaveHint() {
        super.onUserLeaveHint()
        userLeaving = true
    }

    override fun onStop() {
        super.onStop()
        if (!isChangingConfigurations && !terminalOutcomeReported && userLeaving && !helperHandoffInProgress) {
            userLeaving = false
            reportTerminalOutcome(AppConstants.Domain.ALERT_ACTION_BACKGROUNDED)
            postReturnPathNotification()
            finish()
        }
    }

    override fun onDestroy() {
        pauseTimer?.cancel()
        pauseTimer = null
        super.onDestroy()
    }

    private fun bindBackPress() {
        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (proceedConfirmGroup.visibility == View.VISIBLE) {
                        hideProceedConfirmation()
                        return
                    }
                    reportTerminalOutcome(AppConstants.Domain.ALERT_ACTION_BACKED_OUT)
                    postReturnPathNotification()
                    finish()
                }
            },
        )
    }

    private fun bindViews() {
        dismissBtn = findViewById(R.id.dismissBtn)
        usefulBtn = findViewById(R.id.usefulBtn)
        notUsefulBtn = findViewById(R.id.notUsefulBtn)
        trustedPersonBtn = findViewById(R.id.trustedPersonBtn)
        supportBtn = findViewById(R.id.supportBtn)
        pauseHint = findViewById(R.id.alertPauseHint)
        proceedConfirmGroup = findViewById(R.id.alertProceedConfirmGroup)
        confirmProceedBtn = findViewById(R.id.confirmProceedBtn)
    }

    private fun applyAlertIntent(intent: Intent, shouldResetTransientState: Boolean) {
        loadAlertState(intent)
        if (shouldResetTransientState) {
            resetTransientUiState()
        }
        renderAlert()
    }

    private fun loadAlertState(intent: Intent) {
        alertId = intent.getStringExtra(EXTRA_ALERT_ID) ?: UUID.randomUUID().toString()
        alertTitle = intent.getStringExtra(EXTRA_TITLE) ?: getString(R.string.alert_title_default)
        alertBody = intent.getStringExtra(EXTRA_MESSAGE) ?: getString(R.string.alert_body_default)
        alertPauseSeconds = intent.getIntExtra(EXTRA_PAUSE_SECONDS, 0)
        alertSeverity = intent.getStringExtra(EXTRA_SEVERITY).orEmpty()
        whyThisAlert = intent.getStringExtra(EXTRA_WHY_THIS_ALERT).orEmpty()
        nextSafeAction = intent.getStringExtra(EXTRA_NEXT_SAFE_ACTION).orEmpty()
        essentialGoalImpact = intent.getStringExtra(EXTRA_ESSENTIAL_GOAL_IMPACT).orEmpty()
        primaryActionLabel = intent.getStringExtra(EXTRA_PRIMARY_ACTION_LABEL).orEmpty()
        useFocusedPaymentActions = intent.getBooleanExtra(EXTRA_USE_FOCUSED_PAYMENT_ACTIONS, false)
        reportMessage = buildReportMessage(alertBody, whyThisAlert, nextSafeAction, essentialGoalImpact)
    }

    private fun resetTransientUiState() {
        pauseTimer?.cancel()
        pauseTimer = null
        terminalOutcomeReported = false
        userLeaving = false
        helperHandoffInProgress = false
        hideProceedConfirmation()
    }

    private fun renderAlert() {
        findViewById<TextView>(R.id.alertTitle).text = alertTitle
        findViewById<TextView>(R.id.alertMessage).text = alertBody
        bindExplainability(whyThisAlert, nextSafeAction, essentialGoalImpact)
        bindActionListeners()
        configureActionMode()
        applySeverityStyle(alertSeverity)
        setupPause(alertPauseSeconds)
    }

    private fun bindActionListeners() {
        if (useFocusedPaymentActions) {
            dismissBtn.setOnClickListener {
                hideProceedConfirmation()
                reportFeedback(AppConstants.Domain.ALERT_ACTION_PAUSE)
                startManualPause()
            }
            usefulBtn.setOnClickListener {
                hideProceedConfirmation()
                reportTerminalOutcome(AppConstants.Domain.ALERT_ACTION_DECLINE)
                finish()
            }
            trustedPersonBtn.setOnClickListener {
                hideProceedConfirmation()
                launchTrustedPersonHandoff()
            }
            supportBtn.setOnClickListener {
                hideProceedConfirmation()
                launchSupportPath()
            }
            notUsefulBtn.setOnClickListener {
                proceedConfirmGroup.visibility = View.VISIBLE
                confirmProceedBtn.isEnabled = dismissBtn.isEnabled
            }
            confirmProceedBtn.setOnClickListener {
                reportTerminalOutcome(AppConstants.Domain.ALERT_ACTION_PROCEED)
                finish()
            }
        } else {
            usefulBtn.setOnClickListener {
                reportTerminalOutcome(AppConstants.Domain.ALERT_ACTION_USEFUL)
                finish()
            }
            notUsefulBtn.setOnClickListener {
                reportTerminalOutcome(AppConstants.Domain.ALERT_ACTION_NOT_USEFUL)
                finish()
            }
            dismissBtn.setOnClickListener {
                reportTerminalOutcome(AppConstants.Domain.ALERT_ACTION_DISMISSED)
                finish()
            }
            trustedPersonBtn.visibility = View.GONE
            supportBtn.visibility = View.GONE
        }
    }

    private fun setupPause(pauseSeconds: Int) {
        pauseTimer?.cancel()
        pauseTimer = null
        if (pauseSeconds <= 0) {
            pauseHint.text = ""
            setActionEnabledState(true)
            return
        }

        setActionEnabledState(false)
        pauseHint.text = getString(R.string.alert_pause_countdown, pauseSeconds)

        pauseTimer = object : CountDownTimer((pauseSeconds * 1000L), 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                val secondsLeft = ((millisUntilFinished + 999L) / 1000L).toInt()
                pauseHint.text = getString(R.string.alert_pause_countdown, secondsLeft)
            }

            override fun onFinish() {
                pauseHint.text = ""
                setActionEnabledState(true)
            }
        }.start()
    }

    private fun startManualPause() {
        val resolvedPauseSeconds = if (alertPauseSeconds > 0) {
            alertPauseSeconds
        } else {
            AppConstants.Timing.PAYMENT_DECISION_PAUSE_SECONDS
        }
        setupPause(resolvedPauseSeconds)
    }

    private fun setActionEnabledState(enabled: Boolean) {
        dismissBtn.isEnabled = enabled
        usefulBtn.isEnabled = enabled
        notUsefulBtn.isEnabled = enabled
        trustedPersonBtn.isEnabled = enabled
        supportBtn.isEnabled = enabled
        confirmProceedBtn.isEnabled = enabled && proceedConfirmGroup.visibility == View.VISIBLE
    }

    private fun configureActionMode() {
        proceedConfirmGroup.visibility = View.GONE
        if (useFocusedPaymentActions) {
            dismissBtn.text = getString(R.string.alert_action_pause)
            usefulBtn.text = getString(R.string.alert_action_decline)
            notUsefulBtn.text = getString(R.string.alert_action_proceed)
            trustedPersonBtn.visibility = View.VISIBLE
            trustedPersonBtn.text = getString(R.string.alert_action_trusted_person)
            supportBtn.visibility = View.VISIBLE
            supportBtn.text = getString(R.string.alert_action_support)
            notUsefulBtn.setBackgroundResource(R.drawable.bg_btn_low_emphasis)
            notUsefulBtn.setTextColor(ContextCompat.getColor(this, R.color.text_secondary))
            confirmProceedBtn.text = getString(R.string.alert_proceed_confirmation_confirm)
        } else {
            trustedPersonBtn.visibility = View.GONE
            supportBtn.visibility = View.GONE
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

    private fun hideProceedConfirmation() {
        proceedConfirmGroup.visibility = View.GONE
        confirmProceedBtn.isEnabled = false
    }

    private fun launchTrustedPersonHandoff() {
        reportFeedback(AppConstants.Domain.ALERT_ACTION_TRUSTED_PERSON_REQUESTED)
        helperHandoffInProgress = true

        val launched = TrustedPersonHandoffLauncher.launch(
            context = this,
            title = alertTitle,
            body = alertBody,
            nextSafeAction = nextSafeAction,
        )

        if (!launched) {
            helperHandoffInProgress = false
            reportFeedback(AppConstants.Domain.ALERT_ACTION_TRUSTED_PERSON_FAILED)
            Toast.makeText(this, getString(R.string.alert_trusted_person_launch_failed), Toast.LENGTH_SHORT).show()
            return
        }

        reportFeedback(AppConstants.Domain.ALERT_ACTION_TRUSTED_PERSON_LAUNCHED)
    }

    private fun launchSupportPath() {
        reportFeedback(AppConstants.Domain.ALERT_ACTION_SUPPORT_REQUESTED)
        helperHandoffInProgress = true

        val launched = SupportEscalationLauncher.launch(
            context = this,
            alertId = alertId,
            title = alertTitle,
            body = alertBody,
            severity = alertSeverity,
            pauseSeconds = alertPauseSeconds,
            whyThisAlert = whyThisAlert,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
            primaryActionLabel = primaryActionLabel,
            useFocusedPaymentActions = useFocusedPaymentActions,
        )

        if (!launched) {
            helperHandoffInProgress = false
            reportFeedback(AppConstants.Domain.ALERT_ACTION_SUPPORT_FAILED)
            Toast.makeText(this, getString(R.string.alert_support_launch_failed), Toast.LENGTH_SHORT).show()
            return
        }

        reportFeedback(AppConstants.Domain.ALERT_ACTION_SUPPORT_OPENED)
        postReturnPathNotification()
        finish()
    }

    private fun reportTerminalOutcome(action: String) {
        if (terminalOutcomeReported) {
            return
        }
        terminalOutcomeReported = true
        reportFeedback(action)
    }

    private fun reportFeedback(action: String) {
        AlertFeedbackReporter.report(
            context = this,
            alertId = alertId,
            action = action,
            channel = "fullscreen_activity",
            title = alertTitle,
            message = reportMessage,
        )
    }

    private fun postReturnPathNotification() {
        AlertNotifier.postReturnPathNotification(
            context = this,
            alertId = alertId,
            title = alertTitle,
            body = alertBody,
            severity = alertSeverity,
            pauseSeconds = alertPauseSeconds,
            whyThisAlert = whyThisAlert,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
            primaryActionLabel = primaryActionLabel,
            useFocusedPaymentActions = useFocusedPaymentActions,
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
