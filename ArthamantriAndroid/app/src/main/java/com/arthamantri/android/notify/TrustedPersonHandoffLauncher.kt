package com.arthamantri.android.notify

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import com.arthamantri.android.R

object TrustedPersonHandoffLauncher {
    fun launch(
        context: Context,
        title: String,
        body: String,
        nextSafeAction: String,
    ): Boolean {
        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, context.getString(R.string.alert_trusted_person_subject))
            putExtra(
                Intent.EXTRA_TEXT,
                buildHandoffMessage(
                    context = context,
                    title = title,
                    body = body,
                    nextSafeAction = nextSafeAction,
                ),
            )
        }

        if (!canResolve(context, shareIntent)) {
            return false
        }

        val chooserIntent = Intent.createChooser(
            shareIntent,
            context.getString(R.string.alert_trusted_person_chooser_title),
        ).apply {
            if (context !is Activity) {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        }

        return runCatching {
            context.startActivity(chooserIntent)
            true
        }.getOrElse { false }
    }

    private fun buildHandoffMessage(
        context: Context,
        title: String,
        body: String,
        nextSafeAction: String,
    ): String {
        val lines = mutableListOf(
            context.getString(R.string.alert_trusted_person_intro),
            context.getString(R.string.alert_trusted_person_title_line, title),
            body.trim(),
        )

        if (nextSafeAction.isNotBlank()) {
            lines += context.getString(R.string.alert_trusted_person_next_line, nextSafeAction.trim())
        }

        lines += context.getString(R.string.alert_trusted_person_request_line)
        lines += context.getString(R.string.alert_trusted_person_safety_line)
        return lines.joinToString("\n\n")
    }

    private fun canResolve(context: Context, intent: Intent): Boolean {
        val packageManager = context.packageManager
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.queryIntentActivities(
                intent,
                PackageManager.ResolveInfoFlags.of(PackageManager.MATCH_DEFAULT_ONLY.toLong()),
            ).isNotEmpty()
        } else {
            @Suppress("DEPRECATION")
            packageManager.queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY).isNotEmpty()
        }
    }
}
