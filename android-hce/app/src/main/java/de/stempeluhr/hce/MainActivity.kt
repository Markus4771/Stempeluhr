package de.stempeluhr.hce

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var info: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        handlePairingIntent(intent)
        refreshStatus()
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent != null) {
            setIntent(intent)
            handlePairingIntent(intent)
            refreshStatus()
        }
    }

    private fun buildUi() {
        val title = TextView(this).apply { text = "Stempeluhr NFC v2"; textSize = 28f }
        info = TextView(this)
        val clear = Button(this).apply { text = "Kopplung entfernen" }
        clear.setOnClickListener {
            getSharedPreferences("stempeluhr_mobile", MODE_PRIVATE).edit().clear().apply()
            refreshStatus()
        }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 70, 40, 40)
            addView(title)
            addView(info)
            addView(clear)
        }
        setContentView(root)
    }

    private fun handlePairingIntent(intent: Intent) {
        val uri = intent.data ?: return
        if (uri.scheme != "stempeluhr" || uri.host != "pair") return
        val credentialId = uri.getQueryParameter("credential_id")?.trim().orEmpty()
        val deviceToken = uri.getQueryParameter("device_token")?.trim().orEmpty()
        if (credentialId.toLongOrNull() == null || deviceToken.length < 32) {
            info.text = "Pairing-Daten sind ungültig. Bitte einen neuen QR-Code erzeugen."
            return
        }
        getSharedPreferences("stempeluhr_mobile", MODE_PRIVATE).edit()
            .putString("credential_id", credentialId)
            .putString("device_token", deviceToken)
            .apply()
        info.text = "Smartphone wurde automatisch gekoppelt und ist für NFC HCE v2 bereit."
        setIntent(Intent(this, MainActivity::class.java))
    }

    private fun refreshStatus() {
        val prefs = getSharedPreferences("stempeluhr_mobile", MODE_PRIVATE)
        info.text = if (prefs.contains("device_token") && prefs.contains("credential_id")) {
            "Smartphone ist gekoppelt und HCE v2 bereit."
        } else {
            "Noch nicht gekoppelt. Pairing-QR-Code in der Stempeluhr öffnen oder scannen."
        }
    }
}
