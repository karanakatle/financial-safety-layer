package com.arthamantri.android.notify

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants

class AlertDisplayActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_alert_display)

        val title = intent.getStringExtra(EXTRA_TITLE) ?: getString(R.string.alert_title_default)
        val message = intent.getStringExtra(EXTRA_MESSAGE)
            ?: getString(R.string.alert_body_default)

        findViewById<TextView>(R.id.alertTitle).text = title
        findViewById<TextView>(R.id.alertMessage).text = message

        findViewById<Button>(R.id.dismissBtn).setOnClickListener { finish() }
    }

    companion object {
        const val EXTRA_TITLE = AppConstants.IntentExtras.ALERT_TITLE
        const val EXTRA_MESSAGE = AppConstants.IntentExtras.ALERT_MESSAGE
    }
}
