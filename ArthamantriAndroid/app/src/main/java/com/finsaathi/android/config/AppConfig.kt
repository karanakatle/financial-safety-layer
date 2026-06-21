package com.finsaathi.android.config

import android.content.Context
import com.finsaathi.android.BuildConfig
import com.finsaathi.android.core.AppConstants

object AppConfig {
    fun getBaseUrl(context: Context): String {
        val prefs = context.getSharedPreferences(AppConstants.Prefs.APP_CONFIG_PREFS, Context.MODE_PRIVATE)
        val saved = prefs.getString(AppConstants.Prefs.KEY_BASE_URL, null)
        val raw = saved ?: BuildConfig.DEFAULT_BASE_URL
        return normalizeBaseUrl(raw)
    }

    fun setBaseUrl(context: Context, baseUrl: String) {
        context.getSharedPreferences(AppConstants.Prefs.APP_CONFIG_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(AppConstants.Prefs.KEY_BASE_URL, normalizeBaseUrl(baseUrl))
            .apply()
    }

    private fun normalizeBaseUrl(baseUrl: String): String =
        if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
}
