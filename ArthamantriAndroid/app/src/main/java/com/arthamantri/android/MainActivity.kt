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

    private val participantId: String by lazy {
        Secure.getString(contentResolver, Secure.ANDROID_ID) ?: AppConstants.Domain.UNKNOWN_PARTICIPANT_ID
    }

    private lateinit var drawerLayout: DrawerLayout
    private lateinit var navigationView: NavigationView
    private lateinit var statusLine: TextView
    private lateinit var moneySetupLine: TextView
    private lateinit var pilotBanner: TextView
    private lateinit var languageChip: TextView
    private lateinit var summaryCard: View
    private lateinit var monitorCard: View
    private lateinit var infoCard: View
    private var accessItemsExpanded = false
    private var currentHelpDialog: AlertDialog? = null
    private var helpHeadingView: TextView? = null
    private var helpSubtitleView: TextView? = null
    private var helpStepsView: TextView? = null
    private var helpLanguageLabelView: TextView? = null
    private var helpLanguageSpinner: Spinner? = null
    private var helpMoneySetupButton: Button? = null
    private var helpFacilitatorPackButton: Button? = null

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
        val startServiceBtn = findViewById<Button>(R.id.startServiceBtn)
        val stopServiceBtn = findViewById<Button>(R.id.stopServiceBtn)
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
                    openNotificationAccess()
                    true
                }

                R.id.nav_access_overlay -> {
                    openOverlaySettings()
                    true
                }

                R.id.nav_access_usage -> {
                    openUsageSettings()
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

        startServiceBtn.setOnClickListener {
            startMonitoringWithChecks()
        }

        stopServiceBtn.setOnClickListener {
            stopService(Intent(this, AppUsageForegroundService::class.java))
            setStatus(getString(R.string.action_stop_monitor))
            toast(getString(R.string.toast_monitor_stopped))
            sendAppLog("info", "monitor_stopped")
        }

        loadPilotMeta()
        loadEssentialGoalSummary()
        animateDashboardCards()
        continueOnboardingFlow()
        maybeRestoreHelpDialogAfterLanguageSwitch()

        if (shouldRestoreDrawerState) {
            drawerLayout.post { drawerLayout.openDrawer(GravityCompat.START) }
        }
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
        updateLanguageChip()
    }

    private fun continueOnboardingFlow() {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)

        if (!prefs.getBoolean(AppConstants.Prefs.KEY_LANGUAGE_SELECTED, false)) {
            showLanguageSelectionDialog(force = false)
            return
        }

        if (!prefs.getBoolean(AppConstants.Prefs.KEY_CONSENT_ACCEPTED, false)) {
            showConsentDialog()
            return
        }

        if (!prefs.getBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, false)) {
            showMoneySetupDialog()
            return
        }

        if (!prefs.getBoolean(AppConstants.Prefs.KEY_PERMISSION_ONBOARDING_DONE, false)) {
            showPermissionSetupDialog()
            return
        }

        setStatus(getString(R.string.status_initial))
        loadEssentialGoalSummary()
    }

    private fun showLanguageSelectionDialog(force: Boolean) {
        val languageOptions = supportedLanguages()
        val options = languageOptions.map { it.displayName }
        val selectedCode = currentLangCode()
        val selectedIndex = languageOptions.indexOfFirst { it.code == selectedCode }.takeIf { it >= 0 } ?: 0
        val spinner = Spinner(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            )
            adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_spinner_item,
                options,
            ).also { a -> a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
            setSelection(selectedIndex)
        }
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 8, 48, 0)
            addView(spinner)
        }

        val dialog = AlertDialog.Builder(this)
            .setTitle(getString(R.string.dialog_language_title))
            .setMessage(getString(R.string.dialog_language_message))
            .setView(container)
            .setCancelable(false)
            .setPositiveButton(getString(R.string.perm_continue)) { _, _ ->
                val langCode = languageOptions.getOrNull(spinner.selectedItemPosition)?.code
                    ?: AppConstants.Locale.DEFAULT_LANGUAGE
                applyLanguage(langCode, markSelected = true)
            }
            .setNegativeButton(if (force) getString(R.string.help_close) else getString(R.string.consent_exit)) { _, _ ->
                if (!force) finish()
            }
            .create()
        dialog.setCanceledOnTouchOutside(false)
        dialog.show()
    }

    private fun showConsentDialog(allowExit: Boolean = true) {
        val dialog = buildInfoBoxDialog(
            title = getString(R.string.dialog_consent_title),
            subtitle = getString(R.string.dialog_consent_subtitle),
            body = buildBulletedDialogMessage(
                bullets = listOf(
                    getString(R.string.dialog_consent_bullet_1),
                    getString(R.string.dialog_consent_bullet_2),
                    getString(R.string.dialog_consent_bullet_3),
                ),
            ),
            positiveLabel = getString(R.string.consent_accept),
            negativeLabel = if (allowExit) getString(R.string.consent_exit) else getString(R.string.help_close),
            cancelable = false,
            onPositive = {
                val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
                prefs.edit().putBoolean(AppConstants.Prefs.KEY_CONSENT_ACCEPTED, true).apply()
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
            },
            onNegative = { dialogInterface ->
                if (allowExit) finish() else dialogInterface.dismiss()
            }
        )
        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
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

        val dialog = AlertDialog.Builder(this)
            .setTitle(getString(R.string.dialog_money_setup_title))
            .setMessage(getString(R.string.dialog_money_setup_message))
            .setView(contentView)
            .setCancelable(false)
            .setPositiveButton(getString(R.string.money_setup_save_continue), null)
            .setNegativeButton(getString(R.string.money_setup_skip), null)
            .create()
        dialog.setCanceledOnTouchOutside(false)

        dialog.setOnShowListener {
            val saveButton = dialog.getButton(AlertDialog.BUTTON_POSITIVE)
            val skipButton = dialog.getButton(AlertDialog.BUTTON_NEGATIVE)
            val setButtonsEnabled = { enabled: Boolean ->
                saveButton.isEnabled = enabled
                skipButton.isEnabled = enabled
            }

            saveButton.setOnClickListener {
                setButtonsEnabled(false)
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

            skipButton.setOnClickListener {
                setButtonsEnabled(false)
                persistMoneySetup(
                    cohort = "daily_cashflow_worker",
                    goals = emptyList(),
                    setupSkipped = true,
                    dialog = dialog,
                )
            }
        }
        dialog.show()
    }

    private fun showFacilitatorSetupPackDialog() {
        val contentView = LayoutInflater.from(this).inflate(R.layout.dialog_facilitator_pack, null)
        val languageStatus = contentView.findViewById<TextView>(R.id.facilitatorStepLanguageStatus)
        val consentStatus = contentView.findViewById<TextView>(R.id.facilitatorStepConsentStatus)
        val moneySetupStatus = contentView.findViewById<TextView>(R.id.facilitatorStepMoneySetupStatus)
        val permissionsStatus = contentView.findViewById<TextView>(R.id.facilitatorStepPermissionsStatus)
        val monitoringStatus = contentView.findViewById<TextView>(R.id.facilitatorStepMonitoringStatus)
        val languageButton = contentView.findViewById<Button>(R.id.facilitatorLanguageButton)
        val consentButton = contentView.findViewById<Button>(R.id.facilitatorConsentButton)
        val moneySetupButton = contentView.findViewById<Button>(R.id.facilitatorMoneySetupButton)
        val permissionsButton = contentView.findViewById<Button>(R.id.facilitatorPermissionsButton)
        val startMonitoringButton = contentView.findViewById<Button>(R.id.facilitatorStartMonitoringButton)
        val refreshButton = contentView.findViewById<Button>(R.id.facilitatorRefreshButton)
        val closeButton = contentView.findViewById<Button>(R.id.facilitatorCloseButton)

        val dialog = AlertDialog.Builder(this)
            .setView(contentView)
            .create()

        val refresh = {
            refreshFacilitatorStatus(
                languageStatus = languageStatus,
                consentStatus = consentStatus,
                moneySetupStatus = moneySetupStatus,
                permissionsStatus = permissionsStatus,
                monitoringStatus = monitoringStatus,
            )
        }

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
    }

    private fun refreshFacilitatorStatus(
        languageStatus: TextView,
        consentStatus: TextView,
        moneySetupStatus: TextView,
        permissionsStatus: TextView,
        monitoringStatus: TextView,
    ) {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)

        val languageDone = prefs.getBoolean(AppConstants.Prefs.KEY_LANGUAGE_SELECTED, false)
        val consentDone = prefs.getBoolean(AppConstants.Prefs.KEY_CONSENT_ACCEPTED, false)
        val moneySetupDone = prefs.getBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, false)
        val smsRuntimeDone = hasSmsRuntimePermissions()
        val usageDone = hasUsageStatsPermission()
        val overlayDone = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) Settings.canDrawOverlays(this) else true
        val notificationDone = hasAppNotificationsEnabled()
        val monitoringReady = smsRuntimeDone && usageDone && overlayDone

        languageStatus.text = facilitatorStatusText(languageDone)
        consentStatus.text = facilitatorStatusText(consentDone)
        moneySetupStatus.text = facilitatorStatusText(moneySetupDone)
        permissionsStatus.text = getString(
            R.string.facilitator_status_permissions,
            yesNoShort(smsRuntimeDone),
            yesNoShort(usageDone),
            yesNoShort(overlayDone),
            yesNoShort(notificationDone),
        )
        monitoringStatus.text = getString(R.string.facilitator_status_monitoring_ready, yesNoShort(monitoringReady))
    }

    private fun facilitatorStatusText(done: Boolean): String {
        return if (done) getString(R.string.facilitator_status_done) else getString(R.string.facilitator_status_pending)
    }

    private fun yesNoShort(done: Boolean): String {
        return if (done) getString(R.string.icon_check) else getString(R.string.icon_close)
    }

    private fun hasSmsRuntimePermissions(): Boolean {
        val smsReceive = ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED
        val smsRead = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED
        val notifications = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
        return smsReceive && smsRead && notifications
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
                val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
                prefs.edit().putBoolean(AppConstants.Prefs.KEY_MONEY_SETUP_DONE, true).apply()

                response.onSuccess { saved ->
                    updateMoneySetupSummary(saved.profile, saved.envelope)
                    if (!setupSkipped) {
                        toast(getString(R.string.toast_money_setup_saved))
                    }
                    sendAppLog("info", "money_setup_saved:$cohort:${goals.joinToString("|")}")
                }.onFailure { error ->
                    if (setupSkipped) {
                        moneySetupLine.text = getString(R.string.money_setup_skipped)
                    } else {
                        moneySetupLine.text = getString(R.string.money_setup_pending)
                    }
                    toast(getString(R.string.toast_money_setup_failed))
                    sendAppLog("error", "money_setup_save_failed:${error.message}")
                }

                dialog.dismiss()
                continueOnboardingFlow()
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
                    if (moneySetupLine.text.isNullOrBlank()) {
                        moneySetupLine.text = getString(R.string.money_setup_pending)
                    }
                }
            }
        }
    }

    private fun updateMoneySetupSummary(
        profile: EssentialGoalProfileDto?,
        envelope: EssentialGoalEnvelopeDto?,
    ) {
        if (profile == null) {
            moneySetupLine.text = getString(R.string.money_setup_pending)
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

    private fun showPermissionSetupDialog() {
        val dialog = buildInfoBoxDialog(
            title = getString(R.string.dialog_perm_title),
            subtitle = getString(R.string.dialog_perm_subtitle),
            body = buildBulletedDialogMessage(
                intro = getString(R.string.dialog_perm_intro),
                bullets = listOf(
                    getString(R.string.dialog_perm_bullet_sms),
                    getString(R.string.dialog_perm_bullet_usage),
                    getString(R.string.dialog_perm_bullet_overlay),
                ),
                outro = getString(R.string.dialog_perm_followup),
            ),
            positiveLabel = getString(R.string.perm_continue),
            negativeLabel = null,
            cancelable = false,
            onPositive = {
                requestRuntimePermissions()
                openUsageSettings()
                openOverlaySettings()

                val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
                prefs.edit().putBoolean(AppConstants.Prefs.KEY_PERMISSION_ONBOARDING_DONE, true).apply()
                sendAppLog("info", "permission_onboarding_prompted")

                startMonitoringWithChecks()
            },
        )
        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
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

        if (negativeButton.visibility == View.GONE) {
            actionsView.gravity = android.view.Gravity.END
        }

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
        markRestoreDrawerOnReturn()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                AppConstants.RequestCodes.POST_NOTIFICATIONS,
            )
        }

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
    }

    private fun openOverlaySettings() {
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
        if (!hasUsageStatsPermission()) {
            setStatus(getString(R.string.status_usage_missing))
            toast(getString(R.string.toast_usage_missing))
            sendAppLog("warn", "monitor_start_blocked_usage_access")
            return
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            setStatus(getString(R.string.status_overlay_missing))
            toast(getString(R.string.toast_overlay_missing))
            sendAppLog("warn", "monitor_start_without_overlay")
        }

        if (!hasNotificationListenerPermission()) {
            sendAppLog("info", "notification_listener_not_granted")
        }

        try {
            startForegroundService(Intent(this, AppUsageForegroundService::class.java))
            setStatus(getString(R.string.status_monitoring_active))
            toast(getString(R.string.toast_monitor_started))
            sendAppLog("info", "monitor_started")
        } catch (e: Exception) {
            setStatus(getString(R.string.status_monitoring_failed))
            toast(e.message ?: getString(R.string.toast_monitor_failed))
            sendAppLog("error", "monitor_start_error:${e.message}")
        }
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

    private fun showHelpDialog() {
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

        heading.text = getString(R.string.help_title)
        subtitle.text = getString(R.string.help_subtitle)
        helpText.text = helpStepsText()
        languageLabel.text = getString(R.string.help_change_language)
        moneySetupButton.text = getString(R.string.help_edit_money_setup)
        facilitatorPackButton.text = getString(R.string.help_open_facilitator_pack)
        spinner.adapter = ArrayAdapter(
            this@MainActivity,
            android.R.layout.simple_spinner_item,
            options,
        ).also { a -> a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        spinner.setSelection(selectedIndex)

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
                showFacilitatorSetupPackDialog()
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
        helpHeadingView = heading
        helpSubtitleView = subtitle
        helpStepsView = helpText
        helpLanguageLabelView = languageLabel
        helpLanguageSpinner = spinner
        helpMoneySetupButton = moneySetupButton
        helpFacilitatorPackButton = facilitatorPackButton
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

    private fun maybeRestoreHelpDialogAfterLanguageSwitch() {
        val prefs = getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val shouldReopen = prefs.getBoolean(AppConstants.Prefs.KEY_REOPEN_HELP_AFTER_LOCALE_SWITCH, false)
        if (!shouldReopen) {
            return
        }

        prefs.edit().putBoolean(AppConstants.Prefs.KEY_REOPEN_HELP_AFTER_LOCALE_SWITCH, false).apply()
        updateLanguageChip()
        window.decorView.post { showHelpDialog() }
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
        findViewById<Button>(R.id.startServiceBtn).text = getString(R.string.action_start_monitor)
        findViewById<Button>(R.id.stopServiceBtn).text = getString(R.string.action_stop_monitor)
        findViewById<TextView>(R.id.statusLine).text = getString(R.string.status_initial)
        moneySetupLine.text = getString(R.string.money_setup_pending)

        val header = navigationView.getHeaderView(0)
        header.findViewById<TextView>(R.id.navHeaderTitle)?.text = getString(R.string.nav_title)
        header.findViewById<TextView>(R.id.navHeaderSubtitle)?.text = getString(R.string.nav_subtitle)

        applyDrawerMenuState()

        updateLanguageChip()
        loadEssentialGoalSummary()
    }

    private fun refreshHelpDialogTextsInPlace() {
        helpHeadingView?.text = getString(R.string.help_title)
        helpSubtitleView?.text = getString(R.string.help_subtitle)
        helpStepsView?.text = helpStepsText()
        helpLanguageLabelView?.text = getString(R.string.help_change_language)
        helpMoneySetupButton?.text = getString(R.string.help_edit_money_setup)
        helpFacilitatorPackButton?.text = getString(R.string.help_open_facilitator_pack)

        val spinner = helpLanguageSpinner ?: return
        val options = supportedLanguages().map { it.displayName }
        spinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            options,
        ).also { a -> a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        val selectedIndex = supportedLanguages().indexOfFirst { it.code == currentLangCode() }.takeIf { it >= 0 } ?: 0
        spinner.setSelection(selectedIndex)
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

    private fun setStatus(text: String) {
        statusLine.text = text
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
