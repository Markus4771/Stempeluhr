package de.stempeluhr.hce

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("stempeluhr_mobile", MODE_PRIVATE)
        val title = TextView(this).apply { text = "Stempeluhr NFC"; textSize = 28f }
        val info = TextView(this).apply { text = if (prefs.contains("device_token")) "Smartphone ist gekoppelt." else "Geräte-Token aus dem Pairing eintragen." }
        val token = EditText(this).apply { hint = "Geräte-Token"; setSingleLine(false) }
        val save = Button(this).apply { text = "Token sicher lokal speichern" }
        val clear = Button(this).apply { text = "Kopplung entfernen" }
        save.setOnClickListener {
            val value = token.text.toString().trim()
            if (value.isNotEmpty()) { prefs.edit().putString("device_token", value).apply(); token.text.clear(); info.text = "Smartphone ist gekoppelt und für NFC bereit." }
        }
        clear.setOnClickListener { prefs.edit().remove("device_token").apply(); info.text = "Kopplung entfernt." }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setPadding(40, 70, 40, 40)
            addView(title); addView(info); addView(token); addView(save); addView(clear)
        }
        setContentView(root)
    }
}
