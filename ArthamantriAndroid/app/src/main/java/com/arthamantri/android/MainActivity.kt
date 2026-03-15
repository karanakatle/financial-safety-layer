package com.arthamantri.android

import android.Manifest
import android.app.AlertDialog
import android.app.AppOpsManager
import android.content.res.Configuration
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.content.ActivityNotFoundException
import android.net.Uri
import android.os.Build
import android.provider.Settings.EXTRA_APP_PACKAGE
import android.provider.Settings
import android.provider.Settings.Secure
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.BulletSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.AdapterView
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.ImageView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.graphics.Insets
import androidx.core.view.GravityCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowCompat
import androidx.core.view.updatePadding
import androidx.drawerlayout.widget.DrawerLayout
import androidx.core.os.LocaleListCompat
import com.arthamantri.android.BuildConfig
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.model.EssentialGoalEnvelopeDto
import com.arthamantri.android.model.EssentialGoalProfileDto
import com.arthamantri.android.notify.AlertNotifier
import com.arthamantri.android.repo.LiteracyRepository
import com.arthamantri.android.usage.AppUsageForegroundService
import com.google.android.material.navigation.NavigationView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    private data class LanguageOption(
        val code: String,
        val displayName: String,
        val badgeText: String,
    )

    private data class GuidedTrackerCopy(
        val currentStep: Int,
        val title: String,
        val subtitle: String,
        val itemLabels: List<String>,
    )

    private data class SupportAlertContext(
        val alertId: String,
        val title: String,
        val body: String,
        val whyThisAlert: String,
        val nextSafeAction: String,
        val essentialGoalImpact: String,
    )

    private enum class FacilitatorStepProgress {
        PENDING,
        IN_PROGRESS,
        COMPLETE,
        BLOCKED,
    }

    private data class FacilitatorStatusSnapshot(
        val onboardingStep: OnboardingStep,
        val permissionState: PermissionOnboardingState,
        val languageSelected: Boolean,
        val consentAccepted: Boolean,
        val moneySetupDone: Boolean,
        val moneySetupSkipped: Boolean,
        val monitoringActive: Boolean,
        val verificationShown: Boolean,
    )

    private val participantId: String by lazy {
        Secure.getString(contentResolver, Secure.ANDROID_ID) ?: AppConstants.Domain.UNKNOWN_PARTICIPANT_ID
    }

    private lateinit var drawerLayout: DrawerLayout
    private lateinit var navigationView: NavigationView
    private lateinit var statusLine: TextView
    private lateinit var moneySetupLine: TextView
    private lateinit var pilotBanner: TextView
    private lateinit var languageChip: TextView
    private lateinit var startServiceButton: Button
    private lateinit var stopServiceButton: Button
    private lateinit var summaryCard: View
    private lateinit var monitorCard: View
    private lateinit var infoCard: View
    private var accessItemsExpanded = false
    private var currentHelpDialog: AlertDialog? = null
    private var activeFlowDialog: AlertDialog? = null
    private var helpHeadingView: TextView? = null
    private var helpSubtitleView: TextView? = null
    private var helpStepsView: TextView? = null
    private var helpLanguageLabelView: TextView? = null
    private var helpLanguageSpinner: Spinner? = null
    private var helpMoneySetupButton: Button? = null
    private var helpFacilitatorPackButton: Button? = null
    private var helpApplyButton: ImageButton? = null
    private var facilitatorStatusRefresh: (() -> Unit)? = null
    private var activeSupportAlertContext: SupportAlertContext? = null
    private var activeHelpDialogSupportContext: SupportAlertContext? = null

    override fun onDestroy() {
        activeFlowDialog?.dismiss()
        activeFlowDialog = null
        facilitatorStatusRefresh = null
        super.onDestroy()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        applySavedLanguage()
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor = Color.TRANSPARENT
        window.navigationBarColor = Color.TRANSPARENT
        setContentView(R.layout.activity_main)

        drawerLayout = findViewById(R.id.drawerLayout)
        navigationView = findViewById(R.id.navigationView)
        statusLine = findViewById(R.id.statusLine)
        moneySetupLine = findViewById(R.id.moneySetupLine)
        pilotBanner = findViewById(R.id.pilotBanner)
        languageChip = findViewById(R.id.languageChip)
        summaryCard = findViewById(R.id.summaryCard)
        monitorCard = findViewById(R.id.monitorCard)
        infoCard = findViewById(R.id.infoCard)
        val mainScrollView = findViewById<View>(R.id.mainScrollView)
        val mainContentContainer = findViewById<View>(R.id.mainContentContainer)

        applyEdgeToEdgeInsets(mainScrollView, mainContentContainer, navigationView)

        val menuBtn = findViewById<ImageButton>(R.id.menuBtn)
        startServiceButton = findViewById(R.id.startServiceBtn)
        stopServiceButton = findViewById(R.id.stopServiceBtn)
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)

        val shouldRestoreDrawerState = shouldRestoreDrawerStateFromSettings(prefs)
        accessItemsExpanded = shouldRestoreDrawerState &&
            prefs.getBoolean(AppConstants.Prefs.KEY_MANAGE_ACCESS_EXPANDED, false)

        menuBtn.setOnClickListener {
            drawerLayout.openDrawer(GravityCompat.START)
        }

        languageChip.setOnClickListener {
            showLanguageDropdownMenu()
        }
        updateLanguageChip()

        navigationView.setNavigationItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_manage_access -> {
                    toggleManageAccessItems()
                    true
                }

                R.id.nav_access_notifications -> {
                    drawerLayout.closeDrawer(GravityCompat.START)
                    showPermissionSetupDialog(
                        permissionStepOverride = PermissionStep.NOTIFICATIONS,
                        fromReview = true,
                    )
                    true
                }

                R.id.nav_access_overlay -> {
                    drawerLayout.closeDrawer(GravityCompat.START)
                    showPermissionSetupDialog(
                        permissionStepOverride = PermissionStep.OVERLAY,
                        fromReview = true,
                    )
                    true
                }

                R.id.nav_access_usage -> {
                    drawerLayout.closeDrawer(GravityCompat.START)
                    showPermissionSetupDialog(
                        permissionStepOverride = PermissionStep.USAGE,
                        fromReview = true,
                    )
                    true
                }

                R.id.nav_feedback -> {
                    drawerLayout.closeDrawer(GravityCompat.START)
                    promptFeedback()
                    true
                }

                R.id.nav_money_setup -> {
                    drawerLayout.closeDrawer(GravityCompat.START)
                    showMoneySetupDialog()
                    true
                }

                R.id.nav_facilitator_pack -> {
                    drawerLayout.closeDrawer(GravityCompat.START)
                    showFacilitatorSetupPackDialog()
                    true
                }

                R.id.nav_help -> {
                    drawerLayout.closeDrawer(GravityCompat.START)
                    showHelpDialog()
                    true
                }

                R.id.nav_privacy_policy -> {
                    drawerLayout.closeDrawer(GravityCompat.START)
                    openPrivacyPolicy()
                    true
                }

                else -> false
            }
        }
        applyDrawerMenuState()
        drawerLayout.addDrawerListener(object : DrawerLayout.SimpleDrawerListener() {
            override fun onDrawerOpened(drawerView: View) {
                prefs.edit().putBoolean(AppConstants.Prefs.KEY_DRAWER_OPEN, true).apply()
            }

            override fun onDrawerClosed(drawerView: View) {
                prefs.edit().putBoolean(AppConstants.Prefs.KEY_DRAWER_OPEN, false).apply()
            }
        })

        startServiceButton.setOnClickListener {
            handlePrimaryAction()
        }

        stopServiceButton.setOnClickListener {
            stopService(Intent(this, AppUsageForegroundService::class.java))
            setMonitoringActive(false)
            refreshPrimaryActionState()
            toast(getString(R.string.toast_monitor_stopped))
            sendAppLog("info", "monitor_stopped")
        }

        loadPilotMeta()
        loadEssentialGoalSummary()
        animateDashboardCards()
        mainContentContainer.post { continueOnboardingFlow() }
        maybeRestoreHelpDialogAfterLanguageSwitch()
        maybeHandleSupportEscalationIntent(intent)

        if (shouldRestoreDrawerState) {
            drawerLayout.post { drawerLayout.openDrawer(GravityCompat.START) }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        maybeHandleSupportEscalationIntent(intent)
    }

    private fun applyEdgeToEdgeInsets(
        mainScrollView: View,
        mainContentContainer: View,
        drawerNavView: View,
    ) {
        val baseScrollBottom = mainScrollView.paddingBottom
        val baseContentStart = mainContentContainer.paddingLeft
        val baseContentTop = mainContentContainer.paddingTop
        val baseContentEnd = mainContentContainer.paddingRight
        val baseContentBottom = mainContentContainer.paddingBottom
        val baseDrawerTop = drawerNavView.paddingTop
        val baseDrawerBottom = drawerNavView.paddingBottom

        ViewCompat.setOnApplyWindowInsetsListener(drawerLayout) { _, insets ->
            val bars: Insets = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            mainContentContainer.updatePadding(
                left = baseContentStart + bars.left,
                top = baseContentTop + bars.top + 6,
                right = baseContentEnd + bars.right,
                bottom = baseContentBottom,
            )
            mainScrollView.updatePadding(bottom = baseScrollBottom + bars.bottom)
            drawerNavView.updatePadding(
                top = baseDrawerTop + bars.top,
                bottom = baseDrawerBottom + bars.bottom,
            )
            insets
        }
        ViewCompat.requestApplyInsets(drawerLayout)
    }

    override fun onResume() {
        super.onResume()
        syncPermissionOnboardingDone()
        updateLanguageChip()
        refreshPrimaryActionState()
        loadEssentialGoalSummary()
        drawerLayout.post {
            handlePendingPermissionSettingsReturn()
            facilitatorStatusRefresh?.invoke()
        }
    }

    private fun continueOnboardingFlow(forceResumeConsent: Boolean = false) {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        syncPermissionOnboardingDone(prefs)
        val state = onboardingEntryState(prefs)

        refreshPrimaryActionState(state)

        when (state.nextStep()) {
            OnboardingStep.LANGUAGE -> {
                showLanguageSelectionDialog(force = false)
            }

            OnboardingStep.PURPOSE_AND_CONSENT -> {
                if (forceResumeConsent || state.shouldAutoOpenOnLaunch()) {
                    clearDeferredConsent(prefs)
                    showPurposeDialog()
                }
            }

            OnboardingStep.MONEY_SETUP -> {
                showMoneySetupDialog()
            }

            OnboardingStep.PERMISSIONS -> {
                showPermissionSetupDialog()
            }

            OnboardingStep.COMPLETE -> {
                loadEssentialGoalSummary()
            }
        }
    }

    private fun showLanguageSelectionDialog(force: Boolean) {
        val languageOptions = supportedLanguages()
        val options = languageOptions.map { it.displayName }
        val selectedCode = currentLangCode()
        val selectedIndex = languageOptions.indexOfFirst { it.code == selectedCode }.takeIf { it >= 0 } ?: 0
        val contentView = LayoutInflater.from(this).inflate(R.layout.dialog_language_selection, null)
        val spinner = contentView.findViewById<Spinner>(R.id.languageDialogSpinner)
        val primaryButton = contentView.findViewById<Button>(R.id.languageDialogPrimaryButton)
        val secondaryButton = contentView.findViewById<Button>(R.id.languageDialogSecondaryButton)

        spinner.adapter = ArrayAdapter(
            this@MainActivity,
            android.R.layout.simple_spinner_item,
            options,
        ).also { a -> a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        spinner.setSelection(selectedIndex)
        secondaryButton.text = if (force) getString(R.string.help_close) else getString(R.string.consent_exit)
        primaryButton.backgroundTintList = null
        secondaryButton.backgroundTintList = null

        val dialog = AlertDialog.Builder(this)
            .setView(contentView)
            .setCancelable(false)
            .create()
        dialog.setCanceledOnTouchOutside(false)
        dialog.setOnShowListener {
            primaryButton.setOnClickListener {
                val langCode = languageOptions.getOrNull(spinner.selectedItemPosition)?.code
                    ?: AppConstants.Locale.DEFAULT_LANGUAGE
                dialog.dismiss()
                applyLanguage(langCode, markSelected = true)
            }
            secondaryButton.setOnClickListener {
                dialog.dismiss()
                if (!force) {
                    finish()
                }
            }
        }
        showManagedFlowDialog(dialog)
    }

    private fun showConsentDialog(allowExit: Boolean = true) {
        val contentView = LayoutInflater.from(this).inflate(R.layout.dialog_consent_review, null)
        val bodyView = contentView.findViewById<TextView>(R.id.consentDialogBody)
        val primaryButton = contentView.findViewById<Button>(R.id.consentDialogPrimaryButton)
        val secondaryButton = contentView.findViewById<Button>(R.id.consentDialogSecondaryButton)

        bodyView.text = buildBulletedDialogMessage(
            bullets = listOf(
                getString(R.string.dialog_consent_bullet_1),
                getString(R.string.dialog_consent_bullet_2),
                getString(R.string.dialog_consent_bullet_3),
            ),
        )
        primaryButton.backgroundTintList = null
        secondaryButton.backgroundTintList = null
        secondaryButton.text = if (allowExit) getString(R.string.consent_not_now) else getString(R.string.help_close)

        val dialog = AlertDialog.Builder(this)
            .setView(contentView)
            .setCancelable(false)
            .create()
        dialog.setCanceledOnTouchOutside(false)
        dialog.setOnShowListener {
            primaryButton.setOnClickListener {
                dialog.dismiss()
                val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
                prefs.edit()
                    .putBoolean(AppConstants.Prefs.KEY_CONSENT_ACCEPTED, true)
                    .putBoolean(AppConstants.Prefs.KEY_CONSENT_DEFERRED, false)
                    .apply()
                CoroutineScope(Dispatchers.IO).launch {
                    runCatching {
                        LiteracyRepository.submitPilotConsent(
                            context = this@MainActivity,
                            participantId = participantId,
                            accepted = true,
                            language = currentLangCode(),
                        )
                    }
                }
                sendAppLog("info", "consent_accepted")
                continueOnboardingFlow()
            }
            secondaryButton.setOnClickListener {
                dialog.dismiss()
                if (allowExit) {
                    deferConsent()
                }
            }
        }
        showManagedFlowDialog(dialog)
    }

    private fun showPurposeDialog() {
        val contentView = LayoutInflater.from(this).inflate(R.layout.dialog_purpose_review, null)
        val bodyView = contentView.findViewById<TextView>(R.id.purposeDialogBody)
        val primaryButton = contentView.findViewById<Button>(R.id.purposeDialogPrimaryButton)
        val secondaryButton = contentView.findViewById<Button>(R.id.purposeDialogSecondaryButton)

        bodyView.text = buildBulletedDialogMessage(
            bullets = listOf(
                getString(R.string.dialog_purpose_bullet_1),
                getString(R.string.dialog_purpose_bullet_2),
                getString(R.string.dialog_purpose_bullet_3),
            ),
        )
        primaryButton.backgroundTintList = null
        secondaryButton.backgroundTintList = null

        val dialog = AlertDialog.Builder(this)
            .setView(contentView)
            .setCancelable(false)
            .create()
        dialog.setCanceledOnTouchOutside(false)
        dialog.setOnShowListener {
            primaryButton.setOnClickListener {
                dialog.dismiss()
                showConsentDialog()
            }
            secondaryButton.setOnClickListener {
                dialog.dismiss()
                deferConsent()
            }
        }
        showManagedFlowDialog(dialog)
    }

    private fun showMoneySetupDialog() {
        val cohortCodes = listOf("women_led_household", "daily_cashflow_worker")
        val cohortLabels = cohortCodes.map { cohortDisplayName(it) }
        val goalCodes = listOf(
            "",
            "ration",
            "school",
            "fuel",
            "medicine",
            "rent",
            "mobile_recharge",
            "loan_repayment",
        )
        val goalLabels = listOf(getString(R.string.money_setup_none)) + goalCodes.drop(1).map { goalDisplayName(it) }

        val contentView = LayoutInflater.from(this).inflate(R.layout.dialog_money_setup, null)
        val cohortSpinner = contentView.findViewById<Spinner>(R.id.moneySetupCohortSpinner)
        val goalOneSpinner = contentView.findViewById<Spinner>(R.id.moneySetupGoalOneSpinner)
        val goalTwoSpinner = contentView.findViewById<Spinner>(R.id.moneySetupGoalTwoSpinner)
        val primaryButton = contentView.findViewById<Button>(R.id.moneySetupPrimaryButton)
        val secondaryButton = contentView.findViewById<Button>(R.id.moneySetupSecondaryButton)
        cohortSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            cohortLabels,
        ).also { adapter -> adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        goalOneSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            goalLabels,
        ).also { adapter -> adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        goalTwoSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            goalLabels,
        ).also { adapter -> adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }

        primaryButton.backgroundTintList = null
        secondaryButton.backgroundTintList = null
        var moneySetupHandled = false

        val dialog = AlertDialog.Builder(this)
            .setView(contentView)
            .setCancelable(false)
            .create()
        dialog.setCanceledOnTouchOutside(false)

        dialog.setOnShowListener {
            val setButtonsEnabled = { enabled: Boolean ->
                primaryButton.isEnabled = enabled
                secondaryButton.isEnabled = enabled
            }

            primaryButton.setOnClickListener {
                setButtonsEnabled(false)
                moneySetupHandled = true
                val cohort = cohortCodes.getOrNull(cohortSpinner.selectedItemPosition) ?: "daily_cashflow_worker"
                val selectedGoals = listOf(
                    goalCodes.getOrNull(goalOneSpinner.selectedItemPosition).orEmpty(),
                    goalCodes.getOrNull(goalTwoSpinner.selectedItemPosition).orEmpty(),
                ).filter { it.isNotBlank() }.distinct().take(2)
                persistMoneySetup(
                    cohort = cohort,
                    goals = selectedGoals,
                    setupSkipped = selectedGoals.isEmpty(),
                    dialog = dialog,
                )
            }

            secondaryButton.setOnClickListener {
                setButtonsEnabled(false)
                moneySetupHandled = true
                persistMoneySetup(
                    cohort = "daily_cashflow_worker",
                    goals = emptyList(),
                    setupSkipped = true,
                    dialog = dialog,
                )
            }
        }
        showManagedFlowDialog(dialog, onDismissExtra = {
            if (!moneySetupHandled) {
                setStatus(getString(R.string.status_onboarding_resume))
                refreshPrimaryActionState()
            }
        })
    }

    private fun showPermissionSetupDialog(
        permissionStepOverride: PermissionStep? = null,
        fromReview: Boolean = false,
    ) {
        val currentPermissionState = permissionOnboardingState()
        if (!fromReview && permissionStepOverride == null) {
            when (currentPermissionState.nextStep()) {
                PermissionStep.USAGE, PermissionStep.OVERLAY -> {
                    showPermissionSetupDialog(permissionStepOverride = currentPermissionState.nextStep())
                    return
                }
                else -> Unit
            }
        }

        if (!fromReview && permissionStepOverride == null) {
            val dialog = buildInfoBoxDialog(
                title = getString(R.string.dialog_perm_intro_title),
                subtitle = getString(R.string.dialog_perm_step_subtitle, 1, 4),
                guidedStep = 1,
                guidedTrackerCopy = permissionGuidedTrackerCopy(PermissionStep.SMS),
                body = buildBulletedDialogMessage(
                    bullets = listOf(
                        getString(R.string.dialog_perm_bullet_helps, getString(R.string.permission_help_sms)),
                        getString(R.string.dialog_perm_bullet_helps, getString(R.string.permission_help_notifications)),
                        getString(R.string.dialog_perm_bullet_not_access),
                        getString(R.string.dialog_perm_bullet_next, getString(R.string.menu_access_usage)),
                    ),
                    intro = getString(R.string.dialog_perm_intro_step_1),
                    outro = getString(R.string.dialog_perm_followup_step_1),
                ),
                positiveLabel = getString(R.string.perm_continue),
                negativeLabel = getString(R.string.consent_not_now),
                cancelable = false,
                onPositive = {
                    setGuidedPermissionFlowActive(true)
                    sendAppLog("info", "permission_onboarding_prompted")
                    val runtimePermissionsPending = !hasSmsRuntimePermissions() || !hasNotificationPostingPermission()
                    if (runtimePermissionsPending) {
                        requestRuntimePermissions()
                    } else {
                        showPermissionSetupDialog(permissionStepOverride = permissionOnboardingState().nextStep())
                    }
                },
                onNegative = { dialogInterface ->
                    dialogInterface.dismiss()
                    setGuidedPermissionFlowActive(false)
                    setStatus(getString(R.string.status_onboarding_resume))
                    refreshPrimaryActionState()
                    toast(getString(R.string.toast_setup_paused))
                },
            )
            showManagedFlowDialog(dialog, transparentBackground = false)
            return
        }

        val state = currentPermissionState
        syncPermissionOnboardingDone()

        if (!fromReview) {
            setGuidedPermissionFlowActive(true)
        }

        if (!fromReview && state.isComplete()) {
            setGuidedPermissionFlowActive(false)
            continueOnboardingFlow()
            return
        }

        val step = permissionStepOverride ?: state.nextStep()
        if (step == PermissionStep.COMPLETE) {
            val dialog = buildInfoBoxDialog(
                title = getString(R.string.dialog_perm_complete_title),
                subtitle = getString(R.string.dialog_perm_complete_subtitle),
                guidedStep = 4,
                guidedTrackerCopy = if (!fromReview) permissionGuidedTrackerCopy(PermissionStep.COMPLETE) else null,
                body = buildBulletedDialogMessage(
                    bullets = listOf(
                        getString(R.string.dialog_perm_complete_bullet_1),
                        getString(R.string.dialog_perm_complete_bullet_2),
                    ),
                ),
                positiveLabel = getString(R.string.help_close),
                negativeLabel = null,
                cancelable = true,
                onPositive = {
                    refreshPrimaryActionState()
                },
            )
            dialog.show()
            dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
            return
        }

        val currentGranted = isPermissionStepGranted(step, state)
        val remainingLabels = state.remainingSteps()
            .filter { it != step }
            .joinToString(separator = ", ") { permissionStepLabel(it) }
            .ifBlank { getString(R.string.dialog_money_setup_title) }
        val followupText = if (!fromReview && !currentGranted) {
            when (step) {
                PermissionStep.USAGE -> getString(R.string.dialog_perm_followup_usage)
                PermissionStep.OVERLAY -> getString(R.string.dialog_perm_followup_overlay)
                else -> getString(R.string.dialog_perm_bullet_next, remainingLabels)
            }
        } else {
            getString(R.string.dialog_perm_bullet_next, remainingLabels)
        }

        val dialog = buildInfoBoxDialog(
            title = if (currentGranted && fromReview) {
                getString(R.string.dialog_perm_review_title, permissionStepLabel(step))
            } else {
                getString(R.string.dialog_perm_step_title, permissionStepLabel(step))
            },
            subtitle = if (currentGranted && fromReview) {
                getString(R.string.dialog_perm_review_subtitle)
            } else {
                getString(
                    R.string.dialog_perm_step_subtitle,
                    permissionFlowStepNumber(step),
                    4,
                )
            },
            guidedStep = 3,
            guidedTrackerCopy = if (!fromReview) permissionGuidedTrackerCopy(step) else null,
            body = buildBulletedDialogMessage(
                bullets = listOf(
                    getString(R.string.dialog_perm_bullet_helps, permissionStepHelpText(step)),
                    getString(R.string.dialog_perm_bullet_not_access),
                    if (currentGranted && fromReview) {
                        getString(R.string.dialog_perm_bullet_currently_on)
                    } else {
                        getString(R.string.dialog_perm_bullet_if_off, permissionStepOffText(step))
                    },
                ),
                outro = followupText,
            ),
            positiveLabel = permissionStepActionLabel(step),
            negativeLabel = if (!fromReview) getString(R.string.consent_not_now) else getString(R.string.help_close),
            cancelable = true,
            onPositive = {
                openPermissionStep(step, continueGuidedFlow = !fromReview)
            },
            onNegative = { dialogInterface ->
                dialogInterface.dismiss()
                if (!fromReview) {
                    setGuidedPermissionFlowActive(false)
                }
                refreshPrimaryActionState()
            },
        )
        showManagedFlowDialog(dialog, transparentBackground = false)
    }

    private fun showFacilitatorSetupPackDialog(supportContext: SupportAlertContext? = null) {
        val contentView = LayoutInflater.from(this).inflate(R.layout.dialog_facilitator_pack, null)
        val readinessStatus = contentView.findViewById<TextView>(R.id.facilitatorReadinessStatus)
        val nextActionValue = contentView.findViewById<TextView>(R.id.facilitatorNextActionValue)
        val languagePill = contentView.findViewById<TextView>(R.id.facilitatorLanguagePill)
        val consentPill = contentView.findViewById<TextView>(R.id.facilitatorConsentPill)
        val permissionsPill = contentView.findViewById<TextView>(R.id.facilitatorPermissionsPill)
        val languageStatus = contentView.findViewById<TextView>(R.id.facilitatorStepLanguageStatus)
        val consentStatus = contentView.findViewById<TextView>(R.id.facilitatorStepConsentStatus)
        val permissionsStatus = contentView.findViewById<TextView>(R.id.facilitatorStepPermissionsStatus)
        val moneySetupStatus = contentView.findViewById<TextView>(R.id.facilitatorStepMoneySetupStatus)
        val monitoringStatus = contentView.findViewById<TextView>(R.id.facilitatorStepMonitoringStatus)
        val languageButton = contentView.findViewById<Button>(R.id.facilitatorLanguageButton)
        val consentButton = contentView.findViewById<Button>(R.id.facilitatorConsentButton)
        val permissionsButton = contentView.findViewById<Button>(R.id.facilitatorPermissionsButton)
        val moneySetupButton = contentView.findViewById<Button>(R.id.facilitatorMoneySetupButton)
        val startMonitoringButton = contentView.findViewById<Button>(R.id.facilitatorStartMonitoringButton)
        val refreshButton = contentView.findViewById<Button>(R.id.facilitatorRefreshButton)
        val closeButton = contentView.findViewById<Button>(R.id.facilitatorCloseButton)

        bindSupportContextCard(
            contextCard = contentView.findViewById(R.id.facilitatorSupportContextCard),
            titleView = contentView.findViewById(R.id.facilitatorSupportContextTitle),
            bodyView = contentView.findViewById(R.id.facilitatorSupportContextBody),
            whyHeading = contentView.findViewById(R.id.facilitatorSupportWhyHeading),
            whyBody = contentView.findViewById(R.id.facilitatorSupportWhyBody),
            nextHeading = contentView.findViewById(R.id.facilitatorSupportNextHeading),
            nextBody = contentView.findViewById(R.id.facilitatorSupportNextBody),
            goalHeading = contentView.findViewById(R.id.facilitatorSupportGoalHeading),
            goalBody = contentView.findViewById(R.id.facilitatorSupportGoalBody),
            supportContext = supportContext,
        )

        val dialog = AlertDialog.Builder(this)
            .setView(contentView)
            .create()

        val refresh = {
            refreshFacilitatorStatus(
                readinessStatus = readinessStatus,
                nextActionValue = nextActionValue,
                languagePill = languagePill,
                consentPill = consentPill,
                permissionsPill = permissionsPill,
                languageStatus = languageStatus,
                consentStatus = consentStatus,
                permissionsStatus = permissionsStatus,
                moneySetupStatus = moneySetupStatus,
                monitoringStatus = monitoringStatus,
                languageButton = languageButton,
                consentButton = consentButton,
                permissionsButton = permissionsButton,
                moneySetupButton = moneySetupButton,
                startMonitoringButton = startMonitoringButton,
            )
        }
        facilitatorStatusRefresh = refresh
        dialog.setOnDismissListener { facilitatorStatusRefresh = null }

        dialog.setOnShowListener {
            refresh()

            languageButton.setOnClickListener {
                showLanguageSelectionDialog(force = true)
                refresh()
            }
            consentButton.setOnClickListener {
                showConsentDialog(allowExit = false)
                refresh()
            }
            moneySetupButton.setOnClickListener {
                showMoneySetupDialog()
                refresh()
            }
            permissionsButton.setOnClickListener {
                showPermissionSetupDialog()
                refresh()
            }
            startMonitoringButton.setOnClickListener {
                startMonitoringWithChecks()
                refresh()
            }
            refreshButton.setOnClickListener { refresh() }
            closeButton.setOnClickListener { dialog.dismiss() }
        }

        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        val metrics = resources.displayMetrics
        dialog.window?.setLayout(
            (metrics.widthPixels * 0.94f).toInt(),
            (metrics.heightPixels * 0.85f).toInt(),
        )
    }

    private fun refreshFacilitatorStatus(
        readinessStatus: TextView,
        nextActionValue: TextView,
        languagePill: TextView,
        consentPill: TextView,
        permissionsPill: TextView,
        languageStatus: TextView,
        consentStatus: TextView,
        permissionsStatus: TextView,
        moneySetupStatus: TextView,
        monitoringStatus: TextView,
        languageButton: Button,
        consentButton: Button,
        permissionsButton: Button,
        moneySetupButton: Button,
        startMonitoringButton: Button,
    ) {
        val snapshot = facilitatorStatusSnapshot()
        val languageProgress = if (snapshot.languageSelected) {
            FacilitatorStepProgress.COMPLETE
        } else {
            FacilitatorStepProgress.PENDING
        }
        val consentProgress = when {
            snapshot.consentAccepted -> FacilitatorStepProgress.COMPLETE
            snapshot.onboardingStep == OnboardingStep.PURPOSE_AND_CONSENT -> FacilitatorStepProgress.PENDING
            else -> FacilitatorStepProgress.BLOCKED
        }
        val permissionsProgress = when {
            snapshot.permissionState.isComplete() -> FacilitatorStepProgress.COMPLETE
            snapshot.onboardingStep == OnboardingStep.PERMISSIONS && snapshot.permissionState.completedCount() > 0 ->
                FacilitatorStepProgress.IN_PROGRESS
            snapshot.onboardingStep == OnboardingStep.PERMISSIONS -> FacilitatorStepProgress.PENDING
            else -> FacilitatorStepProgress.BLOCKED
        }

        readinessStatus.text = facilitatorReadinessText(snapshot)
        nextActionValue.text = facilitatorNextActionText(snapshot)
        applyFacilitatorPill(languagePill, getString(R.string.facilitator_pill_language), languageProgress)
        applyFacilitatorPill(consentPill, getString(R.string.facilitator_pill_consent), consentProgress)
        applyFacilitatorPill(permissionsPill, getString(R.string.facilitator_pill_permissions), permissionsProgress)

        languageStatus.text = facilitatorStepStatusText(
            progress = languageProgress,
            detail = if (snapshot.languageSelected) {
                getString(R.string.facilitator_detail_language_done)
            } else {
                getString(R.string.facilitator_detail_language_pending)
            },
        )
        consentStatus.text = facilitatorStepStatusText(
            progress = consentProgress,
            detail = when {
                snapshot.consentAccepted -> getString(R.string.facilitator_detail_consent_done)
                snapshot.onboardingStep == OnboardingStep.PURPOSE_AND_CONSENT -> getString(R.string.facilitator_detail_consent_pending)
                else -> getString(R.string.facilitator_detail_finish_earlier_steps)
            },
        )
        permissionsStatus.text = facilitatorPermissionStatusText(snapshot)
        moneySetupStatus.text = facilitatorStepStatusText(
            progress = when {
                snapshot.moneySetupDone -> FacilitatorStepProgress.COMPLETE
                snapshot.onboardingStep == OnboardingStep.MONEY_SETUP -> FacilitatorStepProgress.PENDING
                snapshot.onboardingStep == OnboardingStep.COMPLETE -> FacilitatorStepProgress.PENDING
                snapshot.permissionState.isComplete() -> FacilitatorStepProgress.PENDING
                else -> FacilitatorStepProgress.BLOCKED
            },
            detail = when {
                snapshot.moneySetupDone && snapshot.moneySetupSkipped -> getString(R.string.facilitator_detail_money_setup_skipped)
                snapshot.moneySetupDone -> getString(R.string.facilitator_detail_money_setup_done)
                snapshot.permissionState.isComplete() -> getString(R.string.facilitator_detail_money_setup_pending)
                else -> getString(R.string.facilitator_detail_finish_earlier_steps)
            },
        )
        monitoringStatus.text = facilitatorMonitoringStatusText(snapshot)

        languageButton.text = if (snapshot.languageSelected) {
            getString(R.string.facilitator_action_review_language)
        } else {
            getString(R.string.facilitator_action_select_language)
        }
        consentButton.text = if (snapshot.consentAccepted) {
            getString(R.string.facilitator_action_review_consent)
        } else {
            getString(R.string.facilitator_action_record_consent)
        }
        permissionsButton.text = if (snapshot.permissionState.isComplete()) {
            getString(R.string.facilitator_action_review_permissions)
        } else {
            getString(R.string.facilitator_action_permissions)
        }
        moneySetupButton.text = if (snapshot.moneySetupDone) {
            getString(R.string.facilitator_action_review_money_setup)
        } else {
            getString(R.string.facilitator_action_money_setup)
        }
        startMonitoringButton.text = if (snapshot.monitoringActive && snapshot.verificationShown) {
            getString(R.string.facilitator_action_monitoring_verified)
        } else {
            getString(R.string.facilitator_action_start_monitor)
        }
        startMonitoringButton.isEnabled = !snapshot.monitoringActive || !snapshot.verificationShown
    }

    private fun facilitatorStatusSnapshot(): FacilitatorStatusSnapshot {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        syncPermissionOnboardingDone(prefs)
        return FacilitatorStatusSnapshot(
            onboardingStep = onboardingEntryState(prefs).nextStep(),
            permissionState = permissionOnboardingState(),
            languageSelected = prefs.getBoolean(AppConstants.Prefs.KEY_LANGUAGE_SELECTED, false),
            consentAccepted = prefs.getBoolean(AppConstants.Prefs.KEY_CONSENT_ACCEPTED, false),
            moneySetupDone = prefs.getBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, false),
            moneySetupSkipped = prefs.getBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_SKIPPED, false),
            monitoringActive = isMonitoringActive(),
            verificationShown = prefs.getBoolean(AppConstants.Prefs.KEY_SETUP_VERIFICATION_SHOWN, false),
        )
    }

    private fun facilitatorStepStatusText(progress: FacilitatorStepProgress, detail: String): String {
        val label = when (progress) {
            FacilitatorStepProgress.PENDING -> getString(R.string.facilitator_status_pending)
            FacilitatorStepProgress.IN_PROGRESS -> getString(R.string.facilitator_status_in_progress)
            FacilitatorStepProgress.COMPLETE -> getString(R.string.facilitator_status_done)
            FacilitatorStepProgress.BLOCKED -> getString(R.string.facilitator_status_blocked)
        }
        return getString(R.string.facilitator_status_with_detail, label, detail)
    }

    private fun facilitatorPermissionStatusText(snapshot: FacilitatorStatusSnapshot): String {
        val summary = getString(
            R.string.facilitator_status_permissions,
            yesNoShort(snapshot.permissionState.smsGranted),
            yesNoShort(snapshot.permissionState.notificationsGranted),
            yesNoShort(snapshot.permissionState.usageGranted),
            yesNoShort(snapshot.permissionState.overlayGranted),
        )
        val detail = when {
            snapshot.permissionState.isComplete() -> getString(R.string.facilitator_detail_permissions_done)
            snapshot.onboardingStep == OnboardingStep.PERMISSIONS -> {
                getString(
                    R.string.facilitator_detail_permissions_pending,
                    permissionStepLabel(snapshot.permissionState.nextStep()),
                )
            }
            else -> getString(R.string.facilitator_detail_finish_earlier_steps)
        }
        val progress = when {
            snapshot.permissionState.isComplete() -> FacilitatorStepProgress.COMPLETE
            snapshot.onboardingStep == OnboardingStep.PERMISSIONS && snapshot.permissionState.completedCount() > 0 ->
                FacilitatorStepProgress.IN_PROGRESS
            snapshot.onboardingStep == OnboardingStep.PERMISSIONS -> FacilitatorStepProgress.PENDING
            else -> FacilitatorStepProgress.BLOCKED
        }
        return facilitatorStepStatusText(progress, detail) + "\n" + summary
    }

    private fun applyFacilitatorPill(view: TextView, label: String, progress: FacilitatorStepProgress) {
        val (statusTextRes, backgroundRes, textColorRes) = when (progress) {
            FacilitatorStepProgress.COMPLETE -> Triple(
                R.string.facilitator_pill_done,
                R.drawable.bg_status_pill_done,
                R.color.color_semantic_safe_text,
            )
            FacilitatorStepProgress.IN_PROGRESS -> Triple(
                R.string.facilitator_pill_in_progress,
                R.drawable.bg_status_pill_pending,
                R.color.color_semantic_warning_text,
            )
            FacilitatorStepProgress.PENDING -> Triple(
                R.string.facilitator_pill_pending,
                R.drawable.bg_status_pill_pending,
                R.color.color_semantic_warning_text,
            )
            FacilitatorStepProgress.BLOCKED -> Triple(
                R.string.facilitator_pill_blocked,
                R.drawable.bg_status_pill_blocked,
                R.color.color_semantic_high_risk_text,
            )
        }
        view.text = getString(R.string.facilitator_pill_format, label, getString(statusTextRes))
        view.setBackgroundResource(backgroundRes)
        view.setTextColor(ContextCompat.getColor(this, textColorRes))
    }

    private fun facilitatorMonitoringStatusText(snapshot: FacilitatorStatusSnapshot): String {
        val monitoringReady = snapshot.onboardingStep == OnboardingStep.COMPLETE
            && snapshot.permissionState.isComplete()
            && snapshot.moneySetupDone

        return when {
            snapshot.monitoringActive && snapshot.verificationShown ->
                facilitatorStepStatusText(
                    FacilitatorStepProgress.COMPLETE,
                    getString(R.string.facilitator_detail_monitoring_verified),
                )
            snapshot.monitoringActive ->
                facilitatorStepStatusText(
                    FacilitatorStepProgress.IN_PROGRESS,
                    getString(R.string.facilitator_detail_monitoring_started),
                )
            monitoringReady ->
                facilitatorStepStatusText(
                    FacilitatorStepProgress.PENDING,
                    getString(R.string.facilitator_detail_monitoring_pending),
                )
            else ->
                facilitatorStepStatusText(
                    FacilitatorStepProgress.BLOCKED,
                    getString(R.string.facilitator_detail_finish_earlier_steps),
                )
        }
    }

    private fun facilitatorReadinessText(snapshot: FacilitatorStatusSnapshot): String {
        return when {
            snapshot.monitoringActive && snapshot.verificationShown ->
                getString(R.string.facilitator_readiness_ready)
            snapshot.onboardingStep == OnboardingStep.COMPLETE ->
                getString(R.string.facilitator_readiness_verify)
            else ->
                getString(R.string.facilitator_readiness_not_ready)
        }
    }

    private fun facilitatorNextActionText(snapshot: FacilitatorStatusSnapshot): String {
        return when (snapshot.onboardingStep) {
            OnboardingStep.LANGUAGE -> getString(R.string.facilitator_next_action_language)
            OnboardingStep.PURPOSE_AND_CONSENT -> getString(R.string.facilitator_next_action_consent)
            OnboardingStep.PERMISSIONS -> getString(R.string.facilitator_next_action_permissions)
            OnboardingStep.MONEY_SETUP -> getString(R.string.facilitator_next_action_money_setup)
            OnboardingStep.COMPLETE -> {
                if (snapshot.monitoringActive && snapshot.verificationShown) {
                    getString(R.string.facilitator_next_action_done)
                } else {
                    getString(R.string.facilitator_next_action_monitoring)
                }
            }
        }
    }

    private fun yesNoShort(done: Boolean): String {
        return if (done) getString(R.string.icon_check) else getString(R.string.icon_close)
    }

    private fun hasSmsRuntimePermissions(): Boolean {
        val smsReceive = ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED
        val smsRead = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED
        return smsReceive && smsRead
    }

    private fun hasAppNotificationsEnabled(): Boolean {
        val runtimeGranted = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
        return runtimeGranted && NotificationManagerCompat.from(this).areNotificationsEnabled()
    }

    private fun hasIncompleteAccessSetup(): Boolean {
        return !hasSmsRuntimePermissions() ||
            !hasAppNotificationsEnabled() ||
            !hasUsageStatsPermission() ||
            !Settings.canDrawOverlays(this) ||
            !hasNotificationListenerPermission()
    }

    private fun shouldRestoreDrawerStateFromSettings(prefs: SharedPreferences): Boolean {
        val requested = prefs.getBoolean(AppConstants.Prefs.KEY_RESTORE_DRAWER_ON_RETURN, false)
        val shouldRestore = requested && hasIncompleteAccessSetup()
        prefs.edit()
            .putBoolean(AppConstants.Prefs.KEY_RESTORE_DRAWER_ON_RETURN, false)
            .putBoolean(AppConstants.Prefs.KEY_DRAWER_OPEN, false)
            .putBoolean(
                AppConstants.Prefs.KEY_MANAGE_ACCESS_EXPANDED,
                if (shouldRestore) prefs.getBoolean(AppConstants.Prefs.KEY_MANAGE_ACCESS_EXPANDED, false) else false,
            )
            .apply()
        return shouldRestore
    }

    private fun persistMoneySetup(
        cohort: String,
        goals: List<String>,
        setupSkipped: Boolean,
        dialog: AlertDialog,
    ) {
        cacheMoneySetupSelection(
            cohort = cohort,
            goals = goals,
            done = true,
            skipped = setupSkipped,
        )
        applyLocalMoneySetupFallback()
        dialog.dismiss()
        continueOnboardingFlow()

        CoroutineScope(Dispatchers.IO).launch {
            val response = runCatching {
                LiteracyRepository.saveEssentialGoals(
                    context = this@MainActivity,
                    cohort = cohort,
                    essentialGoals = goals,
                    setupSkipped = setupSkipped,
                )
            }
            runOnUiThread {
                response.onSuccess { saved ->
                    cacheMoneySetupSelection(
                        cohort = saved.profile?.cohort ?: cohort,
                        goals = saved.profile?.essential_goals?.filter { it.isNotBlank() } ?: goals,
                        done = true,
                        skipped = saved.profile?.setup_skipped == true || setupSkipped,
                    )
                    updateMoneySetupSummary(saved.profile, saved.envelope)
                    if (!setupSkipped) {
                        toast(getString(R.string.toast_money_setup_saved))
                    }
                    sendAppLog("info", "money_setup_saved:$cohort:${goals.joinToString("|")}")
                }.onFailure { error ->
                    applyLocalMoneySetupFallback()
                    toast(getString(R.string.toast_money_setup_failed))
                    sendAppLog("error", "money_setup_save_failed:${error.message}")
                }
            }
        }
    }

    private fun loadEssentialGoalSummary() {
        CoroutineScope(Dispatchers.IO).launch {
            val response = runCatching { LiteracyRepository.getEssentialGoals(this@MainActivity) }
            runOnUiThread {
                response.onSuccess { profileResponse ->
                    updateMoneySetupSummary(profileResponse.profile, profileResponse.envelope)
                }.onFailure {
                    applyLocalMoneySetupFallback()
                }
            }
        }
    }

    private fun updateMoneySetupSummary(
        profile: EssentialGoalProfileDto?,
        envelope: EssentialGoalEnvelopeDto?,
    ) {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        if (!prefs.getBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, false)) {
            applyLocalMoneySetupFallback()
            return
        }
        if (profile == null) {
            applyLocalMoneySetupFallback()
            return
        }
        val goals = profile.essential_goals.filter { it.isNotBlank() }
        if (profile.setup_skipped == true) {
            moneySetupLine.text = getString(R.string.money_setup_skipped)
            return
        }
        if (goals.isEmpty()) {
            moneySetupLine.text = getString(R.string.money_setup_pending)
            return
        }
        val reservePercent = (((envelope?.reserve_ratio ?: 0.0) * 100.0).toInt()).coerceAtLeast(0)
        val protectedLimit = ((envelope?.protected_limit ?: 0.0).toInt()).coerceAtLeast(0)
        val goalText = goals.joinToString(", ") { goalDisplayName(it) }
        val cohortText = cohortDisplayName(profile.cohort ?: "daily_cashflow_worker")
        moneySetupLine.text = getString(
            R.string.money_setup_summary,
            cohortText,
            goalText,
            reservePercent,
            protectedLimit,
        )
    }

    private fun cohortDisplayName(cohortCode: String): String {
        return when (cohortCode) {
            "women_led_household" -> getString(R.string.cohort_women_led_household)
            "daily_cashflow_worker" -> getString(R.string.cohort_daily_cashflow_worker)
            else -> getString(R.string.cohort_daily_cashflow_worker)
        }
    }

    private fun goalDisplayName(goalCode: String): String {
        return when (goalCode) {
            "ration" -> getString(R.string.goal_ration)
            "school" -> getString(R.string.goal_school)
            "fuel" -> getString(R.string.goal_fuel)
            "medicine" -> getString(R.string.goal_medicine)
            "rent" -> getString(R.string.goal_rent)
            "mobile_recharge" -> getString(R.string.goal_mobile_recharge)
            "loan_repayment" -> getString(R.string.goal_loan_repayment)
            else -> goalCode
        }
    }

    private fun permissionOnboardingState(): PermissionOnboardingState {
        return PermissionOnboardingState(
            smsGranted = hasSmsAccessEnabled(),
            usageGranted = hasUsageStatsPermission(),
            overlayGranted = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) Settings.canDrawOverlays(this) else true,
            notificationsGranted = hasNotificationAccessForOnboarding(),
        )
    }

    private fun syncPermissionOnboardingDone(
        prefs: SharedPreferences = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE),
    ) {
        val isComplete = permissionOnboardingState().isComplete()
        if (prefs.getBoolean(AppConstants.Prefs.KEY_PERMISSION_ONBOARDING_DONE, false) == isComplete) {
            return
        }
        prefs.edit().putBoolean(AppConstants.Prefs.KEY_PERMISSION_ONBOARDING_DONE, isComplete).apply()
    }

    private fun permissionStepLabel(step: PermissionStep): String {
        return when (step) {
            PermissionStep.SMS -> getString(R.string.permission_label_sms)
            PermissionStep.USAGE -> getString(R.string.menu_access_usage)
            PermissionStep.OVERLAY -> getString(R.string.menu_access_overlay)
            PermissionStep.NOTIFICATIONS -> getString(R.string.menu_access_notifications)
            PermissionStep.COMPLETE -> getString(R.string.dialog_perm_complete_title)
        }
    }

    private fun permissionStepHelpText(step: PermissionStep): String {
        return when (step) {
            PermissionStep.SMS -> getString(R.string.permission_help_sms)
            PermissionStep.USAGE -> getString(R.string.permission_help_usage)
            PermissionStep.OVERLAY -> getString(R.string.permission_help_overlay)
            PermissionStep.NOTIFICATIONS -> getString(R.string.permission_help_notifications)
            PermissionStep.COMPLETE -> getString(R.string.dialog_perm_complete_subtitle)
        }
    }

    private fun permissionStepOffText(step: PermissionStep): String {
        return when (step) {
            PermissionStep.SMS -> getString(R.string.permission_if_off_sms)
            PermissionStep.USAGE -> getString(R.string.permission_if_off_usage)
            PermissionStep.OVERLAY -> getString(R.string.permission_if_off_overlay)
            PermissionStep.NOTIFICATIONS -> getString(R.string.permission_if_off_notifications)
            PermissionStep.COMPLETE -> getString(R.string.dialog_perm_complete_bullet_1)
        }
    }

    private fun permissionStepActionLabel(step: PermissionStep): String {
        return when (step) {
            PermissionStep.SMS -> getString(R.string.permission_action_sms)
            PermissionStep.USAGE -> getString(R.string.permission_action_usage)
            PermissionStep.OVERLAY -> getString(R.string.permission_action_overlay)
            PermissionStep.NOTIFICATIONS -> getString(R.string.permission_action_notifications)
            PermissionStep.COMPLETE -> getString(R.string.help_close)
        }
    }

    private fun openPermissionStep(step: PermissionStep, continueGuidedFlow: Boolean) {
        setGuidedPermissionFlowActive(continueGuidedFlow)
        when (step) {
            PermissionStep.SMS -> {
                requestSmsRuntimePermissions()
                sendAppLog("info", "permission_step_sms_prompted")
            }

            PermissionStep.USAGE -> {
                openUsageSettings()
                sendAppLog("info", "permission_step_usage_prompted")
            }

            PermissionStep.OVERLAY -> {
                openOverlaySettings()
                sendAppLog("info", "permission_step_overlay_prompted")
            }

            PermissionStep.NOTIFICATIONS -> {
                openNotificationAccess()
                sendAppLog("info", "permission_step_notifications_prompted")
            }

            PermissionStep.COMPLETE -> Unit
        }
    }

    private fun isPermissionStepGranted(step: PermissionStep, state: PermissionOnboardingState): Boolean {
        return when (step) {
            PermissionStep.SMS -> state.smsGranted
            PermissionStep.USAGE -> state.usageGranted
            PermissionStep.OVERLAY -> state.overlayGranted
            PermissionStep.NOTIFICATIONS -> state.notificationsGranted
            PermissionStep.COMPLETE -> state.isComplete()
        }
    }

    private fun buildBulletedDialogMessage(
        bullets: List<String>,
        intro: String? = null,
        outro: String? = null,
    ): CharSequence {
        val builder = SpannableStringBuilder()
        val bulletGapPx = (resources.displayMetrics.density * 12).toInt()

        if (!intro.isNullOrBlank()) {
            builder.append(intro.trim())
            if (bullets.any { it.isNotBlank() }) {
                builder.append("\n\n")
            }
        }

        bullets.filter { it.isNotBlank() }.forEachIndexed { index, bullet ->
            if (index > 0) {
                builder.append('\n')
            }
            val start = builder.length
            builder.append(bullet.trim())
            builder.setSpan(
                BulletSpan(bulletGapPx),
                start,
                builder.length,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE,
            )
        }

        if (!outro.isNullOrBlank()) {
            if (builder.isNotEmpty()) {
                builder.append("\n\n")
            }
            builder.append(outro.trim())
        }
        return builder
    }

    private fun buildInfoBoxDialog(
        title: String,
        subtitle: String?,
        guidedStep: Int? = null,
        guidedTrackerCopy: GuidedTrackerCopy? = null,
        body: CharSequence,
        positiveLabel: String,
        negativeLabel: String?,
        cancelable: Boolean,
        onPositive: () -> Unit,
        onNegative: ((AlertDialog) -> Unit)? = null,
    ): AlertDialog {
        val contentView = LayoutInflater.from(this).inflate(R.layout.dialog_info_box, null)
        val titleView = contentView.findViewById<TextView>(R.id.infoDialogTitle)
        val subtitleView = contentView.findViewById<TextView>(R.id.infoDialogSubtitle)
        val stepCard = contentView.findViewById<LinearLayout>(R.id.infoDialogStepCard)
        val stepTitleView = contentView.findViewById<TextView>(R.id.infoDialogStepTitle)
        val stepSubtitleView = contentView.findViewById<TextView>(R.id.infoDialogStepSubtitle)
        val stepNumViews = listOf(
            contentView.findViewById<TextView>(R.id.infoDialogStepOneNum),
            contentView.findViewById<TextView>(R.id.infoDialogStepTwoNum),
            contentView.findViewById<TextView>(R.id.infoDialogStepThreeNum),
            contentView.findViewById<TextView>(R.id.infoDialogStepFourNum),
        )
        val stepTextViews = listOf(
            contentView.findViewById<TextView>(R.id.infoDialogStepOneText),
            contentView.findViewById<TextView>(R.id.infoDialogStepTwoText),
            contentView.findViewById<TextView>(R.id.infoDialogStepThreeText),
            contentView.findViewById<TextView>(R.id.infoDialogStepFourText),
        )
        val bodyView = contentView.findViewById<TextView>(R.id.infoDialogBody)
        val actionsView = contentView.findViewById<LinearLayout>(R.id.infoDialogActions)
        val negativeButton = contentView.findViewById<Button>(R.id.infoDialogNegativeButton)
        val positiveButton = contentView.findViewById<Button>(R.id.infoDialogPositiveButton)

        titleView.text = title
        if (subtitle.isNullOrBlank()) {
            subtitleView.visibility = View.GONE
        } else {
            subtitleView.visibility = View.VISIBLE
            subtitleView.text = subtitle
        }
        bindGuidedSetupTracker(
            stepCard = stepCard,
            stepTitleView = stepTitleView,
            stepSubtitleView = stepSubtitleView,
            stepNumViews = stepNumViews,
            stepTextViews = stepTextViews,
            trackerCopy = guidedTrackerCopy ?: defaultGuidedTrackerCopy(guidedStep),
        )
        bodyView.text = body

        val dialog = AlertDialog.Builder(this)
            .setView(contentView)
            .setCancelable(cancelable)
            .create()
        dialog.setCanceledOnTouchOutside(cancelable)

        if (negativeLabel.isNullOrBlank()) {
            negativeButton.visibility = View.GONE
        } else {
            negativeButton.visibility = View.VISIBLE
            negativeButton.text = negativeLabel
        }
        positiveButton.text = positiveLabel
        negativeButton.setTextColor(ContextCompat.getColor(this, R.color.btn_secondary_text))
        positiveButton.setTextColor(ContextCompat.getColor(this, R.color.btn_primary_text))
        negativeButton.backgroundTintList = null
        positiveButton.backgroundTintList = null

        negativeButton.setOnClickListener {
            if (onNegative != null) {
                onNegative(dialog)
            } else {
                dialog.dismiss()
            }
        }
        positiveButton.setOnClickListener {
            dialog.dismiss()
            onPositive()
        }
        return dialog
    }

    private fun bindGuidedSetupTracker(
        stepCard: View,
        stepTitleView: TextView,
        stepSubtitleView: TextView,
        stepNumViews: List<TextView>,
        stepTextViews: List<TextView>,
        trackerCopy: GuidedTrackerCopy?,
    ) {
        if (trackerCopy == null) {
            stepCard.visibility = View.GONE
            return
        }

        stepCard.visibility = View.VISIBLE
        stepTitleView.text = trackerCopy.title
        stepSubtitleView.text = trackerCopy.subtitle

        stepNumViews.forEachIndexed { index, textView ->
            val stepNumber = index + 1
            when {
                stepNumber < trackerCopy.currentStep -> {
                    textView.setBackgroundResource(R.drawable.bg_step_circle_done)
                    textView.setTextColor(ContextCompat.getColor(this, R.color.color_semantic_safe_text))
                    stepTextViews[index].setTextColor(ContextCompat.getColor(this, R.color.text_primary))
                }
                stepNumber == trackerCopy.currentStep -> {
                    textView.setBackgroundResource(R.drawable.bg_step_circle_active)
                    textView.setTextColor(ContextCompat.getColor(this, android.R.color.white))
                    stepTextViews[index].setTextColor(ContextCompat.getColor(this, R.color.text_primary))
                }
                else -> {
                    textView.setBackgroundResource(R.drawable.bg_step_circle_inactive)
                    textView.setTextColor(ContextCompat.getColor(this, R.color.text_secondary))
                    stepTextViews[index].setTextColor(ContextCompat.getColor(this, R.color.text_secondary))
                }
            }
            stepTextViews[index].text = trackerCopy.itemLabels.getOrElse(index) { "" }
        }
    }

    private fun defaultGuidedTrackerCopy(currentStep: Int?): GuidedTrackerCopy? {
        if (currentStep == null) {
            return null
        }
        val title = when (currentStep) {
            1 -> getString(R.string.dialog_setup_step_1_title)
            2 -> getString(R.string.dialog_setup_step_2_title)
            3 -> getString(R.string.dialog_setup_step_3_title)
            else -> getString(R.string.dialog_setup_step_4_title)
        }
        val subtitle = when (currentStep) {
            1 -> getString(R.string.dialog_setup_step_1_subtitle)
            2 -> getString(R.string.dialog_setup_step_2_subtitle)
            3 -> getString(R.string.dialog_setup_step_3_subtitle)
            else -> getString(R.string.dialog_setup_step_4_subtitle)
        }
        return GuidedTrackerCopy(
            currentStep = currentStep,
            title = title,
            subtitle = subtitle,
            itemLabels = listOf(
                getString(R.string.dialog_setup_step_item_language),
                getString(R.string.dialog_setup_step_item_consent),
                getString(R.string.dialog_setup_step_item_permissions),
                getString(R.string.dialog_setup_step_item_monitoring),
            ),
        )
    }

    private fun permissionGuidedTrackerCopy(step: PermissionStep): GuidedTrackerCopy {
        val currentStep = permissionFlowStepNumber(step)
        val title = when (currentStep) {
            1 -> getString(R.string.dialog_perm_tracker_step_1_title)
            2 -> getString(R.string.dialog_perm_tracker_step_2_title)
            3 -> getString(R.string.dialog_perm_tracker_step_3_title)
            else -> getString(R.string.dialog_perm_tracker_step_4_title)
        }
        val subtitle = when (currentStep) {
            1 -> getString(R.string.dialog_perm_tracker_step_1_subtitle)
            2 -> getString(R.string.dialog_perm_tracker_step_2_subtitle)
            3 -> getString(R.string.dialog_perm_tracker_step_3_subtitle)
            else -> getString(R.string.dialog_perm_tracker_step_4_subtitle)
        }
        return GuidedTrackerCopy(
            currentStep = currentStep,
            title = title,
            subtitle = subtitle,
            itemLabels = listOf(
                getString(R.string.dialog_perm_tracker_item_sms_notifications),
                getString(R.string.dialog_perm_tracker_item_usage),
                getString(R.string.dialog_perm_tracker_item_overlay),
                getString(R.string.dialog_perm_tracker_item_monitoring),
            ),
        )
    }

    private fun permissionFlowStepNumber(step: PermissionStep): Int {
        return when (step) {
            PermissionStep.SMS, PermissionStep.NOTIFICATIONS -> 1
            PermissionStep.USAGE -> 2
            PermissionStep.OVERLAY -> 3
            PermissionStep.COMPLETE -> 4
        }
    }

    private fun showManagedFlowDialog(
        dialog: AlertDialog,
        transparentBackground: Boolean = true,
        onDismissExtra: (() -> Unit)? = null,
    ) {
        activeFlowDialog?.dismiss()
        activeFlowDialog = dialog
        dialog.setOnDismissListener {
            if (activeFlowDialog === dialog) {
                activeFlowDialog = null
            }
            onDismissExtra?.invoke()
        }
        dialog.show()
        if (transparentBackground) {
            dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        }
    }

    private fun requestSmsRuntimePermissions() {
        val needed = mutableListOf<String>()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.RECEIVE_SMS)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.READ_SMS)
        }

        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), AppConstants.RequestCodes.RUNTIME_PERMISSIONS)
        }
    }

    private fun requestRuntimePermissions() {
        val needed = mutableListOf<String>()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.RECEIVE_SMS)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.READ_SMS)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            needed.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), AppConstants.RequestCodes.RUNTIME_PERMISSIONS)
        }
    }

    private fun openUsageSettings() {
        markPendingPermissionSettingsStep(PermissionStep.USAGE)
        markRestoreDrawerOnReturn()
        val directUsageIntent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
            data = Uri.parse("package:$packageName")
            putExtra(EXTRA_APP_PACKAGE, packageName)
            putExtra("packageName", packageName)
        }
        val appDetailsIntent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:$packageName")
        }
        launchSettingsIntent(directUsageIntent, appDetailsIntent)
    }

    private fun openNotificationAccess() {
        if (!hasNotificationPostingPermission()) {
            requestNotificationPermissionIfNeeded()
            return
        }

        val notificationsEnabled = NotificationManagerCompat.from(this).areNotificationsEnabled()
        if (notificationsEnabled && hasNotificationListenerPermission()) {
            val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            if (prefs.getBoolean(AppConstants.Prefs.KEY_GUIDED_PERMISSION_FLOW_ACTIVE, false)) {
                showPermissionSetupDialog(permissionStepOverride = permissionOnboardingState().nextStep())
            }
            return
        }

        markRestoreDrawerOnReturn()
        markPendingPermissionSettingsStep(PermissionStep.NOTIFICATIONS)
        if (!notificationsEnabled) {
            val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                    putExtra(EXTRA_APP_PACKAGE, packageName)
                }
            } else {
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.parse("package:$packageName")
                }
            }
            startActivity(intent)
            return
        }

        val listenerSettingsIntent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
        val appDetailsIntent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:$packageName")
        }
        launchSettingsIntent(listenerSettingsIntent, appDetailsIntent)
    }

    private fun hasNotificationAccessForOnboarding(): Boolean {
        return hasNotificationPostingPermission() &&
            NotificationManagerCompat.from(this).areNotificationsEnabled() &&
            hasNotificationListenerPermission()
    }

    private fun hasNotificationPostingPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
    }

    private fun openOverlaySettings() {
        markPendingPermissionSettingsStep(PermissionStep.OVERLAY)
        markRestoreDrawerOnReturn()
        val packageUri = Uri.parse("package:$packageName")
        val explicitOverlayAospIntent = Intent().apply {
            setClassName(
                "com.android.settings",
                "com.android.settings.Settings\$AppDrawOverlaySettingsActivity",
            )
            data = packageUri
            putExtra(EXTRA_APP_PACKAGE, packageName)
            putExtra("packageName", packageName)
        }
        val explicitOverlaySubSettingsIntent = Intent().apply {
            setClassName("com.android.settings", "com.android.settings.SubSettings")
            putExtra(":settings:show_fragment", "com.android.settings.applications.appinfo.DrawOverlayDetails")
            putExtra(":settings:show_fragment_args", Bundle().apply { putString("package", packageName) })
            putExtra(EXTRA_APP_PACKAGE, packageName)
        }
        val directOverlayIntent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, packageUri)
        val directOverlayWithDataIntent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION).apply {
            data = packageUri
            putExtra(EXTRA_APP_PACKAGE, packageName)
        }
        val appDetailsIntent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = packageUri
        }
        launchSettingsIntents(
            listOf(
                explicitOverlayAospIntent,
                explicitOverlaySubSettingsIntent,
                directOverlayIntent,
                directOverlayWithDataIntent,
                appDetailsIntent,
            ),
        )
    }

    private fun startMonitoringWithChecks() {
        syncPermissionOnboardingDone()
        val onboardingState = onboardingEntryState()
        val activationState = MonitoringActivationState(
            onboardingStep = onboardingState.nextStep(),
            permissionState = permissionOnboardingState(),
        )

        when (activationState.blocker()) {
            MonitoringStartBlocker.ONBOARDING -> {
                refreshPrimaryActionState(onboardingState)
                toast(getString(R.string.toast_complete_setup_first))
                sendAppLog("warn", "monitor_start_blocked_onboarding:${onboardingState.nextStep().name.lowercase()}")
                when (onboardingState.nextStep()) {
                    OnboardingStep.MONEY_SETUP -> showMoneySetupDialog()
                    OnboardingStep.PERMISSIONS -> showPermissionSetupDialog()
                    else -> continueOnboardingFlow(forceResumeConsent = true)
                }
                return
            }

            MonitoringStartBlocker.SMS -> {
                setStatus(getString(R.string.status_sms_missing))
                toast(getString(R.string.toast_sms_missing))
                sendAppLog("warn", "monitor_start_blocked_sms_access")
                continueOnboardingFlow()
                return
            }

            MonitoringStartBlocker.USAGE -> {
                setStatus(getString(R.string.status_usage_missing))
                toast(getString(R.string.toast_usage_missing))
                sendAppLog("warn", "monitor_start_blocked_usage_access")
                continueOnboardingFlow()
                return
            }

            MonitoringStartBlocker.OVERLAY -> {
                setStatus(getString(R.string.status_overlay_missing))
                toast(getString(R.string.toast_overlay_missing))
                sendAppLog("warn", "monitor_start_blocked_overlay_access")
                continueOnboardingFlow()
                return
            }

            MonitoringStartBlocker.NOTIFICATIONS -> {
                setStatus(getString(R.string.status_notifications_missing))
                toast(getString(R.string.toast_notifications_missing))
                sendAppLog("warn", "monitor_start_blocked_notifications_access")
                continueOnboardingFlow()
                return
            }

            MonitoringStartBlocker.NONE -> Unit
        }

        try {
            startForegroundService(Intent(this, AppUsageForegroundService::class.java))
            setMonitoringActive(true)
            setStatus(getString(R.string.status_monitoring_active))
            toast(getString(R.string.toast_monitor_started))
            sendAppLog("info", "monitor_started")
            maybeShowMonitoringVerificationAlert()
        } catch (e: Exception) {
            setMonitoringActive(false)
            setStatus(getString(R.string.status_monitoring_failed))
            toast(e.message ?: getString(R.string.toast_monitor_failed))
            sendAppLog("error", "monitor_start_error:${e.message}")
        }
    }

    private fun handlePrimaryAction() {
        val state = onboardingEntryState()
        if (state.homePrimaryActionState() == HomePrimaryActionState.RESUME_SETUP) {
            continueOnboardingFlow(forceResumeConsent = true)
            return
        }
        startMonitoringWithChecks()
    }

    private fun maybeShowMonitoringVerificationAlert() {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        if (prefs.getBoolean(AppConstants.Prefs.KEY_SETUP_VERIFICATION_SHOWN, false)) {
            return
        }

        prefs.edit().putBoolean(AppConstants.Prefs.KEY_SETUP_VERIFICATION_SHOWN, true).apply()
        AlertNotifier.show(
            context = this,
            title = getString(R.string.alert_setup_verification_title),
            body = getString(R.string.alert_setup_verification_body),
            alertId = "setup-verification-${System.currentTimeMillis()}",
            severity = "soft",
            nextSafeAction = getString(R.string.alert_setup_verification_next_action),
        )
        sendAppLog("info", "setup_verification_alert_shown")
    }

    private fun checkApiStatus() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                LiteracyRepository.status(this@MainActivity)
                runOnUiThread {
                    toast(getString(R.string.toast_api_ok))
                    setStatus(getString(R.string.status_api_connected))
                }
                sendAppLog("info", "api_status_ok")
            } catch (e: Exception) {
                runOnUiThread {
                    toast(getString(R.string.toast_api_failed))
                    setStatus(getString(R.string.status_api_disconnected))
                }
                sendAppLog("error", "api_status_fail:${e.message}")
            }
        }
    }

    private fun supportedLanguages(): List<LanguageOption> {
        return listOf(
            LanguageOption(
                AppConstants.Locale.DEFAULT_LANGUAGE,
                getString(R.string.lang_english),
                getString(R.string.lang_badge_en),
            ),
            LanguageOption(
                AppConstants.Locale.HINDI_LANGUAGE,
                getString(R.string.lang_hindi),
                getString(R.string.lang_badge_hi),
            ),
        )
    }

    private fun showLanguageDropdownMenu() {
        val languageOptions = supportedLanguages()
        val popup = PopupMenu(this, languageChip)
        languageOptions.forEachIndexed { index, option ->
            popup.menu.add(0, index, index, option.displayName)
        }
        popup.setOnMenuItemClickListener { menuItem ->
            val selected = languageOptions.getOrNull(menuItem.itemId) ?: return@setOnMenuItemClickListener false
            applyLanguage(selected.code, markSelected = true)
            true
        }
        popup.show()
    }

    private fun applyLanguage(langCode: String, markSelected: Boolean, reopenHelpAfterSwitch: Boolean = false) {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val editor = prefs.edit().putString(AppConstants.Prefs.KEY_APP_LANGUAGE, langCode)
        if (markSelected) {
            editor.putBoolean(AppConstants.Prefs.KEY_LANGUAGE_SELECTED, true)
        }
        // A locale switch should not inherit drawer-open restoration from earlier navigation state.
        editor.putBoolean(AppConstants.Prefs.KEY_DRAWER_OPEN, false)
        editor.putBoolean(AppConstants.Prefs.KEY_RESTORE_DRAWER_ON_RETURN, false)
        editor.putBoolean(AppConstants.Prefs.KEY_REOPEN_HELP_AFTER_LOCALE_SWITCH, reopenHelpAfterSwitch)
        editor.apply()

        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(langCode))
        sendAppLog("info", "language_selected:$langCode")
        if (reopenHelpAfterSwitch) {
            applyLanguageInPlace()
        } else {
            val restartIntent = Intent(this, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION)
            }
            startActivity(restartIntent)
            finish()
            overridePendingTransition(0, 0)
        }
    }

    private fun updateLanguageChip() {
        val current = supportedLanguages().find { it.code == currentLangCode() } ?: supportedLanguages().first()
        languageChip.text = current.badgeText
    }

    private fun animateDashboardCards() {
        listOf(summaryCard, monitorCard, infoCard).forEachIndexed { index, view ->
            view.alpha = 0f
            view.translationY = 22f
            view.animate()
                .alpha(1f)
                .translationY(0f)
                .setStartDelay((index * 90).toLong())
                .setDuration(240)
                .start()
        }
    }

    private fun promptFeedback() {
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 20, 40, 10)
        }
        val ratingInput = EditText(this).apply {
            hint = getString(R.string.feedback_rating_hint)
            setText(AppConstants.UiDefaults.FEEDBACK_DEFAULT_RATING.toString())
        }
        val commentInput = EditText(this).apply {
            hint = getString(R.string.feedback_comment_hint)
        }
        container.addView(ratingInput)
        container.addView(commentInput)

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.feedback_title))
            .setView(container)
            .setPositiveButton(getString(R.string.feedback_submit)) { _, _ ->
                val rating = ratingInput.text.toString().trim().toIntOrNull()
                val comment = commentInput.text.toString().trim()

                if (rating == null || rating !in 1..5) {
                    toast(getString(R.string.toast_feedback_failed))
                    return@setPositiveButton
                }

                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        val ok = LiteracyRepository.submitPilotFeedback(
                            context = this@MainActivity,
                            participantId = participantId,
                            rating = rating,
                            comment = comment,
                            language = currentLangCode(),
                        )
                        runOnUiThread {
                            if (ok) toast(getString(R.string.toast_feedback_ok))
                            else toast(getString(R.string.toast_feedback_failed))
                        }
                        sendAppLog("info", "feedback_submit:$ok")
                    } catch (e: Exception) {
                        runOnUiThread { toast(getString(R.string.toast_feedback_failed)) }
                        sendAppLog("error", "feedback_submit_error:${e.message}")
                    }
                }
            }
            .setNegativeButton(getString(R.string.feedback_cancel), null)
            .show()
    }

    private fun openPrivacyPolicy() {
        val privacyUrl = BuildConfig.PRIVACY_POLICY_URL
        if (privacyUrl.isBlank()) {
            toast(getString(R.string.toast_settings_open_failed))
            return
        }
        runCatching {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(privacyUrl)))
        }.onFailure {
            toast(getString(R.string.toast_settings_open_failed))
        }
    }

    private fun showHelpDialog(supportContext: SupportAlertContext? = null) {
        val languageOptions = supportedLanguages()
        val options = languageOptions.map { it.displayName }
        val selectedIndex = languageOptions.indexOfFirst { it.code == currentLangCode() }.takeIf { it >= 0 } ?: 0

        val contentView = LayoutInflater.from(this).inflate(R.layout.dialog_help_setup, null)
        val heading = contentView.findViewById<TextView>(R.id.helpDialogTitle)
        val subtitle = contentView.findViewById<TextView>(R.id.helpDialogSubtitle)
        val helpText = contentView.findViewById<TextView>(R.id.helpDialogSteps)
        val languageLabel = contentView.findViewById<TextView>(R.id.helpLanguageLabel)
        val spinner = contentView.findViewById<Spinner>(R.id.helpLanguageSpinner)
        val moneySetupButton = contentView.findViewById<Button>(R.id.helpMoneySetupButton)
        val facilitatorPackButton = contentView.findViewById<Button>(R.id.helpFacilitatorPackButton)
        val closeButton = contentView.findViewById<ImageButton>(R.id.helpCloseButton)
        val applyButton = contentView.findViewById<ImageButton>(R.id.helpApplyButton)
        val isSupportMode = supportContext != null

        heading.text = if (isSupportMode) getString(R.string.help_support_title) else getString(R.string.help_title)
        subtitle.text = if (isSupportMode) getString(R.string.help_support_subtitle) else getString(R.string.help_subtitle)
        helpText.text = if (isSupportMode) supportHelpStepsText() else helpStepsText()
        languageLabel.text = getString(R.string.help_change_language)
        moneySetupButton.text = getString(R.string.help_edit_money_setup)
        facilitatorPackButton.text = if (isSupportMode) {
            getString(R.string.help_support_open_facilitator_pack)
        } else {
            getString(R.string.help_open_facilitator_pack)
        }
        spinner.adapter = ArrayAdapter(
            this@MainActivity,
            android.R.layout.simple_spinner_item,
            options,
        ).also { a -> a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        spinner.setSelection(selectedIndex)
        spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                updateHelpApplyButtonState(
                    applyButton = applyButton,
                    selectedCode = languageOptions.getOrNull(position)?.code ?: currentLangCode(),
                )
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {
                updateHelpApplyButtonState(applyButton, currentLangCode())
            }
        }

        bindSupportContextCard(
            contextCard = contentView.findViewById(R.id.helpSupportContextCard),
            titleView = contentView.findViewById(R.id.helpSupportContextTitle),
            bodyView = contentView.findViewById(R.id.helpSupportContextBody),
            whyHeading = contentView.findViewById(R.id.helpSupportWhyHeading),
            whyBody = contentView.findViewById(R.id.helpSupportWhyBody),
            nextHeading = contentView.findViewById(R.id.helpSupportNextHeading),
            nextBody = contentView.findViewById(R.id.helpSupportNextBody),
            goalHeading = contentView.findViewById(R.id.helpSupportGoalHeading),
            goalBody = contentView.findViewById(R.id.helpSupportGoalBody),
            supportContext = supportContext,
        )
        contentView.findViewById<View>(R.id.helpSupportContextCard).visibility = if (isSupportMode) View.VISIBLE else View.GONE
        languageLabel.visibility = if (isSupportMode) View.GONE else View.VISIBLE
        spinner.visibility = if (isSupportMode) View.GONE else View.VISIBLE
        moneySetupButton.visibility = if (isSupportMode) View.GONE else View.VISIBLE
        applyButton.visibility = if (isSupportMode) View.GONE else View.VISIBLE
        updateHelpApplyButtonState(
            applyButton = applyButton,
            selectedCode = languageOptions.getOrNull(spinner.selectedItemPosition)?.code ?: currentLangCode(),
        )

        val dialog = AlertDialog.Builder(this)
            .setView(contentView)
            .create()

        dialog.setOnShowListener {
            closeButton.setOnClickListener {
                dialog.dismiss()
            }
            moneySetupButton.setOnClickListener {
                dialog.dismiss()
                showMoneySetupDialog()
            }
            facilitatorPackButton.setOnClickListener {
                dialog.dismiss()
                showFacilitatorSetupPackDialog(supportContext)
            }
            applyButton.setOnClickListener {
                val langCode = languageOptions.getOrNull(spinner.selectedItemPosition)?.code ?: currentLangCode()
                if (langCode != currentLangCode()) {
                    applyLanguage(langCode, markSelected = true, reopenHelpAfterSwitch = true)
                }
            }
        }
        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        currentHelpDialog = dialog
        activeHelpDialogSupportContext = supportContext
        helpHeadingView = heading
        helpSubtitleView = subtitle
        helpStepsView = helpText
        helpLanguageLabelView = languageLabel
        helpLanguageSpinner = spinner
        helpMoneySetupButton = moneySetupButton
        helpFacilitatorPackButton = facilitatorPackButton
        helpApplyButton = applyButton
    }

    private fun helpStepsText(): String {
        return listOf(
            getString(R.string.help_step_1),
            getString(R.string.help_step_2),
            getString(R.string.help_step_3),
            getString(R.string.help_step_4),
            getString(R.string.help_step_5),
            getString(R.string.help_step_6),
        ).joinToString(separator = "\n") { "• $it" }
    }

    private fun supportHelpStepsText(): String {
        return listOf(
            getString(R.string.help_support_step_1),
            getString(R.string.help_support_step_2),
            getString(R.string.help_support_step_3),
            getString(R.string.help_support_step_4),
        ).joinToString(separator = "\n") { "• $it" }
    }

    private fun maybeRestoreHelpDialogAfterLanguageSwitch() {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val shouldReopen = prefs.getBoolean(AppConstants.Prefs.KEY_REOPEN_HELP_AFTER_LOCALE_SWITCH, false)
        if (!shouldReopen) {
            return
        }

        prefs.edit().putBoolean(AppConstants.Prefs.KEY_REOPEN_HELP_AFTER_LOCALE_SWITCH, false).apply()
        updateLanguageChip()
        window.decorView.post { showHelpDialog(activeSupportAlertContext) }
    }

    private fun applyLanguageInPlace() {
        val locale = AppCompatDelegate.getApplicationLocales()[0] ?: return
        val config = Configuration(resources.configuration)
        config.setLocale(locale)
        resources.updateConfiguration(config, resources.displayMetrics)

        refreshLocalizedUiTexts()
        refreshHelpDialogTextsInPlace()
    }

    private fun refreshLocalizedUiTexts() {
        findViewById<TextView>(R.id.homeTitle).text = getString(R.string.home_title)
        findViewById<TextView>(R.id.homeSubtitle).text = getString(R.string.home_subtitle)
        findViewById<TextView>(R.id.monitorTitle).text = getString(R.string.home_card_monitor_title)
        findViewById<TextView>(R.id.monitorDesc).text = getString(R.string.home_card_monitor_desc)
        findViewById<TextView>(R.id.infoTitle).text = getString(R.string.home_card_info_title)
        findViewById<TextView>(R.id.infoDesc).text = getString(R.string.home_card_info_desc)
        stopServiceButton.text = getString(R.string.action_stop_monitor)
        moneySetupLine.text = getString(R.string.money_setup_pending)

        val header = navigationView.getHeaderView(0)
        header.findViewById<TextView>(R.id.navHeaderTitle)?.text = getString(R.string.nav_title)
        header.findViewById<TextView>(R.id.navHeaderSubtitle)?.text = getString(R.string.nav_subtitle)

        applyDrawerMenuState()

        updateLanguageChip()
        refreshPrimaryActionState()
        loadEssentialGoalSummary()
    }

    private fun refreshHelpDialogTextsInPlace() {
        val isSupportMode = activeHelpDialogSupportContext != null
        helpHeadingView?.text = if (isSupportMode) getString(R.string.help_support_title) else getString(R.string.help_title)
        helpSubtitleView?.text = if (isSupportMode) getString(R.string.help_support_subtitle) else getString(R.string.help_subtitle)
        helpStepsView?.text = if (isSupportMode) supportHelpStepsText() else helpStepsText()
        helpLanguageLabelView?.text = getString(R.string.help_change_language)
        helpMoneySetupButton?.text = getString(R.string.help_edit_money_setup)
        helpFacilitatorPackButton?.text = if (isSupportMode) {
            getString(R.string.help_support_open_facilitator_pack)
        } else {
            getString(R.string.help_open_facilitator_pack)
        }

        val spinner = helpLanguageSpinner ?: return
        val options = supportedLanguages().map { it.displayName }
        spinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            options,
        ).also { a -> a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        val selectedIndex = supportedLanguages().indexOfFirst { it.code == currentLangCode() }.takeIf { it >= 0 } ?: 0
        spinner.setSelection(selectedIndex)
        updateHelpApplyButtonState(helpApplyButton, currentLangCode())
    }

    private fun maybeHandleSupportEscalationIntent(intent: Intent?) {
        if (intent == null || !intent.getBooleanExtra(AppConstants.IntentExtras.ALERT_OPEN_SUPPORT_PATH, false)) {
            return
        }

        activeSupportAlertContext = SupportAlertContext(
            alertId = intent.getStringExtra(AppConstants.IntentExtras.ALERT_ID).orEmpty(),
            title = intent.getStringExtra(AppConstants.IntentExtras.ALERT_TITLE) ?: getString(R.string.alert_title_default),
            body = intent.getStringExtra(AppConstants.IntentExtras.ALERT_MESSAGE) ?: getString(R.string.alert_body_default),
            whyThisAlert = intent.getStringExtra(AppConstants.IntentExtras.ALERT_WHY_THIS_ALERT).orEmpty(),
            nextSafeAction = intent.getStringExtra(AppConstants.IntentExtras.ALERT_NEXT_SAFE_ACTION).orEmpty(),
            essentialGoalImpact = intent.getStringExtra(AppConstants.IntentExtras.ALERT_ESSENTIAL_GOAL_IMPACT).orEmpty(),
        )
        intent.removeExtra(AppConstants.IntentExtras.ALERT_OPEN_SUPPORT_PATH)
        currentHelpDialog?.dismiss()
        window.decorView.post { showHelpDialog(activeSupportAlertContext) }
    }

    private fun bindSupportContextCard(
        contextCard: View,
        titleView: TextView,
        bodyView: TextView,
        whyHeading: TextView,
        whyBody: TextView,
        nextHeading: TextView,
        nextBody: TextView,
        goalHeading: TextView,
        goalBody: TextView,
        supportContext: SupportAlertContext?,
    ) {
        if (supportContext == null) {
            contextCard.visibility = View.GONE
            return
        }

        contextCard.visibility = View.VISIBLE
        titleView.text = supportContext.title
        bodyView.text = supportContext.body
        bindOptionalSupportField(
            heading = whyHeading,
            body = whyBody,
            headingText = getString(R.string.alert_why_this_alert_label),
            value = supportContext.whyThisAlert,
        )
        bindOptionalSupportField(
            heading = nextHeading,
            body = nextBody,
            headingText = getString(R.string.alert_next_safe_action_label),
            value = supportContext.nextSafeAction,
        )
        bindOptionalSupportField(
            heading = goalHeading,
            body = goalBody,
            headingText = getString(R.string.alert_essential_goal_impact_label),
            value = supportContext.essentialGoalImpact,
        )
    }

    private fun bindOptionalSupportField(
        heading: TextView,
        body: TextView,
        headingText: String,
        value: String,
    ) {
        if (value.isBlank()) {
            heading.visibility = View.GONE
            body.visibility = View.GONE
            return
        }

        heading.text = headingText
        heading.visibility = View.VISIBLE
        body.text = value
        body.visibility = View.VISIBLE
    }

    private fun updateHelpApplyButtonState(applyButton: ImageButton?, selectedCode: String) {
        val button = applyButton ?: return
        val enabled = selectedCode != currentLangCode()
        button.isEnabled = enabled
        button.alpha = if (enabled) 1f else 0.45f
    }

    private fun toggleManageAccessItems() {
        accessItemsExpanded = !accessItemsExpanded
        getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(AppConstants.Prefs.KEY_MANAGE_ACCESS_EXPANDED, accessItemsExpanded)
            .apply()
        applyDrawerMenuState()
    }

    private fun applyDrawerMenuState() {
        val menuRes = if (accessItemsExpanded) R.menu.drawer_menu_expanded else R.menu.drawer_menu_collapsed
        navigationView.menu.clear()
        navigationView.inflateMenu(menuRes)
        bindManageAccessToggleAction()
        if (accessItemsExpanded) {
            navigationView.menu.findItem(R.id.nav_access_notifications)?.title =
                indentedMenuTitle(getString(R.string.menu_access_notifications))
            navigationView.menu.findItem(R.id.nav_access_usage)?.title =
                indentedMenuTitle(getString(R.string.menu_access_usage))
            navigationView.menu.findItem(R.id.nav_access_overlay)?.title =
                indentedMenuTitle(getString(R.string.menu_access_overlay))
        }
        navigationView.invalidate()
    }

    private fun bindManageAccessToggleAction() {
        val manageAccessItem = navigationView.menu.findItem(R.id.nav_manage_access) ?: return
        val actionView = manageAccessItem.actionView ?: return
        val iconView = actionView.findViewById<ImageView>(R.id.manageAccessToggleIcon)
        iconView?.setImageResource(
            if (accessItemsExpanded) R.drawable.ic_chevron_up else R.drawable.ic_chevron_down,
        )

        val toggle = View.OnClickListener {
            toggleManageAccessItems()
        }
        iconView?.setOnClickListener(toggle)
        actionView.setOnClickListener(toggle)
    }

    private fun indentedMenuTitle(text: String): String {
        return "\u2003\u2003$text"
    }

    private fun launchSettingsIntent(primary: Intent, fallback: Intent? = null) {
        val pm = packageManager
        val resolved = when {
            primary.resolveActivity(pm) != null -> primary
            fallback != null && fallback.resolveActivity(pm) != null -> fallback
            else -> null
        }
        if (resolved != null) {
            runCatching { startActivity(resolved) }
                .onFailure {
                    val fallbackResolved = fallback?.takeIf { candidate -> candidate.resolveActivity(pm) != null }
                    if (fallbackResolved != null) {
                        runCatching { startActivity(fallbackResolved) }
                            .onFailure { toast(getString(R.string.toast_settings_open_failed)) }
                    } else {
                        toast(getString(R.string.toast_settings_open_failed))
                    }
                }
        } else {
            toast(getString(R.string.toast_settings_open_failed))
        }
    }

    private fun launchSettingsIntents(candidates: List<Intent>) {
        val pm = packageManager
        for (candidate in candidates) {
            if (candidate.resolveActivity(pm) == null) {
                continue
            }
            try {
                startActivity(candidate)
                return
            } catch (_: ActivityNotFoundException) {
                // try next candidate
            } catch (_: SecurityException) {
                // try next candidate
            } catch (_: RuntimeException) {
                // some OEM settings screens throw runtime exceptions, try next
            }
        }
        toast(getString(R.string.toast_settings_open_failed))
    }

    private fun markRestoreDrawerOnReturn() {
        getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(AppConstants.Prefs.KEY_RESTORE_DRAWER_ON_RETURN, true)
            .putBoolean(AppConstants.Prefs.KEY_DRAWER_OPEN, true)
            .putBoolean(AppConstants.Prefs.KEY_MANAGE_ACCESS_EXPANDED, accessItemsExpanded)
            .apply()
    }

    private fun loadPilotMeta() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val meta = LiteracyRepository.pilotMeta(this@MainActivity)
                runOnUiThread {
                    pilotBanner.text = "${meta.disclaimer}"
                }
            } catch (_: Exception) {
                // keep default banner
            }
        }
    }

    private fun hasUsageStatsPermission(): Boolean {
        val appOps = getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                packageName,
            )
        } else {
            @Suppress("DEPRECATION")
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                packageName,
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }

    private fun hasNotificationListenerPermission(): Boolean {
        val enabled = Secure.getString(contentResolver, AppConstants.SecureSettings.ENABLED_NOTIFICATION_LISTENERS) ?: return false
        return enabled.contains(packageName)
    }

    private fun hasSmsAccessEnabled(): Boolean {
        val smsReceive = ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED
        val smsRead = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED
        return smsReceive && smsRead
    }

    private fun setStatus(text: String) {
        statusLine.text = text
    }

    private fun setMoneySetupState(done: Boolean, skipped: Boolean) {
        getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, done)
            .putBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_SKIPPED, skipped)
            .apply()
    }

    private fun cacheMoneySetupSelection(
        cohort: String,
        goals: List<String>,
        done: Boolean,
        skipped: Boolean,
    ) {
        getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, done)
            .putBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_SKIPPED, skipped)
            .putString(AppConstants.Prefs.KEY_MONEY_SETUP_COHORT, cohort)
            .putString(AppConstants.Prefs.KEY_MONEY_SETUP_GOALS, goals.joinToString("|"))
            .apply()
    }

    private fun applyLocalMoneySetupFallback() {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val done = prefs.getBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, false)
        val skipped = prefs.getBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_SKIPPED, false)
        val cohort = prefs.getString(AppConstants.Prefs.KEY_MONEY_SETUP_COHORT, null).orEmpty()
        val goals = prefs.getString(AppConstants.Prefs.KEY_MONEY_SETUP_GOALS, null)
            .orEmpty()
            .split("|")
            .filter { it.isNotBlank() }

        moneySetupLine.text = when {
            !done -> getString(R.string.money_setup_pending)
            skipped -> getString(R.string.money_setup_skipped)
            cohort.isNotBlank() && goals.isNotEmpty() -> getString(
                R.string.money_setup_local_summary,
                cohortDisplayName(cohort),
                goals.joinToString(", ") { goalDisplayName(it) },
            )
            else -> getString(R.string.money_setup_pending)
        }
    }

    private fun onboardingEntryState(
        prefs: SharedPreferences = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE),
    ): OnboardingEntryState {
        return OnboardingEntryState(
            languageSelected = prefs.getBoolean(AppConstants.Prefs.KEY_LANGUAGE_SELECTED, false),
            consentAccepted = prefs.getBoolean(AppConstants.Prefs.KEY_CONSENT_ACCEPTED, false),
            consentDeferred = prefs.getBoolean(AppConstants.Prefs.KEY_CONSENT_DEFERRED, false),
            moneySetupDone = prefs.getBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, false),
            permissionOnboardingDone = prefs.getBoolean(AppConstants.Prefs.KEY_PERMISSION_ONBOARDING_DONE, false),
        )
    }

    private fun refreshPrimaryActionState(state: OnboardingEntryState = onboardingEntryState()) {
        when (state.homePrimaryActionState()) {
            HomePrimaryActionState.RESUME_SETUP -> {
                startServiceButton.text = getString(R.string.action_resume_setup)
            }

            HomePrimaryActionState.START_MONITORING -> {
                startServiceButton.text = getString(R.string.action_start_monitor)
            }
        }

        val statusText = if (state.nextStep() == OnboardingStep.PERMISSIONS) {
            permissionOnboardingStatusText(permissionOnboardingState())
        } else if (state.nextStep() == OnboardingStep.COMPLETE && isMonitoringActive()) {
            getString(R.string.status_monitoring_active)
        } else {
            when (state.homeStatusState()) {
                HomeStatusState.CHOOSE_LANGUAGE -> getString(R.string.status_onboarding_language)
                HomeStatusState.REVIEW_CONSENT -> getString(R.string.status_onboarding_consent)
                HomeStatusState.SETUP_PAUSED -> getString(R.string.status_onboarding_resume)
                HomeStatusState.CONTINUE_SETUP -> getString(R.string.status_onboarding_continue)
                HomeStatusState.READY -> getString(R.string.status_initial)
            }
        }
        setStatus(statusText)
    }

    private fun handlePendingPermissionSettingsReturn() {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val guidedFlowActive = prefs.getBoolean(AppConstants.Prefs.KEY_GUIDED_PERMISSION_FLOW_ACTIVE, false)
        val pendingStep = pendingPermissionSettingsStep()
        if (!guidedFlowActive || pendingStep == null) {
            return
        }

        clearPendingPermissionSettingsStep()
        val nextOnboardingStep = onboardingEntryState(prefs).nextStep()
        when (pendingStep) {
            PermissionStep.NOTIFICATIONS -> if (nextOnboardingStep != OnboardingStep.PERMISSIONS) return
            PermissionStep.USAGE -> if (nextOnboardingStep != OnboardingStep.PERMISSIONS) return
            PermissionStep.OVERLAY -> if (
                nextOnboardingStep != OnboardingStep.PERMISSIONS &&
                nextOnboardingStep != OnboardingStep.MONEY_SETUP
            ) return
            else -> return
        }

        when (pendingStep) {
            PermissionStep.NOTIFICATIONS -> {
                when (permissionOnboardingState().nextStep()) {
                    PermissionStep.NOTIFICATIONS -> showPermissionSetupDialog(permissionStepOverride = PermissionStep.NOTIFICATIONS)
                    PermissionStep.USAGE -> showPermissionSetupDialog(permissionStepOverride = PermissionStep.USAGE)
                    PermissionStep.OVERLAY -> showPermissionSetupDialog(permissionStepOverride = PermissionStep.OVERLAY)
                    PermissionStep.COMPLETE -> {
                        syncPermissionOnboardingDone(prefs)
                        setGuidedPermissionFlowActive(false)
                        showMoneySetupDialog()
                    }
                    PermissionStep.SMS -> showPermissionSetupDialog(permissionStepOverride = PermissionStep.SMS)
                }
            }

            PermissionStep.USAGE -> {
                if (hasUsageStatsPermission()) {
                    showPermissionSetupDialog(permissionStepOverride = PermissionStep.OVERLAY)
                } else {
                    showPermissionSetupDialog(permissionStepOverride = PermissionStep.USAGE)
                }
            }

            PermissionStep.OVERLAY -> {
                val overlayGranted = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    Settings.canDrawOverlays(this)
                } else {
                    true
                }
                if (overlayGranted) {
                    syncPermissionOnboardingDone(prefs)
                    setGuidedPermissionFlowActive(false)
                    showMoneySetupDialog()
                } else {
                    showPermissionSetupDialog(permissionStepOverride = PermissionStep.OVERLAY)
                }
            }

            else -> Unit
        }
    }

    private fun permissionOnboardingStatusText(state: PermissionOnboardingState): String {
        return if (state.isComplete()) {
            getString(R.string.status_initial)
        } else {
            getString(R.string.status_onboarding_permission, permissionStepLabel(state.nextStep()))
        }
    }

    private fun clearDeferredConsent(
        prefs: SharedPreferences = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE),
    ) {
        if (!prefs.getBoolean(AppConstants.Prefs.KEY_CONSENT_DEFERRED, false)) {
            return
        }
        prefs.edit().putBoolean(AppConstants.Prefs.KEY_CONSENT_DEFERRED, false).apply()
    }

    private fun deferConsent() {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        prefs.edit()
            .putBoolean(AppConstants.Prefs.KEY_CONSENT_ACCEPTED, false)
            .putBoolean(AppConstants.Prefs.KEY_CONSENT_DEFERRED, true)
            .apply()
        setStatus(getString(R.string.status_onboarding_resume))
        refreshPrimaryActionState(onboardingEntryState(prefs))
        toast(getString(R.string.toast_setup_paused))
        sendAppLog("info", "consent_deferred")
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                AppConstants.RequestCodes.POST_NOTIFICATIONS,
            )
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        when (requestCode) {
            AppConstants.RequestCodes.RUNTIME_PERMISSIONS -> {
                val allGranted = grantResults.isNotEmpty() && grantResults.all { it == PackageManager.PERMISSION_GRANTED }
                val guidedFlowActive = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
                    .getBoolean(AppConstants.Prefs.KEY_GUIDED_PERMISSION_FLOW_ACTIVE, false)
                if (allGranted &&
                    guidedFlowActive &&
                    Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
                ) {
                    requestNotificationPermissionIfNeeded()
                } else {
                    refreshPrimaryActionState()
                    if (allGranted && guidedFlowActive) {
                        showPermissionSetupDialog(permissionStepOverride = permissionOnboardingState().nextStep())
                    }
                }
            }

            AppConstants.RequestCodes.POST_NOTIFICATIONS -> {
                refreshPrimaryActionState()
                val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
                val guidedFlowActive = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
                    .getBoolean(AppConstants.Prefs.KEY_GUIDED_PERMISSION_FLOW_ACTIVE, false)
                if (granted && guidedFlowActive) {
                    showPermissionSetupDialog(permissionStepOverride = PermissionStep.NOTIFICATIONS)
                }
            }
        }
    }

    private fun setGuidedPermissionFlowActive(active: Boolean) {
        val editor = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(AppConstants.Prefs.KEY_GUIDED_PERMISSION_FLOW_ACTIVE, active)
        if (!active) {
            editor.remove(AppConstants.Prefs.KEY_PENDING_PERMISSION_SETTINGS_STEP)
        }
        editor.apply()
    }

    private fun markPendingPermissionSettingsStep(step: PermissionStep) {
        getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(AppConstants.Prefs.KEY_PENDING_PERMISSION_SETTINGS_STEP, step.name)
            .apply()
    }

    private fun pendingPermissionSettingsStep(): PermissionStep? {
        val raw = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .getString(AppConstants.Prefs.KEY_PENDING_PERMISSION_SETTINGS_STEP, null)
            ?: return null
        return runCatching { PermissionStep.valueOf(raw) }.getOrNull()
    }

    private fun clearPendingPermissionSettingsStep() {
        getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .remove(AppConstants.Prefs.KEY_PENDING_PERMISSION_SETTINGS_STEP)
            .apply()
    }

    private fun isMonitoringActive(): Boolean {
        return getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .getBoolean(AppConstants.Prefs.KEY_MONITORING_ACTIVE, false)
    }

    private fun setMonitoringActive(active: Boolean) {
        getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(AppConstants.Prefs.KEY_MONITORING_ACTIVE, active)
            .apply()
    }

    private fun toast(text: String) {
        Toast.makeText(this, text, Toast.LENGTH_SHORT).show()
    }

    private fun sendAppLog(level: String, message: String) {
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                LiteracyRepository.submitAppLog(
                    context = this@MainActivity,
                    participantId = participantId,
                    level = level,
                    message = message,
                    language = currentLangCode(),
                )
            }
        }
    }

    private fun applySavedLanguage() {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val lang = prefs.getString(AppConstants.Prefs.KEY_APP_LANGUAGE, AppConstants.Locale.DEFAULT_LANGUAGE)
            ?: AppConstants.Locale.DEFAULT_LANGUAGE
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(lang))
    }

    private fun currentLangCode(): String {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        return prefs.getString(AppConstants.Prefs.KEY_APP_LANGUAGE, AppConstants.Locale.DEFAULT_LANGUAGE)
            ?: AppConstants.Locale.DEFAULT_LANGUAGE
    }
}
