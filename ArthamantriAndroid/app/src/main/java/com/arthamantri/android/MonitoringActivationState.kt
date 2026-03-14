package com.arthamantri.android

internal enum class MonitoringStartBlocker {
    NONE,
    ONBOARDING,
    SMS,
    USAGE,
    OVERLAY,
    NOTIFICATIONS,
}

internal data class MonitoringActivationState(
    val onboardingStep: OnboardingStep,
    val permissionState: PermissionOnboardingState,
) {
    fun blocker(): MonitoringStartBlocker {
        return when {
            onboardingStep != OnboardingStep.COMPLETE -> MonitoringStartBlocker.ONBOARDING
            !permissionState.smsGranted -> MonitoringStartBlocker.SMS
            !permissionState.usageGranted -> MonitoringStartBlocker.USAGE
            !permissionState.overlayGranted -> MonitoringStartBlocker.OVERLAY
            !permissionState.notificationsGranted -> MonitoringStartBlocker.NOTIFICATIONS
            else -> MonitoringStartBlocker.NONE
        }
    }

    fun canStart(): Boolean = blocker() == MonitoringStartBlocker.NONE
}
