package de.stempeluhr.hce

import android.nfc.cardemulation.HostApduService
import android.os.Bundle

class StempeluhrHostApduService : HostApduService() {
    private val aid = byteArrayOf(0xF0.toByte(),0x53,0x54,0x45,0x4D,0x50,0x45,0x4C,0x01)
    private val ok = byteArrayOf(0x90.toByte(),0x00)
    private val notFound = byteArrayOf(0x6A,0x82.toByte())

    override fun processCommandApdu(commandApdu: ByteArray?, extras: Bundle?): ByteArray {
        if (commandApdu == null || commandApdu.size < 6) return notFound
        if (commandApdu[1] != 0xA4.toByte()) return notFound
        val length = commandApdu[4].toInt() and 255
        if (commandApdu.size < 5 + length) return notFound
        val selected = commandApdu.copyOfRange(5, 5 + length)
        if (!selected.contentEquals(aid)) return notFound
        val token = getSharedPreferences("stempeluhr_mobile", MODE_PRIVATE)
            .getString("device_token", "")?.trim().orEmpty()
        if (token.isEmpty()) return notFound
        return ("STEMPELUHR1:" + token).toByteArray(Charsets.UTF_8) + ok
    }

    override fun onDeactivated(reason: Int) = Unit
}
