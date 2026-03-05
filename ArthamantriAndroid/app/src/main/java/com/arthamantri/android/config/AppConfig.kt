package com.arthamantri.android.config

import android.content.Context
import com.arthamantri.android.BuildConfig
import com.arthamantri.android.core.AppConstants

object AppConfig {
    fun getBaseUrl(context: Context): String {
        val prefs = context.getSharedPreferences(AppConstants.Prefs.APP_CONFIG_PREFS, Context.MODE_PRIVATE)
        val saved = prefs.getString(AppConstants.Prefs.KEY_BASE_URL, null)
        val raw = saved ?: BuildConfig.DEFAULT_BASE_URL
        return if (raw.endsWith("/")) raw else "$raw/"
    }

    fun setBaseUrl(context: Context, baseUrl: String) {
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        context.getSharedPreferences(AppConstants.Prefs.APP_CONFIG_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(AppConstants.Prefs.KEY_BASE_URL, normalized)
            .apply()
    }
}
