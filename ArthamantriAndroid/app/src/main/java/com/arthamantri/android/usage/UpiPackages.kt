package com.arthamantri.android.usage

object UpiPackages {
    private val upiApps = mapOf(
        "com.phonepe.app" to "PhonePe",
        "com.google.android.apps.nbu.paisa.user" to "Google Pay",
        "net.one97.paytm" to "Paytm",
        "in.org.npci.upiapp" to "BHIM",
    )

    fun isUpiPackage(packageName: String): Boolean = upiApps.containsKey(packageName)

    fun displayName(packageName: String): String = upiApps[packageName] ?: packageName
}
