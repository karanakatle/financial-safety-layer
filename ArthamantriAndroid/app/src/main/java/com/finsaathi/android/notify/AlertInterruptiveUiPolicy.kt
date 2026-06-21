package com.finsaathi.android.notify

internal object AlertInterruptiveUiPolicy {
    fun shouldAttempt(
        allowOverlay: Boolean,
        keyguardLocked: Boolean,
    ): Boolean {
        return allowOverlay && !keyguardLocked
    }
}
