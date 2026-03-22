package com.arthamantri.android.usage

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri

object UpiPackages {
    // Curated known UPI-capable apps. Easy to extend.
    private val knownUpiApps = mapOf(
        "com.phonepe.app" to "PhonePe",
        "com.google.android.apps.nbu.paisa.user" to "Google Pay",
        "net.one97.paytm" to "Paytm",
        "in.org.npci.upiapp" to "BHIM",
        "com.dreamplug.androidapp" to "CRED",
        "in.amazon.mShop.android.shopping" to "Amazon",
        "com.mobikwik_new" to "MobiKwik",
        "in.swiggy.android" to "Swiggy",
        "com.freecharge.android" to "Freecharge",
    )

    private val discoveredUpiPackages = mutableSetOf<String>()
    private var lastDiscoveryAtMs: Long = 0L

    fun isUpiPackage(context: Context, packageName: String): Boolean {
        if (knownUpiApps.containsKey(packageName)) {
            return true
        }
        ensureDiscovered(context)
        return discoveredUpiPackages.contains(packageName)
    }

    fun displayName(context: Context, packageName: String): String {
        knownUpiApps[packageName]?.let { return it }

        return runCatching {
            val appInfo = context.packageManager.getApplicationInfo(packageName, 0)
            context.packageManager.getApplicationLabel(appInfo).toString()
        }.getOrElse { packageName }
    }

    private fun ensureDiscovered(context: Context) {
        val now = System.currentTimeMillis()
        if (now - lastDiscoveryAtMs < 10 * 60 * 1000L && discoveredUpiPackages.isNotEmpty()) {
            return
        }

        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("upi://pay"))
        val resolved = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            val flags = PackageManager.ResolveInfoFlags.of(PackageManager.MATCH_DEFAULT_ONLY.toLong())
            context.packageManager.queryIntentActivities(intent, flags)
        } else {
            val flags = PackageManager.MATCH_DEFAULT_ONLY
            @Suppress("DEPRECATION")
            context.packageManager.queryIntentActivities(intent, flags)
        }

        discoveredUpiPackages.clear()
        discoveredUpiPackages.addAll(resolved.mapNotNull { it.activityInfo?.packageName })
        lastDiscoveryAtMs = now
    }
}
