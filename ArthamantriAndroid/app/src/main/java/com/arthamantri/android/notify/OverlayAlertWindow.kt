package com.arthamantri.android.notify

import android.content.Context
import android.graphics.PixelFormat
import android.os.Build
import android.provider.Settings
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.TextView
import com.arthamantri.android.R

object OverlayAlertWindow {
    private var overlayView: View? = null

    fun show(context: Context, title: String, message: String): Boolean {
        if (!canShowOverlay(context)) {
            return false
        }

        val appContext = context.applicationContext
        val wm = appContext.getSystemService(Context.WINDOW_SERVICE) as WindowManager

        if (overlayView != null) {
            updateContent(title, message)
            return true
        }

        val view = LayoutInflater.from(appContext).inflate(R.layout.view_overlay_alert, null, false)
        view.findViewById<TextView>(R.id.overlayAlertTitle).text = title
        view.findViewById<TextView>(R.id.overlayAlertMessage).text = message
        view.findViewById<Button>(R.id.overlayDismissBtn).setOnClickListener { dismiss(appContext) }

        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            type,
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.CENTER
        }

        wm.addView(view, params)
        overlayView = view
        return true
    }

    fun dismiss(context: Context) {
        val view = overlayView ?: return
        val appContext = context.applicationContext
        val wm = appContext.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        runCatching { wm.removeView(view) }
        overlayView = null
    }

    private fun updateContent(title: String, message: String) {
        val view = overlayView ?: return
        view.findViewById<TextView>(R.id.overlayAlertTitle).text = title
        view.findViewById<TextView>(R.id.overlayAlertMessage).text = message
    }

    private fun canShowOverlay(context: Context): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(context)
    }
}
