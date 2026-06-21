package com.finsaathi.android

internal enum class PermissionStep {
    SMS,
    USAGE,
    OVERLAY,
    NOTIFICATIONS,
    COMPLETE,
}

internal data class PermissionOnboardingState(
    val smsGranted: Boolean,
    val usageGranted: Boolean,
    val overlayGranted: Boolean,
    val notificationsGranted: Boolean,
) {
    fun nextStep(): PermissionStep {
        return when {
            !smsGranted -> PermissionStep.SMS
            !notificationsGranted -> PermissionStep.NOTIFICATIONS
            !usageGranted -> PermissionStep.USAGE
            !overlayGranted -> PermissionStep.OVERLAY
            else -> PermissionStep.COMPLETE
        }
    }

    fun isComplete(): Boolean = nextStep() == PermissionStep.COMPLETE

    fun completedCount(): Int {
        return listOf(smsGranted, usageGranted, overlayGranted, notificationsGranted).count { it }
    }

    fun totalCount(): Int = 4

    fun remainingSteps(): List<PermissionStep> {
        return buildList {
            if (!smsGranted) add(PermissionStep.SMS)
            if (!notificationsGranted) add(PermissionStep.NOTIFICATIONS)
            if (!usageGranted) add(PermissionStep.USAGE)
            if (!overlayGranted) add(PermissionStep.OVERLAY)
        }
    }

    fun shouldAutoResume(guidedFlowActive: Boolean): Boolean {
        return guidedFlowActive && !isComplete()
    }

    fun shouldStopGuidedFlow(guidedFlowActive: Boolean): Boolean {
        return guidedFlowActive && isComplete()
    }
}

internal fun PermissionStep.isGrantedIn(state: PermissionOnboardingState): Boolean {
    return when (this) {
        PermissionStep.SMS -> state.smsGranted
        PermissionStep.NOTIFICATIONS -> state.notificationsGranted
        PermissionStep.USAGE -> state.usageGranted
        PermissionStep.OVERLAY -> state.overlayGranted
        PermissionStep.COMPLETE -> state.isComplete()
    }
}

internal fun PermissionStep.returnLogMessage(state: PermissionOnboardingState): String? {
    if (this == PermissionStep.COMPLETE) {
        return null
    }
    val outcome = if (isGrantedIn(state)) "granted" else "denied"
    return "permission_step_${name.lowercase()}_$outcome"
}
