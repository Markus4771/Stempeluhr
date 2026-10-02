package de.stempeluhr.hce

import android.app.Activity
import android.content.Intent
import android.nfc.NfcAdapter
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var pairingStatus: TextView
    private lateinit var nfcStatus: TextView
    private lateinit var securityStatus: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        handlePairingIntent(intent)
        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        if (::pairingStatus.isInitialized) refreshStatus()
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
        pairingStatus = TextView(this)
        nfcStatus = TextView(this)
        securityStatus = TextView(this)
        val nfcSettings = Button(this).apply { text = "NFC-Einstellungen öffnen" }
        nfcSettings.setOnClickListener { startActivity(Intent(Settings.ACTION_NFC_SETTINGS)) }
        val clear = Button(this).apply { text = "Kopplung entfernen" }
        clear.setOnClickListener { SecurePairingStore(this).clear(); refreshStatus() }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 70, 40, 40)
            addView(title)
            addView(pairingStatus)
            addView(nfcStatus)
            addView(securityStatus)
            addView(nfcSettings)
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
            pairingStatus.text = "Pairing-Daten sind ungültig. Bitte einen neuen QR-Code erzeugen."
            return
        }
        try {
            SecurePairingStore(this).save(credentialId, deviceToken)
            pairingStatus.text = "Smartphone wurde gekoppelt."
            setIntent(Intent(this, MainActivity::class.java))
        } catch (_: Exception) {
            pairingStatus.text = "Kopplung konnte nicht sicher gespeichert werden."
        }
    }

    private fun refreshStatus() {
        val store = SecurePairingStore(this)
        pairingStatus.text = if (store.isPaired()) {
            "Pairing: aktiv (Credential ${store.credentialId()})"
        } else {
            "Pairing: nicht eingerichtet"
        }
        val adapter = NfcAdapter.getDefaultAdapter(this)
        nfcStatus.text = when {
            adapter == null -> "NFC: auf diesem Gerät nicht verfügbar"
            adapter.isEnabled -> "NFC: eingeschaltet, HCE bereit"
            else -> "NFC: ausgeschaltet"
        }
        securityStatus.text = if (store.isPaired()) {
            "Sicherheit: Geräte-Token AES-GCM verschlüsselt; Schlüssel im Android Keystore. Token wird nicht per NFC übertragen."
        } else {
            "Sicherheit: noch keine Kopplungsdaten gespeichert."
        }
    }
}
