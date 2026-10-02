package de.stempeluhr.hce

import android.nfc.cardemulation.HostApduService
import android.os.Bundle
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

class StempeluhrHostApduService : HostApduService() {
    private val aid=byteArrayOf(0xF0.toByte(),0x53,0x54,0x45,0x4D,0x50,0x45,0x4C,0x01)
    private val ok=byteArrayOf(0x90.toByte(),0x00)
    private val notFound=byteArrayOf(0x6A,0x82.toByte())
    private fun hex(data:ByteArray)=data.joinToString(""){"%02x".format(it)}
    private fun hmac(key:ByteArray,data:ByteArray):ByteArray { val mac=Mac.getInstance("HmacSHA256");mac.init(SecretKeySpec(key,"HmacSHA256"));return mac.doFinal(data) }
    private fun hceKey(token:String)=hmac(token.toByteArray(Charsets.UTF_8),"stempeluhr-hce-v2".toByteArray(Charsets.UTF_8))

    override fun processCommandApdu(commandApdu:ByteArray?,extras:Bundle?):ByteArray {
        val command=commandApdu?:return notFound
        if(command.size>=6 && command[1]==0xA4.toByte() && command[2]==0x04.toByte()){
            val length=command[4].toInt() and 255
            if(command.size<5+length || !command.copyOfRange(5,5+length).contentEquals(aid))return notFound
            return "STEMPELUHR2".toByteArray()+ok
        }
        if(command.size>=5 && command[0]==0x80.toByte() && command[1]==0x10.toByte()){
            val length=command[4].toInt() and 255
            if(length!=32 || command.size<5+length)return notFound
            val store=SecurePairingStore(this)
            val token=store.token()
            val credentialId=store.credentialId()
            if(token.isEmpty()||credentialId.isEmpty())return notFound
            val challenge=command.copyOfRange(5,5+length)
            val proof=hmac(hceKey(token),challenge)
            return "PROOF:$credentialId:${hex(proof)}".toByteArray()+ok
        }
        return notFound
    }
    override fun onDeactivated(reason:Int)=Unit
}
