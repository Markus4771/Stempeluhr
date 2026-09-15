package de.stempeluhr.hce

import android.content.Context
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties

class SecurePairingStore(private val context: Context) {
    companion object {
        private const val KEY_ALIAS = "stempeluhr_hce_pairing_v2"
        private const val PREFS = "stempeluhr_mobile"
        private const val TOKEN_CT = "device_token_ciphertext"
        private const val TOKEN_IV = "device_token_iv"
        private const val CREDENTIAL = "credential_id"
    }

    private fun keyStore(): KeyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    private fun key(): SecretKey {
        val store = keyStore()
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
    }

    fun save(credentialId: String, token: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val ciphertext = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(CREDENTIAL, credentialId)
            .putString(TOKEN_CT, Base64.encodeToString(ciphertext, Base64.NO_WRAP))
            .putString(TOKEN_IV, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .remove("device_token")
            .apply()
    }

    fun credentialId(): String = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        .getString(CREDENTIAL, "")?.trim().orEmpty()

    fun token(): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val ciphertext = prefs.getString(TOKEN_CT, null) ?: return ""
        val iv = prefs.getString(TOKEN_IV, null) ?: return ""
        return try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
            String(cipher.doFinal(Base64.decode(ciphertext, Base64.NO_WRAP)), Charsets.UTF_8)
        } catch (_: Exception) { "" }
    }

    fun isPaired(): Boolean = credentialId().toLongOrNull() != null && token().isNotEmpty()

    fun clear() {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
        try { keyStore().deleteEntry(KEY_ALIAS) } catch (_: Exception) {}
    }
}
